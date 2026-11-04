import type { MaskConfig } from "@/renderer/utils/mask-util"
import RequestModel, { DEFAULT_REQUEST_HEADER, type AfterCheckFunction, type RequestConfig } from "../request-model"
import type { ConfirmVo, ResultModel, ResultObjectVo } from "../result-model"
import { confirmMethod, messageMethod } from "@/renderer/utils/message-util"
import { getRouter } from "@/renderer/router"

// 文件相关配置
export const fileConfig = {
	// 默认文件前缀
	uploadPrefix: '/upload/',
	// 临时文件前缀
	tempPrefix: '/temp/',
	// 备份文件前缀
	backupPrefix: '/backup/',
	// 模板下载前缀
	templatePrefix: ''
}

// 请求成功的代码
const successCodeArray = ['00000', '0', 0]

/**
 * 默认的请求参数
 */
export function getDefaultConfig<T>(): RequestConfig<T> {
	return {
		afterCheckMap: getAfterCheckMap<T>(),
		model: undefined,
		contentType: 'application/json;charset=UTF-8',
		successCodeArray: [...successCodeArray],
		timeout: 60000,
		after: undefined,
		mask: <MaskConfig>{
			flag: true,
			content: '加载中...',
			timeout: 0
		},
		header: DEFAULT_REQUEST_HEADER(),
		isSave: false,
		hasFile: false
	}
}

/**
 * authToken异常或者未登录的处理方法
 * @param data 返回数据
 */
const checkLogin = <T>(data: string): Promise<ResultModel<T> | void> => {
	const vo = JSON.parse(data) as ResultObjectVo
	// 消息提示
	messageMethod.error(vo.message)
	return getRouter()
		.push('/component')
		.then(() => {
			return
		})
}

/**
 * 获取请求之后的操作
 */
export function getAfterCheckMap<T>(): { [key: string | number]: AfterCheckFunction<T> } {
	const array: AfterCheckFunction<T>[] = [
		{
			code: '9',
			fun: checkLogin
		},
		{
			code: '1024',
			fun: checkLogin
		},
		{
			code: '00002',
			fun(data: string, model: RequestModel<T>): Promise<ResultModel<T> | void> {
				const vo = <ConfirmVo>JSON.parse(data)
				const { key, token, skip } = vo.data
				return new Promise((resolve) => {
					confirmMethod.info(
						vo.message,
						() => {
							resolve(
								model
									.appendUrl(key, token)
									.appendUrl(skip ? 'confirm_skip' : '', skip)
									.request()
							)
						},
						() => {
							return Promise.resolve()
						}
					)
				})
			}
		}
	]
	const map: { [key: string | number]: AfterCheckFunction<T> } = {}
	array.forEach((item) => (map[item.code] = item))
	return map
}
