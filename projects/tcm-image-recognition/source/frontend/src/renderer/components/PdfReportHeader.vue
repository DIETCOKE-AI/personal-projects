
<template>
  <div class="report-header-container">
    <h1 class="report-title">中药材识别记录报告</h1>
    <PdfPieChart v-if="historyData.length > 0" :rawData="historyData" />
    <div class="total-summary">
      总计: {{ historyData.length }}条
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';
import PdfPieChart from './PdfPieChart.vue';

defineProps({
  historyData: {
    type: Array as () => Array<any>,
    required: true,
  },
});
</script>

<style scoped>
.report-header-container {
  background-color: #fff;
  padding: 40px;
  width: 210mm; /* A4 宽度 */
  box-sizing: border-box;
  font-family: 'SimSun', '宋体', sans-serif;
}
.report-title {
  text-align: center;
  font-size: 24px;
  margin-bottom: 20px;
}
.total-summary {
  text-align: center;
  font-size: 16px;
  font-weight: bold;
  margin-top: 10px;
  color: #333;
}
</style>
