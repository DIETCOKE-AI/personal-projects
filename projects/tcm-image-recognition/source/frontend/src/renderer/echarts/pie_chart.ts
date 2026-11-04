const pie_option = {
  title: {
    text: "统计图表",
    left: "center",
  },
  tooltip: {
    trigger: "item",
    formatter: "{a} <br/>{b} : {c} ({d}%)",
  },
  legend: {
    left: "center",
    top: "bottom",
    data: [
      "丁香类",
      "人参类",
      "干姜类",
      "土茯苓类",
      "大蒜类",
      "山银花类",
      "川乌类",
      "大蒜类",
    ],
  },
  toolbox: {
    show: true,
    feature: {
      mark: { show: true },
      dataView: { show: false, readOnly: false },
      restore: { show: true },
      saveAsImage: { show: false },
    },
  },
  series: [
    {
      name: "识别数量",
      type: "pie",
      radius: [20, 140],
      center: ["50%", "50%"],
      roseType: "area",
      itemStyle: {
        borderRadius: 5,
      },
      data: [
        { value: 30, name: "丁香类" },
        { value: 28, name: "人参类" },
        { value: 26, name: "干姜类" },
        { value: 24, name: "土茯苓类" },
        { value: 22, name: "大蒜类" },
        { value: 20, name: "山银花类" },
        { value: 18, name: "川乌类" },
        { value: 16, name: "王不留行类" },
        { value: 15, name: "大蒜类" },
      ],
    },
  ],
};
export default pie_option;
