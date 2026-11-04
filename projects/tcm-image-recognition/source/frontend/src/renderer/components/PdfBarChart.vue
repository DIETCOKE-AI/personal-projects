<template>
  <div class="chart-container">
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, BarChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent]);

const props = defineProps({
  // 接收处理好的图表数据
  chartData: {
    type: Object as () => { categories: string[], values: number[] },
    required: true,
  },
});

// 使用计算属性来动态生成图表配置
const chartOption = computed(() => ({
  title: {
    text: '置信度分布情况',
    left: 'center',
    textStyle: {
      fontSize: 14,
      fontWeight: 'normal'
    }
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    },
    formatter: '{b}: {c}条'
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: props.chartData.categories,
    axisLabel: {
      interval: 0,
      rotate: 30 // 倾斜标签以防重叠
    }
  },
  yAxis: {
    type: 'value',
    name: '记录数'
  },
  series: [
    {
      name: '记录数',
      type: 'bar',
      data: props.chartData.values,
      barWidth: '60%',
      itemStyle: {
        color: '#005B94' // 麦肯锡风格主蓝色
      }
    },
  ],
}));

</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 300px; /* 给图表一个默认高度 */
  margin-top: 20px;
}
.chart {
  width: 100%;
  height: 100%;
}
</style>
