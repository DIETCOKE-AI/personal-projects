const hashMap = new Map<string, { latinName: string; origin: string }>();

const setHerb = (
  name: string,
  latinName: string,
  origin: string = "中国药典"
) => {
  hashMap.set(name, { latinName, origin });
};

// 设置药材数据
setHerb("亚麻籽类", "Linum usitatissimum");
setHerb("使君子类", "Quisqualis indica");
setHerb("决明子类", "Cassia obtusifolia");
setHerb("千金子类", "Strychnos nux-vomica");
setHerb("半夏类", "Pinellia ternata");
setHerb("南烛子类", "Evodia rutaecarpa");
setHerb("土茯苓类", "Smilax glabra");
setHerb("太子参类", "Pseudostellaria heterophylla");
setHerb("射干类", "Belamcanda chinensis(L.)Redouté");
setHerb("山麦冬类", "Ophiopogon japonicus");
setHerb("巴戟天类", "Morinda officinalis");
setHerb("拳参类", "Echinops grugeri");
setHerb("月季类", "Rosa chinensis");
setHerb("望江南子类", "Senna tora");
setHerb("木防己类", "Radix Stephaniae");
setHerb("枣仁类", "Ziziphus jujuba");
setHerb("枳椇子类", "Citrus aurantium");
setHerb("枸杞类", "Lycium barbarum");
setHerb("柏子仁类", "Platycladus orientalis");
setHerb("柴胡类", "Bupleurum chinense");
setHerb("栀子类", "Gardenia jasminoides");
setHerb("水半夏类", "Pinellia pedatisecta");
setHerb("沙苑子类", "Sophora flavescens");
setHerb("没药类", "Commiphora wightii");
setHerb("淡竹叶类", "Lophatherum gracile");
setHerb("淮小麦类", "Triticum aestivum");
setHerb("稻芽类", "Oryza sativa");
setHerb("玫瑰类", "Rosa damascena");
setHerb("白扁豆类", "Dolichos lablab");
setHerb("白胡椒类", "Piper nigrum");
setHerb("铁皮石斛类", "Dendrobium officinale");
setHerb("砂仁类", "Amomum villosum");
setHerb("红茴香类", "Cinnamomum zeylanicum");
setHerb("胖大海类", "Sterculia lychnophora");
setHerb("芦苇类", "Phragmites australis");
setHerb("荜澄茄类", "Zanthoxylum piperitum");
setHerb("莪术类", "Curcuma zedoaria");
setHerb("莲子类", "Nelumbo nucifera");
setHerb("拔葜类", "Pueraria lobata");
setHerb("蔓荆子类", "Vitex negundo");
setHerb("西洋参类", "Panax quinquefolius");
setHerb("覆盆子类", "Rubus idaeus");
setHerb("郁金类", "Curcuma longa");
setHerb("防己类", "Stephania tetrandra");
setHerb("陈皮类", "Citrus reticulata");
setHerb("青果类", "Citrus viridis");
setHerb("青风藤类", "Millettia reticulata");
setHerb("麦冬类", "Ophiopogon japonicus");
setHerb("黄荆子类", "Rhamnus davurica");
setHerb("黑芝麻类", "Sesamum indicum");

export default hashMap;
