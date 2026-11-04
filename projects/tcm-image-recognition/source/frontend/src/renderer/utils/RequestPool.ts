/**
 * 任务结构体，封装异步任务及其完成后的处理逻辑
 */
type Task<T> = {
  task: () => Promise<T>; // 任务函数，返回 Promise<T>
  resolve: (value: T) => void; // 成功回调
  reject: (reason?: any) => void; // 失败回调
};

/**
 * 请求池类，控制并发任务执行数量
 */
class RequestPool<T> {
  private maxConcurrency: number; // 最大并发数
  private activeCount: number = 0; // 当前执行中的任务数
  private queue: Task<T>[] = []; // 任务队列，存储等待执行的任务

  constructor(maxConcurrency: number) {
    this.maxConcurrency = maxConcurrency; // 设定最大并发数
  }

  /**
   * 添加任务到请求池，并返回 Promise
   * @param task 需要执行的异步任务
   * @returns 一个 Promise，表示该任务的执行结果
   */
  public add(task: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      // 将任务及其 Promise 控制函数（resolve/reject）加入队列
      this.queue.push({ task, resolve, reject });
      // 尝试执行下一个任务
      this.processNext();
    });
  }

  /**
   * 批量执行所有任务，并发受限制
   * @param tasks 任务数组，每个任务是一个返回 Promise<T> 的函数
   * @returns PromiseSettledResult<T>[] 数组，包含所有任务的最终状态（fulfilled/rejected）
   */
  public async executeAll(
    tasks: (() => Promise<T>)[]
  ): Promise<PromiseSettledResult<T>[]> {
    // 使用 add 方法将所有任务加入请求池，并通过 Promise.allSettled 监听它们的状态
    return Promise.allSettled(tasks.map((task) => this.add(task)));
  }

  /**
   * 处理队列中的下一个任务，如果并发数未超出限制，则启动任务
   */
  private processNext(): void {
    while (this.activeCount < this.maxConcurrency && this.queue.length > 0) {
      // 取出队列中的第一个任务
      const { task, resolve, reject } = this.queue.shift()!;
      this.activeCount++; // 递增正在执行的任务数量

      // 执行任务
      task()
        .then(resolve) // 成功时调用 resolve
        .catch(reject) // 失败时调用 reject
        .finally(() => {
          this.activeCount--; // 任务执行完成，减少并发计数
          this.processNext(); // 递归调用，处理下一个任务
        });
    }
  }
}

// ============ 测试代码 =============

// 创建请求池，最大并发数为 2
const pool = new RequestPool<string>(2);

/**
 * 创建一个模拟异步任务
 * @param id 任务 ID
 * @param delay 任务执行时间（ms）
 * @returns 返回一个 Promise<string> 任务
 */
const createTask = (id: number, delay: number) => () =>
  new Promise<string>((resolve) =>
    setTimeout(() => resolve(`Task ${id} done`), delay)
  );

// 定义任务列表
const tasks = [
  createTask(1, 1000), // 任务 1: 1s
  createTask(2, 500), // 任务 2: 0.5s
  createTask(3, 800), // 任务 3: 0.8s
  createTask(4, 300), // 任务 4: 0.3s
];

// 执行所有任务，并在完成后打印结果
pool.executeAll(tasks).then((results) => {
  results.forEach((result, index) => {
    if (result.status === "fulfilled") {
      console.log(`任务 ${index + 1} 成功:`, result.value);
    } else {
      console.error(`任务 ${index + 1} 失败:`, result.reason);
    }
  });
});
