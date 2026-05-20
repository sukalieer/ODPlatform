#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""odp-transform —— 数据集转换 CLI 入口"""

from __future__ import annotations

import argparse
import logging
import sys

from odp_platform.common.paths import LOGGING_DIR
from odp_platform.common.logging_utils import get_logger
from odp_platform.data_pipeline import ConvertOptions, list_capabilities, transform_dataset

logger = logging.getLogger(__name__)


def _build_epilog() -> str:
    """从 registry 实时读取格式能力矩阵,拼到 --help 末尾。"""
    caps = list_capabilities()
    lines = ["\n格式能力矩阵 (from registry):"]
    lines.append("  {:<16} {}".format("format", "tasks"))
    lines.append("  " + "-" * 40)
    for fmt, tasks in sorted(caps.items()):
        lines.append("  {:<16} {}".format(fmt, ", ".join(tasks)))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="odp-transform",
        description="ODPlatform 数据集转换工具 —— 原始标注 → YOLO + 划分 + 训练配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_build_epilog(),
    )
    parser.add_argument(
        "--dataset", "-d",
        required=True,
        help="数据集名称 (对应 data/raw/<name>/)",
    )
    parser.add_argument(
        "--format", "-f",
        required=True,
        choices=["pascal_voc", "coco", "yolo"],
        help="原始标注格式",
    )
    parser.add_argument(
        "--classes", "-c",
        nargs="*",
        default=None,
        help="要保留的类别名称 (默认: 自动发现全部)",
    )
    parser.add_argument(
        "--task", "-t",
        default="detect",
        choices=["detect", "segment"],
        help="任务类型 (默认: detect)",
    )
    args = parser.parse_args()

    # 装配日志
    get_logger(
        base_path=LOGGING_DIR,
        log_type="transform_data",
        temp_log=False,
    )

    options = ConvertOptions(
        dataset_name=args.dataset,
        format=args.format,
        classes=args.classes,
        task=args.task,
    )

    try:
        yaml_path = transform_dataset(options)
        logger.info(f"✅ 成功! 配置文件: {yaml_path}")
        return 0
    except ValueError as e:
        logger.error(f"❌ 转换失败: {e}")
        return 1
    except FileNotFoundError as e:
        logger.error(f"❌ 文件错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
