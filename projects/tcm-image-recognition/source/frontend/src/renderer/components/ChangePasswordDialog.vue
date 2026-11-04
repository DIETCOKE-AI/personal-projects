
<template>
  <el-dialog
    :model-value="visible"
    title="修改密码"
    width="500px"
    @close="handleClose"
    :close-on-click-modal="false"
  >
    <el-form
      :model="form"
      :rules="rules"
      ref="passwordForm"
      label-width="100px"
    >
      <el-form-item label="旧密码" prop="oldPassword">
        <el-input type="password" v-model="form.oldPassword" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input type="password" v-model="form.newPassword" show-password />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirmPassword">
        <el-input type="password" v-model="form.confirmPassword" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="resetForm">清 空</el-button>
        <el-button type="primary" @click="submitForm" :loading="loading">确 定</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, defineProps, defineEmits } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance } from 'element-plus';
import { updateUserPassword } from '@/renderer/api/ruoyi/user';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(['update:visible']);
const router = useRouter();

const loading = ref(false);
const passwordForm = ref<FormInstance>();
const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入新密码'));
  } else if (value !== form.value.newPassword) {
    callback(new Error("两次输入的新密码不一致!"));
  } else {
    callback();
  }
};

const rules = {
  oldPassword: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validatePass2, trigger: 'blur' }
  ]
};

const submitForm = async () => {
  if (!passwordForm.value) return;
  await passwordForm.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        const response = await updateUserPassword(form.value.oldPassword, form.value.newPassword);
        if (response.code === 200) {
          ElMessage.success('密码修改成功，请重新登录');
          localStorage.removeItem('user');
          localStorage.removeItem('token');
          handleClose();
          router.push({ name: 'login' });
        } else {
          ElMessage.error(response.msg || '密码修改失败');
        }
      } catch (error) {
        ElMessage.error('请求失败');
      } finally {
        loading.value = false;
      }
    }
  });
};

const resetForm = () => {
  passwordForm.value?.resetFields();
};

const handleClose = () => {
  resetForm(); // 关闭时也清空表单
  emit('update:visible', false);
};

</script>
