# GB/T 7714 文献格式整理 Skill

将杂乱的参考文献整理为 GB/T 7714—2025 常见类型的顺序编码格式，支持保守查重、缺失信息分流和来源追踪。

## 分工与功能

- 智能体负责从自然语言、txt、CSV 或 BibTeX 中提取字段和判断歧义。
- Python 脚本接收结构化 JSON，确定性完成规范化、去重、编号和排版。
- 支持期刊 J、会议论文 C、专著 M、学位论文 D 和网页 EB/OL。
- 自动合并有明确证据且元数据兼容的重复项；不同版次、冲突 DOI 和近似题名保留复核。
- 缺失字段保留草稿，原值和来源可追溯。

## 快速运行

需要 Python 3.10 及以上。核心脚本仅使用标准库，无需安装第三方依赖。先从合集仓库根目录进入 `projects/gbt7714-reference-cleaner`，再运行：

```bash
python scripts/format_references.py --input examples/mixed_references.json --outdir output
python -m unittest discover -s tests -v
```

输出 `references.txt`、`drafts.txt`、`normalized.json` 和 `audit.json`。

主样例共 20 条、5 种类型；预期去除 3 条重复后保留 17 条，生成 15 条正式引用和 2 条草稿。23 项测试覆盖格式、去重、异常处理、原值保留和重复执行一致性。

需要增加 DOI 著录时，追加 `--include-doi`；英文姓氏全大写配置为 `--author-case upper`。

## 在智能体中使用

将本项目子目录 `projects/gbt7714-reference-cleaner` 作为完整技能文件夹放入支持的平台技能目录；Codex 个人目录示例为 `~/.codex/skills/gbt7714-reference-cleaner`。

调用示例：

> 使用 $gbt7714-reference-cleaner 整理这批参考文献，按 GB/T 7714 统一格式并查重，缺失字段保留草稿。

触发条件、工作流程、输入字段和输出约定见 [SKILL.md](SKILL.md)，具体格式依据见 [格式规则](references/format-rules.md)，测试设计见 [测试说明](reports/test-design.md)。

## 适用范围

本项目实现标准的常见类型子集，采用保守的成稿质量门槛；缺作者等字段转为草稿属于工具策略。它不执行文献检索或真实性认证，不覆盖全部文献类型及正文引注情形。

测试集包含课程给出的两条示例及明确标注的教学构造数据。测试 DOI 与 example.org 网址仅供测试，不可用作真实文献依据。
