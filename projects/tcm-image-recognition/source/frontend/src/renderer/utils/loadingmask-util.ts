import { ElDialog, ElProgress, ElButton, ElMessage } from 'element-plus'
import { h, render, type VNode } from 'vue'
/**
 * 药材识别进度显示弹窗 对所有的loadingmask进行封装
 * @param {ProgressDialogConfig} config - 配置对象
 * @returns {Promise<void>} - 返回一个Promise对象，用于控制进度条的显示和隐藏
 */


interface ProgressDialogInstance {
  count: number
  container?: HTMLElement | null
  progressInterval?: number
  currentProgress: number
  targetProgress: number
  error?: {
    message: string
    retry?: () => Promise<void>
  }
}

interface ProgressDialogConfig {
  /** Dialog 的唯一标识key */
  key?: string
  /** Dialog 标题 */
  title?: string
  /** 显示内容 */
  content?: string
  /** Dialog 宽度 */
  width?: string
  /** 初始进度百分比（0-100） */
  initialProgress?: number
  /** 进度条类型 */
  type?: 'line' | 'circle' | 'dashboard'
  /** 自定义类名 */
  customClass?: string
  /** 进度递增速度（百分比/秒） */
  progressSpeed?: number
  /** 是否显示关闭按钮 */
  showClose?: boolean
  /** 是否可以通过点击模态框关闭 Dialog */
  modalClickClose?: boolean
  /** 是否显示取消按钮 */
  showCancel?: boolean
  /** 取消按钮文本 */
  cancelText?: string
  /** 取消按钮回调 */
  onCancel?: () => void
  /** 错误时是否自动关闭 */
  autoCloseOnError?: boolean
  /** 是否显示重试按钮 */
  showRetry?: boolean
  /** 重试按钮文本 */
  retryText?: string
}

const DEFAULT_CONFIG = {
  key: 'default',
  title: '药材识别',
  content: '正在识别，请稍候...',
  width: '300px',
  initialProgress: 0,
  type: 'circle',
  progressSpeed: 20,
  showClose: false,
  modalClickClose: false,
  showCancel: false,
  cancelText: '取消',
  onCancel: () => {},
  autoCloseOnError: false,
  showRetry: true,
  retryText: '重试'
} as const

class ProgressDialog {
  private instances: Record<string, ProgressDialogInstance> = {}

  private initInstance(key: string): ProgressDialogInstance {
    if (!this.instances[key]) {
      this.instances[key] = { 
        count: 0,
        currentProgress: 0,
        targetProgress: 0
      }
    }
    return this.instances[key]
  }

  private createDialogElement(
    config: any,
    progress: number,
    onClose: () => void,
    error?: { message: string; retry?: () => Promise<void> }
  ): VNode {
    const isErrorState = !!error

    return h(
      ElDialog,
      {
        key: config.key,
        // title: isErrorState?config.title:'',
        modelValue: true,
        width: config.width,
        class: ['progress-dialog', config.customClass, isErrorState ? 'error-state' : ''],
        'show-close': config.showClose,
        closeOnClickModal: config.modalClickClose,
        onClose: onClose
      },
      {
        default: () => [
          h('div', { 
            class: 'progress-content',
            style: { color: isErrorState ? '#f56c6c' : 'inherit' }
          }, isErrorState ? error.message : config.content),
          isErrorState ? h(ElProgress, {
            type: config.type,
            percentage: 100,
            status: 'exception',
            'show-text': true,
            'text-inside': config.type === 'line',
            'stroke-width': config.type === 'line' ? 18 : 9,
            class: 'dialog-progress',
			width:200,
          }) : h(ElProgress, {
            type: config.type,
            percentage: progress,
            status: isErrorState ? 'exception' : undefined,
            'show-text': true,
            'text-inside': config.type === 'line',
            'stroke-width': config.type === 'line' ? 18 : 9,
            class: 'dialog-progress',
			width:200,
          })
        ],
        footer: () => {
          if (isErrorState) {
            return h(
              'div',
              { class: 'dialog-footer' },
              [
                h(ElButton, { onClick: ()=>{this.close(config.key)} }, '关闭'),
                config.showRetry && error.retry && h(
                  ElButton,
                  { 
                    type: 'primary',
                    onClick: async () => {
                      try {
                        await error.retry!()
                        this.clearError(config.key)
                      } catch (err) {
                        this.showError(config.key, err instanceof Error ? err.message : '重试失败')
                      }
                    }
                  },
                  config.retryText
                )
              ]
            )
          }
          return config.showCancel ? h(
            'div',
            { class: 'dialog-footer' },
            [
              h(
                ElButton,
                {
                  onClick: () => {
                    config.onCancel()
                    onClose()
                  }
                },
                config.cancelText
              )
            ]
          ) : null
        }
      }
    )
  }

  private startProgressAnimation(
    instance: ProgressDialogInstance,
    config: Required<ProgressDialogConfig>,
    onClose: () => void
  ): void {
    if (instance.progressInterval) {
      clearInterval(instance.progressInterval)
    }

    const updateInterval = 100 // 更新间隔(ms)
    const progressPerUpdate = (config.progressSpeed * updateInterval) / 1000

    instance.progressInterval = window.setInterval(() => {
      if (instance.error) return // 如果有错误，停止进度更新

      if (instance.currentProgress < instance.targetProgress) {
        instance.currentProgress = Math.min(
          instance.currentProgress + progressPerUpdate,
          instance.targetProgress
        )
        
        if (instance.container) {
          const newDialog = this.createDialogElement(
            config, 
            instance.currentProgress,
            onClose,
            instance.error
          )
          render(newDialog, instance.container)
        }
      }

      if (instance.currentProgress >= 100 && instance.container) {
        this.clearInstance(instance)
        setTimeout(() => this.close(config.key), 500)
      }
    }, updateInterval)
  }

  private clearInstance(instance: ProgressDialogInstance): void {
    if (instance.progressInterval) {
      clearInterval(instance.progressInterval)
      instance.progressInterval = undefined
    }
  }

  public open(config: ProgressDialogConfig = {}): Promise<void> {
    return new Promise((resolve, reject) => {
      const key = config.key || DEFAULT_CONFIG.key
      const mergedConfig: any = {
        ...DEFAULT_CONFIG,
        ...config,
        key,
        onCancel: () => {
          DEFAULT_CONFIG.onCancel()
          config.onCancel?.()
          reject(new Error('用户取消操作'))
          this.close(key)
        }
      }

      const instance = this.initInstance(key)
      instance.currentProgress = mergedConfig.initialProgress
      instance.targetProgress = 99

      if (instance.count++ === 0) {
        const container = document.createElement('div')
        
        const onClose = () => {
			console.log('关闭')
          this.close(key)
		  
          reject(new Error('对话框已关闭'))
        }
        
        const dialogElement = this.createDialogElement(
          mergedConfig, 
          instance.currentProgress,
          onClose,
          instance.error
        )
        
        render(dialogElement, container)
        document.body.appendChild(container)

        instance.container = container
        this.startProgressAnimation(instance, mergedConfig, onClose)
        resolve()
      }
    })
  }

  public close(key: string = DEFAULT_CONFIG.key): void {
    const instance = this.instances[key]
    if (!instance) return

    instance.count = Math.max(0, instance.count - 1)

    if (instance.count <= 0) {
      this.clearInstance(instance)
      
      if (instance.container) {
        render(null, instance.container)
        document.body.removeChild(instance.container)
        instance.container = null
      }
      
      delete this.instances[key]
    }
  }

  public complete(key: string = DEFAULT_CONFIG.key): void {
    const instance = this.instances[key]
    if (!instance) return

    instance.targetProgress = 100
  }

  public showError(key: string, message: string, retry?: () => Promise<void>): void {
    const instance = this.instances[key]
    if (!instance) return

    const config = {
      ...DEFAULT_CONFIG,
      key,
      ...this.getCurrentConfig(key)
    }

    instance.error = { message, retry }
    
    if (instance.container) {
      const onClose = () => {
        if (config.autoCloseOnError) {
          this.close(key)
        }
      }
      
      const newDialog = this.createDialogElement(
        config, 
        instance.currentProgress,
        onClose,
        instance.error
      )
      render(newDialog, instance.container)
    }

    ElMessage.error(message)
  }

  public clearError(key: string): void {
    const instance = this.instances[key]
    if (!instance || !instance.error) return

    delete instance.error
    
    if (instance.container) {
      const config = {
        ...DEFAULT_CONFIG,
        key,
        ...this.getCurrentConfig(key)
      }
      
      const onClose = () => this.close(key)
      const newDialog = this.createDialogElement(
        config, 
        instance.currentProgress,
        onClose
      )
      render(newDialog, instance.container)
    }
  }

  private getCurrentConfig(key: string): Partial<ProgressDialogConfig> {
    // 这里可以扩展为从实例中获取当前配置
    return {}
  }

  public updateContent(key: string, content: string): void {
    const instance = this.instances[key]
    if (!instance?.container) return

    const currentConfig = {
      ...DEFAULT_CONFIG,
      key,
      content,
      initialProgress: instance.currentProgress,
      onCancel: DEFAULT_CONFIG.onCancel,
      ...this.getCurrentConfig(key)
    }

    const onClose = () => this.close(key)
    const newDialog = this.createDialogElement(
      currentConfig, 
      instance.currentProgress,
      onClose,
      instance.error
    )
    render(newDialog, instance.container)
  }

  public updateProgress(key: string, progress: number): void {
    const instance = this.instances[key]
    if (!instance) return

    instance.currentProgress = Math.min(Math.max(progress, 0), 100)
    instance.targetProgress = instance.currentProgress
  }

  public isOpen(key: string = DEFAULT_CONFIG.key): boolean {
    return !!this.instances[key]
  }
}

export const progressDialog = new ProgressDialog()

// 添加样式
const style = document.createElement('style')
style.textContent = `
  .progress-dialog {
    .el-dialog__body {
      padding: 20px;
	      text-align: center;
    }
    
    .progress-content {
      margin-bottom: 20px;
      text-align: center;
      font-size: 16px;
    }
    
    .dialog-progress {
      margin: 0 auto;
    }
    
    .dialog-footer {
      text-align: right;
      padding-top: 10px;
      
      .el-button + .el-button {
        margin-left: 12px;
      }
    }
    
    &.error-state {
      .el-dialog__header {
        .el-dialog__title {
          color: #f56c6c;
        }
      }
    }
  }
`
document.head.appendChild(style)