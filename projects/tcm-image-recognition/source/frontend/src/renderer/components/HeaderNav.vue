<template>
  <header class="header_box">
    <div class="header">
      
      <div class="logo">
        <img :src="logoPng" style="width: 54px;height: 100%;object-fit: cover;">
        <div>甄识科技</div>
      </div>
      <div class="search">
        <!-- <Search @select="handleSelect" /> -->
      </div>
      <div class="user-info">
        <!-- 用户信息下拉菜单 -->
        <el-dropdown trigger="hover">
          <div class="user-info-dropdown">
            <el-avatar :src="userAvatar" />
            <span class="username">{{ username }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import logoPng from "@/assets/public-brand.svg"

const router = useRouter();
const username = computed(()=>{
  return JSON.parse(localStorage.getItem('user') as string)?.userName||'用户'
})
const userAvatar = ref("./avatar-placeholder.svg");

// 退出登录
const handleLogout = () => {
  localStorage.clear();
  router.push("/login");
  ElMessage.warning("已退出登录");
};
</script>

<style lang="scss" scoped>
.header_box {
  height: 64px;
  background-color: #fff;
  color: #fff;
  top: 0;
  left: 0;
  width: 100%;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header {
  margin: 0 20px;
  line-height: 64px;
  z-index: 100;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;

  .logo {
    font-size: 20px;
    font-weight: bold;
    color: #1a1a1a;
    display: flex;
    flex-direction: row;
    gap: 10px;
    justify-content: center;
    align-items: center;
    letter-spacing: 2px;
  }

  .search {
    width: 400px;
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;

    .user-info-dropdown {
      display: flex;
      align-items: center;
      gap: 8px;

      .username {
        font-size: 14px;
        color: #1a1a1a;
      }
    }
  }
}
</style>

