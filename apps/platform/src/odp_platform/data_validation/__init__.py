# apps/platform/src/odp_platform/data_validation/__init__.py
"""data_validation 子系统的对外公共 API。

外部调用方应该只 import 这里, 不直接 import 内部子模块。

公开符号 (本阶段):
    - CheckContext, CheckResult, CheckSeverity:  数据契约
    - check, get_all_checks, get_check:          注册表 API
    - run_all_checks:                            调度

后续阶段 (4 / 8 / 9) 会再 re-export:
    - DatasetSnapshot, build_snapshot           (阶段 4)
    - ValidationReport                          (阶段 8)
    - render_to_logger                          (阶段 8)
    - validate_dataset                          (阶段 9)
"""
from odp_platform.data_validation.registry import (
    CheckContext,
    CheckResult,
    CheckSeverity,
    check,
    get_all_checks,
    get_check,
    list_check_names,
)
from odp_platform.data_validation.service import run_all_checks
from odp_platform.data_validation.snapshot import (
    DatasetSnapshot, SplitStats, build_snapshot,
)
from odp_platform.data_validation.report import ValidationReport
from odp_platform.data_validation.render import render_to_logger
from odp_platform.data_validation.service import run_all_checks, validate_dataset

__all__ = [
    "CheckContext",
    "CheckResult",
    "CheckSeverity",
    "check",
    "get_all_checks",
    "get_check",
    "list_check_names",
    "run_all_checks",
    "DatasetSnapshot",        # ← 阶段 4 新增
    "SplitStats",             # ← 阶段 4 新增
    "build_snapshot",         # ← 阶段 4 新增
    "ValidationReport",       # ← 阶段 8 新增
    "render_to_logger",       # ← 阶段 8 新增
    "validate_dataset",  # ← 阶段 9 新增
]