import pytest
from pathlib import Path

from odp_platform.data_pipeline.split.manifest import Sample
from odp_platform.data_pipeline.split.splitter import split_pairs, split_manifest


class TestSplitPairs:
    """split_pairs 的 8 个测试"""

    def test_valid_default_ratios(self):
        pairs = split_pairs((0.7, 0.2, 0.1))
        assert len(pairs) == 2
        r1, r2 = pairs
        assert abs(r1[0] - 0.7) < 1e-9
        assert abs(r1[1] - 0.3) < 1e-9
        assert abs(r2[0] - 0.2 / 0.3) < 1e-9
        assert abs(r2[1] - 0.1 / 0.3) < 1e-9

    def test_valid_equal_split(self):
        pairs = split_pairs((0.34, 0.33, 0.33))
        assert len(pairs) == 2

    def test_sum_exceeds_one(self):
        with pytest.raises(ValueError, match="约等于 1.0"):
            split_pairs((0.8, 0.3, 0.1))

    def test_sum_below_one(self):
        with pytest.raises(ValueError, match="约等于 1.0"):
            split_pairs((0.3, 0.2, 0.1))

    def test_zero_train_ratio(self):
        with pytest.raises(ValueError, match="train_ratio"):
            split_pairs((0.0, 0.5, 0.5))

    def test_zero_val_ratio(self):
        with pytest.raises(ValueError, match="val_ratio"):
            split_pairs((0.5, 0.0, 0.5))

    def test_zero_test_ratio(self):
        with pytest.raises(ValueError, match="test_ratio"):
            split_pairs((0.5, 0.5, 0.0))

    def test_float_epsilon_tolerance(self):
        """1.0 - 0.7 - 0.2 - 0.1 在浮点下不是 0, RATE_EPSILON 容差保证不报错"""
        pairs = split_pairs((0.7, 0.2, 0.1))
        assert len(pairs) == 2


class TestSplitManifest:
    """split_manifest 的测试"""

    def _make_samples(self, n: int) -> list:
        return [
            Sample(
                image_path=Path(f"img_{i}.jpg"),
                label_path=Path(f"img_{i}.txt"),
            )
            for i in range(n)
        ]

    def test_basic_split(self):
        samples = self._make_samples(100)
        result = split_manifest(samples, random_state=42)
        assert "train" in result
        assert "val" in result
        assert "test" in result
        assert len(result["train"]) == 70
        assert len(result["val"]) == 20
        assert len(result["test"]) == 10
        assert len(result["train"]) + len(result["val"]) + len(result["test"]) == 100

    def test_reproducible_split(self):
        samples = self._make_samples(100)
        r1 = split_manifest(samples, random_state=42)
        r2 = split_manifest(samples, random_state=42)
        for split_name in ("train", "val", "test"):
            names1 = [s.image_path.name for s in r1[split_name]]
            names2 = [s.image_path.name for s in r2[split_name]]
            assert names1 == names2

    def test_insufficient_samples(self):
        samples = self._make_samples(2)
        with pytest.raises(ValueError, match="样本总数必须"):
            split_manifest(samples)

    def test_no_empty_split(self):
        """即使样本很少，也不应产生空划分"""
        samples = self._make_samples(10)
        result = split_manifest(samples, ratios=(0.5, 0.3, 0.2), random_state=42)
        for name in ("train", "val", "test"):
            assert len(result[name]) >= 1

    def test_custom_ratios(self):
        samples = self._make_samples(100)
        result = split_manifest(samples, ratios=(0.6, 0.2, 0.2), random_state=42)
        assert len(result["train"]) == 60
        assert len(result["val"]) == 20
        assert len(result["test"]) == 20