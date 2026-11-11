# 从源码构建

[返回首页](../README.md) · [使用指南](USAGE.md) · [发布指南](RELEASING.md)

## 环境

- Windows x64 或 ARM64、Python 3.11+。x64 工具链可交叉编译三种架构；ARM64 测试需要 ARM64 Windows。
- LLVM-MinGW 编译器由 `bootstrap.py` 按固定版本下载并校验，保存在项目 `.tools/` 中，不修改系统 PATH。
- 依赖源码已固定在 `vendor/`。Java 兼容性测试额外需要 JDK 17+，CI 使用 JDK 21。
- 真实编辑器和安装测试需对应架构的 Notepad++。`tests/download_npp.py` 下载并校验固定版本的便携包；也可用 `NPP_TEST_DIR` 指定目录。

运行编译后的插件无需 Python 或 Java，使用 Windows 系统 UCRT。

## 编译

在仓库根目录执行：

```powershell
python bootstrap.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

默认构建 x64，会运行核心测试，并生成 `dist/YamlProperties/YamlProperties.dll` 和 `build/ypconvert.exe`。`VERSION` 是关于窗口、DLL 版本资源和发布 manifest 的统一版本来源。

其他目标及交叉编译：

```powershell
.\build.ps1 -Architecture x86
.\build.ps1 -Architecture arm64 -CompileOnly
```

`-CompileOnly` 只编译目标测试而不运行，不代表测试通过。ARM64 Windows 上省略此开关执行测试。x64 产物保留在 `build/`、`dist/`；x86 和 ARM64 分别位于 `build/x86`、`dist/x86` 以及 `build/arm64`、`dist/arm64`。

## 验证与打包

```powershell
$env:YP_ARCH = 'x86' # x86 / x64 / arm64，默认 x64
python tests\download_npp.py
$env:NPP_TEST_DIR = (Resolve-Path '.runtime/x86/npp-source').Path # x64 使用 .runtime/npp-source
python tests\smoke_plugin.py
python tests\java_compat.py
python tests\installer_test.py
python tests\limits_test.py
python tests\plugin_list_test.py
python package_release.py
python tests\release_test.py
```

真实编辑器测试在 `.runtime/` 创建独立 Notepad++ 副本，验证菜单、选区、原位替换、撤销和配置记忆，结束时关闭测试进程。安装回退也使用隔离目录，不修改已有编辑器安装。

本地验证记录写入 `evidence/`，不提交到 Git。CI 自动执行编译、核心测试、Java 比对、资源边界、元数据和发布包检查，并上传产物及验证记录；三种架构都运行真实编辑器和安装器测试；ARM64 使用 windows-11-arm 原生 Windows runner。

打包产物和官方插件目录提交要求见[发布指南](RELEASING.md)。

## 命令行转换

在 Windows 命令提示符（cmd.exe）中执行：

```cmd
build\ypconvert.exe to-properties < application.yaml > application.properties
build\ypconvert.exe to-yaml < application.properties > application.yaml
build\ypconvert.exe to-yaml --literal < flat.properties > flat.yaml
```

## 代码导航

| 路径 | 内容 |
|---|---|
| `src/converter.cpp` | YAML / Properties 解析、转换与格式识别 |
| `src/plugin.cpp` | Notepad++ 菜单、选区、输出与配置 |
| `src/plugin.rc` | Windows DLL 版本资源 |
| `tests/` | 核心、兼容性、编辑器、安装和发布检查 |
| `scripts/plugin_list_entry.py` | 官方插件目录条目生成工具 |
| `SPEC.md` | 行为约定与验收范围 |

## 贡献

欢迎提交 Issue 或 Pull Request。行为变更请附带可复现输入、预期输出与针对性的测试；文档改动检查相对链接和示例即可。

生成目录、日志、编译器和本机备份无需提交。涉及转换规则或菜单变化时，同步更新[使用指南](USAGE.md)与 `CHANGELOG.md`。
