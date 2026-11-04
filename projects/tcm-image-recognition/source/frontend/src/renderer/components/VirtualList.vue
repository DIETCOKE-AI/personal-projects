<template>
  <div
    class="virtual-list-container"
    ref="listContainer"
    @scroll="handleScroll"
  >
    <div class="spacer" :style="{ height: `${totalHeight}px` }"></div>
    <div
      class="virtual-list"
      :style="{ transform: `translateY(${offsetY}px)` }"
    >
      <div class="grid-container" ref="gridContainer">
        <HerbsCar
          v-for="item in visibleItems"
          :key="item.id"
          :herbData="item"
          @openDetail="handleOpenDetail"
        />
        
      </div>
      <!-- <el-divider v-if="(totalRows-visibleRowCount)*(itemsPerRow)+visibleItems.length==items.length">已经到底啦</el-divider> -->
    </div>
    
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import HerbsCar from "./HerbsCard.vue";

const props = defineProps<{
  items: CardItem[];
  itemWidth?: number; // 可选：单个项目的固定宽度（默认自动计算）
}>();

const listContainer = ref<HTMLElement | null>(null);
const gridContainer = ref<HTMLElement | null>(null);
const scrollTop = ref(0);
const containerWidth = ref(0);
const actualItemWidth = ref(0);

// 固定参数
const rowHeight = 250; // 每行高度
const itemGap = 20; // 项目间距
const visibleRowCount = 4; // 可见行数
const bufferRows = 0; // 缓冲行数

// 动态计算每行项目数
const itemsPerRow = computed(() => {
  if (!actualItemWidth.value) return 1;
  return Math.max(1, Math.floor(containerWidth.value / (actualItemWidth.value + itemGap)));
});

// 计算总行数
const totalRows = computed(() => Math.ceil(props.items.length / itemsPerRow.value));

// 计算总高度
const totalHeight = computed(() => totalRows.value * rowHeight);

// 计算可见区域的起始索引
const startRow = computed(() =>
  Math.max(0, Math.floor(scrollTop.value / rowHeight) - bufferRows)
);

// 计算可见区域的结束索引
const endRow = computed(() =>
  Math.min(totalRows.value, startRow.value + visibleRowCount + bufferRows * 2)
);

// 计算偏移量
const offsetY = computed(() => startRow.value * rowHeight);

// 计算可见的列表数据
const visibleItems = computed(() => {
  const startIndex = startRow.value * itemsPerRow.value;
  const endIndex = Math.min(props.items.length, endRow.value * itemsPerRow.value);
  return props.items.slice(startIndex, endIndex);
});

// 处理滚动事件
const handleScroll = () => {
  if (listContainer.value) {
    scrollTop.value = listContainer.value.scrollTop;
  }
};

// 处理点击事件
const emit = defineEmits(["openDetail"]);
const handleOpenDetail = (card: CardItem) => {
  emit("openDetail", card);
};

// 计算容器宽度和项目宽度
const updateDimensions = () => {
  if (!listContainer.value || !gridContainer.value) return;
  
  // 获取容器宽度
  containerWidth.value = listContainer.value.clientWidth;
  
  // 计算实际项目宽度（如果未通过props传入）
  if (props.itemWidth) {
    actualItemWidth.value = props.itemWidth;
  } else if (gridContainer.value.children.length > 0) {
    const firstChild = gridContainer.value.children[0] as HTMLElement;
    actualItemWidth.value = firstChild.offsetWidth;
  }
};

// 使用ResizeObserver监听容器大小变化
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (listContainer.value) {
    listContainer.value.addEventListener('scroll', handleScroll);
    
    // 初始化尺寸
    updateDimensions();
    
    // 监听容器大小变化
    resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(listContainer.value);
  }
});

onUnmounted(() => {
  if (listContainer.value) {
    listContainer.value.removeEventListener('scroll', handleScroll);
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});

// 监听items变化（确保重新计算）
watch(() => props.items, updateDimensions, { immediate: true });

// 调试信息
watch([itemsPerRow, containerWidth], ([perRow, width]) => {
  console.log(`容器宽度: ${width}px, 每行项目数: ${perRow}`);
});
</script>

<style scoped>
.virtual-list-container {
  position: relative;
  overflow-y: auto;
  width: 100%;
  height: 100%; /* 确保容器有高度 */
}

.spacer {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  z-index: -1;
}

.virtual-list {
  position: relative;
  width: 100%;
}

.grid-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px v-bind(itemGap + 'px');
  padding: 8px;
  box-sizing: border-box;
}
</style>