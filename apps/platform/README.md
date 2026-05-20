dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

# Entry-point Scripts (PEP 621 标准字段，与backerd无关)

[project.scripts]
odp-init = "odp_platform.cli.init_project:initialize_project"

# Hatching 配置（告诉它两件事： 包源码在哪、版本号从那读）

# 告诉 hatching 包源码在 src/odp_platform/
# (相当于 setuptools 那一整套 package-dir + packages.find 的简化版)
[tool.hatch.build.targets.sheel]
package = ["src/odp_platform"]

# 动态版本号： 从 src/odp_platform/_version.py 的 _version_