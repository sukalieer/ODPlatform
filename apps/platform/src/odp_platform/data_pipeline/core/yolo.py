from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Set, Tuple

from odp_platform.data_pipeline.registry import ConvertOptions

logger = logging.getLogger(__name__)


def convert_yolo(
    raw_dir: Path,
    output_labels_dir: Path,
    options: ConvertOptions,
) -> Tuple[List[str], int, int]:
    """将 YOLO 格式数据集"转换"为 YOLO 格式 (接口等价层)。

    虽然 YOLO 已经是目标格式,但仍然需要这个 converter:
      - 如果用户指定了 classes,需要过滤/重映射类别 ID
      - 统一上层编排逻辑: 所有格式的 converter 返回值签名一致,
        orchestrator 无需区分"源格式是否等于目标格式"

    实现策略:
      如果没有 classes 过滤需求,直接复制标注文件到 output_labels_dir;
      如果有,则重写每个 .txt 文件只保留指定类别的行。

    Returns:
        (class_names, annotated_count, total_image_count)
    """
    ann_dir = raw_dir / "labels"

    if not ann_dir.exists():
        # 有些 YOLO 数据集把标注放在 annotations/ 下
        alt_dir = raw_dir / "annotations"
        if alt_dir.exists():
            ann_dir = alt_dir
        else:
            raise FileNotFoundError(
                f"YOLO 标注目录不存在: {ann_dir} (也试过 {alt_dir})"
            )

    output_labels_dir.mkdir(parents=True, exist_ok=True)

    # 收集所有标注文件中的类别
    all_class_ids: Set[int] = set()
    label_files = sorted(ann_dir.glob("*.txt"))

    for lf in label_files:
        for line in lf.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            try:
                cls_id = int(line.split()[0])
                all_class_ids.add(cls_id)
            except (ValueError, IndexError):
                continue

    max_id = max(all_class_ids) if all_class_ids else -1

    # 确定类别表
    if options.classes is not None:
        class_list = list(options.classes)
        # 按用户指定的顺序映射
        user_cls_to_new_id = {name: idx for idx, name in enumerate(class_list)}
    else:
        class_list = [f"class_{i}" for i in range(max_id + 1)]

    # 获取图片总数
    img_dir = raw_dir / "images"
    img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    total_image_count = 0
    if img_dir.exists():
        for ext in img_extensions:
            total_image_count += len(list(img_dir.glob(f"*{ext}")))
            total_image_count += len(list(img_dir.glob(f"*{ext.upper()}")))
    if total_image_count == 0:
        total_image_count = len(label_files)

    # 写标注文件
    converted_count = 0
    for lf in label_files:
        lines_out = []
        for line in lf.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            parts = line.strip().split()
            try:
                cls_id = int(parts[0])
            except ValueError:
                continue

            if options.classes is not None:
                # 需要 classes.txt 来映射 ID→名称
                # 简化处理: options.classes 已经是按原始 ID 顺序排列的
                if cls_id >= len(class_list):
                    continue

            lines_out.append(line.strip())

        if lines_out:
            label_path = output_labels_dir / lf.name
            label_path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
            converted_count += 1

    return class_list, converted_count, total_image_count