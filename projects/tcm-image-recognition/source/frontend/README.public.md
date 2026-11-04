# Vue / Electron 桌面端公开源码快照

本目录用于展示中药材识别项目的桌面交互与多进程衔接。来源是2026-11-04核查的项目工作树，保留当时的源码行为；未在此次整理中安装依赖、构建、运行服务或操作相机。

这里展示的是团队工程中的前端部分。代码保留原有署名及注释，本目录没有为整个团队源码另行指定开源许可证。

## 阅读入口

- `src/main/index.js`：窗口、IPC、相机脚本与WebSocket衔接。
- `src/main/backend-service.js`：Flask可执行程序、RuoYi JAR的启动与日志就绪握手。
- `src/preload/preload.js`：contextBridge暴露的桌面接口。
- `src/renderer/views/Dashboard.vue`：本地图片/拍照识别结果及PDF导出。
- `src/renderer/components/ImgUpload.vue`、`ShootUpload.vue`：主要识别入口，都调用Flask的`/predict/batch`。
- `src/renderer/views/LoginPlatform.vue`及`api/ruoyi/user.ts`：RuoYi认证与用户接口。

系统与个人工作范围见[项目说明](../../README.md)和[架构说明](../../docs/architecture.md)。

## 公开整理差异

| 内容 | 发布副本的处理 |
|---|---|
| 开发机EXE、JAR与本地图片绝对路径 | 改为下表所列父进程环境变量，未设置时使用`external/`相对目录 |
| 开发机路径注释 | 移除，不影响活跃代码 |
| 原环境文件 | 不分发，提供三个`.example`文件；其中主进程变量须从启动环境传入 |
| 品牌图、药材示例图、头像、背景位图 | 不分发；活跃静态引用替换为本目录自制SVG占位 |
| NSIS自定义ICO图标 | 移除图标配置项，保留Electron默认图标 |
| 药材资料初始种子数据 | 清空Pinia初始列表，保留后端请求成功后填充列表的动作 |
| 重复/备份代码 | 排除`copy`、`.bak`副本，保留实际主路径 |

没有复制原始聊天、内部改造提示词、实际上传图像、`python-dist`、依赖目录、发布包或Git历史。本目录的`.gitignore`排除了环境文件、外置程序、构建产物及运行日志。

## 外部依赖和配置

`package.json`与锁文件保留历史依赖声明；锁文件下载地址使用公开npm镜像，无认证参数。版本声明不等于已验证的当前安装环境。

| 项目 | 约定 |
|---|---|
| Flask业务接口 | 本机5000端口；开发模式通过Vite的`/flask`代理 |
| RuoYi用户服务 | 本机8080端口；开发模式通过Vite的`/api`代理 |
| 相机视频 | 本机WebSocket 8765 |
| 硬件控制 | 本机WebSocket 8766 |
| 硬件运行目录 | 开发`python-dist/`；打包后为Electron资源目录中的`python-dist/` |

外置目录需要实际的`python.exe`、相机SDK、`v1.py`、`open_small.py`/`open_mid.py`/`open_big.py`与关闭脚本。这些运行环境和脚本未随本前端快照发布。RuoYi需要Java环境及它实际使用的数据库配置；本目录不包含该Java服务源码或JAR。Flask需要对应模型、数据库与后端环境。

三个主进程变量：

| 环境变量 | 含义 | 未设置时的开发回退 |
|---|---|---|
| `TCM_BACKEND_EXE` | Flask打包可执行程序 | `external/tcm_app/tcm_app.exe`，相对启动工作目录 |
| `TCM_RUOYI_JAR` | RuoYi JAR | `external/ruoyi-admin.jar`，相对启动工作目录 |
| `TCM_IMAGE_BASE_PATH` | 资源管理器打开图片时的开发根目录 | 根据主进程文件定位的`external/tcm_app/` |

原代码在`index.js`中调用dotenv，但`backend-service.js`的静态导入会更早求值。因此，仅把主进程变量写入`.env`不足以配置这些路径；应先在启动Electron的父进程环境中设置。`.env.example`也记录了此限制。生产环境仍保留历史打包外置布局，路径变量可以覆盖EXE/JAR位置。

renderer使用`.env.development.example`/`.env.production.example`中的两个`VITE_`变量。准备运行环境时复制为相应的`.env.development`/`.env.production`，根据实际服务配置基址；`VITE_`变量会进入前端代码，只能放公开地址，不能放凭据。原环境文件未复制。

## 当前完成度与验证边界

本次仅做源码脱敏和静态检查：三个JavaScript文件通过`node --check`，常规JSON可解析，tsconfig按允许注释的JSONC检查，已核查公开副本未含真实环境文件、位图及命中的敏感字面量。没有执行`npm install`、构建、端到端测试或运行设备。

快照保留已有集成缝隙，未借发布整理修改业务：

- 开发模式将TCM状态预设为就绪；日志信号握手没有完整超时与重启机制。
- builder配置只携带`python-dist`，Flask EXE、RuoYi JAR及数据库需要另行配套；相机运行目录本次未分发，不能直接生成完整可用安装包。
- Dashboard活跃拍照入口与旧`ShootUploadDiaglog.vue`并存；旧弹窗仍有历史返回字段。
- 配置页参数是禁用的静态展示；数据采集页主要保存本地ZIP，不包含自动训练闭环。
- Dashboard错误结果保留原有`@/renderer/assets/img/error.png`字符串，该文件在原快照中也不存在；此分支属于既有缺口。本次自制占位图仅替换实际分发位图的引用。
- 原Vite/Electron输出和preload格式仍需构建产物验证；本次没有证明该历史配置可以直接打包。

这些限制使本目录适合阅读实现和对照项目复盘；完整复现还需要同版本后端、用户服务、模型资产及硬件环境。
