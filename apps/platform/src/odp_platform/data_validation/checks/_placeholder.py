# apps/platform/src/odp_platform/data_validation/checks/_placeholder.py
"""阶段 2 用的 placeholder check — 只为跑通注册表机制。

注意文件名以下划线开头 — _ensure_initialized() 会跳过它, 不会被自动注册!
要真正验证机制, 阶段 2 调试期手动 import 一次 (见下文跑通脚本)。

阶段 3 第一个真 check (yaml_schema) 接入后, 这个文件会被删掉。
"""
from odp_platform.data_validation.registry import (
    check, CheckContext, CheckResult, CheckSeverity,
)


@check("_placeholder")
def _placeholder_check(ctx: CheckContext) -> CheckResult:
    """永远 PASS 的占位 check, 验证注册表机制。"""
    return CheckResult(
        name="_placeholder",
        severity=CheckSeverity.PASS,
        summary="placeholder check — 注册表机制工作正常",
        details={"yaml_path": str(ctx.yaml_path)},
    )