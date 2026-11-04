import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { app, BrowserWindow } from "electron";

export { start, stop, getReadinessState };

// --- 1. 路径定义 ---
const isPackaged = app.isPackaged;

// Python后端 (tcm_app)
const tcmAppPath = process.env.TCM_BACKEND_EXE || (isPackaged
  ? path.join(path.dirname(app.getAppPath()), "..", "tcm_app", "tcm_app.exe")
  : path.resolve("external", "tcm_app", "tcm_app.exe"));

// Java后端 (ruoyi-admin)
const ruoyiJarPath = process.env.TCM_RUOYI_JAR || (isPackaged
  ? path.join(path.dirname(app.getAppPath()), "..", "ruoyi-admin.jar")
  : path.resolve("external", "ruoyi-admin.jar"));

// --- 2. 信号定义 ---
const tcmReadySignal = "BACKEND_READY_FOR_ELECTRON";
const ruoyiReadySignal = "ruoyi start up successful";

// --- 3. 状态管理 ---
let processes = {
  tcm: null,
  ruoyi: null,
};
let readiness = {
  tcm: false,
  ruoyi: false,
};

// --- 4. 日志记录 ---
const logPath = path.join(app.getPath('userData'), 'main.log');
const log = (message) => {
  const timestamp = new Date().toISOString();
  try {
    fs.appendFileSync(logPath, `[${timestamp}] ${message}\n`, 'utf8');
    console.log(message);
  } catch (err) {
    console.error('Failed to write to log file:', err);
  }
};

/**
 * 向前端发送状态更新
 */
function notifyFrontend() {
  const window = BrowserWindow.getAllWindows()[0];
  if (window) {
    window.webContents.send("backend-readiness-update", readiness);
  }
}

/**
 * 启动两个后端服务
 * @returns {Promise<void>}
 */
function start() {
  return new Promise((resolve, reject) => {
    // 在开发模式下，我们假设Python后端是手动启动的，因此将其状态预设为“就绪”
    if (!isPackaged) {
      readiness.tcm = true;
      log("[BackendService] Development mode: TCM backend readiness is pre-set to true. Please start it manually.");
    }
    
    if (readiness.tcm && readiness.ruoyi) {
      log("[BackendService] Both services are already running and ready.");
      return resolve();
    }

    // 仅在打包后（生产环境）启动TCM Python服务
    if (!processes.tcm && isPackaged) {
      log(`[BackendService] Spawning TCM process from: ${tcmAppPath}`);
      const tcmProcess = spawn(tcmAppPath, [], {
        windowsHide: true,
        //detached: true,
        cwd: path.dirname(tcmAppPath),
      });
      processes.tcm = tcmProcess;
      monitorProcess("tcm", tcmProcess, tcmReadySignal, resolve);
    }

    // 启动RuoYi Java服务
    if (!processes.ruoyi) {
      log(`[BackendService] Spawning RuoYi process from: ${ruoyiJarPath}`);
      const ruoyiProcess = spawn("java", ["-jar", ruoyiJarPath], {
        windowsHide: true,
        //detached: true,
        cwd: path.dirname(ruoyiJarPath),
      });
      processes.ruoyi = ruoyiProcess;
      monitorProcess("ruoyi", ruoyiProcess, ruoyiReadySignal, resolve);
    }
  });
}

/**
 * 监听指定进程的输出和事件
 */
function monitorProcess(name, process, readySignal, resolve) {
  let buffer = '';
  const onData = (data) => {
    buffer += data.toString();
    let eolIndex;
    // 处理所有完整的行
    while ((eolIndex = buffer.indexOf('\n')) >= 0) {
      const line = buffer.substring(0, eolIndex).trim();
      buffer = buffer.substring(eolIndex + 1);

      if (line) {
        log(`[Backend:${name}] ${line}`);
        // 在完整的行上检查信号
        if (!readiness[name] && line.includes(readySignal)) {
          readiness[name] = true;
          log(`[DIAGNOSTIC] ${name} service is ready. Sending notification.`); // <-- 新增的诊断日志
          notifyFrontend();
          if (readiness.tcm && readiness.ruoyi) {
            log("[BackendService] All services are ready!");
            resolve();
          }
        }
      }
    }
  };
  
  process.stdout.on("data", onData);
  process.stderr.on("data", onData);

  process.on("error", (err) => {
    log(`[BackendService] Failed to start ${name} process: ${err}`);
  });

  process.on("close", (code) => {
    log(`[BackendService] ${name} process exited with code: ${code}`);
    processes[name] = null;
    readiness[name] = false;
    notifyFrontend();
  });
}

/**
 * 停止所有后端服务
 */
function stop() {
  log("[BackendService] Attempting to stop all backend services...");
  for (const name in processes) {
    const process = processes[name];
    if (process && process.pid) {
      log(`[BackendService] Killing ${name} process with PID: ${process.pid}`);
      spawn("taskkill", ["/pid", process.pid, "/f", "/t"]);
      processes[name] = null;
      readiness[name] = false;
    }
  }
}

/**
 * 获取当前服务的就绪状态
 * @returns {{tcm: boolean, ruoyi: boolean}}
 */
function getReadinessState() {
  return readiness;
}
