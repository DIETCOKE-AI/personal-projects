# Flask识别后端：脱敏源码快照

此目录保留99大类交付版本的主要源码，用于阅读两阶段预测、类别映射及桌面端接口。来源为历史 `dev_weighting` 分支的 `e78924b` 基础版本，以及原副本中已有的 `predict_two_steps.py` 未提交改动。它是既有团队工程的整理副本，不表示全部代码由个人独立原创。

本次公开整理仅调整配置中的凭据、机器路径及文本编码，没有改写分类算法或修复业务行为。未启动服务、连接数据库、加载模型或验证安装包，因此不能视为开箱即用的发行版。

## 阅读入口

| 文件/目录 | 作用 |
| --- | --- |
| [app.py](app.py) | Flask应用工厂、蓝图、数据库和模型管理器初始化、Electron就绪消息 |
| [predict_two_steps.py](predict_two_steps.py) | 五主模型概率融合、拒识、Top5主类展开、子类分数排序与资料查询 |
| [config/model_config.py](config/model_config.py) | 99类、阈值0.51、批次8、各模型预处理及权重相对路径 |
| [controllers/predictController.py](controllers/predictController.py) | 上传、单张/批量预测、历史记录和响应组装 |
| [nets](nets) | 与该后端权重对应的网络定义；普通MobileViT与PAFPN骨干均为175 |
| [model](model) · [routes](routes) | 药材、标准、用户历史等ORM与HTTP接口 |
| [segmentation.py](segmentation.py) | 陈皮传统轮廓定位及patch裁剪 |

实际HTTP预测直接调用同进程 `ModelManager`。`model_server.py` 与 `predict_client.py` 是旧TCP链路；`templates/index.html` 仍是调用旧 `/predict` 协议的页面，不能当作当前接口演示。现行主要接口为 `POST /predict/one`（字段 `file`）和 `POST /predict/batch`（多项字段 `files`）。

## 配置约定

将 [.env.example](.env.example) 复制为本地 `.env` 并填写自己的值，或在运行环境中设置同名变量。`.env`、权重与用户数据均被 [.gitignore](.gitignore) 排除。

| 环境变量 | 用途 |
| --- | --- |
| `TCM_SECRET_KEY` | Flask应用密钥，必须自行设置 |
| `TCM_JWT_SECRET_KEY` | JWT密钥，必须自行设置 |
| `TCM_DATABASE_URL` | SQLAlchemy连接串，使用自己的数据库驱动、账户和库名 |
| `TCM_DB_HOST`、`TCM_DB_PORT` | 推理查询连接池的地址；默认本机和3306 |
| `TCM_DB_USER`、`TCM_DB_PASSWORD`、`TCM_DB_NAME` | 推理查询连接池的账户、口令与库名，必须自行设置 |
| `TCM_TEST_IMAGE_DIR` | 可选，仅供历史PAFPN测试脚本指定图片目录 |

原工程同时通过SQLAlchemy和 `mysql.connector` 访问数据库，故 `TCM_DATABASE_URL` 与 `TCM_DB_*` 必须指向同一套相容的数据。公开版没有将两套访问方式重构为一个配置入口。缺少必需环境变量时会在导入配置时失败；空值也不是可运行配置。

## 复原运行所需资产

1. 与当前网络定义、99类顺序及子类编号相匹配的检查点，按 `model_config.py` 中的相对路径准备。
2. MySQL数据库与药材类别、子类、标准信息等种子数据；`create_all` 只建表，不会生成这些业务记录。
3. 相容的Python、PyTorch、CUDA及其他依赖环境。两份 `requirements*.txt` 是历史环境清单，并非本轮安装验收过的最小依赖锁；其中 `requirements.txt` 仅由UTF-16转换为UTF-8，包条目保持原样。
4. 与前端、Java用户服务及硬件程序配套的交付布局。此目录不包含这些二进制、模型、图片、数据库导出、虚拟环境或密钥文件。

配置中的检查点路径仍相对于工作目录；入口是 `app.py`，默认监听5000端口。补齐以上资产后仍需独立联调，本次没有执行启动命令。

## 保留的历史边界

- 后端普通 `MobileViT_large` 为 `mobilevitv2_175`，算法研究目录当前同名模型为200。不得仅凭名字直接替换跨版本权重。
- 五个主模型在循环中依次前向；这里没有接入算法目录的高级四GPU集成脚本。
- 旧TCP服务导入当前不存在的模块级 `predict`；动态下拉框加载方案未集成到此快照。
- 未知历史记录的空子类值与当前ORM非空约束、失败模型跳过后的预处理配对等问题仍保留；实际数据库和同版本运行记录需要另行核实。
- 原构建批处理引用 `venv311` 与 `build.spec`，当前副本未包含它们；`build_prod.spec` 还依赖缺少的hooks。构建文件作为历史素材保留，不是已验证的打包指南。
- 当前就绪日志先于HTTP监听，历史接口鉴权和权限绑定也需独立完善；没有在本次发布整理中改变这些行为。

项目背景、个人工作及实验口径见[项目介绍](../../README.md)；跨端版本差异见[架构说明](../../docs/architecture.md)。原文件内已有的署名和注释保留，没有新增覆盖团队或第三方代码的统一开源许可。
