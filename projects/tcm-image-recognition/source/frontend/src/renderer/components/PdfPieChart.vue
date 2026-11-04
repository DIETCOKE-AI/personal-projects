<template>
  <div ref="chartRef" class="pdf-pie-chart"></div>
</template>

<script lang="ts" setup>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts/core';
import { PieChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([TitleComponent, TooltipComponent, LegendComponent, PieChart, CanvasRenderer]);

const props = defineProps({
  rawData: {
    type: Array as () => Array<any>,
    required: true,
  },
});

const chartRef = ref<HTMLElement | null>(null);

const renderChart = () => {
  if (!chartRef.value || !props.rawData || props.rawData.length === 0) return;

  const categoryCount = props.rawData.reduce((acc, item) => {
    const categoryName = item.subclassChineseName || '未知类别';
    acc[categoryName] = (acc[categoryName] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartData = Object.entries(categoryCount).map(([name, value]) => ({ name, value }));

  // --- 开始执行“数据垫高”方案 ---
  const values = chartData.map(item => item.value);
  const sum = values.reduce((s, v) => s + v, 0);
  const max = values.length > 0 ? Math.max(...values) : 0;
  // 将最大值放大20%后，取一个随机整数作为“垫高值”
  const number = Math.floor(max * 1.2);

  // 生成用于视觉展示的“垫高后”的数据
  const showData = chartData.map(item => ({
    name: item.name,
    value: item.value, // 核心：为每个值加上“垫高值”
  }));

  const myChart = echarts.init(chartRef.value);

  const option = {
    title: { text: '导出项目比例图', left: 'center' },
    tooltip: {
      trigger: 'item',
      // **关键：formatter使用函数，以显示原始数据**
      formatter: (params) => {
        const originalValue = params.value - number; // 从“垫高后”的值中，减去“垫高值”，得到原始值
        const percent = sum > 0 ? ((originalValue / sum) * 100).toFixed(2) : 0;
        return `${params.name} : ${originalValue}条 (${percent}%)`;
      }
    },
    legend: {
      orient: 'horizontal',
      left: 'center',
      bottom: 5,
      data: chartData.map(item => item.name)
    },
    // 新增：应用麦肯锡风格色板
    color: [
      '#005B94', // 主蓝色
      '#8C8C8C', // 中性灰
      '#00A3AD', // 青色
      '#BDBDBD', // 浅灰
      '#F5A623', // 强调橙
      '#50E3C2'  // 薄荷绿
    ],
    series: [
      {
        name: '药材种类',
        type: 'pie',
        radius: ['30%', '65%'], // **关键：使用范围数组来创建带空心圆的玫瑰图**
        center: ['50%', '45%'],
        roseType: 'radius', // 重新启用 roseType
        itemStyle: {
          borderRadius: 5
        },
        data: showData, // **使用“垫高后”的数据来绘制图表**
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}: {d}%' // 标签显示的百分比是基于“垫高后”数据的，这在视觉上是正确的
        },
        labelLine: {
          show: true
        },
        animation: false,
      },
    ],
  };

  myChart.setOption(option);
};

onMounted(() => {
  renderChart();
});

watch(() => props.rawData, () => {
  renderChart();
}, { deep: true });

</script>

<style scoped>
.pdf-pie-chart {
  width: 700px;
  height: 650px; /* 增加总高度，为图例和标签提供更充裕的空间 */
  margin: 20px auto;
  overflow: 'breakAll' 
}
</style>