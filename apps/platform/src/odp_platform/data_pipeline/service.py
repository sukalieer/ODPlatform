from __future__ import annotations

import logging
from pathlib import Path

from odp_platform.common.paths import RAW_DATA_DIR, DATASETS_CONFIG_DIR
from odp_platform.data_pipeline.registry import ConvertOptions, get_converter
from odp_platform.data_pipeline.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def transform_dataset(options: ConvertOptions) -> Path:
    """转换一个数据集,返回生成的 yaml 文件路径。

    这是 service 层(调度层)——负责参数校验 + 路径组装 + 委托 orchestrator。
    CLI 入口只调用这一个函数即可。
    """
    raw_dir = RAW_DATA_DIR / options.dataset_name

    if not raw_dir.exists():
        raise FileNotFoundError(
            f"数据集目录不存在: {raw_dir}\n"
            f"请确认 data/raw/ 下存在 '{options.dataset_name}' 文件夹。"
        )

    converter = get_converter(options.format)
    logger.info(
        f"开始转换: dataset={options.dataset_name}, format={options.format}"
    )

    orch = Orchestrator(options=options, raw_dir=raw_dir, converter=converter)
    yaml_path = orch.run()

    logger.info(f"转换完成,配置文件: {yaml_path}")
    return yaml_path