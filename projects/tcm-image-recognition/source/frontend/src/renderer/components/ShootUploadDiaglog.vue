<template>
  <el-dialog :model-value="props.visible" :before-close="handleClose" width="70%">
    <template #header>
      <div class="dialog-header">
        <span class="dialog-title">{{ props.title }}</span>
        <!-- <div class="btns">
          <el-icon @click="handleClose"><Close /></el-icon>
        </div> -->
      </div>
    </template>

    <!-- 拍照上传按钮 -->
    <el-button class="button-shoot" @click="handleUploadClick" type="primary">
      <i class="el-icon-upload"></i>
      <div class="el-button__text"><em>点击拍照</em></div>
    </el-button>

    <!-- 视频和选择框区域 -->
    <div class="content-container">
      <!-- 选择框区域 -->
      <div class="form-container">
        <el-form :model="form" label-width="120px">
          <el-form-item label="灯光控制">
            <el-button @click="controlLight('on')" type="success"
              >开灯</el-button
            >
            <el-button @click="controlLight('off')" type="danger"
              >关灯</el-button
            >
          </el-form-item>
          <el-form-item label="选择类别">
            <el-radio-group v-model="form.selectedCategory">
              <el-radio value="unknown">未知类别</el-radio>
              <el-radio value="known">已知类别</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item
            label="已知类别选择"
            v-if="form.selectedCategory === 'known'"
          >
            <el-select
              v-model="form.selectedKnownOption"
              placeholder="请选择选项"
            >
              <el-option label="选项 1" value="option1"></el-option>
              <el-option label="选项 2" value="option2"></el-option>
              <el-option label="选项 3" value="option3"></el-option>
            </el-select>
          </el-form-item>

          <!-- 镜头选择 -->
          <el-form-item label="镜头选择">
            <el-button-group>
              <el-button
                :type="
                  form.selectedCamera === 'camera1' ? 'primary' : 'default'
                "
                @click="switchCamera('camera1')"
                >小镜头</el-button
              >
              <el-button
                :type="
                  form.selectedCamera === 'camera2' ? 'primary' : 'default'
                "
                @click="switchCamera('camera2')"
                >中镜头</el-button
              >
              <el-button
                :type="
                  form.selectedCamera === 'camera3' ? 'primary' : 'default'
                "
                @click="switchCamera('camera3')"
                >大镜头</el-button
              >
            </el-button-group>
          </el-form-item>

          <!-- 曝光时间 -->
          <el-form-item label="曝光时间">
            <el-input-number
              v-model="form.exposureTime"
              :min="0"
              :max="1000"
              label="曝光时间"
              size="small"
              controls-position="right"
            />
          </el-form-item>

          <el-form-item label="镜头调节">
            <div class="camera-control">
              <div class="camera-group">
                <span>小镜头</span>
                <el-button @click="adjustCamera('small_up')">上移</el-button>
                <el-button @click="adjustCamera('small_down')">下移</el-button>
              </div>
              <div class="camera-group">
                <span>中镜头</span>
                <el-button @click="adjustCamera('medium_up')">上移</el-button>
                <el-button @click="adjustCamera('medium_down')">下移</el-button>
              </div>
              <div class="camera-group">
                <span>大镜头</span>
                <el-button @click="adjustCamera('large_up')">上移</el-button>
                <el-button @click="adjustCamera('large_down')">下移</el-button>
              </div>
            </div>
          </el-form-item>

          <!-- 图片预览 -->
          <div class="image-preview">
            <div
              v-for="(img, index) in imageUrls"
              :key="index"
              class="thumbnail-container"
            >
              <img :src="img" class="thumbnail" />
            </div>
          </div>
        </el-form>
      </div>

      <!-- 视频预览区域 -->
      <div class="video-container">
        <!-- <video
          ref="videoPlayer"
          controls
          autoplay
          class="video-container"
        ></video> -->
        <canvas id="canvas"></canvas>
      </div>
    </div>

    <span slot="footer" class="dialog-footer">
      <el-button @click="shoot" type="success">拍照</el-button>
      <el-button @click="handelCancel">取 消</el-button>
      <el-button type="primary" @click="handleConfirm">确 定</el-button>
    </span>
  </el-dialog>
</template>

<script lang="ts" setup>
import { Close } from "@element-plus/icons-vue";
import { ref, onMounted, onUnmounted } from "vue";
import { useMediaSource } from "@/renderer/hooks/useMediaSource";
import hashMap from "../typeMap/tableHashMap";

const videoPlayer = ref<HTMLVideoElement>();
const { initMediaSource, appendBuffer, destroy } = useMediaSource();
const imageUrls = ref<string[]>([]);
const imagePaths = ref<string[]>([]); // 用于存储每次拍照后的图片路径
const electronApi = window.electron;

electronApi.lightControl();
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

const form = ref({
  selectedCategory: "unknown", // 默认选择 "未知类别"
  selectedKnownOption: "", // "已知类别" 选项
  selectedCamera: "camera1", // 默认选择镜头 1
  exposureTime: 100, // 默认曝光时间
});

const handleClose = () => {
  emit("update:imageDialogValue", false);
  stopCamera();
};

const handleConfirm = async () => {
  if (imagePaths.value.length > 0) {
    const savedImagePaths = imagePaths.value;

    // 遍历图片路径，传递给 `processImage`
    savedImagePaths.forEach((imagePath) => {
      electronApi.processImage(imagePath);
    });

    // 监听预测结果并更新界面
        electronApi.onPredictResult((result: any, base64Image: string) => { // ⚠️ result 类型改为 any
      try {
        // ⚠️ 移除 JSON.parse(result); 主进程现在直接发送 JavaScript 对象
        // const parsedResult = JSON.parse(result); 

        // 预测结果在 result.data 数组的第一个元素中
        // 后端 /predict/batch 接口返回的 `result.data` 是一个数组，即使只处理一个文件，它也仍然是一个包含单个元素的数组。
        const predictionData = result.data[0]; 

        // 确保 predictionData 存在且包含 'data' 属性
        if (predictionData && predictionData.data) {
          const predictionName = predictionData.data.prediction; 
          const herb = hashMap.get(predictionName);

          if (herb) {
            const predictionResult = {
              thumbnail: base64Image,
              chineseName: predictionName,
              latinName: herb.latinName,
              standard: herb.origin,
              confidence: predictionData.data.confidence || "1.0", 
            };

            console.log("====================================");
            console.log(predictionResult);
            console.log("====================================");

            emit("updateMaterialList", predictionResult);
          }
        } else {
          console.error("后端返回的预测数据结构不符合预期或缺少数据:", result);
        }
      } catch (error) {
        console.error("处理预测结果失败:", error);
      }
    });

    emit("update:imageDialogValue", false);
  } else {
    console.warn("没有拍照的图片");
  }
};

const handelCancel = () => {
  imageUrls.value = [];
  emit("update:imageDialogValue", false);
  stopCamera();
};

let wsRef = ref<WebSocket | null>(null);
let count = 0;

// 切换摄像头函数
const switchCamera = async (cameraId: string) => {
  console.log(`切换摄像头到 ${cameraId}，关闭旧的 WebSocket`);

  form.value.selectedCamera = cameraId;
  electronApi.switchCamera(cameraId);

  console.log(`切换到 ${cameraId}`);

  // 清空画布
  const canvas = document.getElementById("canvas") as HTMLCanvasElement;
  const ctx = canvas.getContext("2d");
  canvas.width = 1920;
  canvas.height = 1080;

  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // 创建新的 WebSocket 连接
  wsRef.value = new WebSocket("ws://localhost:8765");

  // WebSocket 连接成功时的回调
  wsRef.value.onopen = () => {
    console.log("WebSocket 连接已打开");
  };

  // 接收到视频流数据的回调
  wsRef.value.onmessage = async (event) => {
    console.log(`收到视频流数据`);
    if (!event.data) {
      console.warn("未收到有效的视频数据");
      return;
    }

    try {
      const bitmap = await createImageBitmap(event.data);
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      }
    } catch (error) {
      console.error("渲染视频流时发生错误:", error);
    }
  };

  // WebSocket 错误时的回调
  wsRef.value.onerror = (err) => {
    console.error("WebSocket 错误:", err);
  };

  // WebSocket 关闭时的回调
  wsRef.value.onclose = () => {
    console.log("WebSocket 连接已关闭");
  };
};

// 启动摄像头
const handleUploadClick = async () => {
  // 启动摄像头
  switchCamera(form.value.selectedCamera);
  // const canvas = document.getElementById("canvas") as HTMLCanvasElement;
  // const ctx = canvas.getContext("2d");

  // // 设置 canvas 的大小为较高的分辨率
  // canvas.width = 1920;
  // canvas.height = 1080;

  // electronApi.receiveFrame((data: any) => {
  //   const blob = new Blob([data], { type: "image/jpeg" });
  //   const img = new Image();
  //   const imageUrl = URL.createObjectURL(blob);
  //   img.src = imageUrl;
  //   img.onload = () => {
  //     if (ctx) {
  //       ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  //     }
  //     URL.revokeObjectURL(imageUrl);
  //   };
  // });
};

// const ws = new WebSocket("ws://localhost:8765");
// const mediaSourceUrl = await initMediaSource(); // 直接返回 URL 字符串
// if (videoPlayer.value) {
//   videoPlayer.value.src = mediaSourceUrl; // 直接赋值，不需要再调用 URL.createObjectURL
// }
// ws.binaryType = "arraybuffer";
// ws.onopen = () => {
//   console.log("--------------------");

//   console.log("WebSocket 连接已打开");
// };
// ws.onmessage = (event) => {
//   const data = new Uint8Array(event.data);
//   const chunkSize = new DataView(data.buffer).getUint32(0);
//   const chunk = data.subarray(4, 4 + chunkSize);
//   appendBuffer(chunk);
// };

// 资源清理
// onUnmounted(() => {
//   ws?.close();
//   destroy();
// });

// 停止摄像头流
const stopCamera = () => {
  electronApi.StopCamera();
};

// 拍照
const shoot = () => {
  const canvas = document.getElementById("canvas") as HTMLCanvasElement;

  if (canvas) {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          const imgUrl = URL.createObjectURL(blob);
          imageUrls.value.push(imgUrl); // 添加到图片预览列表

          const reader = new FileReader();
          reader.onloadend = () => {
            const base64Data = reader.result as string;

            // 保存每一张图片的路径
            electronApi
              .saveImage(
                base64Data.replace(/^data:image\/png;base64,/, ""),
                `image${imageUrls.value.length}.png`
              )
              .then((path: any) => {
                if (path) {
                  imagePaths.value.push(path); // 保存图片路径
                  console.log(`图片保存成功: ${path}`);
                } else {
                  console.error("图片保存失败");
                }
              })
              .catch((err: any) => {
                console.error("保存图片时出错:", err);
              });
          };

          reader.readAsDataURL(blob); // 将 Blob 数据转为 base64 字符串
        }
      },
      "image/png",
      1 // 无损质量
    );
  }
};
//连接websocket
const ws = new WebSocket("ws://localhost:8766");
ws.onopen = function () {
  console.log("WebSocket连接已打开");
};

// 镜头调节
function adjustCamera(direction: string) {
  if (direction === "small_up") {
    ws.send("41");
  } else if (direction === "small_down") {
    ws.send("42");
  } else if (direction === "medium_up") {
    ws.send("31");
  } else if (direction === "medium_down") {
    ws.send("32");
  } else if (direction === "large_up") {
    ws.send("21");
  } else if (direction === "large_down") {
    ws.send("22");
  }
}
function controlLight(action: string) {
  if (action === "on") {
    ws.send("12");
  } else if (action === "off") {
    ws.send("13");
  }
}
</script>

<style lang="scss" scoped>
.button-shoot {
  display: block;
  width: 100%;
  margin-bottom: 20px;
  text-align: center;
}

.content-container {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  position: relative;
}

.form-container {
  width: 40%;
  padding-right: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.video-container {
  width: 90%;
  height: 500px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f2f2f2;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: relative;
}

canvas {
  width: 100%;
  height: 100%;
  position: absolute;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  padding: 10px;
}

.image-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
}

.thumbnail {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
