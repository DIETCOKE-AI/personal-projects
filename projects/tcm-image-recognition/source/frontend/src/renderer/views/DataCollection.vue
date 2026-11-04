<template>
  <div class="dashboard">
    <div class="content-section">
      <div class="column">
        <div class="column-left">
          <div class="resize-bar"></div>
          <div class="resize-line"></div>
          <div class="resize-save">
            <el-tabs v-model="imageShow">
              <el-tab-pane label="数据采集" name="image" style="padding-top: 8px;overflow-y: scroll;">
                <DataShootUpload @updateMaterialList="updateMaterialList" title="点击拍照"
                  :visible.sync="shootUploadDialogVisible" @update:imageDialogValue="closeShootUploadDiaglog"
                  @close="closeShootUploadDiaglog" />
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
        <div class="column-right">
          <div class="data-tables" style="height: 100%;">
            <CardWrapper title="数据列表" :icon="null" >
              <div style="width:100%;display: flex;justify-content: space-between;">
                <div style="font-size: 14px;">已选{{ selectedRows.length }}个/共{{ dataList.length }}个</div>
                <div style="display: flex;">
                  <el-button @click="exportExcel" type="primary" plain>图片保存</el-button>
                  <el-button @click="deleteSelected" type="danger" plain>删除选中</el-button>
                  <el-button @click="clearImageList" plain>清空</el-button>
                </div>
              </div>
              <el-table :data="dataList"
                style="width: 100%;overflow: scroll;max-height: calc(100vh - 280px);" ref="materiaTable"
                @selection-change="handleSelectionChange">
                <el-table-column type="selection" width="55" :selectable="selectable" />
                <el-table-column type="index" width="50" label="#" />
                <el-table-column label="缩略图" align="center">
                  <template #default="{ row }">
                    <img :src="row.imgUrl ? row.imgUrl : ''" alt="缩略图" class="thumbnail"
                      @click="openImageDialog(row)" style="width: 60px; height: 60px" />
                  </template>
                </el-table-column>
                <el-table-column prop="fileName" label="文件名称">
                  <template #default="{ row }">
                    {{ row.fileName ?? '-' }}
                  </template>
                </el-table-column>

              </el-table>
            
            </CardWrapper>
          </div>
        </div>
      </div>

    </div>

    <!-- 缩略图弹窗 -->
    <ImageDialog :visible.sync="imageDialogValue" title="上传图片"
      :imgUrl="selectedMaterial?.imgUrl ? selectedMaterial.imgUrl : ''"
      @update:modelValue="closeImageDialog" @close="closeImageDialog"></ImageDialog>


    <HerbsDetailsDialog :visible.sync="herbsDetailsVisible" :detailData="selectedHerb"
      @update:herbsDetailsVisible="closeHerbsDetailDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import CardWrapper from "@/renderer/components/CardWrapper.vue";
import ImageDialog from "@/renderer/components/ImageDialog.vue";
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import HerbsDetailsDialog from "../components/HerbsDetailsDialog.vue";
import DataShootUpload from "../components/DataShootUpload.vue";
import { messageMethod } from "../utils/message-util.js";
import { ElMessage, ElMessageBox } from "element-plus";

const clearImageList = ()=>{
  dataList.value=[]
  materialList.value=[]
  messageMethod.success("操作成功")
}

const deleteSelected = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请至少选择一张图片进行删除');
    return;
  }

  ElMessageBox.confirm(
    `您确定要删除选中的 ${selectedRows.value.length} 张图片吗？此操作不可恢复。`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    const selectedSet = new Set(selectedRows.value);
    dataList.value = dataList.value.filter(item => !selectedSet.has(item));
    materialList.value = materialList.value.filter(item => !selectedSet.has(item));
    ElMessage.success('删除成功');
  }).catch(() => {
    // 用户点击了取消
  });
};

const herbsDetailsVisible = ref(false)
const selectedHerb = ref<any>({})
// **关闭详情弹窗**
const closeHerbsDetailDialog = () => {
  herbsDetailsVisible.value = false;
};

const moreData = ref<any>([])

const imageShow = ref('image')

const materialList = ref<any[]>([]);
const updateMaterialList = (newMaterial: any) => {
  console.log(newMaterial)
  materialList.value = materialList.value.concat(newMaterial);
  // echartsInit()
};
const dataList = ref<MaterialItem[]>([])
watch(
  () => [...materialList.value], // 监听数组的副本（或使用 deep: true）
  (newv) => {
    dataList.value = newv
  },
  { deep: true } // 深度监听
);
const imageDialogValue = ref(false);
const selectedMaterial = ref<any>(null);
const shootUploadDialogVisible = ref(false);

const materiaTable = ref();
const selectedRows = ref<Material[]>([]);
const selectable = (row: Material) => {
  return true;
};
// 打开缩略图弹窗
const openImageDialog = (material: Material) => {
  selectedMaterial.value = material;
  imageDialogValue.value = true;
};
const closeImageDialog = () => {
  imageDialogValue.value = false;
};

const closeShootUploadDiaglog = () => {
  shootUploadDialogVisible.value = false;
};


const handleSelectionChange = (selection: Material[]) => {
  selectedRows.value = selection;
};

// 导出excel
// 修改后的导出方法 - 使用ZIP打包方案
const exportExcel = async () => {
  if (selectedRows.value.length === 0) {
    messageMethod.warning("请先选择要保存的图片");
    return;
  }

  try {
    const zip = new JSZip();
    const imgFolder = zip.folder("images");
    
    // 添加所有图片到ZIP
    selectedRows.value.forEach((item: any, index: number) => {
      if (item.blob) {
        imgFolder?.file(
          item.fileName+'.png' || `image_${index}.png`, 
          item.blob
        );
      }
    });

    // 生成ZIP并下载
    const content = await zip.generateAsync({ type: 'blob' });
    await saveAs(content, `images_${Date.now()}.zip`)
    messageMethod.success(`已打包${selectedRows.value.length}张图片`);
    
  } catch (error) {
    messageMethod.error("图片打包失败");
    console.error(error);
  }
};
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

//内容部分
.content-section {
  padding: 20px;
  flex: 1;
  height: calc(100% - 233px);

  .data-tables {
    background-color: #ffffff;

    .stat-card {
      width: auto;
    }

    .table-card {
      width: 100%;
      background-color: #ffffff;
      overflow: hidden;

      .card-header {
        font-weight: bold;
        font-size: 18px;
        color: #333;
        padding: 16px 24px;
        border-bottom: 1px solid #e0e0e0;
      }

      :deep(.el-table) {
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
  overflow: hidden;
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
</style>