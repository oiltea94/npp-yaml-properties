<h1 align="center">YamlProperties</h1>

<p align="center">在 Notepad++ 中，一键转换 YAML 与 Properties。</p>

<p align="center">
  <a href="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml"><img src="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml/badge.svg?branch=main" alt="Windows build and release checks"></a>
  <img src="https://img.shields.io/badge/Windows-x64-0078D4" alt="Windows x64">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue" alt="GPL-3.0-or-later"></a>
</p>

<p align="center">
  <a href="#安装">安装</a> ·
  <a href="#使用">使用</a> ·
  <a href="docs/USAGE.md">使用指南</a> ·
  <a href="https://github.com/oiltea94/npp-yaml-properties/issues">问题反馈</a>
</p>

- **双向转换**：YAML ↔ Properties，也可自动识别格式。
- **按需转换**：处理选区或全文，结果可新开标签页或原位替换。
- **支持特殊键名**：处理 `com.his`、中文、空格与转义字符。
- **本地运行**：原生 x64 插件，转换过程无需联网。

## 转换示例

**YAML → Properties**

```yaml
server:
  port: 8080
logging:
  level:
    com.his: off
```

```properties
server.port=8080
logging.level.com.his=off
```

反向转换时，默认按点号展开层级，值输出为带引号的字符串；原始键名分组、注释与排版不保留。[查看转换规则 →](docs/USAGE.md#转换规则)

## 安装

需要 **Windows 和 x64 版 Notepad++**。

1. 从 [Releases](https://github.com/oiltea94/npp-yaml-properties/releases) 下载名称以 **`-x64.zip`** 结尾的手动安装包。尚无发行版时，可在 [Actions](https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml) 成功运行的 **Artifacts** 中下载构建包，解压后找到该 ZIP。
2. 关闭 Notepad++，解压安装包，将 `YamlProperties` 文件夹复制到 Notepad++ 的 `plugins` 目录。
3. 重启 Notepad++，在 **插件 → YamlProperties** 中使用。

安装后的 DLL 路径：

```text
Notepad++/plugins/YamlProperties/YamlProperties.dll
```

[脚本安装、升级与回退 →](docs/USAGE.md#安装与升级)

## 使用

打开配置文件，选择 **插件 → YamlProperties → 自动识别并转换**，或手动选择 **YAML → Properties / Properties → YAML**。

有选区时只转换选区，否则转换全文。默认在新标签页打开结果，原文保留。

| 菜单选项 | 作用 |
|---|---|
| 在新标签页打开转换结果 | 默认开启；关闭后原位替换，按 **Ctrl+Z** 可一次撤销转换文本 |
| 保留完整键名 | 默认关闭；开启后将 `server.port` 等键名作为整体，适用于扁平配置 |

两个选项都会在重启后保留。自动识别优先使用文件扩展名；遇到格式歧义时使用手动转换命令。

## 文档与参与

[使用指南](docs/USAGE.md) · [从源码构建](docs/DEVELOPMENT.md) · [发布指南](docs/RELEASING.md) · [更新记录](CHANGELOG.md)

欢迎提交 [Issue](https://github.com/oiltea94/npp-yaml-properties/issues) 或 Pull Request。报告转换问题时，请附上最小输入样例、预期结果和 Notepad++ 版本，并移除真实密码等配置值。

---

[GPL-3.0-or-later](LICENSE) · [第三方许可](THIRD_PARTY.md)
