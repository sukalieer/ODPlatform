# ADR-002: 数据流水线子系统采用注册表 + 接口等价架构

| 项目 | 内容 |
|---|---|
| 状态 | ✅ Accepted |
| 决策日期 | 2026-05-20 |

## 背景
ODPlatform 需要支持多种标注格式 (Pascal VOC / COCO / YOLO) 的数据集,
统一转换为 YOLO 格式并划分 train/val/test, 最终生成 ultralytics 训练配置。

## 备选方案
- 方案 A: 工厂模式 — ConverterFactory.create("pascal_voc")
- 方案 B: 抽象基类 — class PascalVOCConverter(BaseConverter)
- 方案 C: 注册表 — _registry dict + lazy_init (采纳)

## 决定
方案 C: 注册表模式。

## 理由
1. **注册表解决"发现"问题**: 外部通过字符串名查找 converter,
   新增格式只需加一个注册项,调用方代码不变
2. **工厂解决"创建"问题**: 封装构建复杂度,但我们每个 converter
   是模块级函数,没有复杂构建过程,工厂是过度抽象
3. **ABC 解决"契约"问题**: 定义 converter 必须实现的接口,
   但我们用 Duck Typing (函数签名约定) 就够了,
   不需要运行时 isinstance 检查
4. 延迟导入 (_lazy_init): 避免循环导入,支持渐进开发

## 后果
- 正面: 新增格式只需加一个 .py 和一行注册,无需改调用方
- 负面: 注册表是全局可变状态,并发下需加锁 (当前 CLI 单线程无影响)
- 中性: 接口靠约定 (返回三元组) 而非类型系统强制

## 参考资料
- D3 任务说明中的关键概念检查第 1 题
- apps/platform/src/odp_platform/data_pipeline/registry.py