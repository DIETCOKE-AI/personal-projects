<!-- 缩略图弹窗 -->
<template>
  <el-dialog :model-value="props.visible" :show-close="false" width="900px">
    <template #header>
      <div class="dialog-header">
        <span class="dialog-title">{{ props.title }}</span>
        <div class="btns">
          <el-icon @click="handleFullScreen"><FullScreen /></el-icon>
          <el-icon @click="handleClose"><Close /></el-icon>
        </div>
      </div>
    </template>

    <div class="dialog-img">
      <img :src="props.imgUrl" alt="Dialog Image" />
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts" setup>
import { FullScreen, Close } from "@element-plus/icons-vue";
const baseUrl=import.meta.env.VITE_API_BASE_URL

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  imgUrl: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const handleClose = () => {
  emit("update:modelValue", false);
};

// 可添加全屏逻辑
const handleFullScreen = () => {
  // TPDO: 实现全屏逻辑
};
</script>

<style scoped lang="scss">
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.dialog-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.btns {
  display: flex;
  gap: 12px;
}

.dialog-img {
  text-align: center;
  padding: 20px;
}

.dialog-img img {
  width: 100%;
  // max-width: 500px;
  height: auto;
  border-radius: 8px;
}

.el-button {
  font-size: 14px;
  height: 36px;
}

.el-dialog__footer {
  padding: 10px 20px;
}

.el-icon {
  cursor: pointer;
  font-size: 20px;
  color: #409eff;
  transition: color 0.3s ease;
}

.el-icon:hover {
  color: #66b1ff;
}

/* 确认关闭弹窗样式 */
.el-dialog--small {
  width: 300px;
}

.el-dialog__header {
  background-color: #f0f4f7;
  border-bottom: 1px solid #ebebeb;
}

.el-dialog__footer {
  text-align: right;
}

.el-button--primary {
  background-color: #409eff;
  border-color: #409eff;
}

.el-button--primary:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}
</style>
