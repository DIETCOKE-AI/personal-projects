import { GetRequestModel, PostRequestModel } from '../../http/request-model'


export default {
	/**
	 * 获取历史记录
	 * @param file
	 */
	page: (query?: any) => new PostRequestModel<any>(`/history/page`, query).request(),
    add: (query?: any) => new PostRequestModel<any>(`/history/add`, query).request(),
	batch: (query?: any) => new PostRequestModel<any>(`/history/batch`, query).request()
}
