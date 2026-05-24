# ADR-004: data_validation 子系统架构

**状态**: Accepted
**日期**: 2026-05-16
**作用范围**: `apps/platform/src/odp_platform/data_validation/`

## 上下文

D3 产出的 YOLO yaml 直接进 D5 训练前, 需要质检——验证图像/标签成对、
yaml 字段一致、各 split 无图像名重复、label 格式合法等。

设计这套质检子系统时, 我们面对几个核心选择:

- 调度方式: 一坨函数 / if-elif / 注册表?
- check 间数据共享: 各自扫盘 / 共享快照?
- 失败语义: 早返回 / 收集所有?
- 修复能力: 检测 + 修复 / 仅检测?
- 数据与展示: 耦合 / 分离?

本 ADR 记录最终选择 + 理由。

## 决策

### 1. 调度: 注册表聚合执行

- 每个 check 是 `checks/` 下的独立文件 + `@check("name")` 装饰器自动注册
- 调度层 `service.run_all_checks(ctx)` 跑全部 check, 收集 `List[CheckResult]`
- **任何 check 抛异常都被 service 接住, 包装成 ERROR 级 CheckResult, 不阻断其他 check**

跟 D3 的 data_pipeline.registry 同源, 但调度模式相反:
- D3: 互斥分发 (一次调用选 1 个 converter)
- D4: 聚合执行 (一次调用跑全部 check)

聚合模式的灵魂在 `_safe_run_one` 的 `try/except Exception` — 整个子系统
唯一一处宽泛异常捕获, 因为这是开闭原则下的扩展点, 调度层无法预知 check
会抛什么。

### 2. CheckResult 4 字段 + Severity 4 级

字段: `name / severity / summary / details`, 派生 `passed: bool`。

severity 四级 (PASS/INFO/WARNING/ERROR) 而不是两级 (passed: bool):
- 业务上"失败"分多种紧张度 — pair_existence 缺 0.1% 跟缺 60% 不该同级
- 跟 syslog / k8s events 的成熟习惯对齐, 接监控系统时不需要再翻译

### 3. DatasetSnapshot: 一次扫描多次复用

`build_snapshot(yaml_path, task_type)` 一次扫盘, 装进 frozen dataclass,
通过 `CheckContext.snapshot` 喂给所有 check。

三条铁律:
- **装事实, 不做判断**: snapshot 装数据, check 做判定
- **frozen=True + Tuple 容器**: 不可变, 防 check 串改
- **best-effort, 不抛异常**: yaml 解析失败装进 `yaml_load_error` 字段,
  由对应 check 报告 — 调度层永远不该自己 fail

附带"顺手统计" 3 个数字 per split (image_count / annotated_count /
total_instances) — I/O 密集型流程的免费收益, 但保持 snapshot 装事实的
边界, 不算"业务判断"。

### 4. 自动 import: 加新 check 不改框架代码

`_ensure_initialized` 用 `pkgutil.iter_modules` 自动扫 `checks/` 子包
下所有非下划线模块, 在 import time 触发 `@check` 装饰器副作用。

加新 check = 加新文件, **registry.py 一行不动**。同 pattern 同 Flask 路由
/ pytest 测试函数的自动发现。

### 5. ValidationReport(纯数据) + render.py(纯展示)分离

- `report.py`: ValidationReport dataclass + 派生属性 (overall_severity /
  exit_code / failed_results) + to_dict()
- `render.py`: `render_to_logger(report, logger)` 三段式输出
  (头 / 数据集摘要 / check 一览 / 失败详情 / 尾)

未来加 HTML / Markdown renderer = 新增 `render_to_xxx.py`, 数据层
一行不动。

**已知边界**: 未引入 `ReportSection` 中间抽象层。理由 — YAGNI: 当前只有
一种 renderer, 抽象层需要至少 2 个具体场景才能验证方向。 加 HTML 报告时
再做 refactor 引入。

### 6. 质检与修复在 SRP 层面分开

D4 **只检测, 不修复**。`CheckResult` 无 `fixable` 字段, CLI 无
`--fix` / `--apply` 选项。

理由:
- "质检工具的诚实在于它什么都不动 — 数据是不是被改了, 用户绝不该靠
  看日志推断。"
- 修复属于 data_pipeline 的下一次产线运行 (改完原始标注重跑 odp-transform),
  或独立的 odp-clean 工具
- 把"破坏性操作"作为质检副产品是常见的反模式 (eslint --fix 类工具不在
  CI 里默认开)

### 7. 不引入 DatasetValidator 类

`validate_dataset()` 是函数, 不是类。 内部状态 (run_id / duration /
snapshot / results) 全部进返回值 `ValidationReport`, 调用方一行拿:

```python
report = validate_dataset(yaml_path, task_type='detect')