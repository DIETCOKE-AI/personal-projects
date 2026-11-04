<template>
  <el-card class="stat-card">
    <div class="card-content">
      <div class="card-header">
        <span class="title">{{ title }}</span>
        <div class="chart-icon">
          <el-icon>
            <!-- 使用动态绑定的 icon 组件 -->
            <component :is="icon" />
          </el-icon>
        </div>
      </div>
      <div class="card-body">
        <h3>{{ h3Content }}</h3>
        <div class="stat-info" v-if="iconShow">
          <el-icon :color="iconColor" >
            <component :is="trendIcon" />
          </el-icon>
          <span class="percentage">{{ percentage }}</span>
          <span class="period">{{ period }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ElCard, ElIcon } from "element-plus";
import { Top, Bottom, TrendCharts, User } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

defineProps({
  title: String,
  icon: {
    type: Object, // 传递的 icon 现在是组件对象
    required: true,
  },
  h3Content: String,
  percentage: String,
  period: String,
  trend: {
    type: String,
    default: "up",
  },
  iconColor: {
    type: String,
    default: "#67c23a",
  },
  iconShow:{
    type: Boolean,
    default: true,
  }
});

const trend = ref("up");
const trendIcon = computed(() => {
  return trend.value === "up" ? Top : Bottom; // 根据 trend 来选择 Top 或 Bottom 图标
});
</script>

<style scoped lang="scss">
.stat-card {
  background-color: #fff;
  border-radius: 8px;

  .card-content {
    padding: 20px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      .title {
        font-size: 12px;
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

        &.orange {
          background-color: #ff9f43;
        }
      }
    }

    .card-body {
      h3 {
        margin: 0 0 16px;
        font-size: 24px;
        font-weight: 500;
      }

      .stat-info {
        display: flex;
        align-items: center;
        gap: 8px;

        .percentage {
          font-weight: 500;
        }

        .period {
          color: #909399;
          font-size: 12px;
        }
      }
    }
  }
}
</style>
