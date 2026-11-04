<template>
  <el-dialog
    :model-value="props.visible"
    @close="handleClose"
    style="width: 80vw;height: 80vh;overflow-y: scroll;margin-top: 10vh;"
  >
    <div class="herb-detail">
      <div class="dialog-content">
      <img
        :src="props.detailData.imageUrl ? `${baseUrl}${props.detailData.imageUrl}` : defaultImg"
        alt="图片"
        class="dialog-image"
      />
      <div class="dialog-text">
        <div class="dialog-name" v-if="props.detailData.isTrueHerb==0">暂未录入该药材</div>
        <div class="dialog-name" v-if="props.detailData.isTrueHerb==1">{{ props.detailData.source[0]?.subclassName }}</div>
        <div class="dialog-source" v-if="props.detailData.isTrueHerb==1">所属规范：{{ props.detailData.source?.length>0?props.detailData.source.map((item:any)=>item.standardName).join(","):'-' }}</div>
        <div class="dialog-source">植物中文名：{{ props.detailData.source?.length>0?props.detailData.source[0]?.plantName:'未知' }}</div>
        <div class="dialog-source">植物拉丁名：{{ props.detailData.source?.length>0?props.detailData.source[0]?.latinName:'-' }}</div>
      </div>
    </div>
    <div>
        <el-table :data="props.detailData.isTrueHerb==1 && props.detailData.source ? props.detailData.source : []" border style="width: 100%;height: 55vh;">
          <el-table-column prop="standardName" label="标准名称" width="120">
            <template #default="scope">
              <div>{{scope.row.standardName??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="subclassName" label="药材中文名" width="120">
            <template #default="scope">
              <div>{{scope.row?.subclassName??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="plantEName" label="药材英文名" width="140">
            <template #default="scope">
              <div>{{scope.row.plantEName??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="plantName" label="植物中文名" width="160">
            <template #default="scope">
              <div>{{scope.row.plantName??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="latinName" label="植物拉丁名" width="140">
            <template #default="scope">
              <div>{{scope.row.latinName??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="medicinalParts" label="药用部位" width="160">
            <template #default="scope">
              <div>{{scope.row.medicinalParts??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="characteristics" label="性状" width="344">
            <template #default="scope">
              <div>{{scope.row.characteristics??'-'}}</div>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="来源" width="320">
            <template #default="scope">
              <div>{{scope.row.description??'-'}}</div>
            </template>
          </el-table-column>
          <!-- <el-table-column prop="origin" label="产地信息" width="220">
            <template #default="scope">
              <div>{{scope.row.origin??'-'}}</div>
            </template>
          </el-table-column> -->
        </el-table>
    </div>
    </div>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose">关闭</el-button>
    </div>
  </el-dialog>
</template>

<script lang="ts" setup>
import img1 from "@/assets/public-image-placeholder.svg"
import img2 from "@/assets/public-image-placeholder.svg"
import img3 from "@/assets/public-image-placeholder.svg"
const baseUrl=import.meta.env.VITE_API_BASE_URL;
  // 定义组件的 props 和 emit 方法
  // 定义组件的 props 和 emit 方法
  // 定义组件的 props 和 emit 方法
  const emit = defineEmits(["update:herbsDetailsVisible"]);
  const props = defineProps({
    visible: {
      type: Boolean,
      default: false,
    },
    detailData: {
    type: Object, //  使用 Object 类型
    //required: true, // 可选：是否必传
    default: () => ({source: [] }), // 可选：默认值
  },
});
  console.log("===================="+props.detailData)

  // 关闭弹窗时触发父组件的更新事件
  const handleClose = () => {
    emit("update:herbsDetailsVisible", false);
  };
  //点击 HerbsCard=>archive=>herbsDialog
</script>

<style lang="scss" scoped>
.herb-detail{
  display:flex;
  flex-direction: column;
  gap: 28px;
}
  .dialog-content {
    display: flex;
    // justify-content: space-between; // 将图片和文字分别放在两侧
    align-items: flex-start; // 让内容从顶部开始排列
    // flex-direction: row;
  }

  .dialog-image {
    width: 250px; // 可以根据需求调整图片大小
    height: auto;
    object-fit: cover;
    border-radius: 4px;
    border: 1px solid #eaeaea;
    border-radius: 10px;
  }

  .dialog-text {
    display: flex;
    flex-direction: column; // 使文字部分从上到下排列
    justify-content: flex-start; // 从顶部对齐
    margin-left: 20px; // 给文字部分增加一点间距
    gap: 10px;
  }

  .dialog-name {
    font-size: 28px;
    font-weight: bold;
    color: #333;
    // margin-bottom: 8px; // 文字之间的间距
  }

  .dialog-source {
    font-size: 16px;
    color: #999;
    // margin-bottom: 8px; // 文字之间的间距
  }

  .dialog-details {
    font-size: 16px;
    color: #666;
  }
  .dialog-footer{
    padding: 10px 20px 20px;
    text-align: right;
    box-sizing: border-box;

  }
</style>
