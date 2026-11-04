import { defineStore } from "pinia";
import { getUserById } from "@/renderer/api/User";

// 创建 Pinia Store
export const useUserStore = defineStore("user", {//此处useUserStore是向外暴露的方法，用于获取store
  // 定义状态
  state: () => ({//可以看作是组件的data，用来存储状态的地方，必须是函数，返回一个对象
    currentUser: [], // 用来存储当前用户的详细信息
  }),

  actions: {//action更像于组件的methods，用来定义方法，修改state的地方
    // 获取用户详情
    async UserById(id: string) {
      try {
        const response = await getUserById(id);
        this.currentUser = response; // 假设返回的数据结构为 { data: UserData }
      } catch (error) {
        console.log("====================================");
        console.log(error);
        console.log("====================================");
      }
    },
  },
});
