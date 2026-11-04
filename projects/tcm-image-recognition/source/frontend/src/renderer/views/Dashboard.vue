<template>
  <div class="dashboard">
    <!-- 上半部分 - 紫色背景区域 -->

    <!-- <StartCard>
      
      <card title="image" :icon="TrendCharts" h3Content="拍照识别" trend="up" iconColor="#8687e7"
        @click="()=>{imageShow='image'}" :iconShow="false" />
      <card title="upload" :icon="User" h3Content="图片识别" trend="up" iconColor="#f56c6c"  @click="()=>{imageShow='upload'}"
        :iconShow="false" />
    </StartCard> -->

    <!-- 下半部分 - 白色背景区域 -->
    <div class="content-section">
      <div class="column">
        <div class="column-left">
          <div class="resize-bar"></div>
          <div class="resize-line"></div>
          <div class="resize-save">
            <el-tabs v-model="imageShow">
              <el-tab-pane label="拍照识别" name="image" style="padding-top: 8px;overflow-y: scroll;">
                <ShootUpload @updateMaterialList="updateMaterialList" title="点击拍照"
                  :visible.sync="shootUploadDialogVisible" @update:imageDialogValue="closeShootUploadDiaglog"
                  @close="closeShootUploadDiaglog" />
              </el-tab-pane>
              <el-tab-pane label="图片识别" name="upload" style="padding-top: 8px;">
                <ImgUpload @updateMaterialList="updateMaterialList" title="上传图片" :visible.sync="imgUploadDialogVisible"
                  @update:imageDialogValue="closeImgUploadDialog" @close="closeImgUploadDialog" />
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
        <div class="column-right">
          <div class="data-tables">
            <CardWrapper title="识别结果（置信度越高，识别可信度越高）" :icon="null" :btnClick="handleExportPdf" :btnTitle="'结果导出PDF'" class="card-wrapper">
              <template #btn>
                <!-- <el-button type="primary" plain @click="clearList()">清空</el-button> -->
              </template>
              <div class="table-container dashboard-table-container">
                <el-table :row-class-name="tableRowClassName" :data="dataList"
                  style="width: 100%; height: auto; max-height: none;" ref="materiaTable"
                  @selection-change="handleSelectionChange">
                  <!-- <el-table-column type="selection" width="55" :selectable="selectable" /> -->
                  <el-table-column type="selection" width="55" />
                  <el-table-column type="index" width="50" label="#" />
                  <el-table-column label="缩略图" width="100" align="center">
                    <template #default="{ row }">
                    <!--  <img :src="`/flask/${row.imagePath}`" alt="缩略图" class="thumbnail" @click="openImageDialog(row)"
                        style="width: 60px; height: 60px" /> -->
                      <img 
                      :src="getImageUrl(row.imagePath)" 
                      alt="缩略图" 
                      class="thumbnail" 
                      @click="openImageDialog(row)"
                      style="width: 60px; height: 60px" />
                    </template>
                  </el-table-column>
                  <el-table-column prop="chineseName" width="120" label="中文名称" sortable>
                    <template #default="{ row }">
                      <el-link type="primary" @click="clickNameDetail(row)">{{ row.chineseName ?? '-' }}</el-link>
                    </template>
                  </el-table-column>
                  <el-table-column prop="latinName" width="100" label="拉丁名" sortable />
                  <el-table-column prop="standard" width="100" label="标准" sortable>
                    <template #default="{ row }">
                      <div>{{ row.standard ?? '-' }}</div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="confidence" width="100" label="置信度" sortable />
                  <el-table-column label="更多" width="100" align="center">
                    <template #default="{ row }">
                      <el-button type="primary" size="small" @click="openMore(row)">更多</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <template #footer>
                <div class="pagination-wrapper" style="margin-bottom: 10px;">
                  <!-- 确保分页组件正确渲染 -->
                  <el-pagination v-if="dataList.length > 0" :page-size="pagination.rows" :total="pagination.total"
                    :current-page="pagination.page" @current-change="handlePageChange" layout="prev, pager, next" />
                </div>
              </template>
              
            </CardWrapper>
            <!-- 新的父容器，用于并排显示统计和图表 -->
              <div class="stats-and-chart-container" style="display: flex; flex-direction: column; gap: 20px;">
                <!-- 原有的统计模块 -->
                <div class="herb-stats-outer" style="flex: 1;">
                  <div class="herb-stats-wrapper" v-if="herbStats.stats.length > 0">
                    <div class="herb-stats-title">识别统计</div>
                    <div class="herb-stats-total">总计上传：{{ herbStats.total }} 张</div>
                    <div class="herb-stats-list">
                      <div v-for="item in herbStats.stats" :key="item.herbName" class="herb-stats-item">
                        <span class="herb-name">{{ item.herbName }}</span>
                        <span class="herb-count">{{ item.count }} 张</span>
                      </div>
                    </div>
                  </div>
                </div>
                <!-- 新增的图表模块 -->
                <div class="chart-outer" style="flex: 1;" v-if="materialList.length > 0">
                  <ResultPieChart :results="materialList" />
                </div>
              </div>
            <!-- 统计区块 -->
          </div>
        </div>
      </div>


      <!-- 图表展示区域 -->
      <!-- <div v-if="materialList.length > 0">
        <CardWrapper title="统计图表" :icon="null">
          <div class="count_chart">
            <div id="pie_chart"></div>
            <div id="bar_chart"></div>
          </div>
        </CardWrapper>
      </div> -->


    </div>

    <!-- 缩略图弹窗 -->
    <ImageDialog :visible.sync="imageDialogValue" title="上传图片"
      :imgUrl="selectedMaterial && selectedMaterial.imagePath ? getImageUrl(selectedMaterial.imagePath) : ''"
      @update:modelValue="closeImageDialog" @close="closeImageDialog">
    </ImageDialog>

    <!-- 更多内容的弹窗 -->
    <MoreDialog :visible.sync="moreDialogVisible" title="更多可能" @update:dialogVisible="closeMoreDialog"
      :moreData="moreData" @close="closeMoreDialog" />

      <HerbsDetailsDialog
        :visible.sync="herbsDetailsVisible"
        :detailData="selectedHerb"
        @update:herbsDetailsVisible="closeHerbsDetailDialog"
      />
      <div v-if="selectedHerb">{{ selectedHerb.name }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive, computed, watch } from "vue";
import CardWrapper from "@/renderer/components/CardWrapper.vue";
import ImageDialog from "@/renderer/components/ImageDialog.vue";
import MoreDialog from "@/renderer/components/MoreDialog.vue";
import * as echarts from "echarts";
import pie_option from "../echarts/pie_chart.js";
import bar_option from "../echarts/bar_chart.js";
import { ElMessage } from 'element-plus';
import { exportHistoryToPdf } from "@/renderer/utils/pdf-export";
import { exportToExcel } from "@/renderer/utils/conmon";
import ImgUpload from "../components/ImgUpload.vue";
import ShootUpload from "../components/ShootUpload.vue";
import HerbsDetailsDialog from "../components/HerbsDetailsDialog.vue";
import requestMethodHerb from '../api/herb/herb'
import ResultPieChart from '../components/ResultPieChart.vue'
import { progressDialog } from "@/renderer/utils/loadingmask-util";

const baseUrl = import.meta.env.VITE_API_BASE_URL;

const clearList = () => {
  dataList.value=[]
  materialList.value = []
}

const herbsDetailsVisible = ref(false)
const selectedHerb = ref<any>({ source: [] })

const closeHerbsDetailDialog = () => {
  herbsDetailsVisible.value = false;
  setTimeout(() => {
    selectedHerb.value = { source: [] }
  }, 300)
};

const clickNameDetail = (row:any)=>{
  console.log('点击了', row)
  herbsDetailsVisible.value = true
  requestMethodHerb
    .getOne({ id:row.id })
    .then((res:any) => {
      selectedHerb.value = { ...res.data, source: res.data.source || [] }
    })
    .finally(() => {
      console.log(selectedHerb.value)
    })
}
const getImageUrl = (imagePath: string) => {
  if (import.meta.env.DEV) {
    return `/flask${imagePath}`; // 开发环境走代理
  } else {
    return `http://localhost:5000${imagePath}`; 
  }
};
const moreData = ref<any>([])

//表格加载中
const loading = ref<boolean>(false)
const searchInfo = reactive({
  searchName: ''
})
//分页参数
const pagination = reactive({
  page: 1,
  rows: 10,
  total: 0,
  pageSizeOptions: ['8', '10', '20', '50', '100'],
  isLast: false
})

const handlePageChange = (page: number) => {
  pagination.page = page
  let newvv = materialList.value.map(item => {
    return {
      status: item.code == 0,
      standard: item.data?.source && item.data.source.length > 0 ? item.data.source?.map((sitem: any) => sitem.standard_name).join(",") : '-',
      ...item.data
    }
  })
  dataList.value = newvv.slice(
    (pagination.page - 1) * pagination.rows,
    pagination.page * pagination.rows
  );
};

const imageShow = ref('image')

const materialList = ref<any[]>([]);
const updateMaterialList = (newMaterial: any) => {
  materialList.value = materialList.value.concat(newMaterial);
};
function tableRowClassName({ row, rowIndex }: any) {
  if (!row.status) {
    return 'error-row';
  }
  else if (row.confidence < 0.9) {
    return 'warning-row';
  }
  return '';
}
const dataList = ref<MaterialItem[]>([])
watch(
  () => [...materialList.value], 
  (newv) => {
    let newvv = newv.map(item => {
      if (item.code === 0 && item.data) {
        return {
          status: true,
          standard: item.data.source && item.data.source.length > 0 ? item.data.source.map((sitem: any) => sitem.standard_name).join(",") : '-',
          ...item.data
        };
      } else {
        return {
          status: false,
          chineseName: item.filename || '未知文件',
          latinName: '识别失败',
          confidence: 0,
          imagePath: '@/renderer/assets/img/error.png',
          standard: item.message || '无'
        };
      }
    });
    pagination.total = newvv.length;
    dataList.value = newvv.slice(
      (pagination.page - 1) * pagination.rows,
      pagination.page * pagination.rows
    );
  },
  { deep: true }
);
const imageDialogValue = ref(false);
const selectedMaterial = ref<Material | null>(null);
const moreDialogVisible = ref(false);
const shootUploadDialogVisible = ref(false);
const selectUploadMethodDialogVisible = ref(false);
const imgUploadDialogVisible = ref(false);

const materiaTable = ref();
const selectedRows = ref<any[]>([]);

const openImageDialog = (material: Material) => {
  selectedMaterial.value = material;
  imageDialogValue.value = true;
};
const closeImageDialog = () => {
  imageDialogValue.value = false;
};

const openMore = (row: any) => {
  moreData.value = row.more ?? []
  moreDialogVisible.value = true;
};
const closeMoreDialog = () => {
  moreDialogVisible.value = false;
};

const openShootUploadDiaglog = () => {
  shootUploadDialogVisible.value = true;
};
const closeShootUploadDiaglog = () => {
  shootUploadDialogVisible.value = false;
};

const openImgUploadDialog = () => {
  imgUploadDialogVisible.value = true;
};
const closeImgUploadDialog = () => {
  imgUploadDialogVisible.value = false;
};
const openSelectUploadMethodDialog = () => {
  selectUploadMethodDialogVisible.value = true;
};

const handleSelectUploadMethod = (method: string) => {
  if (method === "photo") {
    openShootUploadDiaglog();
  } else if (method === "image") {
    openImgUploadDialog();
  }
};

const closeSelectUploadMethodDialog = () => {
  selectUploadMethodDialogVisible.value = false;
};

const handleSelectionChange = (selection: Material[]) => {
  selectedRows.value = selection;
};
import { imageUrlToBase64 } from "@/renderer/utils/imageToBase64";

const handleExportPdf = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请至少选择一条结果进行导出');
    return;
  }

  ElMessage.info('正在处理图片数据并生成PDF，请稍候...');

  // 从localStorage获取当前用户信息
  const currentUserData = localStorage.getItem('user');
  const currentUser = currentUserData ? JSON.parse(currentUserData) : {};
  // 优先使用昵称，如果没有则使用用户名
  const creatorName = currentUser.nickName || currentUser.userName || '未知用户';

  try {
    const dataToExport = await Promise.all(selectedRows.value.map(async item => {
      let imageBase64 = '';
      try {
        imageBase64 = await imageUrlToBase64(getImageUrl(item.imagePath));
      } catch (e) {
        console.error(`图片转换失败: ${item.imagePath}`, e);
      }

      return {
        id: item.id,
        confidence: item.confidence,
        latinName: item.latinName,
        source: item.source ? (Array.isArray(item.source) ? item.source : [item.source]) : [],
        creatorName: creatorName, // 使用动态获取的用户名
        createdAt: new Date().toISOString(),
        subclassChineseName: item.chineseName,
        imageBase64: imageBase64,
      };
    }));

    await exportHistoryToPdf(dataToExport);

  } catch (error) {
    console.error('PDF导出流程出错:', error);
    ElMessage.error('导出PDF时发生未知错误。');
  }
};

const exportExcel = () => {
  const selectedRowsToExport = selectedRows.value;
  const clomuns = Object.keys(materialList.value[0]).map((key) => {
    return { header: key, key, width: 15 };
  });
  exportToExcel(
    materialList.value,
    "结果导出.xlsx",
    clomuns,
    selectedRowsToExport
  );
};
const pie_chart = ref<any>(null)
const bar_chart = ref<any>(null)
const echartsInit = () => {
  if (document.getElementById("pie_chart")) {
    pie_chart.value = echarts.init(document.getElementById("pie_chart"));
    pie_chart.value.setOption(pie_option);
  }
  if (document.getElementById("bar_chart")) {
    bar_chart.value = echarts.init(document.getElementById("bar_chart"));
    bar_chart.value.setOption(bar_option);
  }
}

// --- 后端服务状态管理 (增强版) ---

// 用于“记忆”识别引擎是否曾经就绪过
const wasTcmReadyOnce = ref(false);

// 统一的处理器，根据状态更新UI
const handleBackendReadiness = (readiness) => {
  const isTcmReady = readiness.tcm;

  if (isTcmReady) {
    // 1. 如果识别引擎现在是就绪的
    wasTcmReadyOnce.value = true; // 记录下来它已经就绪过了
    // 如果遮罩是打开的，就完成它
    if (progressDialog.isOpen('backend-waiter')) {
      setTimeout(() => {
      progressDialog.complete('backend-waiter', '所有服务已就绪！');
    },5000)}
  } else {
    // 2. 如果识别引擎现在是未就绪的
    if (wasTcmReadyOnce.value) {
      // 如果它“曾经”就绪过，说明是中途崩溃了
      progressDialog.showError('backend-waiter', '核心识别引擎意外中断，正在尝试自动恢复...');
    } else {
      // 如果它从未就绪过，说明是正常的初次加载
      if (!progressDialog.isOpen('backend-waiter')) {
        progressDialog.open({
          key: 'backend-waiter',
          title: '系统初始化',
          content: '正在启动核心识别引擎，请稍候...',
          showClose: false,
          modalClickClose: false,
        });
      }
    }
  }
};

onMounted(async () => {
  // 原有的 ECharts 初始化
  echartsInit();

  // 注册监听器，用于接收来自主进程的实时状态更新
  (window as any).electron.onBackendReadinessUpdate(handleBackendReadiness);

  // 立即获取一次当前的后端状态，以处理初次加载
  try {
    const result = await (window as any).electron.getBackendReadiness();
    if (result.success) {
      handleBackendReadiness(result.readiness);
    } else {
      // 如果连获取状态都失败了，显示一个错误
      progressDialog.showError('backend-waiter', '无法获取后端服务状态，请尝试重启应用。');
    }
  } catch (error) {
    progressDialog.showError('backend-waiter', '查询后端状态时出错，请尝试重启应用。');
  }
});

onUnmounted(() => {
  // 组件销毁时，移除监听器以防止内存泄漏
  (window as any).electron.onBackendReadinessUpdate(() => {});
  
  // 同时，如果遮罩还在，也关闭它，避免影响其他页面
  if (progressDialog.isOpen('backend-waiter')) {
    progressDialog.close('backend-waiter');
  }
});

// 统计药材数量
const herbStats = computed(() => {
  const statMap: Record<string, number> = {};
  let total = 0;
  materialList.value.forEach(item => {
    if (item.data && item.data.chineseName) {
      const name = item.data.chineseName;
      statMap[name] = (statMap[name] || 0) + 1;
      total++;
    } else if (item.chineseName) {
      const name = item.chineseName;
      statMap[name] = (statMap[name] || 0) + 1;
      total++;
    }
  });
  const stats = Object.entries(statMap).map(([herbName, count]) => ({
    herbName,
    count
  }));
  return { stats, total };
});

</script>

<style lang="scss">
.el-table .warning-row {
  background: oldlace;
}

.el-table .success-row {
  background: #f0f9eb;
}

.el-table .error-row {
  background: #f9ebeb;
}

.dashboard {
  display: flex;
  flex-direction: column;
  min-height: 100%;

  .stat-card:hover {
    border-color: #61c9f5;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    transform: translateY(-5px);
  }
}

// 内容部分
.content-section {
  padding: 20px;
  flex: 1;
  height: calc(100% - 233px);
}

.data-tables {
  background-color: #ffffff;
  width: 100%;
  height: auto;
  min-height: auto;
  display: flex;
  flex-direction: column;
  overflow: visible; /* 允许内容溢出 */
}

.table-container {
  width: 100%;
  overflow: auto !important; /* 强制启用滚动 */
  max-width: 100%;
  height: auto; /* 允许自动调整高度 */
  max-height: none; /* 移除高度限制 */
  margin-bottom: 15px;
  padding-bottom: 15px;
  position: relative;
}

/* 强制显示表格滚动条 - 只在Dashboard组件中应用 */
.dashboard .el-table {
  overflow: visible !important;
}

.dashboard .el-table__body-wrapper {
  overflow: auto !important;
  min-height: auto; /* 允许自动调整最小高度 */
  max-height: none; /* 移除高度限制 */
}

/* 确保水平滚动条始终可见 - 只在Dashboard组件中应用 */
.dashboard .el-table__body-wrapper::-webkit-scrollbar {
  height: 12px !important;
  display: block !important;
  width: 12px !important;
  position: absolute !important;
  bottom: 0 !important;
}

.dashboard .el-table__body-wrapper::-webkit-scrollbar-thumb {
  background: #c1c1c1 !important;
  border-radius: 6px !important;
}

.dashboard .el-table__body-wrapper::-webkit-scrollbar-track {
  background: #f1f1f1 !important;
}

/* 添加一个固定的滚动条区域 - 只在Dashboard组件中应用 */
.dashboard .dashboard-table-container::after {
  display: none;
}

.dashboard .el-table {
  --el-table-header-bg-color: transparent;
  --el-table-border-color: transparent;
  background-color: transparent;

  th {
    background-color: transparent;
    border-bottom: 1px solid #e0e0e0;
    color: #333;
    font-weight: bold;
    padding: 12px 16px;
  }

  td {
    border-bottom: 1px solid #e0e0e0;
    color: #555;
    padding: 12px 16px;
  }

  tr:hover {
    background-color: rgba(0, 0, 0, 0.02);
  }
}

.count_chart {
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  height: 400px;
  width: 100%;
  background-color: #ffffff;

  #pie_chart {
    height: 100%;
    width: 50%;
  }

  #bar_chart {
    height: 100%;
    width: 50%;
  }
}

.column {
  overflow: hidden;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  padding: 6px;
  border: 1px solid #e4e7ed;
}

.column-left {
  height: calc(100vh - 135px);
  position: relative;
  float: left;
}

.column-right {
  padding: 16px;
  height: calc(100vh - 135px);
  box-sizing: border-box;
  overflow: auto !important; /* 强制启用滚动 */
  display: flex;
  flex-direction: column;
}

.card-wrapper {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: visible; /* 允许内容溢出 */
}

/* 确保卡片不会过高导致滚动条消失 - 只在Dashboard组件中应用 */
.dashboard .el-card {
  max-height: none; /* 移除最大高度限制 */
  overflow: visible; /* 允许内容溢出 */
}

/* 确保卡片体可以滚动 - 只在Dashboard组件中应用 */
.dashboard .el-card__body {
  height: auto;
  max-height: none; /* 移除最大高度限制 */
  overflow: visible;
  display: flex;
  flex-direction: column;
}

.resize-save {
  position: absolute;
  top: 0;
  right: 5px;
  bottom: 0;
  left: 0;
  padding: 16px;
  overflow-x: hidden;
}

.resize-bar {
  width: 48vw;
  height: inherit;
  resize: horizontal;
  cursor: ew-resize;
  opacity: 0;
  overflow: scroll;
}

/* 拖拽线 */
.resize-line {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  border-right: 2px solid #eee;
  border-left: 1px solid #bbb;
  pointer-events: none;
}

.resize-bar:hover~.resize-line,
.resize-bar:active~.resize-line {
  border-left: 1px dashed skyblue;
}

.resize-bar::-webkit-scrollbar {
  width: 200px;
  height: inherit;
}

/* Firefox只有下面一小块区域可以拉伸 */
@supports (-moz-user-select: none) {
  .resize-bar:hover~.resize-line,
  .resize-bar:active~.resize-line {
    border-left: 1px solid #bbb;
  }

  .resize-bar:hover~.resize-line::after,
  .resize-bar:active~.resize-line::after {
    content: '';
    position: absolute;
    width: 16px;
    height: 16px;
    bottom: 0;
    right: -8px;
    background-size: 100% 100%;
  }
}

.herb-stats-outer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  margin-top: 30px; /* 增加顶部边距，确保有足够空间 */
  margin-bottom: 50px; /* 增加底部边距，确保滚动时有足够空间 */
  flex-shrink: 0; /* 防止统计模块被压缩 */
  position: relative; /* 使统计模块保持在视图中 */
  z-index: 1;
}

.herb-stats-wrapper {
  min-width: 450px;
  background: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  padding: 16px 20px;
  max-height: 180px;
  overflow-y: auto;
  margin-left: auto;
  margin-right: 0;
}

.herb-stats-title {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 8px;
  color: #333;
}
.herb-stats-total {
  color: #666;
  margin-bottom: 8px;
}
.herb-stats-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.herb-stats-item {
  display: flex;
  justify-content: space-between;
  font-size: 15px;
  padding: 2px 0;
  border-bottom: 1px dashed #e0e0e0;
}
.herb-name {
  color: #1976d2;
}
.herb-count {
  color: #d32f2f;
  font-weight: bold;
}

/* 确保分页组件正确显示 */
.pagination-wrapper {
  margin-top: 10px;
  margin-bottom: 10px;
  display: flex;
  justify-content: center;
}
</style>
