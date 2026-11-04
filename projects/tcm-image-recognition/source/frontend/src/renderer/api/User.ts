import { handleRequestError } from "../utils/conmon";
import instance from "../https"; // 引入 Axios 实例

export interface UserData {
  name: string;
  email: string;
  password: string;
  permissions: string[];
  level: number;
  phone: string;
  avatar?: string;
}
export interface LoginData {
  email: string;
  password: string;
}
// 获取所有用户
export const getUsers = async (): Promise<any> => {
  try {
    const response = await instance.get("/users");
    return response; // 返回响应的数据
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 获取用户详情
export const getUserById = async (id: string): Promise<any> => {
  try {
    const response = await instance.get(`/users/${id}`);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 创建用户
export const createUser = async (userData: UserData): Promise<any> => {
  try {
    const response = await instance.post("/users", userData);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 更新用户
export const updateUser = async (
  id: string,
  userData: UserData
): Promise<any> => {
  try {
    const response = await instance.put(`/users/${id}`, userData);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 删除用户
export const deleteUser = async (id: string): Promise<any> => {
  try {
    const response = await instance.delete(`/users/${id}`);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

export const login = async (loginData:any): Promise<any> => {
  try {
    const response = await instance.post("/login", loginData);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

export interface ContactInfoResponse {
  code: number
  message: string
  data?: {
    address: string
    city: string
    country: string
    postalCode: string
  }
}
export interface ContactInfo {
  address: string
  city: string
  country: string
  postalCode: string
}
//获取用户的联系方式
export const getContactInfo = async(userId: string) => {
  try{
    const response = await instance.get(`/contactInfo/${userId}`);
    return response;
  }
  catch(error: unknown){
    handleRequestError(error);
  }
}
//更新用户的联系方式
export const updateContactInfo = async(userId: string, contactInfo: ContactInfo) => {
  try{
    //传入的用户id如何获取？从user.id当中进行id的获取
    const response = await instance.put(`/contactInfo/${userId}`, contactInfo);
    return response;
  }
  catch(error: unknown){
    handleRequestError(error);
  }
}



