# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the directory containing this spec file
spec_root = Path(SPECPATH)
project_root = spec_root.parent  # Go up one level to project root

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include configuration schemas and examples
        (str(project_root / 'schemas'), 'schemas'),
        # Include documentation (contains README.md)
        (str(project_root / 'docs'), 'docs'),
    ],
    hiddenimports=[
        # Ensure all our modules are included
        'src.ansible_service',
        'src.config.loader',
        'src.config.file_validator',
        'src.adapters.ansible_cli.command_builder',
        'src.adapters.ansible_cli.multi_command_builder',
        'src.core.execution.executor',
        'src.core.execution.multi_executor',
        'src.core.metadata.manager',
        'src.models.ansible_config',
        'src.infrastructure.logging.log_manager',
        'src.adapters.systemd.service_generator',
        # YAML dependencies
        'yaml',
        'yaml.loader',
        'yaml.dumper',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'jupyter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ansible-runner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)