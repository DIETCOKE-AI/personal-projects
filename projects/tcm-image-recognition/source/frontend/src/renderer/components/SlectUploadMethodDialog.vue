<template>
  <el-dialog
    :model-value="props.visible"
    @update:modelValue="handleCancel"
    width="400px"
    :show-close="false"
  >
    <template #header>
      <span>选择上传方式</span>
    </template>

    <el-form :model="form" label-width="120px">
      <el-form-item label="上传方式">
        <el-select
          v-model="form.selectedUploadMethod"
          placeholder="请选择上传方式"
        >
          <el-option label="拍照上传" value="photo"></el-option>
          <el-option label="图片上传" value="image"></el-option>
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确认</el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts" setup>
import { ref } from "vue";
const emit = defineEmits(["update:slectMethod", "selectMethod"]);

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
});

const form = ref({
  selectedUploadMethod: "",
});

const handleCancel = () => {
  emit("update:slectMethod", false);
};

const handleConfirm = () => {
  if (form.value.selectedUploadMethod) {
    emit("selectMethod", form.value.selectedUploadMethod);
    emit("update:slectMethod", false);
  } else {
    alert("请选择上传方式");
  }
};
</script>

<!-- dashboar=> select =>dashboar =>uploaddialog -->
