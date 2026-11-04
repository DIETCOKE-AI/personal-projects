# 三端核心源码快照

本目录提供项目的核心源码阅读入口，帮助理解算法研究如何衔接推理业务和桌面采集。公开副本经过配置脱敏、路径整理和静态示例资产替换，原始工程保留原状。

| 目录 | 主要内容 | 入口 |
| --- | --- | --- |
| backend | Flask路由、ModelManager、主子类融合、药材和历史模型、构建素材 | [说明](backend/README.public.md) · [app.py](backend/app.py) · [predict_two_steps.py](backend/predict_two_steps.py) |
| frontend | Vue 3业务界面、Electron主进程与preload、API封装、构建配置 | [说明](frontend/README.public.md) · [进程编排](frontend/src/main/backend-service.js) · [Dashboard](frontend/src/renderer/views/Dashboard.vue) |
| algorithm | 训练入口、网络与数据、general、集成评估和错误分析 | [说明](algorithm/README.public.md) · [epoch_run.py](algorithm/epoch_run.py) · [高级集成](algorithm/modelEnsemble/evaluate_advanced_ensemble.py) |

## 建议阅读顺序

1. [架构说明](../docs/architecture.md)：区分99类交付后端与200类研究。
2. backend模型管理器与预测控制器：图像如何转成具体药材对象。
3. frontend进程编排、Dashboard和ImgUpload：用户操作如何进入后端。
4. algorithm主入口、general和高级集成：训练/验证/独立测试及TTA如何分工。
5. [实现完成度](../docs/source-review.md)：识别当前生效代码、占位分支和历史残留。

## 发布范围

不分发权重、药材图片、数据库备份或种子数据、访问凭据、日志、原始开发对话、交接附件、依赖虚拟环境与构建产物；Java服务和工业相机/电气运行环境也未包含。公开目录不是整套可直接运行的独立发行包，参见[复现条件](../docs/reproducibility.md)。

核心源码保持历史研究行为，没有以此次展示整理补齐算法或业务缺口。保留原文件已有署名与许可声明，未为团队代码或第三方实现统一新增许可；个人参与范围见[贡献说明](../docs/contributions.md)。
