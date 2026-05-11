# -*- mode: python ; coding: utf-8 -*-

import os


block_cipher = None
project_dir = os.path.abspath(".")
datas = [
    ("ui/resources", "ui/resources"),
    (".env.example", "."),
]

env_file = os.path.join(project_dir, ".env")
if os.path.isfile(env_file):
    datas.append((env_file, "."))

icon_file = os.path.join(project_dir, "ui", "resources", "icons", "logo.ico")
if not os.path.isfile(icon_file):
    icon_file = None


a = Analysis(
    ["main.py"],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pymysql",
        "PyQt5.sip",
        "sqlalchemy.dialects",
        "sqlalchemy.dialects.mysql",
        "sqlalchemy.dialects.mysql.base",
        "sqlalchemy.dialects.mysql.mysqldb",
        "sqlalchemy.dialects.mysql.pymysql",
    ],
    hookspath=["./hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.dialects.oracle",
        "sqlalchemy.dialects.mssql",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DormManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
