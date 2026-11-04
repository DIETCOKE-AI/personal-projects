# -*- mode: python; coding: utf-8 -*-

# 这是一个为生产环境优化的 PyInstaller 配置文件。
# 它移除了所有对本地虚拟环境的硬编码依赖，使其更健壮、更可移植。

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 1. 数据文件 (datas)
# 我们需要将应用运行所需的非代码文件（如模型、配置、模板）包含进来。
# 格式为 ('源文件/文件夹路径', '打包后在根目录下的目标文件夹名')
datas = [
    # 将 templates 文件夹完整复制到打包后的 templates 文件夹中
    ('templates', 'templates'),
    # 将 uploads 文件夹完整复制到打包后的 uploads 文件夹中
    ('uploads', 'uploads'),
    # 将 model 文件夹完整复制到打包后的 model 文件夹中
    ('model', 'model'),
    # 将 checkpoints 文件夹完整复制到打包后的 checkpoints 文件夹中
    ('checkpoints', 'checkpoints'),
    # 将 config 文件夹完整复制到打包后的 config 文件夹中
    ('config', 'config'),
    # 自动收集 SQLAlchemy 需要的数据文件
    *collect_data_files('sqlalchemy'),
    # 自动收集 Flask-Cors 需要的数据文件
    *collect_data_files('flask_cors')
]

# 2. 隐藏导入 (hiddenimports)
# 告诉 PyInstaller 一些它可能无法自动发现的、需要打包的库。
# 这对于那些使用动态导入（如 Flask 插件）的库尤其重要。
hiddenimports = [
    'flask_cors',
    'flask_jwt_extended',
    'sqlalchemy.dialects.mysql',
    'mysql.connector',
    # 关键修复：为PyTorch手动添加所有必需的隐藏导入，以解决JIT编译错误
    *collect_submodules('torch'),
    *collect_submodules('torchvision'),
    # 自动包含您项目中的所有控制器、路由和模型模块
    *collect_submodules('controllers'),
    *collect_submodules('routes'),
    *collect_submodules('model')
]

# 3. 主分析程序 (Analysis)
# 这是 PyInstaller 的核心配置。
a = Analysis(
    # 应用的入口文件是 app.py
    ['app.py'],
    # 将所有数据文件包含进来
    datas=datas,
    # 将所有隐藏的导入包含进来
    hiddenimports=hiddenimports,
    # 指定自定义钩子文件的位置
    hookspath=['hooks'],
    # 指定在程序启动时需要运行的运行时钩子
    runtime_hooks=['hooks/pyi_rth_torch.py', 'hooks/pyi_rth_inspect.py'],
    # 以下为标准配置
    pathex=[],
    binaries=[],
    # 关键修复：排除会导致运行时错误的 PyTorch JIT 编译器模块
    excludes=[
        'torch.jit.ScriptModule',
        'torch.jit.ScriptFunction',
        'torch.jit._script.ScriptModule',
        'torch.jit._script.ScriptFunction'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

# 4. 打包可执行文件 (EXE)
# 基于上面的分析结果，创建 .exe 文件。
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='tcm_app',          # 生成的 .exe 文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,               # 使用 UPX 压缩 (如果已安装)
    console=True,           # 保持控制台窗口，以便查看日志
    icon=None               # 您可以在这里指定一个 .ico 文件作为图标
)

# 5. 收集所有文件 (COLLECT)
# 将 .exe 文件、所有依赖的动态链接库 (.dll) 和数据文件，收集到一个最终的文件夹中。
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='tcm_app'          # 最终生成的文件夹名
)
