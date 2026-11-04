
// src/renderer/utils/eventBus.ts

import { ref } from 'vue';

// 创建一个简单的事件总线
const events = ref<Record<string, Function[]>>({});

export const eventBus = {
  // 订阅事件
  on(eventName: string, callback: Function) {
    if (!events.value[eventName]) {
      events.value[eventName] = [];
    }
    events.value[eventName].push(callback);
  },

  // 发布事件
  emit(eventName: string, ...args: any[]) {
    if (events.value[eventName]) {
      events.value[eventName].forEach(callback => {
        callback(...args);
      });
    }
  },

  // 取消订阅
  off(eventName: string, callback: Function) {
    if (events.value[eventName]) {
      const index = events.value[eventName].indexOf(callback);
      if (index > -1) {
        events.value[eventName].splice(index, 1);
      }
    }
  },
};
