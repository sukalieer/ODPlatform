from __future__ import annotations

import logging
from typing import List, Tuple

from sklearn.model_selection import train_test_split

from odp_platform.common.constants import (
    DEFAULT_RANDOM_STATE,
    DEFAULT_SPLIT_RATIOS,
    RATE_EPSILON,
    SPLIT_TRAIN,
    SPLIT_VAL,
    SPLIT_TEST,
)
from odp_platform.data_pipeline.split.manifest import Manifest, Sample, SplitResult

logger = logging.getLogger(__name__)


def split_pairs(
    ratios: Tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
) -> List[Tuple[float, float]]:
    """将三元组比例转为两阶段划分的参数对。

    (0.7, 0.2, 0.1) → [(0.7, 0.3), (0.666..., 0.333...)]

    第一阶段: train_ratio=0.7, rest=0.3
    第二阶段: 在 rest 内部, val 占 rest 的比例 = 0.2/(0.2+0.1) = 0.667

    5 个边界检查:
      ① 三比例之和必须约等于 1.0 (RATE_EPSILON 容差)
      ② train 比例 > 0
      ③ val 比例 > 0
      ④ test 比例 > 0
      ⑤ 剩余比例 (val + test) > 0 (保证第二阶段分母非零)

    1.0 - 0.7 - 0.3 的浮点结果不是 0,而是 ≈ -5.55e-17,
    所以必须用 RATE_EPSILON 而非 == 0.0。
    """
    r_train, r_val, r_test = ratios

    # ① 总和 ≈ 1.0
    if abs(sum(ratios) - 1.0) >= RATE_EPSILON:
        raise ValueError(
            f"划分比例之和必须约等于 1.0,当前 sum={sum(ratios):.10f}, "
            f"ratios={ratios}"
        )

    # ②③④ 各项 > 0
    for label, r in zip(("train", "val", "test"), ratios):
        if r <= 0:
            raise ValueError(
                f"{label}_ratio 必须 > 0,当前为 {r}"
            )

    rest = r_val + r_test
    # ⑤ rest > 0
    if rest <= RATE_EPSILON:
        raise ValueError(f"val + test 比例必须 > 0,当前 {rest}")

    return [
        (r_train, rest),
        (r_val / rest, r_test / rest),
    ]


def split_manifest(
    manifest: Manifest,
    ratios: Tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
    random_state: int = DEFAULT_RANDOM_STATE,
    stratify_by: str | None = None,
) -> SplitResult:
    """将 manifest 按比例划分为 train / val / test。

    使用两阶段 sklearn train_test_split:
      1. train vs (val+test)
      2. val vs test (在剩余部分内)

    Args:
        manifest: 样本列表
        ratios: (train_ratio, val_ratio, test_ratio)
        random_state: 随机种子 (保证可复现)
        stratify_by: 暂未使用,为将来分层划分预留

    Returns:
        {"train": Manifest, "val": Manifest, "test": Manifest}
    """
    if len(manifest) < 3:
        raise ValueError(
            f"样本总数必须 ≥ 3 (以保证每个划分至少 1 个样本),"
            f"当前有 {len(manifest)} 个样本"
        )

    pairs = split_pairs(ratios)

    # 第一阶段: train vs rest
    train, rest = train_test_split(
        manifest,
        train_size=pairs[0][0],
        random_state=random_state,
        shuffle=True,
    )

    # 第二阶段: val vs test (在 rest 内部)
    val, test = train_test_split(
        rest,
        train_size=pairs[1][0],
        random_state=random_state,
        shuffle=True,
    )

    # 确保每个划分至少 1 个样本
    for name, split in [(SPLIT_TRAIN, train), (SPLIT_VAL, val), (SPLIT_TEST, test)]:
        if len(split) == 0:
            raise ValueError(
                f"'{name}' 划分为空 (0 个样本)。请检查数据集大小和比例设置。"
            )

    logger.info(
        f"划分完成: train={len(train)}, val={len(val)}, test={len(test)}, "
        f"total={len(manifest)}, random_state={random_state}"
    )

    return {
        SPLIT_TRAIN: train,
        SPLIT_VAL: val,
        SPLIT_TEST: test,
    }