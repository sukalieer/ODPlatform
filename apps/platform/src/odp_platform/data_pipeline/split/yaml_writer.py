from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import yaml

from odp_platform.common.constants import SCHEMA_VERSION
from odp_platform.common.paths import ROOT_DIR

logger = logging.getLogger(__name__)


def write_dataset_yaml(
    dataset_name: str,
    class_names: List[str],
    split_counts: Dict[str, int],
    random_state: int,
    output_path: Path,
) -> Path:
    """生成 ultralytics 兼容的 data.yaml + odp_meta 元数据块。

    Args:
        dataset_name: 数据集名称
        class_names: 类别名称列表
        split_counts: {"train": N, "val": M, "test": K}
        random_state: 划分时使用的随机种子
        output_path: yaml 文件输出路径

    Returns:
        生成的 yaml 文件路径
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 相对于 ROOT_DIR 的路径 (ultralytics 需要绝对路径或相对路径)
    data_dir = ROOT_DIR / "data"

    doc = {
        "path": str(data_dir.resolve()),
        "train": str(Path("data") / "train" / "images"),
        "val": str(Path("data") / "val" / "images"),
        "test": str(Path("data") / "test" / "images"),
        "nc": len(class_names),
        "names": class_names,
        "odp_meta": {
            "schema_version": SCHEMA_VERSION,
            "dataset_name": dataset_name,
            "random_state": random_state,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "split": {
                "counts": split_counts,
                "total": sum(split_counts.values()),
            },
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"训练配置文件已生成: {output_path}")
    return output_path