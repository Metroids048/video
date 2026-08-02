"""cut.skill — 安装脚本。

用法：
    cd scripts/
    pip install -e .

之后可直接：
    cut-cli detect
    cut-cli get-state --backend jianying --project my_vlog
"""
from setuptools import setup, find_packages

setup(
    name="cut-skill",
    version="1.2.0",
    description="统一视频剪辑操控 skill（剪映 + Premiere）",
    author="cut.skill",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        # 核心无依赖
    ],
    extras_require={
        "premiere": ["pymiere>=0.2.0"],
        "ui": ["pyautogui>=0.9.54", "pygetwindow>=0.0.9; sys_platform == 'win32'"],
        "mcp": ["mcp>=0.1.0"],
        "http": ["flask>=2.0.0"],
        "all": [
            "pymiere>=0.2.0",
            "pyautogui>=0.9.54",
            "mcp>=0.1.0",
            "flask>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cut-cli=cut.cli:main",
        ],
    },
)
