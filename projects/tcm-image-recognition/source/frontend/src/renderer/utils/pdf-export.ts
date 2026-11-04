
import { createApp } from 'vue';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { ElMessage } from 'element-plus';
import PdfReport from '../components/PdfReport.vue';

// 定义每页渲染的固定行数
const ROWS_PER_PAGE = 8; // 这是一个可以根据实际效果微调的关键参数

/**
 * 使用“按固定行数切片，逐页渲染”的方案导出PDF
 * @param historyData 要导出的数据
 */
export const exportHistoryToPdf = async (historyData: any[]) => {
  if (!historyData || historyData.length === 0) {
    ElMessage.warning('没有可导出的数据');
    return;
  }

  ElMessage.info('正在生成PDF，由于数据量较大，可能需要一些时间，请稍候...');

  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'pt',
    format: 'a4',
  });

  try {
    // --- 第一步：单独渲染并添加饼图页 ---
    const chartContainer = document.createElement('div');
    chartContainer.style.position = 'absolute';
    chartContainer.style.left = '-9999px';
    document.body.appendChild(chartContainer);
    // 只传递饼图需要的数据
    const chartApp = createApp(PdfReport, { pieData: historyData });
    chartApp.mount(chartContainer);
    await new Promise(resolve => setTimeout(resolve, 1500));
    const chartElement = chartContainer.querySelector('.report-container') as HTMLElement;
    const chartCanvas = await html2canvas(chartElement, { scale: 2, useCORS: true });
    const chartPageWidth = pdf.internal.pageSize.getWidth();
    const chartPageHeight = (chartCanvas.height * chartPageWidth) / chartCanvas.width;
    pdf.addImage(chartCanvas.toDataURL('image/jpeg', 1.0), 'JPEG', 0, 0, chartPageWidth, chartPageHeight);
    chartApp.unmount();
    document.body.removeChild(chartContainer);

    // --- 第二步：循环渲染并添加表格数据页 ---
    const totalTablePages = Math.ceil(historyData.length / ROWS_PER_PAGE);

    for (let i = 0; i < totalTablePages; i++) {
      const startIndex = i * ROWS_PER_PAGE;
      const endIndex = startIndex + ROWS_PER_PAGE;
      const pageTableData = historyData.slice(startIndex, endIndex);

      const tableContainer = document.createElement('div');
      tableContainer.style.position = 'absolute';
      tableContainer.style.left = '-9999px';
      document.body.appendChild(tableContainer);
      
      // 核心：创建一个只包含当页表格数据的报告实例
      const tableApp = createApp(PdfReport, { tableData: pageTableData, startIndex: startIndex });
      tableApp.mount(tableContainer);
      await new Promise(resolve => setTimeout(resolve, 1000));
      const tableElement = tableContainer.querySelector('.report-container') as HTMLElement;
      const tableCanvas = await html2canvas(tableElement, { scale: 2, useCORS: true });
      
      pdf.addPage(); // 为每一页表格创建新页面
      const tablePageWidth = pdf.internal.pageSize.getWidth();
      const tablePageHeight = (tableCanvas.height * tablePageWidth) / tableCanvas.width;
      pdf.addImage(tableCanvas.toDataURL('image/jpeg', 1.0), 'JPEG', 0, 0, tablePageWidth, tablePageHeight);

      tableApp.unmount();
      document.body.removeChild(tableContainer);
    }

    pdf.save('记录报告.pdf');
    ElMessage.success('PDF导出成功！');

  } catch (error) {
    console.error('生成PDF时出错:', error);
    ElMessage.error('生成PDF失败，请查看控制台获取更多信息。');
    // 确保即使出错也清理所有临时DOM
    const tempContainers = document.querySelectorAll('div[style*="left: -9999px"]');
    tempContainers.forEach(c => c.remove());
  }
};
