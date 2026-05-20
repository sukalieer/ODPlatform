from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Sample:
    """一个数据样本——图片 + 标注的配对。"""
    image_path: Path
    label_path: Path


Manifest = List[Sample]

def build_manifest_from_dir(
    images_dir: Path,
    labels_dir: Path,
) -> Manifest:
    """从图片目录和标注目录构建 manifest (按 stem 配对)。

    只有同时存在图片和对应标注文件的样本才会被收录。
    """
    img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

    # 收集标注文件的 stem
    label_stems: dict[str, Path] = {}
    if labels_dir.exists():
        for lbl in labels_dir.glob("*.txt"):
            label_stems[lbl.stem] = lbl

    manifest = []
    if images_dir.exists():
        for ext in img_extensions:
            for img in images_dir.glob(f"*{ext}"):
                stem = img.stem
                if stem in label_stems:
                    manifest.append(Sample(
                        image_path=img,
                        label_path=label_stems[stem],
                    ))
            for ext in img_extensions:
                for img in images_dir.glob(f"*{ext.upper()}"):
                    stem = img.stem
                    if stem in label_stems:
                        manifest.append(Sample(
                            image_path=img,
                            label_path=label_stems[stem],
                        ))

    return manifest

SplitResult = dict[str, Manifest]