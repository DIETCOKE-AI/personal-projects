// axios 实例文件
import axios from "axios";

const instance = axios.create({
  baseURL: import.meta.env.VITE_RUOYI_API_BASE_URL, // 读取若依专用的环境变量
  timeout: 10000,
});

// 请求拦截器：在请求发送之前做一些处理
instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 返回错误供外部处理
    return Promise.reject(error);
  }
);

export default instance;