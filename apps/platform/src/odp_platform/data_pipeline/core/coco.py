from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from odp_platform.data_pipeline.registry import ConvertOptions

logger = logging.getLogger(__name__)


def convert_coco(
    raw_dir: Path,
    output_labels_dir: Path,
    options: ConvertOptions,
) -> Tuple[List[str], int, int]:
    """将 COCO JSON 格式数据集转换为 YOLO 格式。

    COCO 的 images[].file_name 可能与磁盘实际文件名不一致
    (含子路径前缀、大小写差异等),因此:
      1. 把原始图片复制到 tempfile 临时目录,统一用 images[].file_name 命名
      2. 在临时目录下以统一文件名生成 YOLO 标注
      3. 标注写入 output_labels_dir,临时图片目录自动清理

    Returns:
        (class_names, annotated_count, total_image_count)
    """
    ann_dir = raw_dir / "annotations"
    img_dir = raw_dir / "images"

    # 找 COCO JSON 文件
    json_files = list(ann_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"未找到 COCO JSON 标注文件: {ann_dir}")

    ann_path = json_files[0]  # 取第一个 JSON
    with open(ann_path, "r", encoding="utf-8") as f:
        coco = json.load(f)

    # 类别映射
    categories = coco.get("categories", [])
    if options.classes is not None:
        class_list = [
            c for c in options.classes
            if any(cat["name"] == c for cat in categories)
        ]
    else:
        class_list = sorted(
            cat["name"] for cat in categories
            if cat.get("name")
        )

    cat_id_to_idx: Dict[int, int] = {}
    for cat in categories:
        name = cat.get("name", "")
        if name in class_list:
            cat_id_to_idx[cat["id"]] = class_list.index(name)

    # 图片 ID → file_name 映射
    img_id_to_info: Dict[int, Dict] = {}
    for img in coco.get("images", []):
        img_id_to_info[img["id"]] = img

    # 标注按 image_id 分组
    anns_by_image: Dict[int, List] = {}
    for ann in coco.get("annotations", []):
        img_id = ann["image_id"]
        if img_id not in anns_by_image:
            anns_by_image[img_id] = []
        anns_by_image[img_id].append(ann)

    # 用 tempfile 中转: 复制图片到临时目录 (统一文件名)
    output_labels_dir.mkdir(parents=True, exist_ok=True)
    total_image_count = len(img_id_to_info)
    converted_count = 0

    with tempfile.TemporaryDirectory(prefix="odp_coco_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        for img_id, img_info in img_id_to_info.items():
            file_name = img_info["file_name"]
            stem = Path(file_name).stem

            # 找原始图片
            src_img = None
            for ext in (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"):
                candidate = img_dir / f"{stem}{ext}"
                if candidate.exists():
                    src_img = candidate
                    break
                candidate_upper = img_dir / f"{stem}{ext.upper()}"
                if candidate_upper.exists():
                    src_img = candidate_upper
                    break

            # 复制到临时目录 (统一用 file_name 作为文件名)
            if src_img is not None:
                dst_img = tmp_path / Path(file_name).name
                shutil.copy2(src_img, dst_img)

            # 生成 YOLO 标注
            anns = anns_by_image.get(img_id, [])
            if not anns:
                continue

            lines = []
            img_w = img_info.get("width", 0)
            img_h = img_info.get("height", 0)
            if img_w <= 0 or img_h <= 0:
                continue

            for ann in anns:
                cat_id = ann["category_id"]
                if cat_id not in cat_id_to_idx:
                    continue

                bbox = ann.get("bbox", [])
                if len(bbox) != 4:
                    continue

                x, y, w, h = bbox
                x_center = (x + w / 2.0) / img_w
                y_center = (y + h / 2.0) / img_h
                norm_w = w / img_w
                norm_h = h / img_h

                class_idx = cat_id_to_idx[cat_id]
                lines.append(
                    f"{class_idx} {x_center:.6f} {y_center:.6f} "
                    f"{norm_w:.6f} {norm_h:.6f}"
                )

            if lines:
                label_path = output_labels_dir / f"{stem}.txt"
                label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                converted_count += 1

    return class_list, converted_count, total_image_count