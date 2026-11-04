<template>
  <el-dialog
    :model-value="visible"
    title="联系方式设置"
    width="600px"
    @close="handleClose"
    :close-on-click-modal="false"
  >
    <el-form 
      :model="form"
      :rules="rules"
      ref="settingsForm"
      label-width="100px"
    >
      <el-form-item label="联系地址" prop="address">
        <el-input v-model="form.address" placeholder="请输入详细地址" />
      </el-form-item>
      <el-form-item label="所在城市" prop="city">
        <el-input v-model="form.city" placeholder="请输入城市" />
      </el-form-item>
      <el-form-item label="国家/地区" prop="country">
        <el-select v-model="form.country" placeholder="请选择国家">
          <el-option label="中国" value="CN" />
          <el-option label="其他" value="OTH" />
        </el-select>
      </el-form-item>
      <el-form-item label="邮政编码" prop="postalCode">
        <el-input v-model="form.postalCode" placeholder="请输入邮政编码" />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取 消</el-button>
        <el-button type="primary" @click="submitForm">保 存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, defineProps, defineEmits } from 'vue';
import { ElMessage, type FormInstance } from 'element-plus';
import { getContactInfoByUserId, updateContactInfo } from '@/renderer/api/ruoyi/user';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
  userId: {
    type: [Number, String],
    required: true,
  },
});

const emit = defineEmits(['update:visible', 'data-updated']);

const settingsForm = ref<FormInstance>();
const form = ref({
  userId: props.userId,
  address: '',
  city: '',
  country: 'CN',
  postalCode: ''
});

const rules = {
  address: [{ required: true, message: '请输入联系地址', trigger: 'blur' }],
  city: [{ required: true, message: '请输入所在城市', trigger: 'blur' }],
  postalCode: [{ required: true, message: '请输入邮政编码', trigger: 'blur' }, { pattern: /^[0-9]{6}$/, message: '请输入6位数字邮政编码', trigger: 'blur' }]
};

const loadData = async () => {
  if (!props.userId) return;
  try {
    const res = await getContactInfoByUserId(Number(props.userId));
    if (res.code === 200 && res.data) {
      form.value = { ...form.value, ...res.data };
    }
  } catch (error) {
    ElMessage.error('加载联系方式失败');
  }
};

const submitForm = async () => {
  if (!settingsForm.value) return;
  await settingsForm.value.validate(async (valid) => {
    if (valid) {
      try {
        const response = await updateContactInfo(form.value);
        if (response.code === 200) {
          ElMessage.success('保存成功');
          emit('data-updated'); // 通知父组件数据已更新
          handleClose();
        } else {
          ElMessage.error(response.msg || '保存失败');
        }
      } catch (error) {
        ElMessage.error('保存请求失败');
      }
    }
  });
};

const handleClose = () => {
  emit('update:visible', false);
};

// 监听 props.visible 的变化，当弹窗显示时加载数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    // 关键：在加载新数据前，先重置表单状态，防止显示旧的脏数据
    form.value = {
      userId: props.userId,
      address: '',
      city: '',
      country: 'CN',
      postalCode: ''
    };
    loadData();
  }
});

</script>

<style scoped>
.el-select {
  width: 100%;
}
</style>