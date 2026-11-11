<h1 align="center">YamlProperties</h1>

<p align="center">Convert between YAML and Properties in Notepad++ with one click.</p>

<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>

<p align="center">
  <a href="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml"><img src="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml/badge.svg?branch=main" alt="Windows build and release checks"></a>
  <img src="https://img.shields.io/badge/Windows-x86%20%7C%20x64%20%7C%20ARM64-0078D4" alt="Windows x86, x64 and ARM64">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue" alt="GPL-3.0-or-later"></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#usage">Usage</a> ·
  <a href="docs/USAGE.md">User guide (中文)</a> ·
  <a href="https://github.com/oiltea94/npp-yaml-properties/issues">Report an issue</a>
</p>

- **Convert both ways**: YAML ↔ Properties, with optional automatic format detection.
- **Choose what to convert**: process a selection or the entire document, and open the result in a new tab or replace the original text.
- **Handle special keys**: supports keys such as `com.example`, Chinese characters, spaces, and escape sequences.
- **Run locally**: native x86, x64 and ARM64 plugins; conversion requires no network connection.

## Example

**YAML → Properties**

```yaml
server:
  port: 8080
logging:
  level:
    com.example: off
```

```properties
server.port=8080
logging.level.com.example=off
```

When converting back, dots expand into nested keys by default, except that logger names beneath `logging.level` remain complete keys (for example, `com.example` and `com.example.dao.Mapper` can coexist). Existing quotes in Properties are retained as YAML syntax and no new quotes are added, including for `00123`, `true`, or `off`. YAML double-quoted values also keep their quotes in Properties: `name: "demo"` becomes `name="demo"`. YAML escape spellings are retained with Java Properties escaping; multiline double-quoted values become a quoted single line. Other original key grouping, comments, and formatting are not preserved. [Conversion rules (中文) →](docs/USAGE.md#转换规则)

## Installation

Supports **32-Bit (x86), 64-Bit (x64), and 64-Bit ARM (ARM64) Notepad++**. Match the plugin to the architecture of Notepad++, not just Windows.

| Notepad++ edition | Manual package suffix |
|---|---|
| 32-Bit | `-x86.zip` |
| 64-Bit | `-x64.zip` |
| 64-Bit ARM | `-arm64.zip` |

1. Download the manual installation package ending in **`-x86.zip`, `-x64.zip`, or `-arm64.zip`** for your Notepad++ edition from [Releases](https://github.com/oiltea94/npp-yaml-properties/releases). If your architecture is not in a published release yet, download its build artifact from a successful [Actions](https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml) run and extract it to find the ZIP.
2. Close Notepad++, extract the package, and copy the `YamlProperties` folder into Notepad++'s `plugins` directory.
3. Restart Notepad++ and open **Plugins → YamlProperties**.

The installed DLL should be at:

```text
Notepad++/plugins/YamlProperties/YamlProperties.dll
```

[Scripted installation, upgrades, and rollback (中文) →](docs/USAGE.md#安装与升级)

## Usage

Open a configuration file and select **Plugins → YamlProperties → 自动识别并转换** (automatically detect and convert), or choose **YAML → Properties / Properties → YAML** explicitly.

If text is selected, only that selection is converted; otherwise, the whole document is converted. By default, the result opens in a new tab and the original text is preserved.

The output option uses a Chinese menu label:

| Menu option | Behavior |
|---|---|
| 在新标签页打开转换结果 (open results in a new tab) | Enabled by default. Disable it to replace text in place; press **Ctrl+Z** to undo the converted text in one step. |

The output preference persists across restarts. Automatic detection prioritizes the file extension; use an explicit conversion command when the format is ambiguous.

## Documentation and contributing

The detailed guides below are in Chinese:

[User guide](docs/USAGE.md) · [Build from source](docs/DEVELOPMENT.md) · [Release guide](docs/RELEASING.md) · [Changelog (English)](CHANGELOG.md)

[Issues](https://github.com/oiltea94/npp-yaml-properties/issues) and pull requests are welcome. When reporting a conversion problem, include a minimal input sample, the expected result, and your Notepad++ version. Remove real passwords and other sensitive configuration values from samples.

---

[GPL-3.0-or-later](LICENSE) · [Third-party licenses](THIRD_PARTY.md)
