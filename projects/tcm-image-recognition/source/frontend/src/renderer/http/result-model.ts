/**
 * api返回值的实体类
 */
export interface ResultModel<T> {
	code: string|number
	t: string
	message: string
	data: T
	success?: boolean
}

/**
 * 默认分页接收的对象模块
 */
export interface PageModel<T> {
	pageNum: number
	pageSize: number
	total: number
	isLastPage: boolean
	list: Array<T>
}

interface ConfirmVoData {
	key: string
	skip: string
	token: string
}

export declare type ConfirmVo = ResultModel<ConfirmVoData>

export declare type ResultObjectVo = ResultModel<object>
