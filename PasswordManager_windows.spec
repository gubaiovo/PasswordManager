# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# 1. 定义基础资源和配置
# datas 格式: ('源路径', '打包后的目标路径')
datas = [
    ('src', 'src'),                        # 打包源代码
    ('src/client/assets', 'src/client/assets') # [关键] 打包资源文件(图标等)
]
binaries = []
hiddenimports = ['sqlalchemy.sql.default_comparator', 'sqlite3']

# 2. 收集 Flet 框架所需的所有钩子和资源
tmp_ret = collect_all('flet')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 3. 分析阶段
a = Analysis(
    ['run_client.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 4. 生成 EXE 阶段
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PasswordManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    
    # [设置] 关闭控制台黑框 (GUI模式)
    console=False, 
    
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
    # [设置] EXE 文件图标 (Windows)
    icon='src/client/assets/icon.ico' 
)