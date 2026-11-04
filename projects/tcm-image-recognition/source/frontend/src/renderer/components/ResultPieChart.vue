<template>
  <div class="chart-container">
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, onMounted } from 'vue'; // **移除了 computed，增加了 watch 和 onMounted**
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { PieChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

// **新增：一个简单的防抖工具函数**
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

use([CanvasRenderer, PieChart, TitleComponent, TooltipComponent, LegendComponent]);

const props = defineProps({
  results: {
    type: Array as () => Array<any>,
    required: true,
  },
});

// **将 chartOption 从 computed 改为 ref**
const chartOption = ref({});

// **定义一个独立的、用于更新图表的函数**
const updateChart = () => {
  const categoryCount = props.results.reduce((acc, item) => {
    let categoryName = null;
    if (item.data && item.data.chineseName) {
      categoryName = item.data.chineseName;
    } else if (item.chineseName) {
      categoryName = item.chineseName;
    }
    if (categoryName) {
      acc[categoryName] = (acc[categoryName] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  const chartData = Object.entries(categoryCount).map(([name, value]) => ({ name, value }));

  chartOption.value = {
    title: {
      text: '识别结果比例图',
      left: 'center',
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b} : {c}张 ({d}%)',
    },
    // 新增：根据用户提供的配色方案进行颜色主题定义
    color: [
      '#4cc6f8', '#4ed0f7', '#52e2f4', '#5fecee', '#6df1e8', '#84f5de'
    ],
    series: [
      {
        name: '识别结果',
        type: 'pie',
        // **修改为标准饼图样式**
        // roseType: 'radius', // 已移除，改为标准饼图
        radius: '55%', // 设置为实心饼图，无中空
        center: ['50%', '55%'],
        itemStyle: {
          borderRadius: 5 // 添加圆角，让扇区更美观
        },
        data: chartData,
        // **恢复您之前的标签配置**
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}: {d}%',
          alignTo: 'edge',
          minMargin: 5,
          edgeDistance: 10,
          lineHeight: 16,
          overflow: 'breakAll'
        },
        labelLine: { 
          show: true,
          length: 15,
          length2: 10,
          smooth: 0.5
        },
        emphasis: {
          // 新增：鼠标悬浮时放大扇区，以响应交互
          scale: true,
          scaleSize: 15,
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  };
};

// **创建一个带防抖的更新函数**
const debouncedUpdate = debounce(updateChart, 300); // 300毫秒的防抖延迟

// **监听 props.results 的变化，并调用带防抖的函数**
watch(() => props.results, () => {
  debouncedUpdate();
}, { deep: true });

// **在组件首次挂载时，立即执行一次更新**
onMounted(() => {
  updateChart();
});

</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 400px;
  margin-top: 20px;
}
.chart {
  width: 100%;
  height: 100%;
}
</style>