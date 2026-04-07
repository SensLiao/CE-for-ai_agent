"""Setup for cli-anything-cheatengine."""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-cheatengine",
    version="0.2.0",
    description="CLI harness for Cheat Engine — memory inspection, scanning, and cheat table management",
    author="CLI-Anything",
    python_requires=">=3.9",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0",
        "psutil>=5.0",
    ],
    extras_require={
        "asm": [
            "keystone-engine",
            "capstone",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-cheatengine=cli_anything.cheat_engine.cheat_engine_cli:cli",
        ],
    },
)
