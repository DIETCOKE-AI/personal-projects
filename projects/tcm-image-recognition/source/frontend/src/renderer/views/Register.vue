<template>
  <div class="register">
    <div class="register-card">
      <el-form ref="registerFormRef" :model="registerForm" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="name">
          <el-input v-model="registerForm.name" placeholder="请输入用户名"></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="请输入密码"></el-input>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码"></el-input>
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="registerForm.phone" placeholder="请输入手机号"></el-input>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" placeholder="请输入邮箱"></el-input>
        </el-form-item>
        <!-- 新增的验证码组件 -->
        <el-form-item label="验证码" prop="code">
          <div class="captcha-wrapper">
            <el-input v-model="registerForm.code" placeholder="请输入验证码" class="captcha-input"></el-input>
            <img :src="captchaImg" @click="getCaptcha" class="captcha-img" title="看不清？点击刷新" />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitForm">注册</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="goLogin">返回登录</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { register, getCaptchaImage } from "@/renderer/api/ruoyi/user";

const router = useRouter();
const registerFormRef = ref<FormInstance>();

// 表单数据
const registerForm = reactive({
  name: "",
  password: "",
  confirmPassword: "",
  email: "",
  phone: "",
  code: "", // 新增：验证码
});

// 验证码相关状态
const captchaImg = ref("");
const uuid = ref("");

// 获取验证码逻辑
const getCaptcha = async () => {
  try {
    const res = await getCaptchaImage();
    if (res.img) {
      captchaImg.value = "data:image/gif;base64," + res.img;
      uuid.value = res.uuid;
    }
  } catch (error) {
    ElMessage.error("验证码加载失败");
  }
};

// 组件加载时自动获取一次验证码
onMounted(() => {
  getCaptcha();
});

// 确认密码校验器
const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error("两次输入密码不一致!"))
  } else {
    callback()
  }
}

// 表单验证规则
const rules = reactive<FormRules>({
  name: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, max: 16, message: "长度在 3 到 16 个字符", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码长度至少6位", trigger: "blur" },
  ],
  confirmPassword: [
    { required: true, validator: validatePass2, trigger: "blur" },
  ],
  phone: [
    { required: true, message: "请输入手机号", trigger: "blur" },
    { pattern: /^1[3-9]\d{9}$/, message: "请输入有效的手机号码", trigger: "blur" },
  ],
  email: [
      { required: true, message: "请输入邮箱地址", trigger: "blur" },
      { type: "email", message: "请输入有效的邮箱地址", trigger: "blur" }
  ],
  code: [ // 新增：验证码校验规则
      { required: true, message: "请输入验证码", trigger: "blur" },
  ],
});

// 提交表单
const submitForm = async () => {
  if (!registerFormRef.value) return;
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        // 提交包含所有信息的完整数据
        const res = await register({
          username: registerForm.name,
          password: registerForm.password,
          email: registerForm.email,
          phonenumber: registerForm.phone,
          code: registerForm.code,
          uuid: uuid.value,
        });
        if (res.code === 200) {
          ElMessage.success("注册成功，即将跳转到登录页面");
          setTimeout(() => router.push("/login"), 1500);
        } else {
          // 注册失败时，自动刷新验证码
          getCaptcha();
          ElMessage.error(res.msg || "注册失败");
        }
      } catch (error: any) {
        // 请求失败时，也自动刷新验证码
        getCaptcha();
        const msg = error.response?.data?.msg || error.message || "注册请求失败";
        ElMessage.error(msg);
      }
    }
  });
};

const goLogin = () => {
  router.push("/login");
};
</script>

<style lang="scss" scoped>
.register {
  background: linear-gradient(135deg, #a3c8f0 0%, #e1f1ff 100%);
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;

  .register-card {
    width: 100%;
    max-width: 400px;
    background-color: #ffffff;
    padding: 40px;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);

    .el-form-item {
      margin-bottom: 20px;
    }

    .el-button {
      width: 100%;
      height: 36px;
      font-size: 14px;
      border-radius: 18px;
      margin-bottom: 10px;
    }

    .captcha-wrapper {
      display: flex;
      align-items: center;
      width: 100%;
      
      .captcha-input {
        flex-grow: 1;
        margin-right: 10px;
      }

      .captcha-img {
        width: 110px;
        height: 32px;
        cursor: pointer;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
      }
    }
  }
}
</style>
