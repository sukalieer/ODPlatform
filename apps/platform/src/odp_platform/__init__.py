#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
ODPlatform - 通用的目标检测开发平台

Public API入口，具体的子模块
- odp_platform.common : 基础工具(路径、日志、字符串，系统，性能)
- odp_platform.cli : 命令行入口
"""
from odp_platform._version import __version__

__all__ = ["__version__"]
