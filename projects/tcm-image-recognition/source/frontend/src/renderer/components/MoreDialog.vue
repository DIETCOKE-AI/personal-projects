<!-- 更多可能弹窗 -->
<template>
  <el-dialog :model-value="props.visible" :title="props.title"  @close="handleClose" width="600px">
    <!-- <template #header>
      <div class="dialog-header">
        <span class="dialog-title">{{ props.title }}</span>
        <div class="btns">
          <el-icon @click="handleClose">
            <Close />
          </el-icon>
        </div>
      </div>
    </template> -->

    <div class="dialog-table">
      <el-table :data="props.moreData" style="width: 100%">
        <el-table-column prop="chineseName" label="中文名">
          <template #default="{ row }">
            <el-link type="primary" @click="clickNameDetail(row)">{{ row.chineseName ?? '-' }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="latinName" label="拉丁名" />
        <el-table-column prop="source" label="标准">
          <template #default="{ row }">
            <div>{{row.source.length>0?row.source?.map((item: any) => item.standard_name).join(',') : '-'}}</div>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" />
      </el-table>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
  <HerbsDetailsDialog
        :visible.sync="herbsDetailsVisible"
        :detailData="selectedHerb"
        @update:herbsDetailsVisible="closeHerbsDetailDialog"
      />
</template>

<script lang="ts" setup>
import { ref } from "vue";
import { FullScreen, Close } from "@element-plus/icons-vue";
import requestMethodHerb from '../api/herb/herb'
import HerbsDetailsDialog from "../components/HerbsDetailsDialog.vue";

const emit = defineEmits(["update:dialogVisible"]);
const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  moreData: {
    type: Object,
    required: true,
  }
});

const herbsDetailsVisible = ref(false)
const selectedHerb = ref<any>({})
// **关闭详情弹窗**
const closeHerbsDetailDialog = () => {
  herbsDetailsVisible.value = false;
};

const clickNameDetail = (row:any)=>{
  herbsDetailsVisible.value = true
  requestMethodHerb
    .getOne({ id:row.id })
    .then((res:any) => {
      selectedHerb.value = res.data
    })
    .finally(() => {
    })
  
}

const moreMaterialList = ref<Material[]>([
  {
    chineseName: "药材1",
    latinName: "Radix Ginseng",
    standard: "中国药典",
    confidence: "98%",
    thumbnail: "",
  },
  {
    chineseName: "药材2",
    latinName: "Radix Ginseng",
    standard: "中国药典",
    confidence: "92%",
    thumbnail: "",
  },
  {
    chineseName: "药材3",
    latinName: "Radix Ginseng",
    standard: "中国药典",
    confidence: "85%",
    thumbnail: "",
  },
  {
    chineseName: "药材4",
    latinName: "Radix Ginseng",
    standard: "中国药典",
    confidence: "96%",
    thumbnail: "",
  },
]);

const handleClose = () => {
  emit("update:dialogVisible", false);
};
</script>

<style scoped lang="scss">
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.dialog-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.btns {
  display: flex;
  gap: 12px;
}

.dialog-img {
  text-align: center;
  padding: 20px;
}

.dialog-img img {
  width: 100%;
  max-width: 500px;
  height: auto;
  border-radius: 8px;
}

.el-button {
  font-size: 14px;
  height: 36px;
}

.el-dialog__footer {
  padding: 10px 20px;
}

.el-icon {
  cursor: pointer;
  font-size: 20px;
  color: #409eff;
  transition: color 0.3s ease;
}

.el-icon:hover {
  color: #66b1ff;
}

/* 确认关闭弹窗样式 */
.el-dialog--small {
  width: 300px;
}

.el-dialog__header {
  background-color: #f0f4f7;
  border-bottom: 1px solid #ebebeb;
}

.el-dialog__footer {
  text-align: right;
}

.el-button--primary {
  background-color: #409eff;
  border-color: #409eff;
}

.el-button--primary:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}
</style>
