import { GetRequestModel, PostRequestModel } from '../../http/request-model'


export default {
	/**
	 * 获取药材数据库
	 * @param file
	 */
	page: (query?: any) => new PostRequestModel<any>(`/herb/page`, query).request(),

	getOne: (query?: any) => new PostRequestModel<any>(`/herb/getOne`, query).request(),

	/**
     * 条件查询药材数据
     * @param query 查询条件对象
	 * 暂时没有使用，因为条件查询直接复用了分页查询的代码，
	 * 只是传输时多传送了一个用户变量userInfo
    search: (query?: any) => new PostRequestModel<any>(`/herb/search`, query).request(),
	*/
}
