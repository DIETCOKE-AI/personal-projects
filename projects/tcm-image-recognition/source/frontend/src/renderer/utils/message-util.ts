import { ElMessage, ElMessageBox } from 'element-plus'
import type { ElMessageBoxOptions } from 'element-plus/es/components/message-box'

export const messageMethod = {
  /**
   * 消息提示
   * @param content
   * @param duration
   * @param onClose
   */
  info(content: string, duration?: number, onClose?: () => void): void {
    ElMessage({
      message: content,
      type: 'info',
      duration: duration || 3000,
      onClose
    })
  },
  
  /**
   * 错误消息提示
   * @param content
   * @param duration
   * @param onClose
   */
  error(content: string, duration?: number, onClose?: () => void): void {
    ElMessage({
      message: content,
      type: 'error',
      duration: duration || 3000,
      onClose
    })
  },
  
  /**
   * 警告消息提示
   * @param content
   * @param duration
   * @param onClose
   */
  warning(content: string, duration?: number, onClose?: () => void): void {
    ElMessage({
      message: content,
      type: 'warning',
      duration: duration || 3000,
      onClose
    })
  },
  
  /**
   * 成功消息提示
   * @param content
   * @param duration
   * @param onClose
   */
  success(content: string, duration?: number, onClose?: () => void): void {
    ElMessage({
      message: content,
      type: 'success',
      duration: duration || 3000,
      onClose
    })
  },
  
  /**
   * 加载框
   * @param content
   * @param duration
   * @param onClose
   */
  loading(content: string, duration?: number, onClose?: () => void): void {
    ElMessage({
      message: content,
      type: 'info',
      duration: duration || 3000,
      customClass: 'loading-message',
      iconClass: 'el-icon-loading',
      onClose
    })
  }
}

export const confirmMethod = {
  /**
   * 提示弹框
   * @param title
   * @param ok
   * @param cancel
   */
  info(title: string, ok?: () => void, cancel?: () => void, options?: ElMessageBoxOptions) {
    ElMessageBox.confirm(
      title,
      '提示',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'info',
        ...options
      }
    )
      .then(() => {
        if (ok) ok()
      })
      .catch(() => {
        if (cancel) cancel()
      })
  }
}