import pytest

from odp_platform.data_pipeline.registry import (
    ConvertOptions,
    get_converter,
    list_capabilities,
)


class TestConvertOptions:
    def test_defaults(self):
        opts = ConvertOptions(dataset_name="test", format="pascal_voc")
        assert opts.dataset_name == "test"
        assert opts.format == "pascal_voc"
        assert opts.classes is None
        assert opts.task == "detect"

    def test_with_classes(self):
        opts = ConvertOptions(
            dataset_name="test",
            format="coco",
            classes=["cat", "dog"],
        )
        assert opts.classes == ["cat", "dog"]

    def test_empty_classes_is_not_none(self):
        """[] 和 None 语义不同,不能混淆"""
        opts = ConvertOptions(
            dataset_name="test",
            format="yolo",
            classes=[],
        )
        assert opts.classes == []
        assert opts.classes is not None


class TestRegistry:
    def test_get_converter_valid(self):
        for fmt in ("pascal_voc", "coco", "yolo"):
            converter = get_converter(fmt)
            assert callable(converter)

    def test_get_converter_invalid(self):
        with pytest.raises(ValueError, match="未知格式"):
            get_converter("nonexistent_format")

    def test_list_capabilities(self):
        caps = list_capabilities()
        assert isinstance(caps, dict)
        assert "pascal_voc" in caps
        assert "coco" in caps
        assert "yolo" in caps
        assert caps["pascal_voc"] == ("detect",)
        assert caps["coco"] == ("detect", "segment")
        assert caps["yolo"] == ("detect",)