<template>
  <div class="layout">
    <div class="header_box">
      <HeaderNav @search="handleSearch" />
    </div>
    <div class="content_box">
      <div class="page">
        <SideNav v-model="activeMenu" :searchText="searchText" />
        <main class="content">
          <!-- 动态加载的组件 -->
          <component :is="currentComponent" />

          <SearchResults v-if="filteredResults.length" :results="filteredResults" />
        </main>

      </div>

    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import HeaderNav from "@/renderer/components/HeaderNav.vue";
import SideNav from "@/renderer/components/SideNav.vue";
import { defineAsyncComponent } from "vue";
import SearchResults from "@/renderer/components/Search.vue";
import { useTableDataStore } from "@/renderer/store/tableDataStore";
import { filterTableData } from "@/renderer/utils/conmon";
// 用数字表示菜单项（提高类型安全性）
const activeMenu = ref<string>("1"); // 默认菜单项，类型为 string
const tableDataStore = useTableDataStore();
const tableData = tableDataStore.tableData;
// 通过异步组件加载优化
const Dashboard = defineAsyncComponent(() => import("./Dashboard.vue"));
const History = defineAsyncComponent(() => import("./History.vue"));
const Archive = defineAsyncComponent(() => import("./Archive.vue"));
const UserInfo = defineAsyncComponent(() => import("./UserInfo.vue"));
const ConfigInfo = defineAsyncComponent(() => import("./ConfigInfo.vue"));
const DataCollection = defineAsyncComponent(() => import("./DataCollection.vue"));
const UserManagement = defineAsyncComponent(() => import("./UserManagement.vue"));
// 存储搜索文本
const searchText = ref("");

// 过滤后的结果
const filteredResults = computed(() =>
  filterTableData(tableData, searchText.value)
);

// 根据 activeMenu 动态选择组件
const currentComponent = computed(() => {
  switch (activeMenu.value) {
    case "1":
      return Dashboard;
    case "2":
      return History;
    case "3":
      return Archive;
    case "4":
      return UserInfo;
    case "5":
      return ConfigInfo;
    case "6":
      return DataCollection;
    case "7":
      return UserManagement;
    default:
      return Dashboard; // 默认组件
  }
});

// 处理搜索文本
const handleSearch = (text: string) => {
  searchText.value = text; // 更新搜索文本
};
</script>

<style lang="scss" scoped>
.layout {
  // display: grid;
  // grid-template-areas:
  //   "header header"
  //   "sidebar main";
  // grid-template-columns: 256px calc(100vw - 256px);
  // grid-template-rows: 64px calc(100vw - 64px);
  // min-height: 100vh;
  // background-color: #f0f2f5;
  background-color: #f9fbff;

  .content {
    // grid-area: main;
    // background-color: #fff;
    margin-left: 233px;
    // padding-bottom: 100px;
    box-sizing: border-box;
    min-height: calc(100vh - 64px);
    // padding: 20px;

  }
}

.header_box {
  position: fixed;
  width: 100%;
  left: 0;
  top: 0;
  z-index: 1500;
  height: 64px;
}

.content_box {
  padding: 0;
  margin-top: 0;
  height: 100%;
  min-height: auto;
  
  // width: 100vw;
  .page {
    height: calc(100% - 64px);
    margin-top: 64px;

  }

}
</style>
