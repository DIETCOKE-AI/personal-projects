<template>
  <aside class="sidebar">
    <el-menu :default-active="activeIndex" class="sidebar-menu" background-color="#f0f2f5" @select="handleSelect">
      <el-menu-item v-for="item in filteredMenu" :key="item.index" :index="item.index">
        <el-icon>
          <Camera />
        </el-icon>
        <span>{{ item.name }}</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Camera, Picture, Location, User } from "@element-plus/icons-vue";

const activeIndex = ref("1");
const searchText = ref("");
const emit = defineEmits(["update:modelValue"]);
// 菜单数据
const menuData = [
  { name: "药材识别", index: "1" },
  { name: "数据采集", index: "6" },
  { name: "历史记录", index: "2" },
  { name: "药材资源库", index: "3" },
  { name: "用户信息", index: "4" },
  { name: "配置数据", index: "5" },
  {name:"用户管理",index:"7"},
];

// 过滤后的菜单项
const filteredMenu = computed(() => {
  if (!searchText.value) return menuData;
  return menuData.filter((item) => item.name.includes(searchText.value));
});

const handleSelect = (index: string) => {
  activeIndex.value = index;
  emit("update:modelValue", index);
};
</script>

<style lang="scss" scoped>
.sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  margin-top: 64px;
  width: 233px;
  transition: padding-top .3s;
  grid-area: sidebar;
  background-color: #ffffff;
  border-right: 1px solid #e8e8e8;

  .sidebar-menu {
    background-color: #ffffff;
    border-right: none;
  }
}
</style>
