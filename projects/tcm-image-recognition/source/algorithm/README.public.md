# 算法研究源码快照

本目录展示中药材分类工程的训练、独立评估、集成和错误追溯实现，来自2026-11-04读取的本地源码副本。它对应历史研究过程；原工程的模型、数据和运行环境未随仓库发布。本次整理只调整私人路径和公开说明，没有补写或修复模型/评估业务逻辑。

## 阅读入口

| 入口 | 作用 |
| --- | --- |
| [epoch_run.py](epoch_run.py) | train / test / general命令入口 |
| [训练引擎](utils/training/epoch_train_engine.py) | 损失、优化器、验证、检查点与曲线 |
| [增强加载器](datasets/enhanced_dataset_loader.py) | ROI、CLAHE、类别特定增强与数据加载 |
| [模型工厂](models/get_network.py) | 按模型名创建网络 |
| [类别配置](custom_mapping.json) | 有序标签、类别数、相对数据路径及类别策略 |
| [独立general评估](utils/testing/epoch_generalizability_engine_new.py) | 逐图预测、分类表及混淆矩阵 |
| [200类高级集成配置](modelEnsemble/model_ensemble_config_hybrid_200_advanced.json) | 各模型检查点与预处理/TTA开关 |
| [高级集成](modelEnsemble/evaluate_advanced_ensemble.py) | 异构预处理、翻转TTA、加权/投票及模型级多GPU |
| [开集阈值扫描](modelEnsemble/run_threshold_sweep_hybrid.py) | 已知接受/未知拒绝与阈值比较 |
| [集成错误分析](modelEnsemble/analysis/analyze_errors.py) | 已知误分、已知拒绝、未知误接受 |
| [单模型错误分析](test/analyze/analyze_classification_errors.py) | general逐图表的错误类别与误分对 |

## 配置与复现条件

从本目录作为工作目录使用相对路径。`custom_mapping.json` 的每个数据集路径已替换为 `./data/<数据集名>/train` 与 `./data/<数据集名>/test`；它们是占位位置，不含真实图像。使用自己的数据时，应成套核对该模型训练时的有序标签、原图目录和采集分组。旧入口的 `conf/global_configs.py` 使用 `./data/<数据集名>`，并可能自行拼接train/test子目录；不同入口不能视为等价。

两处本地预训练位置可用环境变量配置：

- `TCM_PRETRAINED_ROOT`：公共加载器的本地缓存根目录，默认 `./weights/pretrained`；子目录与文件名见 `_local_weights_loader.py` 的映射。
- `TCM_MNV4_PRETRAINED_PATH`：MNv4单文件路径，默认 `./weights/mnv4_conv_aa_large.bin`。

`.env.example`仅记录变量名称。代码读取进程环境，不会自动加载.env；请在所用终端或启动环境设置。部分其他模型仍使用timm的预训练路径，可能读取缓存或联网，离线策略未完全统一。

当前 `ckpts` 未提供训练检查点。高级JSON保留历史version/epoch用来展示实验组合，不意味着这些权重已随包发布。也未提供原始图像、独立测试集、预训练权重、服务器启动脚本、ONNX/密钥、日志或原始对话。`requirements.txt`保留原工程的历史环境快照，版本组合未在本公开副本重新安装验收；`requirements-public.txt`仅列通过import静态确认的主要依赖，不是经过验证的锁文件。PyTorch/CUDA/timm及模型注册兼容性需要另行配套。

## 已知实现边界

- 当前普通MobileViT_large构造 `mobilevitv2_200`，PAFPN构造 `mobilevitv2_175`；与99类后端的同名模型定义需要分版本对待。
- advanced的 `use_enhanced` 分支仍为`pass`；配置true并未接入训练侧ROI/CLAHE。其center_crop尺度也与普通general路径不同。
- general的TTA平均logits后softmax，advanced平均两次softmax概率；hybrid开集扫描没有自动复用这套TTA和增强配置。
- 155/200训练与验证分别建立样本列表再划分，未保存共享的互斥清单；实际图片重叠量未核实。200训练的柴胡类特定灰度也未统一到验证/general。
- 旧run=test及旧评估脚本保留历史兼容问题；Swin增强局部注意力接入、部分CLI参数和损失选项并未完整落地。
- 四GPU分配/线程池有源码，实际GPU利用率、耗时或最终成绩未在本次整理中重新测试。

这些边界用于解释历史实验，不能把静态源码存在当作完整复现或当前部署验收。本次仅做Python AST与JSON静态检查，没有import项目、安装依赖、加载权重、启动服务或运行训练/推理。

## 整理记录与归属

发布副本保留原有代码注释与署名；没有为既有团队代码另行授予新的开源许可。私人服务器路径替换为上述相对占位或环境变量；原始工程保持不变。文件中保留的公开模型下载地址属于既有实现，未在整理时访问。
