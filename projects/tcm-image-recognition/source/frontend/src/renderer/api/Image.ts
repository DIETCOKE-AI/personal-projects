import instance from "../https";
import { handleRequestError } from "../utils/conmon";
// 定义图片数据类型
interface ImageData {
  localPath: string;
  chineseName: string;
  latinName: string;
  standard: string; // 标准
  confidence: number; // 置信度
  uploadedBy: number; // 上传者
  uploadedAt: string; // 上传时间
  updatedAt: string; // 更新时间
}

// 获取指定ID的图片
export const getImage = async (id: string): Promise<any> => {
  try {
    const response = await instance.get(`/images/${id}`);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 获取所有图片列表
export const getImageList = async (): Promise<any> => {
  try {
    const response = await instance.get("/images");
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 创建图片
export const createImage = async (imageData: ImageData): Promise<any> => {
  try {
    const response = await instance.post("/images", imageData);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 更新图片
export const updateImage = async (
  id: string,
  imageData: ImageData
): Promise<any> => {
  try {
    const response = await instance.put(`/images/${id}`, imageData);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};

// 删除图片
export const deleteImage = async (id: string): Promise<any> => {
  try {
    const response = await instance.delete(`/images/${id}`);
    return response;
  } catch (error: unknown) {
    handleRequestError(error);
  }
};
