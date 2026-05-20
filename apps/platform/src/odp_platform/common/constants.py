# 任务类型
TASK_DETECT = "detect"
TASK_SEGMENT = "segment"

# 标注格式名
FORMAT_PASCAL_VOC = "pascal_voc"
FORMAT_COCO = "coco"
FORMAT_YOLO = "yolo"

# 数据集划分名称
SPLIT_TRAIN = "train"
SPLIT_VAL = "val"
SPLIT_TEST = "test"

# 默认划分比例
DEFAULT_SPLIT_RATIOS = (0.7, 0.2, 0.1)

# 随机种子
DEFAULT_RANDOM_STATE = 42

# 浮点比例容差 (解决 1.0 - 0.7 - 0.3 != 0 的问题)
RATE_EPSILON = 1e-6

# 覆盖率最低阈值 (低于此值 fail-fast)
MIN_COVERAGE_THRESHOLD = 0.5

# YAML schema 版本号
SCHEMA_VERSION = 1

# 格式 → 支持的任务类型 映射
FORMAT_TASK_MAP = {
    FORMAT_PASCAL_VOC: (TASK_DETECT,),
    FORMAT_COCO: (TASK_DETECT, TASK_SEGMENT),
    FORMAT_YOLO: (TASK_DETECT,),
}