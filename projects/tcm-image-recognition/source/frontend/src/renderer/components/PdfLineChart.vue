<template>
  <div class="chart-container">
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent]);

const props = defineProps({
  chartData: {
    type: Object as () => { categories: string[], values: number[] },
    required: true,
  },
});

const chartOption = computed(() => ({
  title: {
    text: '识别记录趋势',
    left: 'center',
    textStyle: {
      fontSize: 14,
      fontWeight: 'normal'
    }
  },
  tooltip: {
    trigger: 'axis',
    formatter: '{b}: {c}条'
  },
  grid: {
    left: '3%',
    right: '10%', // 留出更多空间给Y轴标签
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: props.chartData.categories,
  },
  yAxis: {
    type: 'value',
    name: '记录数'
  },
  series: [
    {
      name: '记录数',
      type: 'line',
      data: props.chartData.values,
      smooth: true, // 平滑曲线
      itemStyle: {
        color: '#00A3AD' // 麦肯锡风格青色
      },
      areaStyle: { // 填充区域颜色
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{
            offset: 0, color: '#00A3AD'
          }, {
            offset: 1, color: 'rgba(0, 163, 173, 0.1)' // 使用带透明度的渐变
          }]
        }
      }
    },
  ],
}));
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 300px;
}
.chart {
  width: 100%;
  height: 100%;
}
</style>
