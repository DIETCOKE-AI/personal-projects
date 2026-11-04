<template>
  <div class="login_container">
    <div class="login_card">
      <div class="left">
        <div class="left_img">
          <img src="../../assets/public-image-placeholder.svg" alt="face_logo" />
        </div>
      </div>
      <div class="right">
        <div class="login_form">
          <img src="@/assets/public-brand.svg" alt="form_logo" class="logo" />
          <div class="form_inner">
            <div class="title">账户登录</div>
            <el-form :model="ruleForm" :rules="rules" ref="loginFormRef" label-width="100px" class="demo-ruleForm"
              label-position="top" @keyup.enter="loginPlatform">
              <el-form-item label="用户名" prop="username">
                <el-input v-model="ruleForm.username" placeholder="请输入用户名" clearable></el-input>
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input v-model="ruleForm.password" type="password" placeholder="请输入密码" show-password
                  clearable></el-input>
              </el-form-item>
              <el-form-item label="验证码" prop="code">
                <div class="captcha">
                  <el-input v-model="ruleForm.code" type="text" placeholder="请输入验证码" style="width: 62%;font-size: 14px;"
                    clearable />
                  <div class="captcha-canvas" style="display: flex; align-items: center; justify-content: center;">
                    <img v-if="isRuoYiReady" :src="captcha.img" @click="getCaptcha" style="max-width: 100%; max-height: 100%;" />
                    <span v-else style="font-size: 12px; color: #909399;">服务启动中...</span>
                  </div>
                </div>
              </el-form-item>
              <el-form-item style="margin-top: 30px;">
                <div style="display: flex;justify-content: space-between;width: 100%;">
                  <el-button :loading="isLoading" style="width: 50%;height: 42px;font-size: 16px;letter-spacing: 10px;"
                    type="primary" @click="loginPlatform">
                    登录
                  </el-button>
                  <el-button style="width: 50%;height: 42px;font-size: 16px;letter-spacing: 10px;" @click="goRegister">
                    注册
                  </el-button>
                </div>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted, reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { login, getUserInfo, getCaptchaImage } from "@/renderer/api/ruoyi/user";

const router = useRouter();
const loginFormRef = ref<any>();
const isLoading = ref(false);

// --- Backend Status ---
const isRuoYiReady = ref(false);

const ruleForm = reactive({
  username: '',
  password: '',
  code: ''
});

const captcha = reactive({
    img: '',
    uuid: ''
});

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
  ]
};

// --- API Calls ---
const getCaptcha = async () => {
    try {
        console.log(`[DIAGNOSTIC] Frontend: Attempting to fetch captcha...`);
        const res = await getCaptchaImage();
        if(res.code === 200) {
            captcha.img = "data:image/gif;base64," + res.img;
            captcha.uuid = res.uuid;
        } else {
            ElMessage.error(res.msg || '获取验证码失败');
        }
    } catch (error) {
        console.error("获取验证码失败", error);
        ElMessage.error('获取验证码失败，请检查用户服务是否正常。');
    }
};

const loginPlatform = async () => {
  if (isLoading.value) return;
  if (!isRuoYiReady.value) {
    ElMessage.warning('用户服务尚未就绪，请稍候。');
    return;
  }
  await loginFormRef.value?.validate();
  isLoading.value = true;
  
  try {
    const loginRes = await login({ 
        username: ruleForm.username, 
        password: ruleForm.password, 
        code: ruleForm.code, 
        uuid: captcha.uuid 
    });

    if (loginRes.code === 200) {
      localStorage.setItem("token", loginRes.token);
      const userInfoRes = await getUserInfo();
      if (userInfoRes.code === 200) {
        localStorage.setItem("user", JSON.stringify(userInfoRes.user));
        ElMessage.success("登录成功！");
        router.push("/");
      } else {
        ElMessage.error(userInfoRes.msg || '获取用户信息失败');
        getCaptcha();
      }
    } else {
      ElMessage.error(loginRes.msg || '登录失败');
      getCaptcha();
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.msg || '登录请求失败');
    getCaptcha();
  } finally {
    isLoading.value = false;
  }
};

const goRegister = () => {
  router.push("/register");
};

// --- Backend Readiness Logic ---
const handleBackendReadiness = (readiness) => {
  console.log(`[DIAGNOSTIC] Frontend: Received readiness update: ${JSON.stringify(readiness)}`);
  if (readiness.ruoyi && !isRuoYiReady.value) {
    isRuoYiReady.value = true;
    console.log('[DIAGNOSTIC] Frontend: RuoYi is ready, fetching captcha...');
    getCaptcha();
  }
  if (!readiness.ruoyi) {
      isRuoYiReady.value = false;
  }
};

onMounted(async () => {
  console.log('[DIAGNOSTIC] Frontend: LoginPlatform onMounted hook started.');
  
  // 注册监听器，用于接收来自主进程的实时状态更新
  (window as any).electron.onBackendReadinessUpdate(handleBackendReadiness);

  // 立即获取一次当前的后端状态
  try {
    console.log('[DIAGNOSTIC] Frontend: Requesting initial readiness state...');
    const result = await (window as any).electron.getBackendReadiness();
    if (result.success) {
      console.log(`[DIAGNOSTIC] Frontend: Got initial readiness: ${JSON.stringify(result.readiness)}`);
      handleBackendReadiness(result.readiness);
    } else {
      ElMessage.error('无法获取后端服务初始状态');
    }
  } catch (error) {
    console.error('查询后端初始状态时出错:', error);
    ElMessage.error('查询后端状态时出错');
  }
});

onUnmounted(() => {
  // 组件销毁时，移除监听器以防止内存泄漏
  (window as any).electron.onBackendReadinessUpdate(() => {});
});

</script>

<style lang="scss" scoped>
.login_container {
  display: flex;
  justify-content: center;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  position: fixed;
  background-color: #cae6fc;

  .login_card {
    width: 90%;
    height: 100%;
    display: flex;

    .left {
      width: 50%;
      height: 100%;
      display: flex;

      .left_img {
        margin: auto;
      }
    }

    .right {
      width: 50%;
      height: 100%;
      display: flex;
      justify-content: center;

      .login_form {
        border-radius: 12px;
        margin: auto;
        background-color: #ffffff;
        height: 600px;
        width: 485px;
        position: relative;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

        .logo {
          position: absolute;
          top: -9%;
          left: 35%;
          width: 30%;
          z-index: 1;
        }

        .form_inner {
          margin-top: 90px;
          padding: 20px;

          .title {
            font-size: 27px;
            margin-bottom: 30px;
            color: #333333;
            font-weight: bold;
            text-align: center;
          }

          :deep(.el-form-item__label) {
            font-weight: bold;
            padding-bottom: 8px;
          }

          :deep(.el-input__wrapper) {
            height: 48px;
            width: 100%;
            border-radius: 8px;
            border: 1px solid #d1e3f4;
            padding: 0 15px;
            font-size: 16px;
            color: #666666;
            box-sizing: border-box;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
          }

          :deep(.el-input__wrapper.is-focus) {
            border-color: #cae6fc;
            box-shadow: 0 0 6px rgba(202, 230, 252, 0.5);
          }
        }
      }

      .captcha {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;

        .captcha-canvas {
          cursor: pointer;
          border-radius: 4px;
          border: 1px solid #dcdfe6;
          transition: border-color 0.3s;
          height: 40px; // 确保高度一致

          &:hover {
            border-color: #c0c4cc;
          }
        }
      }
    }
  }
}
</style>