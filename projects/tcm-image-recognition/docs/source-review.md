# 源码核查与实现完成度

核查日期：2026-11-04。对照历史周报、51条算法对话请求、11条后端对话请求及三端源码，区分需求、当前实现和运行验收。原始对话不随仓库公开；本文不把AI的完成宣称、演示数值或预期加速当作实测。

## 当前实现

| 项目 | 已确认 | 边界 |
| --- | --- | --- |
| 主类与子类识别 | 99类五实例融合、阈值拒识、Top5主类展开和子类乘积分数排序 | 训练200类不等于后端已部署200类 |
| PAFPN | 多尺度自顶向下、自底向上融合后池化拼接分类 | 具体收益需对应检查点及对照实验 |
| MobileViT骨干 | 算法普通large=200、PAFPN=175；后端两者均175 | 当前文件正确不证明每个历史检查点都与之匹配 |
| 单模型general TTA | 原图+水平翻转，两次logits平均后softmax | fine_grain开关触发；训练验证仍单次前向 |
| 高级集成TTA | 按模型use_tta做原图+水平翻转，平均softmax概率 | 与general平均位置不同；不能当完全等价 |
| 高级集成增强 | 配置声明四模型use_enhanced=true | get_transform内对应分支是pass，未调用ROI/CLAHE |
| 多GPU | advanced用线程池，显式四GPU时五模型按0/1/2/3/0分配 | 默认单GPU；未复测四卡利用率或加速比；后端未使用此脚本 |
| 开集阈值扫描 | hybrid缓存概率，比较投票、加权及一致性/两阶段策略 | 不读取advanced的TTA/增强位；执行方式不同 |
| 最佳精度记录 | 正常新训练先更新best_acc/best_epoch再保存 | resume未恢复历史best和完整调度状态 |
| 本地预训练 | 多模型已接入本地加载辅助器 | 未统一覆盖；“成功加载”日志不替代键/形状匹配统计 |
| Swin增强 | 分类头正则化有代码 | 局部注意力接入函数为空；项目名不代表固定官方V3架构 |
| 动态模型加载 | 历史对话提出下拉框驱动加载方案 | 当前后端未找到宣称新增的文件/方法/蓝图，仍启动预加载 |

实现入口：[模型管理器](../source/backend/predict_two_steps.py)、[general评估](../source/algorithm/utils/testing/epoch_generalizability_engine_new.py)、[高级集成](../source/algorithm/modelEnsemble/evaluate_advanced_ensemble.py)、[hybrid扫描](../source/algorithm/modelEnsemble/run_threshold_sweep_hybrid.py)、[增强Swin](../source/algorithm/models/net/swin_v3_base_enhanced.py)。

## 数据和预处理的可比性

- train日志中的Test来自训练目录内部约10%验证集；general从独立test_path加载；旧run=test又走另一套加载器。
- 155/200类别特定增强路径下，训练与验证分别枚举文件并划分，排序/目录深度/类顺序不同，没有共享图片清单来保证互斥。此为静态风险，没有原图清单，尚未计算或证明实际泄漏。
- 200训练按柴胡类标签灰度，验证/general未维持该类专属分支；advanced增强为空，center_crop短边731再裁640，而常规验证/general短边640再裁640。
- 同名CLI选项不保证在所有模型/入口生效，例如Enhanced的dropout/local_attention未由工厂传入；不能依据命令中出现参数便认定该模块参与实验。

这些差异是解释高验证分数与独立泛化差距时应先核对的条件，尚不能据此将差距归结为一个已确认根因。历史成绩和实验口径见[实验结果](experiments.md)。

## 产品与交付边界

当前Dashboard图片及拍照走batch HTTP；旧单张IPC组件保留过时返回字段，未挂载到当前主页面。配置页硬编码且禁用；采集页主要保存本地ZIP。登录依赖RuoYi，相机及电气控制依赖外置Python与SDK。

后端还有未知历史写入None与ORM非空声明、加载失败跳过模型后位置配对、编号隐式假设等需要联调的点；构建素材有缺失文件，日志就绪标记先于HTTP监听。它们是源码可定位的维护事项，不是本轮运行失败的实测结论。发布副本没有擅自修复这些行为。

## 归属与证据

个人周报说明参与和实施的工作，对话说明提出的需求和调试过程，源码说明当前快照内的实现。三者不能相互替代。目录内的团队框架、前后端和第三方网络不全部归为个人原创；200类集成工作以“推进与调试”表述，未宣称最终多GPU收益或完整上线。
