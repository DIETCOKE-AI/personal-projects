import { ElLoading } from 'element-plus'
import type { LoadingOptions } from 'element-plus/es/components/loading/src/types'

type numMapType = { [key: string]: SpinType }

interface SpinType {
  count: number
  loadingInstance?: {
    close: () => void
  } | null
}

export interface MaskConfig {
  // 是否开启遮罩层
  flag?: boolean
  // 遮罩层的编号
  key?: string
  // 显示文字
  content?: string
  // 超时时间
  timeout?: number
  // Element UI 特有的加载选项
  options?: Omit<LoadingOptions, 'text' | 'fullscreen'>
}

const DEFAULT_PARAM = {
  /**
   * 计数键值对
   */
  numMap: <numMapType>{},
  /**
   * 默认的Key值
   */
  key: 'dc_mask'
}

/**
 * 初始化计数键值对
 * @param key
 */
const init = (key = DEFAULT_PARAM.key) => {
  if (!DEFAULT_PARAM.numMap[key]) {
    DEFAULT_PARAM.numMap[key] = {
      count: 0,
      loadingInstance: null
    }
  }
}

export const mask = {
  /**
   * 显示遮罩层
   * @param config 其他配置
   */
  open: (config?: MaskConfig) => {
    const key = config?.key || DEFAULT_PARAM.key
    init(key)
    
    if (DEFAULT_PARAM.numMap[key].count++ === 0) {
      const options: LoadingOptions = {
        lock: true,
        text: config?.content || '正在加载',
        background: 'rgba(0, 0, 0, 0.7)',
        ...config?.options
      }

      const loadingInstance = ElLoading.service(options)
      DEFAULT_PARAM.numMap[key].loadingInstance = loadingInstance

      // 如果设置了自动超时时间，不需要手动关闭
      if ((config?.timeout || 0) > 0) {
        setTimeout(() => {
          mask.close(key)
        }, config?.timeout)
      }
    }
  },
  
  /**
   * 关闭遮罩层
   * @param key
   * @param num 关闭的数据
   */
  close: (key = DEFAULT_PARAM.key, num = 1) => {
    const spinData = DEFAULT_PARAM.numMap[key]
    if (!spinData) return
    spinData.count -= num
    if (spinData.count <= 0) {
      spinData.count = 0
      // 关闭遮罩层
      if (spinData.loadingInstance) {
        spinData.loadingInstance.close()
        spinData.loadingInstance = null
      }
    }
  }
}