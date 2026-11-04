# 个人项目展示

用于展示个人项目的功能、源码、使用方法与可复现示例。每个项目保存在独立目录中，后续可继续加入新的项目。

## 项目目录

| 项目 | 简介 | 技术 | 入口 |
| --- | --- | --- | --- |
| 中药材智能识别系统 | 两阶段识别、交付维护、泛化评估与数据治理，含三端核心源码快照 | Python、PyTorch、Flask、Vue/Electron | [项目介绍](projects/tcm-image-recognition/README.md) · [源码导航](projects/tcm-image-recognition/source/README.md) · [实验结果](projects/tcm-image-recognition/docs/experiments.md) |
| GB/T 7714 文献格式整理 Skill | 批量规范参考文献、保守去重、分流缺失信息并追踪来源 | Python 标准库、Agent Skill | [项目介绍](projects/gbt7714-reference-cleaner/README.md) · [技能说明](projects/gbt7714-reference-cleaner/SKILL.md) |

## 中药材智能识别系统

记录2025年8月起参与的算法研发与交付协作：子类模型与部署配置排查、155类预处理对照、200类general评估、错误溯源及数据治理；补充后期五模型TTA与多GPU集成实验的源码状态。

- 两阶段识别：多模型大类融合、未知拒识、子类细分与候选排序。
- 代表性历史结果：200类、5,974张已知类general测试，MNv4指定检查点Top-1为95.88%。
- 展示形式：项目复盘、架构说明、个人贡献时间线、23次评估摘要，以及脱敏的前端、后端和算法核心源码快照。
- 源码范围：保留团队框架与个人参与的边界；权重、原图、数据库、硬件运行环境和原始内部材料不随仓库分发。

[阅读项目档案](projects/tcm-image-recognition/README.md) · [浏览三端源码](projects/tcm-image-recognition/source/README.md) · [查看个人贡献](projects/tcm-image-recognition/docs/contributions.md) · [查看评估数据](projects/tcm-image-recognition/results/evaluation-summary.csv)

## GB/T 7714 文献格式整理 Skill

将大模型的语义提取与 Python 的确定性处理分开：智能体识别作者、题名、来源和文献类型，脚本完成规范化、查重、顺序编号与格式排版。

- 支持期刊论文、会议论文、专著、学位论文和网页五种常见类型。
- 相同 DOI 或兼容的完整元数据才自动合并；不同版次、冲突 DOI、近似题名保留复核。
- 输出正式引用、待补草稿、规范化 JSON 和审计记录。
- 20 条测试输入覆盖 5 种类型，23 项测试通过。

### 快速体验

需要 Python 3.10 及以上，无第三方运行依赖。

```bash
cd projects/gbt7714-reference-cleaner
python scripts/format_references.py --input examples/mixed_references.json --outdir output
python -m unittest discover -s tests -v
```

主样例预期：20 条输入，合并 3 条重复，保留 17 条；其中 15 条正式引用、2 条待补草稿。

### 进一步了解

- [完整使用说明](projects/gbt7714-reference-cleaner/README.md)
- [触发条件与智能体工作流程](projects/gbt7714-reference-cleaner/SKILL.md)
- [核心 Python 脚本](projects/gbt7714-reference-cleaner/scripts/format_references.py)
- [测试数据](projects/gbt7714-reference-cleaner/examples/mixed_references.json)
- [测试设计](projects/gbt7714-reference-cleaner/reports/test-design.md)
- [GB/T 7714 格式依据与实现范围](projects/gbt7714-reference-cleaner/references/format-rules.md)

测试集中的构造记录仅用于验证格式转换与去重逻辑；格式整理结果不能代替文献真实性核验。

