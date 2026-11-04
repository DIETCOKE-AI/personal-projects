<template>
  <div style="overflow-y: scroll;padding:20px">
    <!-- <div class="Archive"></div> -->
  <div class="archive-show">
    <CardWrapper title="药材资源库" style="min-height: calc(100vh - 114px);">
      <!-- 搜索部分 - 移动到标题正下方 -->
      
        <!--搜索按钮并且使用放大镜矢量图-->
       <!--  <el-date-picker v-model="searchInfo.searchTime" type="date" placeholder="选择时间" class="search-date" /> -->
      <!-- 标签部分 -->
      <div class="tags">
        <el-tag
          v-for="(tag, index) in tags"
          :key="index"
          :type="activeTag === tag ? 'primary' : 'success'"
          @click="changeTag(tag)"
          class="tag"
        >
          {{ tag }}
        </el-tag>
      </div>
      <div class="tags" style="margin: 10px 0;">
        <el-input 
          style="width: 300px;" 
          v-model="searchInfo.searchName" 
          placeholder="输入名称搜索"
          @keyup.enter="queryByCondition">
          <template #suffix>
            <el-icon @click="queryByCondition" style="cursor: pointer;">
              <Search />
            </el-icon>
          </template>
        </el-input>
      </div>

      <!-- 卡片内容部分 -->
      <div class="archive-show-card">
        <VirtualList :items="filteredData" @openDetail="handleOpenDetail" />
      </div>
      

    </CardWrapper>
  </div>
  </div>

  <!-- 药材档案详情弹窗 -->
  <HerbsDetailsDialog
    :visible.sync="herbsDetailsVisible"
    :detailData="selectedHerb"
    @update:herbsDetailsVisible="closeHerbsDetailDialog"
  />
</template>

<script lang="ts" setup>
import { ref, computed, reactive, onBeforeMount } from "vue";
import CardWrapper from "@/renderer/components/CardWrapper.vue";
import HerbsDetailsDialog from "@/renderer/components/HerbsDetailsDialog.vue";
import VirtualList from "@/renderer/components/VirtualList.vue";
import { useTableDataStore } from "@/renderer/store/tableDataStore";
import requestMethodHerb from '../api/herb/herb'

const tableDataStore = useTableDataStore();
const tags = ref(["全部", "中国药典", "浙江省中药炮制规范","其他"]);
const activeTag = ref("全部");



const herbsDetailsVisible = ref(false);
const selectedHerb = ref<CardItem>({
  id: 0,
  // subclassName: "",
  imageUrl: "",
  // latinName: "",
  // medicinalParts: "",
  source:[],
  isTrueHerb:1,
});

// **计算筛选后的数据**
const filteredData = computed<CardItem[]>(() => {
  console.log(tableDataStore.tableData)
  return tableDataStore.tableData
    .filter(
      (item) => activeTag.value === "全部" || item?.source.some(items => items.standardName === activeTag.value)
    )
    .map((item, index) => ({
      id: index + 1, // id 改为 number
      // subclassName: item?.subclassName,
      imageUrl: item?.imageUrl,//存入carddItem的imageUrl字段
      // latinName: item?.latinName,
      // medicinalParts: item?.medicinalParts,
      source: item?.source,
      isTrueHerb:item.isTrueHerb
    }));
});

// **标签切换**
const changeTag = (tag: string) => {
  activeTag.value = tag;
};

// **点击卡片打开详情**
const handleOpenDetail = (item: CardItem) => {
  console.log(item)
  selectedHerb.value = item;
  herbsDetailsVisible.value = true;
};

// **关闭详情弹窗**
const closeHerbsDetailDialog = () => {
  herbsDetailsVisible.value = false;
};

const loading = ref<boolean>(false)
const searchInfo = reactive({
  searchName: '',
  searchTime: ''
})
//分页参数
const pagination = reactive({
  page: 1,
  rows: 2000,
  total: 0,
  pageSizeOptions: ['8', '10', '20', '50', '100'],
  isLast: false
})

function pageRequest() {
  //打开加载动画
  loading.value = true
  requestMethodHerb
    .page({ ...searchInfo, pageNum: pagination.page, pageSize: pagination.rows })
    .then(({ data }) => {
      const { isLastPage, pageNum, total, list } = data
      pagination.isLast = isLastPage
      pagination.page = pageNum
      pagination.total = total
      // orderTotal.value = list[2].orderTotal as unknown as number
      // tableData.value = list ?? []
      tableDataStore.updateTableData(list??[])
    })
    .finally(() => {
      //关闭加载动画
      loading.value = false
    })
}

onBeforeMount(async () => {
  await pageRequest()
})

// 添加查询方法
/**
 * 按条件查询 2025.06.09
 * 
 */
const queryByCondition = async () => {
  loading.value = true;
  try {
    const { data } = await requestMethodHerb.page({
      //传入动态绑定的输入框内容
      ...searchInfo,
      pageNum: pagination.page,
      pageSize: pagination.rows
    });
    const { isLastPage, pageNum, total, list } = data;
    pagination.isLast = isLastPage;
    pagination.page = pageNum;
    pagination.total = total;
    tableDataStore.updateTableData(list ?? []);
  } catch (error) {
    console.error('查询失败:', error);
  } finally {
    loading.value = false;
  }
};


</script>

<style lang="scss">
.Archive {
  background-color: #8687e7;
  width: 100%;
  height: 240px;
}

.archive-show {
  position: relative;
  border-radius: 50px;
  width: 100%;

  .tags {
    display: flex;
    gap: 12px; /* 增加间距 */
    // position: absolute;
    // right: 280px;
    // top: 20px;
    width: 100%;//宽度占比百分之一百时才能进行左对齐
  }

  .tag {
    cursor: pointer;
    font-size: 14px;
    padding: 6px 12px;
    transition: 0.3s;
  }

  .archive-show-card {
    width: 100%;
    display: flex;
    justify-content: center;
    // padding-top: 20px;
  }
}

.search-container {
  display: flex;
  align-items: left;// 修改为左对齐;
  margin-bottom: 15px; // 与下方内容保持间距
  
  .el-input {
    flex: 1;
    margin-right: 10px;
    
    
    .el-input__inner {
      height: 40px;
      line-height: 40px;
    }
  }
  
  .el-button {
    height: 40px;
    padding: 0 20px;
    text-align: left; /* 修改为左对齐 */
    justify-content: flex-start; /* 确保图标和文字都左对齐 */
  }
}
</style>
