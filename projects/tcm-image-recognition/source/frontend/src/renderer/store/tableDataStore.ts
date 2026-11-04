// stores/tableDataStore.ts 
//TODO:此处的图片请求应该设置一个default图片，防止图片请求失败
import { defineStore } from "pinia";

export const useTableDataStore = defineStore("tableData", {
  state: () => ({
    // 公开快照不包含药材资料种子数据；运行时由后端填充。
    tableData: [] as any[],
  }),
  actions: {
    updateTableData(
      newData: any
    ) {
      console.log(newData)
      this.tableData = newData;
    },
  },
  getters: {
    getTableData: (state) => state.tableData,
  },
});