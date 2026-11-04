<template>
  <div class="history">
    <!-- <div class="history-startcard">
      <StartCard>
        <Card title="TRAFFIC" :iconShow="false" :icon="TrendCharts" h3Content="历史记录导出" percentage="3.0%" period="今日"
          trend="up" iconColor="#8687e7" @click="exportExcel" />
      </StartCard>
    </div> -->

    <!-- 项目统计卡片 -->
    <div class="history-section">
      <div class="history-tables">
        <CardWrapper :title="'历史记录'" :icon="undefined" :btnTitle="isAdmin ? '历史记录导出PDF' : undefined" :btnClick="handleExportPdf">
          <div style="width: 100%;margin-bottom: 15px;">
            <div style="position: relative;display: flex;justify-self: start;gap: 10px;">
              <div style="display: flex;" class="search-box">
                <el-date-picker style="width: 200px;" class="search-right" v-model="searchInfo.searchTime" type="daterange"
                  range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期">
                </el-date-picker>
                <el-input style="width: 300px;" v-model="searchInfo.searchName" placeholder="输入名称搜索"
                  @keyup.enter="handleSearch">
                  <template #suffix>
                    <el-icon @click="handleSearch" style="cursor: pointer;">
                      <Search />
                    </el-icon>
                  </template>
                </el-input>
              </div>
              <el-button type="primary" @click="handleSearch" round>搜索</el-button>
              <el-button @click="handleClearSearch" round style="margin-left: 0;">重置</el-button>
            </div>
          </div>
          <!-- 插入表格内容 -->
          <el-table :data="tableData" border style="width: 100%;height: calc(100vh - 287px);" ref="historyTable"
            @selection-change="handleSelectionChange" :load="loading"
            :default-sort="{ prop: 'uploadedAt', order: 'descending' }">
            <!-- 可选框<el-table-column type="selection" width="55" :selectable="selectable" /> -->
            <el-table-column type="selection" width="55" />
            <el-table-column type="index" width="50" label="#" />
            <el-table-column label="素材图片">
              <template #default="{ row }">
                <img :src="getImageUrl(row.imagePath)" :alt="row.imageName" class="thumbnail"
                  style="width: 60px; height: 60px" />
              </template>
            </el-table-column>
            <el-table-column prop="imagePath" label="图片保存路径">
              <template #default="{ row }">
                <el-link type="primary" @click="handleOpenPath(row.imagePath)">{{ row.imagePath }}</el-link>
              </template>
            </el-table-column>

            <el-table-column prop="subclassChineseName" label="中文名" sortable>
              <template #default="{ row }">
                <span>{{ row.subclassChineseName }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="latinName" label="拉丁名" sortable>
              <template #default="{ row }">
                <span>{{ row.latinName }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="confidence" label="置信度" sortable>
              <template #default="{ row }">
                <span>{{ row.confidence }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="source" label="标准" sortable
              :filters="[{ text: '中国药典', value: '中国药典' }, { text: '标准', value: '标准' }]" :filter-method="(value: any, row: any) => {
                // return row.standard === value;
                console.log(row.source,value)
                return row.source?.some((items:any) => items.standardName === value)
              }" filter-placement="bottom-end">
              <template #default="{ row }">
                <span>{{ row.source.length>0?row.source?.map((item:any)=>item.standardName).join(","):'-' }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="creatorName" label="上传用户" sortable>
              <template #default="{ row }">
                <span>{{ row.creatorName }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="createdAt" label="登记时间" sortable>
              <template #default="{ row }">
                <span>{{ renderTime(row.createdAt) }}</span>
              </template>
            </el-table-column>
          </el-table>

          <!-- 插入分页组件 -->
          <template #footer>
            <div class="pagination-wrapper">
              <el-pagination v-if="tableData.length > 0" @size-change="handleSizeChange"
                @current-change="handlePageChange" :current-page="pagination.page"
                :page-sizes="pagination.pageSizeOptions" :page-size="pagination.rows"
                layout="total, sizes, prev, pager, next" :total="pagination.total">
              </el-pagination>
            </div>
          </template>
        </CardWrapper>
      </div>
    </div>
    </div>
</template>

<script lang="ts" setup>
import CardWrapper from "@/renderer/components/CardWrapper.vue";
import { ref, reactive, onBeforeMount, computed } from "vue";
import { ElMessage } from 'element-plus';
import { exportHistoryToPdf } from "@/renderer/utils/pdf-export";
import requestMethodHistory from '../api/history/history'
import type { HistoryItem } from "@/types/history";
import { renderTime } from "../utils/timestamp";
import { Search } from "@element-plus/icons-vue";



const tableData = ref<HistoryItem[]>([]);

// --- 权限控制 ---
const currentUser = ref(JSON.parse(localStorage.getItem('user') || '{}'));
const isAdmin = computed(() => {
  return currentUser.value.roles?.some((role: any) => role.roleKey === 'admin');
});

import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const handleOpenPath = (path: string) => {
  // --- 修改：调用新的 aPI ---
  window.electron.openInExplorer(path);
};

//表格加载中
const loading = ref<boolean>(false)
const searchInfo = reactive({
  searchName: '',
  searchTime: ''
})
//分页参数
const pagination = reactive({
  page: 1,
  rows: 10,
  total: 0,
  pageSizeOptions: ['8', '10', '20', '50', '100'],
  isLast: false
})

function pageRequest() {
  loading.value = true;

  const currentUserData = localStorage.getItem('user');
  const currentUser = currentUserData ? JSON.parse(currentUserData) : {};
  const isAdmin = currentUser.roles?.some((role: any) => role.roleKey === 'admin');

  const requestParams = {
    ...searchInfo,
    pageNum: pagination.page,
    pageSize: pagination.rows,
    userId: currentUser.userId,
    isAdmin: isAdmin
  };

  requestMethodHistory
    .page(requestParams)
    .then(({ data }) => {
      const { isLastPage, pageNum, total, list } = data;
      pagination.isLast = isLastPage;
      pagination.page = pageNum;
      pagination.total = total;
      tableData.value = list ?? [];
    })
    .finally(() => {
      loading.value = false;
    });
}

onBeforeMount(async () => {
  await pageRequest()
})


// 处理页码变化的函数
const handlePageChange = (page: number) => {
  pagination.page = page
  pageRequest()
};

const handleSearch = () => {
  if(searchInfo.searchTime==null){
    searchInfo.searchTime=''
  }
  pagination.page = 1
  pageRequest()
};
const handleClearSearch = () => {
  searchInfo.searchName = ''
  searchInfo.searchTime = ''
  handleSearch()
}

const handleSizeChange = (size: number) => {
  pagination.rows = size
  pageRequest()
}
// 表格选择
const selectedRows = ref<HistoryItem[]>([]);

const handleSelectionChange = (selection: HistoryItem[]) => {
  console.log('Selection changed:', selection);
  selectedRows.value = selection;
};

// 导出excel
const exportExcel = () => {
  const selectedRowsToExport = selectedRows.value;

  const columns = Object.keys(tableData.value[0]).map((key) => {
    return { header: key, key, width: 15 };
  });
  exportToExcel(tableData.value, "output.xlsx", columns, selectedRowsToExport);
};

import { imageUrlToBase64 } from "@/renderer/utils/imageToBase64";

const handleExportPdf = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请至少选择一条记录进行导出');
    return;
  }

  if (!isAdmin.value) {
    ElMessage.error('只有管理员才能导出PDF');
    return;
  }

  ElMessage.info('正在处理图片数据，请稍候...');

  const dataToExport = await Promise.all(
    selectedRows.value.map(async (row) => {
      let imageBase64 = '';
      try {
        imageBase64 = await imageUrlToBase64(getImageUrl(row.imagePath));
      } catch (e) {
        console.error(`图片加载或转换失败: ${row.imagePath}`, e);
      }
      return {
        ...row,
        imageBase64: imageBase64,
      };
    })
  );

  await exportHistoryToPdf(dataToExport);
};

const getImageUrl = (imagePath: string) => {
  return `${import.meta.env.VITE_API_BASE_URL}${imagePath}`;
}

</script>

<style lang="scss">
.history {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100vh - 64px);

  .history-startcard {
    background-color: #8687e7;
    // padding: 24px;
    height: 100%;

    .stat-cards {
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
      justify-items: center;
      /* 水平居中 */
    }

    /* 设置每个卡片的固定宽度 */
    .stat-card {
      width: 100%;
      /* 根据需要调整宽度 */
    }
  }

  .stat-card:hover {
    border-color: #61c9f5;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    transform: translateY(-5px);
  }

  .history-section {
    height: 100%;
    padding: 20px;
    flex: 1;
    // background-color: #f0f2f8;

    .history-tables {
      height: 100%;
      background-color: #ffffff;

      .start-card {
        width: auto;

        .table-card {
          width: 100%;
          background-color: #ffffff;
          overflow: hidden;

          /* 防止内容溢出 */
          .card-header {
            font-weight: bold;
            font-size: 18px;
            /* 更大的字体 */
            color: #333;
            /* 深色文字 */
            padding: 16px 24px;
            /* 增加内边距 */
            border-bottom: 1px solid #e0e0e0;
            /* 底部分隔线 */
          }
        }
      }
    }
  }

  /* 样式：分页器 */
  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    /* 使分页器靠右 */
    // margin-top: 20px;
    // margin-top:-24px;
  }
}

.search-box {
  border: 1px solid #dcdfe6;
  border-radius: 20px;
  overflow: hidden;
  .search-right{
    border-right: 1px solid #dcdfe6;
    border-radius: 0;
  }
  .el-input__wrapper {
    box-shadow: 0 0 0 0;
  }
}
.search-box:hover{
  border: 1px solid #409eff;
  .search-right{
    box-shadow: 0 0 0 0;
    border-right: 1px solid #409eff;
  }
}
</style>
