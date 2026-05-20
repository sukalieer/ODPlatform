from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from odp_platform.common.constants import (
    DEFAULT_RANDOM_STATE,
    MIN_COVERAGE_THRESHOLD,
    SCHEMA_VERSION,
    SPLIT_TRAIN,
    SPLIT_VAL,
    SPLIT_TEST,
)
from odp_platform.common.paths import (
    DATASETS_CONFIG_DIR,
    INTERIM_LABELS_DIR,
    ROOT_DIR,
    TRAIN_IMAGES_DIR,
    TRAIN_LABELS_DIR,
    VAL_IMAGES_DIR,
    VAL_LABELS_DIR,
    TEST_IMAGES_DIR,
    TEST_LABELS_DIR,
)
from odp_platform.data_pipeline.registry import ConvertOptions, ConverterFunc
from odp_platform.data_pipeline.split.manifest import build_manifest_from_dir
from odp_platform.data_pipeline.split.splitter import split_manifest
from odp_platform.data_pipeline.split.materializer import materialize
from odp_platform.data_pipeline.split.yaml_writer import write_dataset_yaml

logger = logging.getLogger(__name__)

# 划分 → 目标目录的映射
_SPLIT_TARGETS = {
    SPLIT_TRAIN: (TRAIN_IMAGES_DIR, TRAIN_LABELS_DIR),
    SPLIT_VAL: (VAL_IMAGES_DIR, VAL_LABELS_DIR),
    SPLIT_TEST: (TEST_IMAGES_DIR, TEST_LABELS_DIR),
}


class Orchestrator:
    """数据集转换编排器——端到端流水线。

    关键设计:
      - _user_classes: 用户传入的类别过滤条件 (None = 全部)
      - _final_classes: 转换后实际得到的类别列表 (由 converter 返回)
        两者分开存储是因为语义不同:
          None  → "用户没限制,给我全部"
          [...] → "用户指定了这些"
        如果合并成一个属性,当 converter 返回 10 个类别而用户没传 classes 时,
        无法区分"用户要求 10 个"还是"数据集恰好有 10 个"——
        后续 filter 逻辑就会出错。
    """

    def __init__(
        self,
        options: ConvertOptions,
        raw_dir: Path,
        converter: ConverterFunc,
    ) -> None:
        self._options = options
        self._raw_dir = raw_dir
        self._converter = converter
        self._user_classes: Optional[List[str]] = options.classes
        self._final_classes: List[str] = []

    def run(self) -> Path:
        """执行完整流水线,返回 yaml 路径。"""
        # 1. 前置检查 (目录 + 覆盖率 fail-fast)
        self._check_raw()

        # 2. 格式转换
        interim_dir = INTERIM_LABELS_DIR / self._options.dataset_name
        if interim_dir.exists():
            import shutil
            shutil.rmtree(interim_dir)
        interim_dir.mkdir(parents=True, exist_ok=True)

        final_classes, annotated_count, total_count = self._converter(
            self._raw_dir, interim_dir, self._options
        )
        self._final_classes = final_classes

        logger.info(
            f"转换完成: {annotated_count}/{total_count} 个样本有标注, "
            f"类别数={len(final_classes)}"
        )

        # 3. 构建 manifest
        manifest = build_manifest_from_dir(
            images_dir=self._raw_dir / "images",
            labels_dir=interim_dir,
        )

        if len(manifest) == 0:
            raise ValueError("转换后未产生任何有效样本,无法继续")

        # 4. 划分
        random_state = DEFAULT_RANDOM_STATE
        splits = split_manifest(manifest, random_state=random_state)

        # 5. 落盘
        for split_name, split_samples in splits.items():
            img_dir, lbl_dir = _SPLIT_TARGETS[split_name]
            materialize(split_samples, img_dir, lbl_dir)

        # 6. 生成 yaml
        split_counts = {
            name: len(s) for name, s in splits.items()
        }
        yaml_path = DATASETS_CONFIG_DIR / f"{self._options.dataset_name}.yaml"
        write_dataset_yaml(
            dataset_name=self._options.dataset_name,
            class_names=final_classes,
            split_counts=split_counts,
            random_state=random_state,
            output_path=yaml_path,
        )

        return yaml_path

    def _check_raw(self) -> None:
        """前置检查: 目录结构 + 标注覆盖率 fail-fast。

        覆盖率检查必须放在 converter 之前:
          如果 1000 张图片只有 50 张有标注 (覆盖率 5%),
          调用 converter 会浪费大量时间处理 950 张无标注图片,
          且产出的数据集对训练毫无价值。
          fail-fast 直接报 ValueError,让用户修复数据后再来。

        覆盖率 = 有标注的图片数 / 总图片数
        """
        ann_dir = self._raw_dir / "annotations"
        img_dir = self._raw_dir / "images"

        if not img_dir.exists() and not ann_dir.exists():
            raise FileNotFoundError(
                f"数据集目录结构不完整: {self._raw_dir}\n"
                f"需要 images/ 和/或 annotations/ 子目录"
            )

        # 根据格式确定标注扩展名
        fmt = self._options.format
        if fmt == "pascal_voc":
            ann_ext = ".xml"
        elif fmt == "coco":
            ann_ext = ".json"  # COCO 单文件,特殊处理
        else:
            ann_ext = ".txt"

        # 计数
        img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        img_names: set[str] = set()
        if img_dir.exists():
            for ext in img_extensions:
                for p in img_dir.glob(f"*{ext}"):
                    img_names.add(p.stem)
                for p in img_dir.glob(f"*{ext.upper()}"):
                    img_names.add(p.stem)

        total_images = len(img_names)
        if total_images == 0:
            raise FileNotFoundError(f"图片目录为空: {img_dir}")

        # 标注总数
        if fmt == "coco":
            json_files = list(ann_dir.glob("*.json")) if ann_dir.exists() else []
            if not json_files:
                annotated_count = 0
            else:
                import json
                with open(json_files[0], "r", encoding="utf-8") as f:
                    coco = json.load(f)
                # 有标注的图片 = 在 annotations 中出现的 unique image_id
                ann_img_ids = {a["image_id"] for a in coco.get("annotations", [])}
                annotated_count = len(ann_img_ids)
        else:
            if not ann_dir.exists():
                annotated_count = 0
            else:
                ann_names: set[str] = set()
                for p in ann_dir.glob(f"*{ann_ext}"):
                    ann_names.add(p.stem)
                # 有标注的图片 = annotations 和 images 的交集
                annotated_count = len(img_names & ann_names)

        coverage = annotated_count / total_images if total_images > 0 else 0.0
        logger.info(
            f"覆盖率检查: {annotated_count}/{total_images} "
            f"({coverage:.1%}), 阈值={MIN_COVERAGE_THRESHOLD:.0%}"
        )

        if coverage < MIN_COVERAGE_THRESHOLD:
            raise ValueError(
                f"数据集 '{self._options.dataset_name}' 标注覆盖率过低: "
                f"{annotated_count}/{total_images} ({coverage:.1%}) < "
                f"阈值 {MIN_COVERAGE_THRESHOLD:.0%}。\n"
                f"请检查标注文件是否完整,或手动补全缺失的标注。"
            )