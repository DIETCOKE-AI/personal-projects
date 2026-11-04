<template>
  <el-card class="custom-card" @click="handleOpenDetail">
     <!-- 图片部分 -->
     <img :src="getImageUrl(props.herbData.imageUrl)" alt="图片" class="card-image" style="min-height:107px;"/>
      <!-- 内容部分 -->
      <div class="card-text">
        <p class="card-name">{{ props.herbData.source[0]?.subclassName }}</p>
        <p class="card-source">植物中文名：{{ props.herbData.source[0]?.plantName }}</p>
        <p class="card-source">植物拉丁名：{{ props.herbData.source[0]?.latinName }}</p>
        <p class="card-details">{{ props.herbData.isTrueHerb==1?props.herbData.source.length>0?props.herbData.source.map((item:any)=>item.standardName).join(","):'-':'暂未录入该药材' }}</p>
      </div>
  </el-card>
</template>

<script lang="ts" setup>
const emit = defineEmits(["openDetail"]);
const props = defineProps({
  herbData: {
    type: Object, //  使用 Object 类型
    required: true, // 可选：是否必传
    default: () => ({}), // 可选：默认值
  },
});

const handleOpenDetail = () => {
  // 打开详情弹窗
  emit("openDetail", props.herbData);
};
const getImageUrl = (imagePath: string) => {
  console.log('方法被调用，参数:', imagePath); // 新增调用日志
  console.log("当前环境:", import.meta.env.VITE_API_BASE_URL); 
   return `${import.meta.env.VITE_API_BASE_URL}${imagePath}`;
}
</script>
<style lang="scss" scoped>
.custom-card {
  width: 200px;
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  // padding: 8px;
  cursor: pointer;
  box-sizing: border-box;
  border-radius: 8px;
  border: 1px solid #e0e0e0;

  // 为整个卡片设置阴影
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); // 增加悬停时的阴影效果
  }
}

.card-content {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  // width: 100%;
  gap: 8px;
}

.card-image {
  width: 160px;
  // height: 35%;
  object-fit: cover;
  border-radius: 4px;
}

.card-text {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  height: 100%;
  // width: calc(100% - 48px); // 让文本部分占据剩余空间，避免重叠
  overflow: hidden;
}

.card-name {
  margin: 0;
  font-size: 12px; // 设置 name 字体大小
  font-weight: bold;
  color: #333;
  white-space: nowrap; // 防止换行
  overflow: hidden;
  text-overflow: ellipsis; // 超出时显示省略号
}

.card-source {
  margin: 0;
  font-size: 10px;
  color: #999;
  display: inline-block;
  // white-space: nowrap; 
  width: 160px; 
  -webkit-line-clamp: 2; // 显示最多2行文本
  overflow: hidden;
  text-overflow:ellipsis;
}

.card-details {
  margin: 0;
  font-size: 12px;
  color: #666;
  width: 160px; 
  // 设置为多行文本，超出时使用省略号
  display: -webkit-box;
  -webkit-line-clamp: 2; // 显示最多2行文本
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis; // 超出时显示省略号
}
</style>
