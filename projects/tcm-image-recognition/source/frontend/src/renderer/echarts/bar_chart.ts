const bar_options = {
  dataset: {
    source: [
      ["score", "amount", "product"],
      [30, 68, "大蒜类"],
      [57.1, 77, "王不留行类"],
      [74.4, 66, "人参类"],
      [50.1, 58, "川乌类"],
      [89.7, 99, "山银花类"],
      [68.1, 99, "丁香类"],
      [19.6, 99, "土茯苓类"],
    ],
  },
  grid: { containLabel: true },
  xAxis: {
    name: "ratio",
    type: "value", // 确保 X 轴是数值类型
    min: 0, // 设置最小值为 0
    max: 100, // 设置最大值为 100
    interval: 10, // 可选：设置每隔 10 显示一个刻度
  },
  yAxis: {
    type: "category", // Y轴保持为类别类型
  },
  visualMap: {
    orient: "horizontal",
    left: "center",
    min: 10,
    max: 100,
    text: ["High Confidence", "Low Confidence"],
    dimension: 0,
    inRange: {
      color: ["#FD665F", "#FFCE34", "#65B581"],
    },
  },
  series: [
    {
      type: "bar",
      encode: {
        // Map the "amount" column to X axis.
        x: "amount",
        // Map the "product" column to Y axis
        y: "product",
      },
    },
  ],
};

export default bar_options;
