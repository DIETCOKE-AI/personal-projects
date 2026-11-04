<template>
  <!-- 拍照识别界面 -->
  <div :icon="null" width="70%">
    <div style="width: 100%;">
      <div class="content-container">
        <!-- 选择框区域 -->
        <div class="form-container">
          <el-form :model="form" label-width="80px" style="display: flex;flex-wrap: wrap;">
            <el-form-item label="灯光控制" style="width: 50%;">
              <el-switch @change="handleLightChange" v-model="lightStatus" active-color="#13ce66"
                inactive-color="#ff4949">
                <!-- :disabled="!isConnected" -->
              </el-switch>
            </el-form-item>

            <!-- <el-form-item label="选择类别">
              <el-radio-group v-model="form.selectedCategory">
                <el-radio value="unknown">未知类别</el-radio>
                <el-radio value="known">已知类别</el-radio>
              </el-radio-group>
            </el-form-item> -->


            <!-- 镜头选择 -->
            <el-form-item label="镜头选择" style="width: 50%;">
    <el-button-group>
      <el-button :type="form.selectedCamera === 'camera1' ? 'primary' : 'default'"
        @click="switchCamera('camera1')" :disabled="isConnecting || isConnected">小镜头</el-button>
      <el-button :type="form.selectedCamera === 'camera2' ? 'primary' : 'default'"
        @click="switchCamera('camera2')" :disabled="isConnecting || isConnected">中镜头</el-button>
      <el-button :type="form.selectedCamera === 'camera3' ? 'primary' : 'default'"
        @click="switchCamera('camera3')" :disabled="isConnecting || isConnected">大镜头</el-button>
    </el-button-group>
</el-form-item>

            <!-- 曝光时间 -->
            <!-- <el-form-item label="曝光时间" style="width: 50%;">
              <el-input-number v-model="form.exposureTime" :min="0" :max="1000" label="曝光时间" controls-position="right"
                :disabled="!isConnected" />
            </el-form-item> -->

            <el-form-item label="镜头调节" style="width: 50%;" v-if="form.selectedCamera != ''">
              <div class="camera-control">
                <div class="camera-group" v-if="form.selectedCamera === 'camera1'">
                  <el-button @click="adjustCamera('small_up')" :disabled="!isConnected">上移</el-button>
                  <el-button @click="adjustCamera('small_down')" :disabled="!isConnected">下移</el-button>
                  <el-button @click="rotateCamera('left')" :disabled="!isConnected">向左转</el-button>
                  <el-button @click="rotateCamera('right')" :disabled="!isConnected">向右转</el-button>
                </div>
                <div class="camera-group" v-if="form.selectedCamera === 'camera2'">
                  <el-button @click="adjustCamera('medium_up')" :disabled="!isConnected">上移</el-button>
                  <el-button @click="adjustCamera('medium_down')" :disabled="!isConnected">下移</el-button>
                  <el-button @click="rotateCamera('left')" :disabled="!isConnected">向左转</el-button>
                  <el-button @click="rotateCamera('right')" :disabled="!isConnected">向右转</el-button>
                </div>
                <div class="camera-group" v-if="form.selectedCamera === 'camera3'">
                  <el-button @click="adjustCamera('large_up')" :disabled="!isConnected">上移</el-button>
                  <el-button @click="adjustCamera('large_down')" :disabled="!isConnected">下移</el-button>
                  <el-button @click="rotateCamera('left')" :disabled="!isConnected">向左转</el-button>
                  <el-button @click="rotateCamera('right')" :disabled="!isConnected">向右转</el-button>
                </div>
              </div>
            </el-form-item>
            <!-- <el-form-item label="选择类别" style="width: 50%;">
              <el-radio-group v-model="form.selectedCategory">
                <el-radio value="unknown">未知类别</el-radio>
                <el-radio value="known">已知类别</el-radio>
              </el-radio-group>
            </el-form-item> -->

            <el-form-item label="类别选择" style="width: 100%;" v-if="form.selectedCategory === 'known'">
              <el-select v-model="form.selectedKnownOption" placeholder="请选择选项">
                <el-option label="选项 1" value="option1"></el-option>
                <el-option label="选项 2" value="option2"></el-option>
                <el-option label="选项 3" value="option3"></el-option>
              </el-select>
            </el-form-item>

            <!-- 图片预览 -->
            <div class="image-preview" style="width: 100%;" v-if="imageUrls.length > 0">
              <div v-for="(img, index) in imageUrls" :key="index" class="thumbnail-container">
                <img :src="img" class="thumbnail" />
                <el-button circle size="small" @click="removeImage(index)" class="delete-btn">
                  <el-icon>
                    <Close />
                  </el-icon>
                </el-button>
              </div>
            </div>
          </el-form>

          <div slot="footer" class="dialog-footer">
            <el-button plain @click="connectDevice" type="success" :loading="isConnecting" :disabled="isConnected">
              {{ isConnecting ? '连接中...' : '连接设备' }}
            </el-button>
            <el-button plain @click="disconnectDevice" type="error" :disabled="!isConnected" :loading="loadingSure">
              关闭设备
            </el-button>
            <el-button @click="captureImage" plain :disabled="!isConnected||imageUrls.length>=50" :loading="loadingSure">拍 照</el-button>
            <el-button type="primary" plain @click="clearImage" :disabled="imageUrls.length === 0"
              :loading="loadingSure">清 空</el-button>

            <el-button type="primary" plain @click="confirmSelection" :disabled="imageUrls.length === 0"
              :loading="loadingSure">确 定</el-button>
          </div>
          <el-button
                class="tips-btn"
                plain
                disabled
              >
                <span class="tips-btn-flex">
                  <el-icon class="tips-btn-icon">
                    <WarningFilled />
                  </el-icon>
                  <span class="tips-btn-text">为保证识别准确性，应拍摄10张以上后进行识别</span>
                </span>
              </el-button>
        </div>

        <!-- 视频预览区域 -->
        <div class="video-container" v-loading="isLoading" :element-loading-text="loadingText" :style="{
          'aspect-ratio': '3 / 2',
          'transform-origin': 'center',
          'transform': `rotate(${rotationAngle}deg) translateX(${translationX}%)`
        }">
          <canvas id="cameraCanvas" :class="{ 'connected': isConnected }"></canvas>
          <div v-if="!isConnected" class="camera-placeholder">
            <el-icon>
              <Camera />
            </el-icon>
            <span>摄像头未连接</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { Close, Camera } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from 'element-plus'
import { messageMethod } from "../utils/message-util";
import historyApi from "../api/history/history"
import { progressDialog } from "../utils/loadingmask-util";
import { WarningFilled } from '@element-plus/icons-vue'

// 常量定义
const MAX_ROTATION_ANGLE = 360;
const ROTATION_STEP = 90;
const MAX_CONNECTION_RETRIES = 3;
const WEBSOCKET_URL = "ws://localhost:8765";

const loadingSure = ref(false)
// 组件属性
const emit = defineEmits(["update:imageDialogValue", "updateMaterialList"]);
const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
});

// 状态管理
const form = ref({
  selectedCategory: "unknown",
  selectedKnownOption: "",
  selectedCamera: "",
  exposureTime: 100,
});

const imageUrls = ref<string[]>([]);
const imagePaths = ref<string[]>([]);
const rotationAngle = ref(0);
const translationX = ref(0);
const translationY = ref(0);
const lightStatus = ref(true);
const isLoading = ref(false);
const isConnecting = ref(false);
const isConnected = ref(false);
const connectionRetries = ref(0);
const loadingText = computed(() =>
  isConnecting.value ? loadingSure ? "正在识别中" : "正在连接摄像头..." : "正在处理..."
);

// WebSocket 和 Electron API
const electronApi = window.electron;
electronApi.lightControl();
const videoWs = ref<WebSocket | null>(null);

const clearImage = () => {
  ElMessageBox.confirm(
    '确定要清空所有已拍摄的照片吗？此操作不可撤销。',
    '清空确认',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    imageUrls.value = [];
    formDataFile = new FormData();
    ElMessage({
      type: 'success',
      message: '已清空',
    });
  }).catch(() => {
    // 用户点击了取消，或关闭了对话框
    ElMessage({
      type: 'info',
      message: '已取消清空操作',
    });
  });
};

// 初始化视频WebSocket
const initVideoWebSocket = async () => {
  return new Promise<void>((resolve, reject) => {
    if (videoWs.value && [WebSocket.OPEN, WebSocket.CONNECTING].includes(videoWs.value.readyState as any)) {
      videoWs.value.close();
    }

    videoWs.value = new WebSocket(WEBSOCKET_URL);
    const canvas = document.getElementById("cameraCanvas") as HTMLCanvasElement;
    const ctx = canvas.getContext("2d");

    videoWs.value.onopen = () => {
      console.log("视频WebSocket连接已打开");
      resolve();
    };

    videoWs.value.onmessage = async (event) => {
      try {
        const blob = new Blob([event.data], { type: "image/jpeg" });
        const bitmap = await createImageBitmap(blob);
        ctx?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      } catch (error) {
        console.error("渲染视频帧失败:", error);
      }
    };

    videoWs.value.onerror = (error) => {
      console.error("视频WebSocket错误:", error);
      reject(error); // 【关键修正】将错误传递出去
    };

    videoWs.value.onclose = (event) => {
      console.log("视频WebSocket关闭:", event.code, event.reason);
    };
  });
};

// 摄像头旋转控制
const rotateCamera = (direction: 'left' | 'right') => {
  const newAngle = direction === 'left'//若是向左
    ? rotationAngle.value + ROTATION_STEP
    //若是向右
    : rotationAngle.value - ROTATION_STEP;

  rotationAngle.value = newAngle % MAX_ROTATION_ANGLE;

  /* if (newAngle === 90 || newAngle === -90) {
    translationX.value = 20;
    
  } else if (newAngle === 270 || newAngle === -270) {
    translationX.value = -20;
  } else {
    translationX.value = 0;
  } */
 switch (newAngle) {
    case 90:
      translationX.value = 20;
    case -270:
      translationX.value = 20;
      break;
    case -90:
      translationX.value = -20;
    case 270:
      translationX.value = -20;
      break;
    default:
      translationX.value = 0;
      break;
  }
};


// 切换摄像头
const switchCamera = async (cameraId: string) => {
  if (isConnecting.value) return;

  isConnecting.value = true;
  isLoading.value = true;
   //此处新增激光打开 根据id选择镜头传入switch

  try {
    // 停止当前摄像头
    await electronApi.StopCamera();

    // 关闭旧WebSocket连接
    if (videoWs.value) {
      videoWs.value.close();
      videoWs.value = null;
    }

    // 更新UI状态
    form.value.selectedCamera = cameraId;
    const canvas = document.getElementById("cameraCanvas") as HTMLCanvasElement;
    const ctx = canvas.getContext("2d");
    ctx?.clearRect(0, 0, canvas.width, canvas.height);

    // 切换摄像头硬件
    await electronApi.switchCamera(cameraId);

    // 建立新WebSocket连接
    await initVideoWebSocket();

    isConnected.value = true;
    connectionRetries.value = 0;

    // 根据连接的摄像头，发送对应的激光开启指令
    switch (cameraId) {
      case 'camera1':
        ws.send("51"); // 激光1开
        break;
      case 'camera2':
        ws.send("54"); // 激光2开
        break;
      case 'camera3':
        ws.send("57"); // 激光3开
        break;
    }
  } catch (error) {
    console.error("摄像头切换失败:", error);

    // 【关键修正】带延迟的重试逻辑
    if (connectionRetries.value < MAX_CONNECTION_RETRIES) {
      connectionRetries.value++;
      console.log(`尝试重新连接 (${connectionRetries.value}/${MAX_CONNECTION_RETRIES})`);
      await new Promise(resolve => setTimeout(resolve, 1000 * connectionRetries.value)); // 延迟时间可以根据需要调整
      await switchCamera(cameraId); // 重新调用自身以重试
    } else {
      messageMethod.error("摄像头连接失败，请检查设备或重启应用。");
      isConnected.value = false;
      connectionRetries.value = 0; // 重置重试次数
    }
  } finally {
    isConnecting.value = false;
    isLoading.value = false;
   
  }
};


// 连接设备
const connectDevice = async () => {
  if (form.value.selectedCamera == "") {
    console.log("请选择镜头")
    messageMethod.info("请选择镜头")
    return;
  }
  console.log(isConnecting.value)
  if (isConnecting.value) return;

  try {
    // isConnecting.value = true;
    isLoading.value = true;

    // 初始化canvas
    const canvas = document.getElementById("cameraCanvas") as HTMLCanvasElement;
    if (!canvas.width || !canvas.height) {
      canvas.width = 1920;
      canvas.height = 1080;
    }

    // 停止可能存在的旧连接
    await electronApi.StopCamera();

    // 初始化控制WebSocket
    // initControlWebSocket();

    // 使用默认摄像头或已选摄像头
    const cameraId = form.value.selectedCamera || 'camera1';
    console.log(cameraId)
    await switchCamera(cameraId);
    console.log('11111')
  } catch (error) {
    console.error("设备连接失败:", error);
    isConnected.value = false;
  } finally {
    isConnecting.value = false;
    isLoading.value = false;
  }
};

// 断开设备连接
const disconnectDevice = async () => {
  try {
    isLoading.value = true;

    // 根据当前连接的摄像头，发送对应的激光关闭指令
    switch (form.value.selectedCamera) {
      case 'camera1':
        ws.send("52"); // 激光1关
        break;
      case 'camera2':
        ws.send("55"); // 激光2关
        break;
      case 'camera3':
        ws.send("58"); // 激光3关
        break;
    }

    // 关闭WebSocket连接
    if (videoWs.value) {
      videoWs.value.close();
      videoWs.value = null;
    }

    // 清除画布
    const canvas = document.getElementById("cameraCanvas") as HTMLCanvasElement;
    const ctx = canvas.getContext("2d");
    ctx?.clearRect(0, 0, canvas.width, canvas.height);
    // 停止摄像头
    await electronApi.StopCamera();

    console.log(isConnecting.value)

    isConnected.value = false;
  } catch (error) {
    console.error("断开设备连接失败:", error);
  } finally {
    isLoading.value = false;
    isConnected.value = false
  }
};

// 拍照
const captureImage = async () => {
  if (imageUrls.value.length >= 50) {
    messageMethod.warning("最多可识别50张图");
    return;
  }

  const executeCapture = () => {
    const canvas = document.getElementById("cameraCanvas") as HTMLCanvasElement;
    if (canvas) {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const imgUrl = URL.createObjectURL(blob);
            imageUrls.value.push(imgUrl); // 添加到图片预览列表

            const file = new File([blob], `image${Date.now()}.png`, {
              type: "image/png",
            });
            formDataFile.append("files", file);
            if (imageUrls.value.length === 50) {
              messageMethod.warning("已达到最多可识别50张图，无法继续添加！");
            }
          }
        },
        "image/png",
        1
      );
    }
  };

  let delay = 400; // 默认延时
  let laserCommand = "";

  switch (form.value.selectedCamera) {
    case 'camera1':
      delay = 400; // 您可以在此为小镜头设置最佳延时
      laserCommand = "53"; // 激光1延时打开
      break;
    case 'camera2':
      delay = 800; // 您可以在此为中镜头设置最佳延时
      laserCommand = "56"; // 激光2延时打开
      break;
    case 'camera3':
      delay = 200; // 您可以在此为大镜头设置最佳延时
      laserCommand = "59"; // 激光3延时打开
      break;
    default:
      console.log("未选择摄像头，无法执行拍照");
      messageMethod.warning("请先选择一个镜头");
      return;
  }

  // 发送激光指令
  if (laserCommand) {
    ws.send(laserCommand);
  }

  // 在设定的延时后执行截图
  setTimeout(executeCapture, delay);
};

// 移除图片
const removeImage = (index: number) => {
  // 释放图片URL
  URL.revokeObjectURL(imageUrls.value[index]);
  
  // 删除预览图片
  imageUrls.value.splice(index, 1);
  imagePaths.value.splice(index, 1);
  
  // 重建FormData，排除被删除的文件
  const newFormData = new FormData();
  Array.from(formDataFile.getAll("files"))
    .filter((_, i) => i !== index) // 过滤掉要删除的索引
    .forEach(file => newFormData.append("files", file));
  
  formDataFile = newFormData;
  console.log("删除后的文件列表:", formDataFile.getAll("files"));
};

let formDataFile = new FormData();

const abortController = ref<AbortController | null>(null);
// 确认选择
const confirmSelection = async () => {
  loadingSure.value = true
  if (imageUrls.value.length === 0) {
    console.warn("没有拍照的图片");
    return;
  }
  
  const userData = JSON.parse(localStorage.getItem('user') || '{}');
  const userId = userData.userId || '1'; // 如果没有用户信息，默认为1
  formDataFile.append('userId', userId);
  try {
    isLoading.value = true;
    abortController.value = new AbortController();

    if (formDataFile) {
      progressDialog.open({
        key: 'shoot-upload',
        title: '上传识别',
        content: '正在识别中...',
        type: 'circle',
        progressSpeed: 30,
        showCancel: true,
        cancelText: '取消识别',
        onCancel: async () => {
          abortController.value?.abort();
          progressDialog.close();
          isLoading.value = false;
        }
      })
      await fetch(`${import.meta.env.VITE_API_BASE_URL}/predict/batch`, {//此处在样机拉取后需要修改
        method: "POST",
        body: formDataFile,
        signal: abortController.value.signal  // 传入 AbortSignal
      })
        .then((response) => response.json())
        .then((res: any) => {
          // emit("updateMaterialList", res.data);
          // historyApi.batch(res.data.map((item: any) => {
          //   return { ...item, 'uploaded_by': 1 }
          //   // uploaded_by为当前用户，此处需修改
          // })).then((ress: any) => {
          //   if (ress.code == 0) {
          //     messageMethod.success(`${ress.message}`);
          //     emit("update:imageDialogValue", false);
          //     emit("updateMaterialList", res.data);
          //   } else {
          //     messageMethod.warning(`${ress.message}`);
          //   }
          // })
          messageMethod.success(`${res.message}`);
          emit("update:imageDialogValue", false);
          emit("updateMaterialList", res.data);
          progressDialog.complete('shoot-upload')
        })
        .catch((err) => {
          messageMethod.error("识别失败")
          progressDialog.showError('shoot-upload', '识别过程中出错')
        }).finally(() => {
          isLoading.value = false;
          loadingSure.value = false;
        })
    }
  } catch {
    messageMethod.error("识别失败")
    progressDialog.showError('shoot-upload', '识别失败')

  } finally {
    // isLoading.value = false;
    // loadingSure.value = false;
  }
}
let ws = new WebSocket("ws://localhost:8766"); 
ws.onopen = function () {
  console.log("WebSocket连接已打开");
};
// 生命周期钩子
onMounted(() => {
  const canvas = document.getElementById("cameraCanvas") as HTMLCanvasElement;
  canvas.width = 1920;
  canvas.height = 1080;
  ws = new WebSocket("ws://localhost:8766");
  ws.onopen = function () {
    console.log("WebSocket连接已打开");
  };
});




// 修改灯光控制函数
const handleLightChange = () => {
  if (lightStatus.value) {
    // 如果开关状态为 on (true)
    ws.send("12"); // 发送开灯指令
  } else {
    // 如果开关状态为 off (false)
    ws.send("13"); // 发送关灯指令
  }
};

function adjustCamera(direction: string) {
  if (direction === "small_up") {
    ws.send("41");
  } else if (direction === "small_down") {
    ws.send("42");
  } else if (direction === "medium_up") {
    ws.send("21");
  } else if (direction === "medium_down") {
    ws.send("22");
  } else if (direction === "large_up") {
    ws.send("32");
  } else if (direction === "large_down") {
    ws.send("31");
  }
}


onUnmounted(() => {
  if (videoWs.value) {
    videoWs.value.close();
  }

  // 根据当前连接的摄像头，发送对应的激光关闭指令
  if(isConnected.value) {
    switch (form.value.selectedCamera) {
      case 'camera1':
        ws.send("52"); // 激光1关
        break;
      case 'camera2':
        ws.send("55"); // 激光2关
        break;
      case 'camera3':
        ws.send("58"); // 激光3关
        break;
    }
  }

  // [REMOVED] 自动关闭灯光逻辑已被移除，以防止刷新页面时灯光意外关闭。
  // if (lightStatus.value) {
  //   console.log(lightStatus.value)
  //   ws.send('13'); // 关闭灯光
  // }

  electronApi.StopCamera().catch(console.error);


  // 释放图片URL
  imageUrls.value.forEach(url => URL.revokeObjectURL(url));
});

</script>

<style lang="scss" scoped>
.content-container {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
}

.form-container {
  width: 100%;
  padding-right: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.tips-btn {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color:rgb(152, 241, 229) !important;
  font-weight: bold;
  border-radius: 0 !important;
  height: 18px;
  font-size: 13px;
  margin: 6px 0 0 0;
  width: auto;
  white-space: nowrap;
  cursor: default;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.tips-btn-flex {
  display: flex;
  align-items: center;
  flex-direction: row;
  justify-content: flex-start;
  width: 100%;
  height: 100%;
  padding: 0;
}

.tips-btn-icon {
  font-size: 16px;
  display: flex;
  align-items: center;
  margin-right: 6px;
  position: relative;
  top: 0;
}

.tips-btn-text {
  font-size: 13px;
  display: flex;
  align-items: center;
  line-height: 1;
  color:rgb(114, 212, 239);
  margin-left: 2px;
}
.video-container {
  width: 99%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f2f2f2;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: relative;
  min-height: 300px;

  #cameraCanvas {
    width: 100%;
    height: 100%;
    position: absolute;

    &.connected {
      background-color: transparent;
    }
  }

  .camera-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    color: #999;

    .el-icon {
      font-size: 48px;
      margin-bottom: 8px;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-start;
  padding: 10px;
  gap: 10px;
}

.image-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  //margin-top: 20px;

  .thumbnail-container {
    position: relative;

    .thumbnail {
      width: 100px;
      height: 100px;
      object-fit: cover;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .delete-btn {
      position: absolute;
      top: -8px;
      right: -8px;
      background-color: #ff4d4f;
      color: white;

      &:hover {
        background-color: #ff7875;
      }
    }
  }
}

.camera-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;

  :deep(.el-button+.el-button) {
    margin-left: 2px;
  }
}

.camera-control {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.el-button-group {
  display: flex;
  gap: 1px;

  .el-button {
    flex: 1;
  }
}
</style>