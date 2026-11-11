<h1 align="center">YamlProperties</h1>

<p align="center">Convert between YAML and Properties in Notepad++ with one click.</p>

<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>

<p align="center">
  <a href="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml"><img src="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml/badge.svg?branch=main" alt="Windows build and release checks"></a>
  <img src="https://img.shields.io/badge/Windows-x64-0078D4" alt="Windows x64">
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
- **Run locally**: a native x64 plugin; conversion requires no network connection.

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

When converting back, dots expand into nested keys by default, and values are emitted as quoted strings. Original key grouping, comments, and formatting are not preserved. [Conversion rules (中文) →](docs/USAGE.md#转换规则)

## Installation

Requires **Windows and the x64 edition of Notepad++**.

1. Download the manual installation package ending in **`-x64.zip`** from [Releases](https://github.com/oiltea94/npp-yaml-properties/releases). If no release is available yet, download the build artifact from a successful [Actions](https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml) run and extract it to find the ZIP.
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

The conversion options currently use Chinese menu labels:

| Menu option | Behavior |
|---|---|
| 在新标签页打开转换结果 (open results in a new tab) | Enabled by default. Disable it to replace text in place; press **Ctrl+Z** to undo the converted text in one step. |
| 保留完整键名 (preserve full keys) | Disabled by default. Enable it to treat keys such as `server.port` as a single key, useful for flat configurations. |

Both options persist across restarts. Automatic detection prioritizes the file extension; use an explicit conversion command when the format is ambiguous.

## Documentation and contributing

The detailed guides below are in Chinese:

[User guide](docs/USAGE.md) · [Build from source](docs/DEVELOPMENT.md) · [Release guide](docs/RELEASING.md) · [Changelog (English)](CHANGELOG.md)

[Issues](https://github.com/oiltea94/npp-yaml-properties/issues) and pull requests are welcome. When reporting a conversion problem, include a minimal input sample, the expected result, and your Notepad++ version. Remove real passwords and other sensitive configuration values from samples.

---

[GPL-3.0-or-later](LICENSE) · [Third-party licenses](THIRD_PARTY.md)
