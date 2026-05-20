from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from odp_platform.common.constants import FORMAT_TASK_MAP

# Converter 函数签名:
#   (raw_dir: Path, output_labels_dir: Path, options: ConvertOptions)
#       -> Tuple[List[str], int, int]
#   返回值: (class_names, annotated_count, total_image_count)
ConverterFunc = Callable[..., Tuple[List[str], int, int]]

_registry: Dict[str, ConverterFunc] = {}
_initialized: bool = False


@dataclass
class ConvertOptions:
    """数据集转换选项。

    classes=None 表示"用户未指定,自动发现全部类别"。
    classes=[]  表示"用户明确不要任何类别"(边界情形)。
    这个语义差异不能用可变默认参数 = [] 来表达,
    因为 Python 会在函数定义时求值一次,导致所有调用方共享同一个 list 对象。
    """
    dataset_name: str
    format: str
    classes: Optional[List[str]] = None
    task: str = "detect"


def _lazy_init() -> None:
    """延迟导入三个 converter,避免循环导入和阶段性缺文件问题。"""
    global _initialized
    if _initialized:
        return

    from odp_platform.data_pipeline.core.pascal_voc import convert_pascal_voc
    from odp_platform.data_pipeline.core.coco import convert_coco
    from odp_platform.data_pipeline.core.yolo import convert_yolo

    _registry["pascal_voc"] = convert_pascal_voc
    _registry["coco"] = convert_coco
    _registry["yolo"] = convert_yolo
    _initialized = True


def get_converter(format: str) -> ConverterFunc:
    """按格式名查找 converter 函数。

    Raises:
        ValueError: 格式名未注册
    """
    _lazy_init()
    if format not in _registry:
        raise ValueError(
            f"未知格式 '{format}'。已知格式: {sorted(_registry.keys())}"
        )
    return _registry[format]


def list_capabilities() -> Dict[str, Tuple[str, ...]]:
    """返回所有已注册格式及其支持的任务类型。

    Returns:
        {'pascal_voc': ('detect',), 'coco': ('detect', 'segment'), 'yolo': ('detect',)}
    """
    _lazy_init()
    return {fmt: FORMAT_TASK_MAP.get(fmt, ()) for fmt in _registry}