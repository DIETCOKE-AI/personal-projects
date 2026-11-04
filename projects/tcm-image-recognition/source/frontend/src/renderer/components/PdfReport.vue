<template>
  <div class="report-container" ref="reportRef">
    <div class="watermark"></div>
    <h1 class="report-title">中药材识别记录报告</h1>
    
    <!-- 图表区域 -->
    <div class="charts-area" v-if="pieData && pieData.length > 0">
      <!-- 上层：饼图，独占一行 -->
      <div class="chart-row">
        <div class="chart-wrapper chart-wrapper-full">
          <PdfPieChart :rawData="pieData" />
        </div>
      </div>
      <!-- 下层：柱状图和折线图，并排 -->
      <div class="chart-row">
        <div class="chart-wrapper">
          <PdfBarChart :chartData="barChartData" />
        </div>
        <div class="chart-wrapper">
          <PdfLineChart :chartData="lineChartData" />
        </div>
      </div>
    </div>

    <div class="report-summary" v-if="pieData && pieData.length > 0">
      共导出 {{ pieData.length }} 条记录
    </div>

    <!-- 表格区域 -->
    <table class="report-table" v-if="tableData && tableData.length > 0">
      <thead>
        <tr>
          <th>#</th>
          <th>图片</th>
          <th>中文名</th>
          <th>拉丁名</th>
          <th>置信度</th>
          <th>标准</th>
          <th>上传用户</th>
          <th>登记时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in tableData" :key="item.id">
          <td>{{ startIndex + index + 1 }}</td>
          <td><img :src="item.imageBase64" alt="药材图片"></td>
          <td>{{ item.subclassChineseName || '-' }}</td>
          <td>{{ item.latinName || '-' }}</td>
          <td>{{ item.confidence || '-' }}</td>
          <td>{{ formatSource(item.source) }}</td>
          <td>{{ item.creatorName || '-' }}</td>
          <td>{{ item.createdAt || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { defineProps, computed } from 'vue';
import PdfPieChart from './PdfPieChart.vue';
import PdfBarChart from './PdfBarChart.vue';
import PdfLineChart from './PdfLineChart.vue';

const props = defineProps({
  pieData: { type: Array as () => Array<any>, default: () => [] },
  tableData: { type: Array as () => Array<any>, default: () => [] },
  startIndex: { type: Number, default: 0 }
});

// 柱状图数据：置信度分布
const barChartData = computed(() => {
  // 安全检查：如果pieData为空，则返回空图表数据，防止在纯表格页报错
  if (!props.pieData || props.pieData.length === 0) {
    return { categories: [], values: [] };
  }
  const categories = ['95-100', '90-94', '80-89', '70-79', '<70'];
  const values = [0, 0, 0, 0, 0];
  props.pieData.forEach(item => {
    // 修正：将小数形式的置信度乘以100，转换为百分比再进行比较
    const confidence = parseFloat(item.confidence) * 100;
    if (confidence >= 95) values[0]++;
    else if (confidence >= 90) values[1]++;
    else if (confidence >= 80) values[2]++;
    else if (confidence >= 70) values[3]++;
    else values[4]++;
  });
  return { categories, values };
});

// 折线图数据：识别趋势
const lineChartData = computed(() => {
  // 安全检查：如果pieData为空，则返回空图表数据
  if (!props.pieData || props.pieData.length === 0) {
    return { categories: [], values: [] };
  }
  const countsByDate: Record<string, number> = {};
  props.pieData.forEach(item => {
    const date = item.createdAt.split(' ')[0]; // 只取年月日部分
    countsByDate[date] = (countsByDate[date] || 0) + 1;
  });

  const sortedDates = Object.keys(countsByDate).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
  const categories = sortedDates;
  const values = sortedDates.map(date => countsByDate[date]);

  return { categories, values };
});

const formatSource = (source: any[]) => {
  if (!source || source.length === 0) return '-';
  return source.map(s => s.standardName).join(", ");
};
</script>

<style scoped>
.report-container {
  position: relative;
  background-color: #fff;
  padding: 40px;
  width: 210mm;
  box-sizing: border-box;
  font-family: 'SimSun', '宋体', sans-serif;
}

.charts-area {
  margin-bottom: 20px;
}

.chart-row {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: 20px;
}

.chart-wrapper {
  flex: 1;
  min-width: 0;
}

.chart-wrapper-full {
  flex-basis: 100%;
}

.watermark {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  background-image: url('/image-placeholder.svg');
  background-repeat: no-repeat; /* 改为不重复 */
  background-position: center center; /* 定位到中心 */
  background-size: 50%; /* 设置水印大小 */
  opacity: 0.05; /* 降低透明度 */
}

.report-title {
  text-align: center;
  font-size: 24px;
  margin-bottom: 20px;
  color: #333;
}

.report-summary {
  text-align: center;
  font-size: 12px;
  color: #666;
  margin-top: 10px;
  margin-bottom: 20px;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
  margin-bottom: 20px;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  overflow: hidden;
}

.report-table tr {
  height: 100px; 
  page-break-inside: avoid;
  border-bottom: 1px solid #EAEAEA;
}

.report-table tbody tr:last-child {
  border-bottom: none;
}

.report-table tbody tr:nth-child(even) {
  background-color: #F8F8F8;
}

.report-table th, .report-table td {
  padding: 10px 12px;
  text-align: left;
  vertical-align: middle;
  border: none;
}

.report-table th {
  background-color: #005B94;
  color: white;
  font-weight: bold;
  border-bottom: none;
}

.report-table th:first-child, .report-table td:first-child,
.report-table th:nth-child(2), .report-table td:nth-child(2),
.report-table th:nth-child(5), .report-table td:nth-child(5) {
  text-align: center;
}

.report-table img {
  max-width: 60px;
  max-height: 60px;
  display: block;
  margin: auto;
  border-radius: 4px;
}
</style>
