<template>
  <div class="search-wrapper">
    <el-input
      v-model="searchText"
      placeholder="Search"
      class="search-input"
      @input="onSearch"
      @focus="showDropdown = true"
      @blur="onBlur"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <div v-if="showDropdown && filteredResults.length" class="search-results">
      <div
        v-for="(item, index) in limitedResults"
        :key="index"
        class="result-item"
        @mousedown.prevent="handleSelect(item)"
      >
        <h3>{{ item.name }}</h3>
        <p>{{ item.details }}</p>
        <p class="source">
          <span class="label">来源：</span>
          {{ item.source }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Search } from "@element-plus/icons-vue";
import { useTableDataStore } from "@/renderer/store/tableDataStore";

const searchText = ref("");
const showDropdown = ref(false);
const tableDataStore = useTableDataStore();
const tableData = tableDataStore.tableData;

const emit = defineEmits(["select"]);

const filteredResults = computed(() => {
  if (!searchText.value.trim()) return [];
  return tableData.filter((item) => item.name.includes(searchText.value));
});

const limitedResults = computed(() => filteredResults.value.slice(0, 4));

const onSearch = () => {
  showDropdown.value = true;
};

const handleSelect = (item: {
  name: string;
  details: string;
  source: string;
}) => {
  emit("select", item);
  showDropdown.value = false;
  searchText.value = item.name;
};

const onBlur = () => {
  setTimeout(() => {
    showDropdown.value = false;
  }, 200); // 延迟隐藏以确保点击事件触发
};
</script>

<style lang="scss" scoped>
.search-wrapper {
  position: relative;
  width: 400px;
}

.search-results {
  position: absolute;
  width: 100%;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  margin-top: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.result-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.3s;
  &:hover {
    background-color: #f5f7fa;
  }

  h3 {
    font-size: 14px;
    margin-bottom: 6px;
    color: #303133;
  }

  p {
    font-size: 12px;
    color: #606266;
    line-height: 1.5;
    margin-bottom: 4px;
  }

  .source {
    font-size: 12px;
    color: #909399;
    .label {
      color: #909399;
    }
  }
}
</style>
