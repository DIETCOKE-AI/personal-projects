import { GetRequestModel, PostRequestModel } from '../../http/request-model'


export default {
	/**
	 * 上传图片
	 * @param file
	 * query?表示参数可选
	 */
	predict: (query?: any,config?:any) => new PostRequestModel<any>(`/predict`, query,config).request()
}
