import { GetRequestModel, PostRequestModel,PutRequestModel } from '../../http/request-model'
import { updateContactInfo } from '../User'

export default {
	/**
	 * 用户
	 * @param file
	 */
	login: (query?: any) => new PostRequestModel<any>(`/users/login`, query).request(),
	register: (query?: any) => new PostRequestModel<any>(`/users/register`, query).request(),
	getUserContactInfo: (query?: any) => new GetRequestModel<any>(`/userContact/getUserContactInfo/${query}`).request(),
	//updateContactInfo: (query?: any, value?: { address: string; city: string; country: string; postalCode: string }) => new PostRequestModel<any>(`/users/updateContactInfo`, query).request(),
	// 修改updateContactInfo方法，接受userId和contactInfo两个参数
	updateContactInfo: (userId: number, contactInfo: {address: string; city: string; country: string; postalCode: string }) =>
	new PostRequestModel<any>(`/userContact/updateContactInfo/${userId}`, contactInfo).request(),
}
