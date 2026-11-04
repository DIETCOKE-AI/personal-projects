<!-- src/renderer/views/UserManagement.vue -->
<template>
  <div class="user-management-container p-4">
    <div>
      <!-- 搜索卡片 -->
      <el-card class="mb-4">
        <el-form :model="queryParams" ref="queryFormRef" :inline="true" label-width="68px">
          <el-form-item label="用户名" prop="userName">
            <el-input
              v-model="queryParams.userName"
              placeholder="请输入用户名"
              clearable
              @keyup.enter="handleQuery"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleQuery" v-if="isAdmin">搜索</el-button>
            <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 用户数据表格卡片 -->
      <el-card>
        <template #header>
          <div class="flex justify-between items-center">
            <span>用户列表</span>
            <el-button type="primary" :icon="Plus" @click="handleAdd" v-if="isAdmin">新增用户</el-button>
          </div>
        </template>

        <el-table v-loading="loading" :data="userList" row-key="userId" :row-class-name="tableRowClassName">
          <el-table-column prop="userId" label="用户ID" width="100" align="center" />
          <el-table-column prop="userName" label="用户名" align="center" />
          <el-table-column prop="nickName" label="用户昵称" align="center" />
          <el-table-column prop="email" label="邮箱" align="center" />
          <el-table-column prop="phonenumber" label="手机号" align="center" />
          <el-table-column prop="roles" label="角色" align="center">
            <template #default="{ row }">
              <el-tag 
                v-for="role in row.roles" 
                :key="role.roleId" 
                class="mx-1"
              >
                {{ role.roleName }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" align="center">
            <template #default="{ row }">
              <el-tag :type="row.del_flag === '0' ? 'success' : 'info'">
                {{ row.delFlag === '0' ? '正常' : '已删除' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="创建时间" align="center" width="180" />
          <el-table-column label="操作" align="center" width="220">
            <template #default="{ row }">
              <template v-if="row.delFlag === '0'">
                <el-button type="primary" :icon="Edit" text @click="handleEdit(row)">编辑</el-button>
                <el-button type="warning" :icon="Key" text @click="handleResetPassword(row)">修改密码</el-button>
                <el-button type="danger" :icon="Delete" text @click="handleDelete(row)">禁用</el-button>
              </template>
              <template v-else>
                <el-button type="success" :icon="RefreshLeft" text @click="handleRestore(row)">恢复用户</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <el-pagination
          class="mt-4"
          v-model:current-page="pagination.pageNum"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </el-card>
    </div>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="600px" @close="handleDialogClose">
      <el-form ref="userFormRef" :model="userForm" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="userName">
          <el-input v-model="userForm.userName" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="用户昵称" prop="nickName">
          <el-input v-model="userForm.nickName" placeholder="请输入用户昵称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phonenumber">
          <el-input v-model="userForm.phonenumber" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item v-if="!userForm.userId" label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="roleIds">
          <el-select v-model="userForm.roleIds" multiple placeholder="请选择角色">
            <el-option
              v-for="item in roleOptions"
              :key="item.roleId"
              :label="item.roleName"
              :value="item.roleId"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleSubmit">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog title="修改密码" v-model="resetPwdDialogVisible" width="500px" @close="handleResetPwdDialogClose">
      <el-form ref="resetPwdFormRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="80px">
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetPwdForm.newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="resetPwdForm.confirmPassword" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdDialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleResetPwdSubmit">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { Search, Plus, Edit, Delete, Refresh, Key } from '@element-plus/icons-vue';
import { getRuoYiUsers, getRuoYiUsersAll, getRuoYiUserById, createRuoYiUser, updateRuoYiUser, deleteRuoYiUser, getAllRoles, getUserRolesByUserIds, resetUserPassword, restoreRuoYiUser, type RuoYiUserData } from '@/renderer/api/ruoyi/user';

// --- 响应式数据 ---
const loading = ref(true);
const userList = ref<RuoYiUserData[]>([]);
const total = ref(0);
const tableRowClassName = ({ row }: { row: any }) => {
  if (row.delFlag === '2') {
              if (row.delFlag === '2') { // <--- 将 del_flag 改为 delFlag
                return 'deleted-row';
              }
             return '';
           };
          }

          const handleRestore = (row: RuoYiUserData) => {
      ElMessageBox.confirm(`确定要恢复用户 "${row.userName}" 吗？`, '提示', {
        confirmButtonText: '确定恢复',
        cancelButtonText: '取消',
        type: 'success',
      }).then(async () => {
        try {
          const res = await restoreRuoYiUser(row.userId!);
          if (res.code === 200) {
            ElMessage.success('恢复成功');
            fetchUserList();
          } else {
            ElMessage.error(res.msg || '恢复失败');
          }
        } catch (error) {
          ElMessage.error('网络错误，恢复失败');
        }
      }).catch(() => {
       ElMessage.info('已取消恢复');
      });
    };
// 查询参数
const queryParams = reactive({
  userName: '',
});
const queryFormRef = ref<FormInstance>();

// 分页
const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
});

// 对话框
const dialogVisible = ref(false);
const dialogTitle = ref('');
const userFormRef = ref<FormInstance>();
const userForm = reactive<any>({
  userId: undefined,
  userName: '',
  nickName: '',
  email: '',
  phonenumber: '',
  password: '',
  roleIds: [] // 新增：用于存储用户所选的角色ID
});

// 所有可用角色的列表
const roleOptions = ref<{ roleId: number, roleName: string }[]>([]);

// --- 权限控制 ---
const currentUser = ref(JSON.parse(localStorage.getItem('user') || '{}'));
const isAdmin = computed(() => {
  return currentUser.value.roles?.some((role: any) => role.roleKey === 'admin');
});

// --- 修改密码对话框相关 ---
const resetPwdDialogVisible = ref(false);
const resetPwdFormRef = ref<FormInstance>();
const currentUserForPwdReset = ref<{ userId?: number; userName?: string }>({});
const resetPwdForm = reactive({
  newPassword: '',
  confirmPassword: ''
});

// 确认密码的自定义校验器
const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入密码'));
  } else if (value !== resetPwdForm.newPassword) {
    callback(new Error("两次输入的密码不一致!"));
  } else {
    callback();
  }
};

const resetPwdRules = reactive<FormRules>({
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }],
  confirmPassword: [{ required: true, validator: validatePass2, trigger: 'blur' }]
});

// 表单校验规则
const rules = reactive<FormRules>({
  userName: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  nickName: [{ required: true, message: '请输入用户昵称', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  phonenumber: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  roleIds: [{ required: true, type: 'array', message: '请至少选择一个角色', trigger: 'change' }]
});

// --- 方法 ---

/** 获取所有角色列表 */
const fetchRoleList = async () => {
  try {
    const res = await getAllRoles();
    if (res.code === 200) {
      roleOptions.value = res.rows;
    } else {
      ElMessage.error(res.msg || '获取角色列表失败');
    }
  } catch (error) {
    ElMessage.error('网络错误，无法获取角色列表');
  }
};

/** 获取用户列表 */
const fetchUserList = async () => {
  loading.value = true;
  try {
    // 第一步：获取用户基础列表
    const baseUserRes = await getRuoYiUsersAll({ ...queryParams, ...pagination });
    if (baseUserRes.code !== 200) {
      ElMessage.error(baseUserRes.msg || '获取用户列表失败');
      return;
    }

    const baseUsers = baseUserRes.rows;
    total.value = baseUserRes.total;

    // 如果列表为空，则无需获取角色
    if (baseUsers.length === 0) {
      userList.value = [];
      return;
    }

    // 第二步：提取用户ID，批量获取角色信息
    const userIds = baseUsers.map(u => u.userId);
    const rolesRes = await getUserRolesByUserIds(userIds);
    if (rolesRes.code !== 200) {
      ElMessage.error(rolesRes.msg || '获取用户角色失败');
      // 即使角色获取失败，也显示基础用户列表
      userList.value = baseUsers.map(u => ({ ...u, roles: [] }));
      return;
    }

    // 第三步：将角色信息拼接回用户列表
    const usersWithRoles = rolesRes.data;
    const userMap = new Map(usersWithRoles.map(u => [u.userId, u.roles]));

    userList.value = baseUsers.map(user => ({
      ...user,
      roles: userMap.get(user.userId) || []
    }));

  } catch (error) {
    console.error(error);
    ElMessage.error('网络错误，无法获取用户列表');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (isAdmin.value) {
    fetchUserList();
    fetchRoleList(); // 组件加载时获取所有角色
  } else {
    loading.value = false;
     ElMessage.error('您没有权限访问此页面');
  }
});

const handleQuery = () => {
  pagination.pageNum = 1;
  fetchUserList();
};

const resetQuery = () => {
  queryFormRef.value?.resetFields();
  handleQuery();
};

const handleSizeChange = (size: number) => {
  pagination.pageSize = size;
  fetchUserList();
};

const handleCurrentChange = (page: number) => {
  pagination.pageNum = page;
  fetchUserList();
};

const handleAdd = () => {
  handleDialogClose();
  dialogTitle.value = '新增用户';
  dialogVisible.value = true;
};

const handleEdit = async (row: RuoYiUserData) => {
  handleDialogClose();
  dialogTitle.value = '编辑用户';
  try {
    const res = await getRuoYiUserById(row.userId!);
    if (res.code === 200) {
        nextTick(() => {
            Object.assign(userForm, res.data);
            // 单独处理角色ID
            userForm.roleIds = res.postIds || [];
        });
        dialogVisible.value = true;
    } else {
        ElMessage.error(res.msg || '获取用户信息失败');
    }
  } catch (error) {
      ElMessage.error('网络错误，无法获取用户信息');
  }
};

const handleDelete = (row: RuoYiUserData) => {
  ElMessageBox.confirm(`确定要删除用户 "${row.userName}" 吗？`, '警告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      const res = await deleteRuoYiUser(row.userId!);
      if (res.code === 200) {
        ElMessage.success('删除成功');
        fetchUserList();
      } else {
        ElMessage.error(res.msg || '删除失败');
      }
    } catch (error) {
      ElMessage.error('网络错误，删除失败');
    }
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
};

const handleDialogClose = () => {
  userFormRef.value?.resetFields();
  Object.assign(userForm, {
    userId: undefined,
    userName: '',
    nickName: '',
    email: '',
    phonenumber: '',
    password: ''
  });
};

const handleSubmit = async () => {
  if (!userFormRef.value) return;
  await userFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        let res;
        if (userForm.userId) {
          res = await updateRuoYiUser(userForm);
        } else {
          res = await createRuoYiUser(userForm);
        }
        if (res.code === 200) {
          ElMessage.success(userForm.userId ? '更新成功' : '新增成功');
          dialogVisible.value = false;
          fetchUserList();
        } else {
          ElMessage.error(res.msg || '操作失败');
        }
      } catch (error) {
        ElMessage.error('网络错误，操作失败');
      }
    }
  });
};

// --- 修改密码相关方法 ---

/** 处理修改密码按钮点击 */
const handleResetPassword = (row: RuoYiUserData) => {
  currentUserForPwdReset.value = { userId: row.userId, userName: row.userName };
  resetPwdDialogVisible.value = true;
};

/** 修改密码对话框关闭回调 */
const handleResetPwdDialogClose = () => {
  resetPwdFormRef.value?.resetFields();
  resetPwdDialogVisible.value = false; // 确保v-model绑定的值被更新
};

/** 提交修改密码表单 */
const handleResetPwdSubmit = async () => {
  if (!resetPwdFormRef.value) return;
  await resetPwdFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const res = await resetUserPassword(currentUserForPwdReset.value.userId!, resetPwdForm.newPassword);
        if (res.code === 200) {
          ElMessage.success(`用户 "${currentUserForPwdReset.value.userName}" 的密码修改成功`);
          resetPwdDialogVisible.value = false;
        } else {
          ElMessage.error(res.msg || '密码修改失败');
        }
      } catch (error) {
        ElMessage.error('网络错误，密码修改失败');
      }
    }
  });
};
</script>

<style scoped>
.user-management-container {
  height: 100%;
}
.p-4 {
  padding: 1.5rem;
}
.mb-4 {
  margin-bottom: 1.5rem;
}
.mt-4 {
  margin-top: 1.5rem;
}
.flex {
  display: flex;
}
.justify-between {
  justify-content: space-between;
}
.items-center {
  align-items: center;
}
:deep(.el-table .deleted-row) {
  color: #909399 !important;
  background-color: #f5f5f5 !important;
}
:deep(.el-table .deleted-row:hover > td) {
    background-color: #f0f0f0 !important;
}
</style>