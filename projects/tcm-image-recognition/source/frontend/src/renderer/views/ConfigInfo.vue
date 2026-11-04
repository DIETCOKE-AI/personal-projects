<template>
  <div class="user-info">
    <div class="content-section">
      <!-- <div class="user-form">
        <div class="block">
          <div class="demonstration">曝光</div>
          <el-input-number v-model="form1.bg" controls-position="right" :min="0"></el-input-number>
        </div>
        <div class="block">
          <div class="demonstration">增益</div>
          <el-slider v-model="form1.zy" show-input :min="0" :max="100"></el-slider>
        </div>
      </div> -->
      <div class="jt-content">
        <div class="jt-title">
          镜头参数
        </div>
        <el-table :data="tableData" border style="width: 100%">
          <el-table-column prop="name" label="镜头名称" width="180">
          </el-table-column>
          <el-table-column prop="bg" label="曝光" width="180">
            <template #default="scope">
              <el-input-number :disabled="true" v-model="scope.row.bg" controls-position="right" :min="0"></el-input-number>
            </template>
          </el-table-column>
          <el-table-column prop="zy" label="增益">
            <template #default="scope">
              <el-input-number :disabled="true" v-model="scope.row.zy" controls-position="right" :min="0"></el-input-number>
            </template>
          </el-table-column>
          <el-table-column prop="autoW" label="自动白平衡">
            <template #default="scope">
              <el-switch :disabled="true" v-model="scope.row.autoW" active-color="#13ce66" inactive-color="#ff4949" />
            </template>
          </el-table-column>
          <el-table-column prop="redW" label="白平衡分量红">
            <template #default="scope">
              <el-input-number :disabled="true" v-model="scope.row.redW" controls-position="right" :min="0"></el-input-number>
            </template>
          </el-table-column>
          <el-table-column prop="greenW" label="白平衡分量绿">
            <template #default="scope">
              <el-input-number :disabled="true" v-model="scope.row.greenW" controls-position="right" :min="0"></el-input-number>
            </template>
          </el-table-column>
          <el-table-column prop="blueW" label="白平衡分量蓝">
            <template #default="scope">
              <el-input-number :disabled="true" v-model="scope.row.blueW" controls-position="right" :min="0"></el-input-number>
            </template>
          </el-table-column>
        </el-table>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import CardWrapper from "@/renderer/components/CardWrapper.vue";

const form1 = ref<any>({
  bg: 53000
})

const tableData = ref<any>([{
  bg: 53000,
  name: '小镜头',
  zy: 0,
  autoW: false,
  redW: 2155,
  greenW: 1024,
  blueW: 1890,
}, {
  bg: 230000,
  name: '中镜头',
  zy: 0,
  autoW: false,
  redW: 2155,
  greenW: 1024,
  blueW: 1890,
},
{
  bg: 22000,
  name: '大镜头',
  zy: 0,
  autoW: false,
  redW: 2155,
  greenW: 1024,
  blueW: 1890,
}])
</script>

<style scoped lang="scss">
$primary-color: #f0f2f8;
$card-background: #fff;
$shadow-color: rgba(0, 0, 0, 0.1);
$text-secondary: #909399;

.user-info {
  display: flex;
  flex-direction: column;
  padding: 20px;
  flex: 1;
  min-height: calc(100vh - 104px);
  overflow: hidden;
  margin: auto;
}

//内容部分
.content-section {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 20px;
  border: 1px solid #e4e7ed;
  .jt-content{
    display: flex;
    flex-direction: column;
    gap: 15px;
    .jt-title{
      color: #333;
      font-weight: bold;
    }
  }
}

.user-form {
  // width: 100vh;
  // height: 70vh;
  // padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;

  .block {
    display: flex;
    justify-content: center;
    align-items: center;

    .demonstration {
      width: 70px;
    }
  }
}
</style>
