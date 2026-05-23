# apps/platform/src/odp_platform/data_validation/checks/yaml_schema.py
"""yaml_schema check — 验证数据集 yaml 文件的字段完整性和一致性。

检查项 (任何一项失败都标 ERROR):
    1. yaml 文件存在且可解析
    2. yaml 顶层是 dict (不是 list / scalar) — 仅指文件根节点
    3. 包含 'nc' 字段, 正整数
    4. 包含 'names' 字段, list[str] 或 dict[int,str], 元素非空
    5. len(names) == nc

不检查的项 (后续 check 负责):
    - train / val / test 路径是否存在 → pair_existence
    - 类别 ID 是否越界 → label_format
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import yaml

from odp_platform.data_validation.registry import (
    check, CheckContext, CheckResult, CheckSeverity,
)


@check("yaml_schema")
def validate_yaml_schema(ctx: CheckContext) -> CheckResult:
    yaml_path = ctx.yaml_path

    # ---------- 第 1 类错: 文件不存在 ----------
    if not yaml_path.exists():
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 文件不存在: {yaml_path}",
            details={
                "reason":    "file_not_found",
                "yaml_path": str(yaml_path),
            },
        )

    # ---------- 第 2 类错: 解析失败 ----------
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 解析失败: {e}",
            details={
                "reason":      "parse_error",
                "yaml_path":   str(yaml_path),
                "parse_error": str(e),
            },
        )
    except OSError as e:
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 读取失败: {e}",
            details={
                "reason":    "read_error",
                "yaml_path": str(yaml_path),
                "os_error":  str(e),
            },
        )

    # ---------- 第 3 类错: 顶层不是 dict ----------
    if not isinstance(cfg, dict):
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 顶层不是 dict: {type(cfg).__name__}",
            details={
                "reason":     "not_dict",
                "actual_type": type(cfg).__name__,
            },
        )

    # ---------- 第 4-6 类错: 字段一致性 ----------
    problems: List[str] = []

    nc = cfg.get("nc")
    if not isinstance(nc, int) or nc <= 0:
        problems.append(f"nc 缺失或不是正整数: {nc!r}")
        nc = None   # 防止下面继续检查时炸

    names_raw = cfg.get("names")
    names_count, names_problem = _validate_names(names_raw)
    if names_problem:
        problems.append(names_problem)

    if nc is not None and names_count is not None and nc != names_count:
        problems.append(f"nc ({nc}) 跟 names 长度 ({names_count}) 不一致")

    if problems:
        return CheckResult(
            name="yaml_schema",
            severity=CheckSeverity.ERROR,
            summary=f"yaml 字段不一致: {len(problems)} 处问题",
            details={
                "reason":   "field_inconsistency",
                "problems": problems,
                "nc":       nc,
                "names_count": names_count,
            },
        )

    # ---------- 全部通过 ----------
    return CheckResult(
        name="yaml_schema",
        severity=CheckSeverity.PASS,
        summary=f"yaml 字段一致 (nc={nc}, names_count={names_count})",
        details={
            "nc":          nc,
            "names_count": names_count,
        },
    )


# ============================================================
# 私有辅助
# ============================================================

def _validate_names(names_raw: Any) -> Tuple[Any, str]:
    """验证 names 字段, 返回 (count, problem_msg)。

    names 合法写法 (ultralytics 接受两种):
        list[str]:      [a, b, c]
        dict[int, str]: {0: a, 1: b, 2: c}    ← D3 yaml_writer 写的就是这种

    Returns:
        (names_count, problem_msg)
        - 成功: (len(names), "")
        - 失败: (None, "具体问题描述")
    """
    if isinstance(names_raw, list):
        if not names_raw:
            return None, "names 是空列表"
        if not all(isinstance(n, str) and n for n in names_raw):
            return None, "names 列表里存在非字符串或空字符串元素"
        return len(names_raw), ""

    if isinstance(names_raw, dict):
        if not names_raw:
            return None, "names 是空字典"
        if not all(isinstance(k, int) for k in names_raw.keys()):
            return None, "names 字典的 key 必须全部是 int"
        if not all(isinstance(v, str) and v for v in names_raw.values()):
            return None, "names 字典里存在非字符串或空字符串值"
        return len(names_raw), ""

    return None, f"names 不是合法的 list[str] / dict[int, str]: {type(names_raw).__name__}"