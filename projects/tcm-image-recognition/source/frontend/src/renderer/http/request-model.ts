import axios, { type AxiosRequestConfig, type Method } from 'axios'
import type { ResultModel } from './result-model'
import { getDefaultConfig } from './config/custom-config'
import { mask, type MaskConfig } from '../utils/mask-util'
import { messageMethod } from '../utils/message-util'

/**
 * API信息
 */
export const BASE_URL = import.meta.env.VITE_API_BASE_URL=="http://localhost:5173"?'/flask':import.meta.env.VITE_API_BASE_URL
console.log('当前API基础路径:', import.meta.env.VITE_API_BASE_URL)

// 请求前缀
export const METHOD_TYPE_GET: Method = 'GET'
export const METHOD_TYPE_POST: Method = 'POST'
export const METHOD_TYPE_DELETE: Method = 'DELETE'
export const METHOD_TYPE_PUT: Method = 'PUT'
export const METHOD_TYPE_PATCH: Method = 'PATCH'

// 单个的参数类型
export type ParamsItemType = string | number | Date | Blob | boolean | undefined | unknown[]
// 默认的参数类型
export type QueryObjectType = { [key: string]: ParamsItemType }
// 默认的参数类型
export type QueryType = QueryObjectType | ParamsItemType
// 完成之后的类型
type AfterType = (data?: unknown) => void

/**
 * 请求类
 * <PARAMS_TYPE> 传入参数类型
 */
export default class RequestModel<T> {
	/**
	 * 返回值
	 */
	result: T | undefined
	// 请求方式
	private readonly method: Method
	// 请求的api
	private api: string
	// 请求的参数
	private readonly data: QueryType
	// 请求完成之后的操作信息
	private after: AfterType | undefined
	// 其他配置信息
	private readonly config: RequestConfig<T>

	constructor(method: Method, api: string, data?: QueryType, config?: RequestConfig<T>) {
		this.method = method
		this.api = api
		this.data = data || {}
		this.result = undefined
		this.config = this.mergeConfig(config)
		this.config.model = this
	}

	/**
	 * 设置是否需要缓存
	 * @param isSave 是否需要缓存
	 */
	public setIsSave(isSave: boolean) {
		this.config.isSave = isSave
	}

	/**
	 * 执行请求
	 */
	public request(): Promise<ResultModel<T>> {
		const key = this.api + JSON.stringify(this.data)
		// // 判断是否有缓存信息
		// if (this.config.isSave) {
		// 	// 去缓存中获取信息
		// 	const requestStore = useRequestStore()
		// 	const store = requestStore.cache[key]
		// 	if (store) {
		// 		return new Promise((resolve) => {
		// 			resolve(JSON.parse(store) as ResultModel<T>)
		// 		})
		// 	}
		// }
		return request<T>(this.method, this.api, this.data, this.config).then((data: ResultModel<T>) => {
			// 构造返回数据
			this.result = data.data
			if (this.after) {
				this.after(data)
			}
			// // 判断是否需要缓存
			// if (this.config.isSave) {
			// 	// 去缓存中获取信息
			// 	const requestStore = useRequestStore()
			// 	requestStore.save(key, JSON.stringify(data))
			// }
			
			return data
		})
	}

	/**
	 * 在data中添加参数信息
	 * @param key 键
	 * @param value 值
	 */
	public appendParam(key: string, value: string | number): RequestModel<T> {
		if (key) {
			const temp = this.data as { [key: string]: ParamsItemType }
			temp[key] = value
		}
		return this
	}

	/**
	 * 在url上添加参数信息
	 * @param key 键
	 * @param value 值
	 */
	public appendUrl(key: string, value: string | number): RequestModel<T> {
		if (key) {
			// 如果存在参数，在问号后面拼接新的参数
			const index = this.api.indexOf('?')
			const api = this.api
			if (~index) {
				this.api = `${api.slice(0, index + 1)}${key}=${value}&${api.slice(index + 1)}`
			} else {
				this.api = `${api}?${key}=${value}`
			}
		}
		return this
	}

	/**
	 * 配置合并
	 * @param config 自定义的配置信息
	 * @private
	 */
	private mergeConfig(config?: RequestConfig<T> | RequestConfig<object>): RequestConfig<T> {
		const defaultConfig = getDefaultConfig<T>()
		if (!config) {
			return defaultConfig
		}
		return <RequestConfig<T>>{
			afterCheckMap: {
				// 后置操作和并购
				...defaultConfig.afterCheckMap,
				...config.afterCheckMap
			},
			model: config.model || defaultConfig.model,
			contentType: config.contentType || defaultConfig.contentType,
			after: config.after || defaultConfig.after,
			mask: config.mask || defaultConfig.mask,
			header: config.header || defaultConfig.header,
			successCodeArray: config.successCodeArray || defaultConfig.successCodeArray,
			isSave: config.isSave == undefined ? defaultConfig.isSave : config.isSave,
			hasFile: config.hasFile == undefined ? defaultConfig.hasFile : config.hasFile
		}
	}
}

/**
 * get请求
 */
export class GetRequestModel<T> extends RequestModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_GET, api, data, config)
	}
}

/**
 * post请求
 */
export class PostRequestModel<T> extends RequestModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_POST, api, data, config)
	}
}

/**
 * put请求
 */
export class PutRequestModel<T> extends RequestModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_PUT, api, data, config)
	}
}

/**
 * delete请求
 */
export class DeleteRequestModel<T> extends RequestModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_DELETE, api, data, config)
	}
}

/**
 * 默认缓存的请求对象
 */
export class RequestCacheModel<T> extends RequestModel<T> {
	constructor(method: Method, api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(method, api, data, config)
		super.setIsSave(true)
	}
}

/**
 * 带缓存的get请求
 */
export class GetRequestCacheModel<T> extends RequestCacheModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_GET, api, data, config)
	}
}

/**
 * 带缓存的post请求
 */
export class PostRequestCacheModel<T> extends RequestCacheModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_POST, api, data, config)
	}
}

/**
 * 带缓存的put请求
 */
export class PutRequestCacheModel<T> extends RequestCacheModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_PUT, api, data, config)
	}
}

/**
 * 带缓存的delete请求
 */
export class DeleteRequestCacheModel<T> extends RequestCacheModel<T> {
	constructor(api: string, data?: QueryType, config?: RequestConfig<T>) {
		super(METHOD_TYPE_DELETE, api, data, config)
	}
}

const instance = axios.create({})

/**
 * 最终发起请求的方法
 * @param method 请求方法
 * @param url 请求地址
 * @param data 数据
 * @param config 配置
 * @returns {Promise<Object>} 异步数据
 */
function request<T>(method: Method, url: string, data: QueryType, config: RequestConfig<T>): Promise<ResultModel<T>> {
	const headers = <{ [key: string]: string }>{}
	Object.entries(config.header.data).map(([key, value]) => {
		headers[key] = typeof value === 'string' ? value : value()
	})
	// 判断请求前缀
	const prefixFlag = url.startsWith('without')
	const requestData = <AxiosRequestConfig>{
		baseURL: prefixFlag ? '/' : BASE_URL,
		method,
		url: prefixFlag ? url.replace('without', '') : url,
		headers,
		timeout: config.timeout || 60000
	}
	if (
		(method === METHOD_TYPE_POST || method === METHOD_TYPE_PUT || method === METHOD_TYPE_PATCH || method === METHOD_TYPE_DELETE) &&
		config.contentType != 'application/x-www-form-urlencoded'
	) {
		if (config.contentType && !config.hasFile) {
			headers['Content-Type'] = config.contentType
			requestData.data = data
		} else {
			if (config.hasFile) {
				config.contentType = 'application/x-www-form-urlencoded'
			}
			const formData = new FormData()
			if (typeof data === 'object') {
				Object.entries(data)
					.map(([key, value]) => {
						if (typeof value === 'number') {
							return { key, value: value.toString() }
						} else if (value instanceof File) {
							return { key, value }
						} else if (typeof value === 'object') {
							return { key, value: value.toString() }
						} else if (typeof value === 'boolean') {
							return { key, value: value.toString() }
						}
						return { key, value }
					})
					// 需要过滤掉所有未空的字符串的值
					.filter(({ value }) => value !== null && value !== undefined)
					.forEach(({ key, value }) => {
						if (typeof value === 'undefined') {
							return
						}
						formData.append(key, value)
					})
				requestData.data = formData
			} else {
				requestData.data = data
			}
		}
	} else {
		requestData.params = data
	}
	return new Promise((resolve) => {
		const flag = config.mask?.flag
		if (flag) {
			mask.open(config.mask)
		}
		instance
			.request(requestData)
			.then((data) => {
				// 判断结果是否在正确的集合内
				const response: ResultModel<T> = data.data
				const code = response.code
				if (~config.successCodeArray.indexOf(code)) {
					resolve(response)
				} else {
					after(code, response, config as RequestConfig<T>).then((data) => {
						if (data) {
							// 需要强转类型
							resolve(data as ResultModel<T>)
						}
					})
				}
			})
			.catch(((err:any)=>{
				messageMethod.error(err.response.data.message)
				resolve({ code: '00000', message: err.response.data.message, data: undefined } as ResultModel<T>)
			}))
			.finally(() => {
				if (flag) {
					setTimeout(() => {
						mask.close()
					}, config.mask?.timeout || 200)
				}
			})
	})
}

/**
 * 执行后续操作
 * @param code 返回code
 * @param response 响应数据
 * @param config 配置信息
 */
async function after<T>(code: number | string, response: ResultModel<T>, config: RequestConfig<T>): Promise<ResultModel<T> | void> {
	console.log(config.afterCheckMap[code],config.afterCheckMap,config)
	const item = config.afterCheckMap[code]
	console.log(item,code)
	debugger;
	if (item) {
		return item.fun(JSON.stringify(response), config.model)
	} else {
		messageMethod.error(response.message)
		return Promise.resolve()
	}
}

export interface AfterCheckFunction<T> {
	/**
	 * 返回code
	 */
	code: string | number

	/**
	 * 方法
	 * @param data 返回数据
	 * @param model 请求模型对象
	 */
	fun(data?: string, model?: RequestModel<T>): Promise<ResultModel<T> | void>
}

export interface RequestConfig<T> {
	/**
	 * 完成请求后的code操作
	 */
	afterCheckMap: { [key: string | number]: AfterCheckFunction<T> }
	model: RequestModel<T> | undefined
	contentType: 'application/x-www-form-urlencoded' | 'application/json;charset=UTF-8'
	after: ((data: ResultModel<T>) => void) | undefined
	/**
	 * 超时时间
	 */
	timeout: number
	/**
	 * 成功的代码code
	 */
	successCodeArray: Array<string | number>

	/**
	 * 遮罩层
	 */
	mask: MaskConfig
	/**
	 * 请求头
	 */
	header: RequestHeaderModel
	/**
	 * 是否暂存数据（暂存数据，会将当前请求的api与参数一同缓存）
	 */
	isSave?: boolean
	/**
	 * 是否含有文件
	 */
	hasFile?: boolean
}

/**
 * 请求头对象信息
 */
export class RequestHeaderModel {
	public readonly data: { [key: string]: string | (() => string) }

	constructor(...fun: Array<(header: RequestHeaderModel) => void>) {
		this.data = <{ [key: string]: string | (() => string) }>{}
		if (fun && fun.length) {
			fun.forEach((item) => {
				item(this)
			})
		}
	}

	/**
	 * 追加信息
	 * @param key
	 * @param value
	 */
	public put(key: string, value: string | (() => string)) {
		this.data[key] = value
	}
}

/**
 * 设置默认的请求头信息
 */
export const setDefaultHeaderAuthToken = (header: RequestHeaderModel): void => {
	// header.put('authToken', () => {
	// 	const systemStore = useSystemStore()
	// 	return systemStore.token
	// })
}

/**
 * 设置默认的表单防重内容
 */
export const setDefaultHeaderSubmitKey = (header: RequestHeaderModel): void => {
	// header.put('submitKey', uuid)
}

/**
 * 自定义的请求头信息数组
 */
export const CUSTOM_GLOBAL_HEADER_MAP: { [key: string]: string | (() => string) } = {}

/**
 * 追加全局请求头信息的方法
 * @param key
 * @param value
 */
export const putGlobalHeader = (key: string, value: string | (() => string)) => {
	CUSTOM_GLOBAL_HEADER_MAP[key] = value
}

/**
 * 设置全局请求头信息的方法
 * @param header
 */
export const setCustomGlobalHeaderArray = (header: RequestHeaderModel): void => {
	Object.entries(CUSTOM_GLOBAL_HEADER_MAP).forEach(([key, value]) => {
		header.put(key, value)
	})
}

// 默认的请求方式
export const DEFAULT_REQUEST_HEADER = () => {
	return new RequestHeaderModel(setDefaultHeaderAuthToken, setDefaultHeaderSubmitKey, setCustomGlobalHeaderArray)
}
