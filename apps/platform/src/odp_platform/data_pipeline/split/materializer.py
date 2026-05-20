from __future__ import annotations

import logging
import shutil
from pathlib import Path

from odp_platform.data_pipeline.split.manifest import Manifest

logger = logging.getLogger(__name__)


def materialize(
    manifest: Manifest,
    target_images_dir: Path,
    target_labels_dir: Path,
    mode: str = "copy",
) -> None:
    """将 manifest 中的样本落盘到目标目录。

    使用依赖注入 (DI) 接收目标目录参数,而非直接 import paths.py:
      - 优势 1: 单元测试时可以传入 tempfile 临时目录,
               不污染真实 data/ 目录
      - 优势 2: 同一进程内可复用,产出到不同目标路径
               (如同时生成 "debug" 和 "release" 两份)

    Args:
        manifest: 样本列表
        target_images_dir: 图片目标目录
        target_labels_dir: 标注目标目录
        mode: "copy" (默认) 或 "symlink"
    """
    target_images_dir.mkdir(parents=True, exist_ok=True)
    target_labels_dir.mkdir(parents=True, exist_ok=True)

    for sample in manifest:
        src_img = sample.image_path
        src_lbl = sample.label_path

        dst_img = target_images_dir / src_img.name
        dst_lbl = target_labels_dir / src_lbl.name

        if mode == "symlink":
            if not dst_img.exists():
                dst_img.symlink_to(src_img.resolve())
            if not dst_lbl.exists():
                dst_lbl.symlink_to(src_lbl.resolve())
        else:
            if not dst_img.exists():
                shutil.copy2(src_img, dst_img)
            if not dst_lbl.exists():
                shutil.copy2(src_lbl, dst_lbl)

    logger.info(
        f"落盘完成: {len(manifest)} 个样本 → "
        f"images={target_images_dir.name}, labels={target_labels_dir.name} "
        f"(mode={mode})"
    )
