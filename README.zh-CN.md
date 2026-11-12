<h1 align="center">YamlProperties</h1>

<p align="center">在 Notepad++ 中，一键转换 YAML 与 Properties。</p>

<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>

<p align="center">
  <a href="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml"><img src="https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml/badge.svg?branch=main" alt="Windows build and release checks"></a>
  <img src="https://img.shields.io/badge/Windows-x86%20%7C%20x64%20%7C%20ARM64-0078D4" alt="Windows x86、x64 与 ARM64">
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
- **支持特殊键名**：处理 `com.example`、中文、空格与转义字符。
- **本地运行**：原生 x86、x64 和 ARM64 插件，转换过程无需联网。

## 转换示例

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

反向转换时，默认按点号展开层级；`logging.level` 下保留完整日志名称，使 `com.example` 与 `com.example.dao.Mapper` 可以并存。Properties 中原本有引号的就保留为 YAML 引号，原本没有的也不添加，包括 `00123`、`true`、`off`。YAML 值原本带双引号，转为 Properties 后也保留，例如 `name: "demo"` → `name="demo"`。其中的 YAML 转义写法经过 Java Properties 转义后保留；跨行双引号值整理为带双引号的单行值。其他原始键名分组、注释与排版不保留。[查看转换规则 →](docs/USAGE.md#转换规则)

## 安装

支持 **32-Bit（x86）、64-Bit（x64）和 64-Bit ARM（ARM64）版 Notepad++**。插件必须匹配编辑器的架构，不能只根据 Windows 架构选择。

| Notepad++ 版本 | 手动安装包后缀 |
|---|---|
| 32-Bit | `-x86.zip` |
| 64-Bit | `-x64.zip` |
| 64-Bit ARM | `-arm64.zip` |

1. 从 [Releases](https://github.com/oiltea94/npp-yaml-properties/releases) 下载名称以 **`-x86.zip`、`-x64.zip` 或 `-arm64.zip`** 结尾的手动安装包。对应架构尚未发布时，可在 [Actions](https://github.com/oiltea94/npp-yaml-properties/actions/workflows/ci.yml) 成功运行的 **Artifacts** 中下载该架构的构建包，解压后找到该 ZIP。
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
| 转换时按键名排序 | 默认关闭；开启后两个转换方向均按每层键名升序排列，区分大小写，保留数组元素顺序和现有引号规则 |

两个选项都会在重启后保留。排序只在执行转换时生效，不在编辑或保存时触发。键名按 Unicode 字符顺序比较，不按拼音或自然数字排序（`key10` 排在 `key2` 前面）；数组下标仍按数值顺序。自动识别优先使用文件扩展名；遇到格式歧义时使用手动转换命令。

## 文档与参与

[使用指南](docs/USAGE.md) · [从源码构建](docs/DEVELOPMENT.md) · [发布指南](docs/RELEASING.md) · [更新记录](CHANGELOG.md)

欢迎提交 [Issue](https://github.com/oiltea94/npp-yaml-properties/issues) 或 Pull Request。报告转换问题时，请附上最小输入样例、预期结果和 Notepad++ 版本，并移除真实密码等配置值。

正式版本通过 GitHub Actions 自动构建和发布：推送版本标签后，完成 x86、x64、ARM64 编译及测试，再自动上传验证后的安装包到 GitHub Releases。详见[发布指南](docs/RELEASING.md)。

发布完成后，Actions 会更新尚未合并的官方目录 PR，或在上次 PR 合并后新建 PR。跨仓库提交需一次性配置仓库 Secret `NPP_PLUGIN_LIST_TOKEN`；配置与手动重试步骤见发布指南，最终仍需官方维护者审核。

---

[GPL-3.0-or-later](LICENSE) · [第三方许可](THIRD_PARTY.md)
