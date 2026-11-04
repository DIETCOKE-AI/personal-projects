<template>
  <!--图片识别界面 -->
  <div>
    <div style="width: 100%;">
      <!-- 图片上传 -->
      <div>
        <el-upload 
          drag 
          class="upload-demo" 
          ref="upload"
          action="#" 
          :http-request="handleHttpRequest"
          :on-change="handleChange" 
          :file-list="fileList" 
          :before-upload="beforeUpload" 
          :on-remove="handleRemove"
          :auto-upload="false"
          multiple
          list-type="picture" 
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
          <div class="el-upload__tip" slot="tip">最多上传50张，只能上传jpg/png/bmp文件</div>
        </el-upload>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button type="info" plain @click="clearImage" :disabled="fileList.length === 0">清 空</el-button>
        <el-button type="primary" plain @click="submitUpload" :disabled="fileList.length === 0" :loading="uploading">开始识别</el-button>
      </span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { ref } from "vue";
import axios from "axios";
import { messageMethod } from "../utils/message-util";
import { progressDialog } from "../utils/loadingmask-util";

const fileList = ref<any[]>([]);
const upload = ref<any>(null);
const uploading = ref(false);
const BaseUrl = import.meta.env.VITE_API_BASE_URL;

const emit = defineEmits(["update:imageDialogValue", "updateMaterialList"]);

const clearImage = () => {
  upload.value.clearFiles();
};

const beforeUpload = (file: any) => {
  const isImage = ['image/jpeg', 'image/png', 'image/bmp'].includes(file.type);
  const isLt5M = file.size / 1024 / 1024 < 5; // 检查文件大小是否小于5MB
  const isGt10K = file.size / 1024 > 10; // 检查文件大小是否大于10KB

  if (!isImage) {
    messageMethod.error('只能上传 JPG/PNG/BMP 格式的图片!');
    return false;
  }
  if (!isLt5M) {
    messageMethod.error('图片大小不能超过 5MB!');
    return false;
  }
  if (!isGt10K) {
    messageMethod.error('图片大小不能低于 10KB，请选择更清晰的图片!');
    return false;
  }
  return true;
};

const handleChange = (file: any, files: any) => {
  if (files.length > 50) {
    messageMethod.warning("最多可识别50张图");
    fileList.value = files.slice(0, 50);
  } else {
    fileList.value = files;
  }
};

const handleRemove = (file: any, files: any) => {
  fileList.value = files;
};

const submitUpload = () => {
  if (fileList.value.length === 0) {
    messageMethod.warning('请先选择文件');
    return;
  }
  upload.value.submit();
};

const handleHttpRequest = async (options: { file: File }) => {
  // 注意：el-upload 在自定义上传时，会为每个文件单独调用一次此函数
  // 我们需要收集所有文件的Promise，然后一次性处理
  // 但更简单、更可靠的做法是，只在第一次调用时，收集所有待上传文件并发送请求
  if (uploading.value) return; // 如果正在上传，则忽略后续的调用

  uploading.value = true;
  const formData = new FormData();
  const userData = JSON.parse(localStorage.getItem('user') || '{}');
  const userId = userData.userId || '1'; // 如果没有用户信息，默认为1
  formData.append('userId', userId);
  
  fileList.value.forEach(file => {
    if (file.raw) {
      formData.append('files', file.raw);
    }
  });

  if (!formData.has('files')) {
      messageMethod.info("没有新的文件需要上传");
      uploading.value = false;
      return;
  }

  progressDialog.open({
    key: 'image-upload',
    title: '上传识别',
    content: '正在识别中...',
    type: 'circle'
  });

  try {
    const response = await axios.post(`${BaseUrl}/predict/batch`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    if (response.data && response.data.code === 0) {
      const results = response.data.data;
      const successCount = results.filter((r: any) => r.code === 0).length;
      const failureCount = results.length - successCount;

      if (failureCount > 0) {
        messageMethod.warning(`上传完成: ${successCount}成功, ${failureCount}失败`);
      } else {
        messageMethod.success(`全部 ${successCount} 个文件识别成功`);
      }
      
      emit("updateMaterialList", results); // 传递完整的、包含成功和失败信息的结果数组
      emit("update:imageDialogValue", false);
      progressDialog.complete('image-upload');

    } else {
      throw new Error(response.data.message || '批量上传失败');
    }

  } catch (error) {
    console.error("上传失败:", error);
    messageMethod.error('上传失败，请检查网络或联系管理员');
    progressDialog.showError('image-upload', '上传过程中出错');
  } finally {
    uploading.value = false;
    upload.value.clearFiles();
  }
};

</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-start;
  padding: 10px;
  gap: 10px;
  margin-bottom: 20px;
}
</style>