"""
Setup script for creating Mac .app bundle
사용법:
    python3 setup.py py2app
"""

from setuptools import setup

APP = ['batch_rename_gui.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter'],
    'iconfile': None,  # 아이콘 파일이 있으면 경로 지정
    'plist': {
        'CFBundleName': '파일 이름 일괄 변경',
        'CFBundleDisplayName': '파일 이름 일괄 변경',
        'CFBundleGetInfoString': "파일 이름을 쉽게 일괄 변경하는 Mac 앱",
        'CFBundleIdentifier': "com.batchrename.gui",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': "Copyright © 2024. All rights reserved."
    }
}

setup(
    name='BatchRenameGUI',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
