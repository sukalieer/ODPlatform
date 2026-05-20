from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from odp_platform.data_pipeline.registry import ConvertOptions

logger = logging.getLogger(__name__)


def _parse_voc_xml(xml_path: Path) -> Tuple[Optional[str], Optional[int], Optional[int], List[Dict]]:
    """解析单个 Pascal VOC XML 标注文件。

    Returns:
        (filename, width, height, [{"name": str, "xmin","ymin","xmax","ymax"}, ...])
        解析失败返回 (None, None, None, [])
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError:
        logger.warning(f"XML 解析失败,跳过: {xml_path.name}")
        return None, None, None, []

    filename_el = root.find("filename")
    filename = filename_el.text if filename_el is not None else None

    size_el = root.find("size")
    if size_el is not None:
        w_el = size_el.find("width")
        h_el = size_el.find("height")
        width = int(w_el.text) if w_el is not None and w_el.text else None
        height = int(h_el.text) if h_el is not None and h_el.text else None
    else:
        width, height = None, None

    objects = []
    for obj in root.findall("object"):
        name_el = obj.find("name")
        bndbox = obj.find("bndbox")
        if name_el is None or bndbox is None:
            continue
        try:
            xmin = float(bndbox.find("xmin").text)
            ymin = float(bndbox.find("ymin").text)
            xmax = float(bndbox.find("xmax").text)
            ymax = float(bndbox.find("ymax").text)
        except (AttributeError, ValueError):
            continue
        objects.append({
            "name": name_el.text,
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
        })

    return filename, width, height, objects


def _voc_to_yolo_line(
    xmin: float, ymin: float, xmax: float, ymax: float,
    img_w: int, img_h: int, class_id: int,
) -> str:
    """将 VOC bbox 转为 YOLO 归一化格式字符串。"""
    x_center = (xmin + xmax) / 2.0 / img_w
    y_center = (ymin + ymax) / 2.0 / img_h
    width = (xmax - xmin) / img_w
    height = (ymax - ymin) / img_h
    return f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def convert_pascal_voc(
    raw_dir: Path,
    output_labels_dir: Path,
    options: ConvertOptions,
) -> Tuple[List[str], int, int]:
    """将 Pascal VOC 格式数据集转换为 YOLO 格式。

    Args:
        raw_dir: 数据集根目录 (含 images/ 和 annotations/)
        output_labels_dir: 转换后 YOLO 标注输出目录
        options: 转换选项

    Returns:
        (class_names, annotated_count, total_image_count)
    """
    ann_dir = raw_dir / "annotations"
    img_dir = raw_dir / "images"

    if not ann_dir.exists():
        raise FileNotFoundError(f"标注目录不存在: {ann_dir}")

    output_labels_dir.mkdir(parents=True, exist_ok=True)

    # 第一遍: 扫描全部 XML,收集类别名
    xml_files = sorted(ann_dir.glob("*.xml"))
    all_class_names: Set[str] = set()
    xml_data: List[Tuple[Path, str, int, int, List[Dict]]] = []

    for xml_path in xml_files:
        filename, width, height, objects = _parse_voc_xml(xml_path)
        if filename is None or width is None or height is None:
            continue
        xml_data.append((xml_path, filename, width, height, objects))
        for obj in objects:
            all_class_names.add(obj["name"])

    # 确定最终类别表
    if options.classes is not None:
        class_list = [c for c in options.classes if c in all_class_names]
    else:
        class_list = sorted(all_class_names)

    class_to_id = {name: idx for idx, name in enumerate(class_list)}

    # 获取全部图片文件名集合 (用于计算覆盖率)
    img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    all_images: Set[str] = set()
    if img_dir.exists():
        for ext in img_extensions:
            for p in img_dir.glob(f"*{ext}"):
                all_images.add(p.name)
            for p in img_dir.glob(f"*{ext.upper()}"):
                all_images.add(p.name)

    total_image_count = len(all_images) if all_images else len(xml_files)

    # 第二遍: 写 YOLO 标注文件
    converted_count = 0
    for xml_path, voc_filename, width, height, objects in xml_data:
        # 找到对应的图片文件
        stem = Path(voc_filename).stem
        matched_images = [
            name for name in all_images
            if Path(name).stem == stem
        ]
        if not matched_images:
            logger.warning(f"找不到对应图片,跳过: {voc_filename}")
            continue

        lines = []
        for obj in objects:
            name = obj["name"]
            if name not in class_to_id:
                continue
            line = _voc_to_yolo_line(
                obj["xmin"], obj["ymin"], obj["xmax"], obj["ymax"],
                width, height, class_to_id[name],
            )
            lines.append(line)

        if not lines:
            continue

        label_name = stem + ".txt"
        label_path = output_labels_dir / label_name
        label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        converted_count += 1

    return class_list, converted_count, total_image_count