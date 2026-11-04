import * as XLSX from "xlsx";
// 通用的导出 Excel 方法
export function exportToExcel(
  data: any[], // 数据
  fileName: string, // 文件名
  columns: any, // 列配置
  selectRows: any[] = [] // 选中的行
) {
  // 判断是否选择了行，如果选择了，则导出选中的行，否则导出所有数据
  const rowsToExport = selectRows.length > 1 ? selectRows : data;

  // 筛选数据，提取需要的列
  const filteredData = rowsToExport.map((row) => {
    const filteredRow: any = {};
    columns.forEach((column: any) => {
      filteredRow[column.key] = row[column.key];
    });
    return filteredRow;
  });

  // 将数据转换为工作表（Sheet）
  console.log(filteredData);
  const ws = XLSX.utils.json_to_sheet(filteredData);

  // 创建一个工作簿（Workbook）
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1");

  // 导出 Excel 文件
  XLSX.writeFile(wb, fileName);
}

// 通用的过滤方法
export const filterTableData = (data: any[], searchText: string) => {
  if (!searchText) {
    return [];
  }
  return data.filter(
    (item) =>
      item.name.includes(searchText) || item.details.includes(searchText)
  );
};

// 请求错误处理函数
export const handleRequestError = (error: unknown): never => {
  if (error instanceof Error) {
    throw new Error(error.message || "请求失败");
  }
  throw new Error("请求失败");
};
