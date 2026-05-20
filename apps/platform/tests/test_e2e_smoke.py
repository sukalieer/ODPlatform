"""端到端冒烟测试 —— 用 rsod 数据集验证整条流水线。

前提: data/raw/rsod/ 下已有 images/ 和 annotations/ (Pascal VOC XML)。
"""

import tempfile
from pathlib import Path

import pytest

from odp_platform.common.paths import RAW_DATA_DIR, DATASETS_CONFIG_DIR
from odp_platform.data_pipeline import ConvertOptions, transform_dataset


@pytest.fixture
def rsod_available():
    """检查 rsod 数据集是否可用"""
    ann_dir = RAW_DATA_DIR / "rsod" / "annotations"
    img_dir = RAW_DATA_DIR / "rsod" / "images"
    if not ann_dir.exists() or not img_dir.exists():
        pytest.skip("rsod 数据集不可用")
    return True


class TestEndToEnd:
    def test_voc_smoke(self, rsod_available):
        """端到端: VOC → YOLO + 划分 + yaml"""
        options = ConvertOptions(
            dataset_name="rsod",
            format="pascal_voc",
        )
        yaml_path = transform_dataset(options)
        assert yaml_path.exists()
        assert yaml_path.suffix == ".yaml"

        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        assert "odp_meta" in doc
        meta = doc["odp_meta"]
        assert "random_state" in meta
        assert "created_at" in meta
        assert "split" in meta
        assert "counts" in meta["split"]
        assert "nc" in doc
        assert "names" in doc

    def test_coverage_fail_fast(self):
        """覆盖率 < 50% 应快速失败"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # 创建伪造数据集: 3 张图,只有 1 个标注
            img_dir = tmp_path / "images"
            ann_dir = tmp_path / "annotations"
            img_dir.mkdir()
            ann_dir.mkdir()

            for i in range(3):
                (img_dir / f"{i}.jpg").touch()
            # 只给 1 张图创建标注 → 覆盖率 1/3 = 33% < 50%
            (ann_dir / "0.xml").write_text(
                '<?xml version="1.0"?><annotation>'
                '<filename>0.jpg</filename>'
                '<size><width>100</width><height>100</height></size>'
                '<object><name>cat</name><bndbox>'
                '<xmin>10</xmin><ymin>10</ymin><xmax>50</xmax><ymax>50</ymax>'
                '</bndbox></object></annotation>'
            )

            from odp_platform.data_pipeline.registry import ConvertOptions
            from odp_platform.data_pipeline.orchestrator import Orchestrator
            from odp_platform.data_pipeline.registry import get_converter

            options = ConvertOptions(
                dataset_name=tmp_path.name,
                format="pascal_voc",
            )
            converter = get_converter("pascal_voc")
            orch = Orchestrator(
                options=options,
                raw_dir=tmp_path,
                converter=converter,
            )

            with pytest.raises(ValueError, match="覆盖率过低"):
                orch.run()