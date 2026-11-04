// 该文件专门用于对接若依后端的用户管理API
import { handleRequestError } from "../../utils/conmon";
import instance from "../../https"; // 引入指向 /api 的 Axios 实例

// 用户数据接口，严格与后端若依的 SysUser.java 实体类对应
export interface RuoYiUserData {
  userId?: number;
  userName: string;
  nickName?: string;
  email: string;
  phonenumber?: string;
  password?: string;
  avatar?: string;
  createTime?: string; // 在JSON传输中，Date通常为字符串
}

// 登录接口
export const login = async (loginData: any): Promise<any> => {
  try {
    return await instance.post("/login", loginData);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 公开注册接口
 * @param registerData 注册信息
 */
export const register = async (registerData: any): Promise<any> => {
  try {
    // 调用后端的公开注册API，路径通常是 /register
    return await instance.post("/register", registerData);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 获取用户列表 (若依分页查询)
export const getRuoYiUsers = async (params: { pageNum: number, pageSize: number, userName?: string, phonenumber?: string }): Promise<any> => {
  try {
    // 若依生成的Controller路径默认为 /system/user/list
    return await instance.get("/system/user/list", { params });
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 新增：获取所有用户（包括已删除）
export const getRuoYiUsersAll = async (params: { pageNum: number, pageSize: number, userName?: string, phonenumber?: string }): Promise<any> => {
  try {
    return await instance.get("/system/user/list/all", { params });
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 获取用户详情
export const getRuoYiUserById = async (userId: number): Promise<any> => {
  try {
    return await instance.get(`/system/user/${userId}`);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 创建用户
export const createRuoYiUser = async (userData: RuoYiUserData): Promise<any> => {
  try {
    return await instance.post("/system/user", userData);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 更新用户
export const updateRuoYiUser = async (userData: RuoYiUserData): Promise<any> => {
  try {
    return await instance.put("/system/user", userData);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 删除用户
export const deleteRuoYiUser = async (userId: number | number[]): Promise<any> => {
  try {
    const ids = Array.isArray(userId) ? userId.join(',') : userId;
    return await instance.delete(`/system/user/${ids}`);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 根据用户ID获取联系方式
 * @param userId 用户ID
 */
export const getContactInfoByUserId = async (userId: number): Promise<any> => {
  try {
    // 路径应与您后端Controller中定义的路径一致, 若依代码生成器默认为 /system/{业务名}/...
    return await instance.get(`/system/contact/${userId}`);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 更新或创建用户的联系方式
 * @param contactData 包含userId和其他联系信息的对象
 */
export const updateContactInfo = async (contactData: any): Promise<any> => {
  try {
    // 使用 PUT 方法，将整个对象作为请求体发送
    return await instance.put("/system/contact", contactData);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 重置用户密码
 * @param userId 用户ID
 * @param password 新密码
 */
export const resetUserPassword = async (userId: number, password: string): Promise<any> => {
  const data = { userId, password };
  try {
    return await instance.put('/system/user/resetPwd', data);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 用户修改自己的密码
 * @param oldPassword 旧密码
 * @param newPassword 新密码
 */
export const updateUserPassword = async (oldPassword: string, newPassword: string): Promise<any> => {
  const data = { oldPassword, newPassword };
  try {
    return await instance.put('/system/user/profile/updatePwd', data);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 获取当前登录用户的详细信息
 * (若依标准接口，通过请求头中的Token自动识别用户)
 */
export const getUserInfo = async (): Promise<any> => {
  try {
    return await instance.get("/getInfo");
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 获取登录验证码
 */
export const getCaptchaImage = async (): Promise<any> => {
  try {
    return await instance.get("/captchaImage");
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 获取所有可用的角色列表
 */
export const getAllRoles = async (): Promise<any> => {
  try {
    // 若依获取角色列表的默认接口，通常不需要分页
    return await instance.get("/system/role/list");
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 根据用户ID列表批量获取用户信息（主要用于获取角色）
 * @param userIds 用户ID列表
 */
export const getUserRolesByUserIds = async (userIds: number[]): Promise<any> => {
  try {
    // 使用 paramsSerializer 来处理数组参数，确保其能被后端正确解析
    return await instance.get("/system/user/list/roles", { 
      params: { userIds },
      paramsSerializer: params => {
        const qs = new URLSearchParams();
        for (const key in params) {
          const val = params[key];
          if (Array.isArray(val)) {
            val.forEach(v => qs.append(key, v));
          } else {
            qs.append(key, val);
          }
        }
        return qs.toString();
      }
    });
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

/**
 * 恢复被软删除的用户
 * @param userId 用户ID
 */
export const restoreRuoYiUser = async (userId: number): Promise<any> => {
  try {
    return await instance.put(`/system/user/restore/${userId}`);
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

