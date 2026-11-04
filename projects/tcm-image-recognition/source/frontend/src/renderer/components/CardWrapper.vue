<template>
  <el-card class="stat-card">
    <!-- Header 部分 -->
    <div class="card-content">
      <div class="card-header">
        <span class="title">{{ title }}</span>
        <div class="chart-icon" v-if="icon">
          <el-icon :component="icon" />
        </div>
        <div v-if="btnTitle && btnClick">
          <el-button type="primary" plain @click="btnClick()">{{ btnTitle }}</el-button>
          <slot name="btn"> </slot>
        </div>
      </div>

      <!-- Body 部分，支持动态插入内容 -->
      <div class="card-body">
        <slot></slot>
      </div>
    </div>
    <!-- Footer 部分 -->
    <div class="card-footer">
      <slot name="footer"> </slot>
    </div>
  </el-card>
</template>

<script lang="ts" setup>
import { ElCard, ElIcon } from "element-plus";
import { type PropType } from "vue";

const props = defineProps({
  title: String,
  icon: {
    type: Object as PropType<Record<string, any> | null>,
    required: false,
    default: null,
  },
  btnTitle:String,
  btnClick: Function,
});
</script>

<style scoped lang="scss">
.stat-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  /* overflow: visible; /* 允许内容溢出，不隐藏 */ 
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.title {
  font-size: 14px;
  color: #909399;
  text-transform: uppercase;
}

.chart-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #f56c6c;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  /* overflow: visible; /* 允许内容溢出，不隐藏 */
} 

.card-footer {
  margin-top: 16px;
  text-align: right;
  font-size: 14px;
  color: #909399;
}
</style>
