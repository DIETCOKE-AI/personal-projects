<template>
  <div class="user-info">
    <CardWrapper>
      <div class="main-content">
        <div class="left-panel">
          <!-- <div class="nav-item">我的账号</div> -->
          <!-- 用户信息表单 -->
          <div class="user-form">
            <h3>用户信息</h3>
            <el-form :model="userInfo" label-position="top">
              <div class="form-row">
                <el-form-item label="用户名">
                  <el-input v-model="userInfo.username" readonly />
                </el-form-item>
                <el-form-item label="用户邮箱">
                  <el-input v-model="userInfo.email" readonly />
                </el-form-item>
              </div>
            </el-form>
          </div>

          <!-- 联系信息部分 -->
          <div class="contact-info">
            <h3>联系信息</h3>
            <el-form :model="contactInfo" label-position="top">
              <el-form-item label="联系地址">
                <el-input v-model="contactInfo.address" readonly />
              </el-form-item>
              <div class="form-row">
                <el-form-item label="地区">
                  <el-input v-model="contactInfo.city" readonly />
                </el-form-item>
                <el-form-item label="国家">
                  <el-input v-model="contactInfo.country" readonly />
                </el-form-item>
                <el-form-item label="邮政编码">
                  <el-input v-model="contactInfo.postalCode" readonly />
                </el-form-item>
              </div>
            </el-form>
          </div>
        </div>

        <!-- 右侧用户卡片 -->
        <div class="right-panel">
          <div class="user-card">
            <el-avatar :size="100" :src="userInfo.avatar" />
            <h2>{{ userInfo.username }}</h2>
            <p class="job-title">{{ userInfo.jobTitle }}</p>
            <p class="education">{{ userInfo.education }}</p>
            <div class="action-buttons">
              <el-button type="primary" @click="showSettingsDialog = true">联系方式设置</el-button>
              <el-button type="warning" @click="showChangePasswordDialog = true">修改密码</el-button>
            </div>
          </div>
        </div>
      </div>
    </CardWrapper>

    <!-- 设置弹窗 -->
    <UserSettingsDialog 
      v-if="userInfo.userId" 
      v-model:visible="showSettingsDialog" 
      :user-id="userInfo.userId"
      @data-updated="loadContactInfo"
    />

    <!-- 修改密码弹窗 -->
    <ChangePasswordDialog 
      v-if="userInfo.userId"
      v-model="showChangePasswordDialog"
      :user-id="userInfo.userId"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import CardWrapper from "@/renderer/components/CardWrapper.vue";
import UserSettingsDialog from "@/renderer/components/UserSettingsDialog.vue";
import ChangePasswordDialog from "@/renderer/components/ChangePasswordDialog.vue";
import { ElMessage } from 'element-plus';
import { getContactInfoByUserId } from '@/renderer/api/ruoyi/user';

const showSettingsDialog = ref(false);
const showChangePasswordDialog = ref(false);

const userInfo = ref({
  userId: null as number | null,
  avatar: './avatar-placeholder.svg',
  username: "",
  email: "",
  jobTitle: "",
  education: "",
});

const contactInfo = ref({
  address: "",
  city: "",
  country: "",
  postalCode: "",
});

const loadUserInfo = () => {
  const userData = localStorage.getItem('user');
  if (userData) {
    const parsedData = JSON.parse(userData);
    userInfo.value.userId = parsedData.userId;
    userInfo.value.username = parsedData.userName || '';
    userInfo.value.email = parsedData.email || '';
  }
};

const loadContactInfo = async () => {
  if (!userInfo.value.userId) {
    return;
  }
  try {
    const response = await getContactInfoByUserId(userInfo.value.userId);
    if (response.code === 200 && response.data) {
      contactInfo.value = response.data;
    } else {
      contactInfo.value = { address: "", city: "", country: "", postalCode: "" };
    }
  } catch (error) {
    ElMessage.error('请求加载联系人信息失败');
    contactInfo.value = { address: "", city: "", country: "", postalCode: "" };
  }
};

onMounted(() => {
  loadUserInfo();
  loadContactInfo();
});

</script>

<style scoped lang="scss">
$primary-color: #f0f2f8;
$card-background: #fff;
$shadow-color: rgba(0, 0, 0, 0.1);
$text-secondary: #909399;

.user-info {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 64px);
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 20px;
  max-width: 1200px;
  width: 100%;
}

.left-panel,
.right-panel {
  background: $card-background;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px $shadow-color;
}

.user-card {
  text-align: center;

  .action-buttons {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .job-title,
  .education {
    color: $text-secondary;
    font-size: 14px;
  }
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
</style>