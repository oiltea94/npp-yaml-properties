# YamlProperties

Notepad++ 的 YAML ↔ Properties 双向转换插件，Windows x64，当前准备版本 0.3.1。

A native Notepad++ plugin for bidirectional YAML ↔ Java Properties conversion, with automatic format detection and configurable new-tab or in-place output.

GitHub 首次提交、Release 附件、官方 Plugins Admin 收录流程见 [发布指南](docs/RELEASING.md)。版本变更见 [CHANGELOG.md](CHANGELOG.md)。

## 使用

1. 解压发布包，将 `YamlProperties` 文件夹复制到 Notepad++ 的 `plugins` 目录。最终路径应为 `plugins\YamlProperties\YamlProperties.dll`。
2. 重启 Notepad++，打开 **插件 → YamlProperties**。
3. 选择 **YAML → Properties** 或 **Properties → YAML**。有单个连续选区时转换选区，否则转换当前文档；默认将结果放到新标签页，原文保留。
4. **保留完整键名（不拆分点号和下标）** 是可记忆的开关，默认关闭。
5. 也可以选择 **自动识别并转换**，由插件判断转换方向；手动转换入口继续保留。
6. **在新标签页打开转换结果** 默认勾选，取消勾选后在当前标签页替换选区或全文。两个手动命令和自动转换均遵循此设置，重启后仍记忆。

原位替换只修改编辑器中的内容，不自动保存文件；按 **Ctrl+Z** 可一次撤销转换文本。选区外的内容保持不变，结果继续保持选中；全文转换时切换语法高亮，选区转换时保留当前高亮。保持原编码和换行符；只读文档、转换错误或原编码无法准确表示结果时提示错误并保留原文，此时可改用新标签页输出。

两个开关保存在 Notepad++ 插件配置目录的 `YamlProperties.ini` 中，分别为 `LiteralKeys` 和 `NewTab`（`1` 为开启，`0` 为关闭）。旧配置缺少 `NewTab` 时默认开启。

自动识别先使用 `.yaml` / `.yml` / `.properties` 扩展名；没有这些扩展名时根据内容判断。无扩展名的 `key: value` 默认按 YAML 处理，`key=value` 按 Properties 处理。冒号分隔的 Properties 如需消除歧义，可保存为 `.properties`，或使用手动入口。判断为 YAML 后如果解析失败会显示错误，不会改按 Properties 转换；无扩展名的空白/纯注释文本提示选择方向。

原位替换保留文件名。若转换后内容格式与原扩展名不同，再次转换可使用对应的手动命令，或先另存为匹配的扩展名。

也可运行安装脚本；安装到 Program Files 时需要在管理员 PowerShell 中执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

安装脚本会备份已有的同名 DLL，记录安装后的 SHA-256。使用同一份脚本撤销安装：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Restore
```

自定义安装目录时，两条命令均加 `-NotepadDir 'D:\Apps\Notepad++'`。恢复前关闭已加载插件的 Notepad++。首次安装的撤销操作只移除本插件 DLL；升级安装则恢复备份 DLL。保留安装包旁的 `.install-state.json` 和 `.backups` 目录。

## 两种键名模式

默认使用 Spring Boot 风格的点号和下标展开约定：

```properties
server.port=8080
servers[0]=localhost
servers[1]=example.com
code=00123
```

转换为：

```yaml
"server":
  "port": "8080"
"servers":
  - "localhost"
  - "example.com"
"code": "00123"
```

启用“保留完整键名”后，`server.port` 和 `servers[0]` 都作为完整的普通键名，YAML 输出为扁平映射。该模式的 YAML 输入也需要是扁平标量映射。

默认模式也支持 YAML 内的带点键，例如：

```yaml
logging:
  level:
    com.his: off
    com.emr: debug
```

转换为：

```properties
logging.level.com.his=off
logging.level.com.emr=debug
```

`off` 保留原始字符串，不转换为布尔值。反向转换时，默认会按点号展开层级；Properties 文本本身没有记录原始点号属于键名还是层级，因此不保证恢复 `com.his` 原先的分组方式。

## 转换边界

- Properties 的值全部是字符串，YAML 输出明确加双引号，保留 `00123`、`true`、日期等原始文本；不自动猜类型。
- 注释、缩进样式、引号样式、YAML 原始类型和锚点名称不还原。普通无循环别名展开成值。含敏感值的配置仅在本机内存中处理，插件没有联网功能。
- 支持 UTF-8、中文、表情、`\uXXXX`、UTF-16 代理对、Java 转义、`=` / `:` / 空白分隔符、续行和 CR/LF/CRLF。
- 新标签页输出 Properties 使用 UTF-8 字符，原位替换保持文档原编码。Java 读取请使用匹配编码的 `Reader`；旧式 `Properties.load(InputStream)` 按 ISO-8859-1 读取，不适合直接读取 UTF-8 输出中的中文。
- 重复键、父子路径冲突、稀疏数组、无效 Unicode、递归别名、多文档 YAML、合并键和自定义 YAML 标签会报错。
- YAML 根节点须为映射；`null`、空嵌套映射和空数组会报错，因为转换成普通字符串键值对会丢失信息。显式空字符串 `""` 可以转换。
- 支持点号键、中文键、空格、`:`、`=`、`#`、`!`、斜杠、反斜杠及普通文本方括号（如 `name[prod]`）；Properties 中需要转义的字符自动转义。`a[0]` 这样的数字后缀仍表示数组；负数、非规范数字下标和空路径段会报错。不同 YAML 路径若展开成同一个 Properties 键，会报错而不是覆盖。插件未实现 Spring 的全部 relaxed binding、Map 键保留语法或 profile 合并行为。
- 最大输入 8 MiB，最大输出 16 MiB，最大深度 64，最多 100,000 节点，数组最大下标 9,999。暂只提供 x64 构建。

## 构建与验证

Python 3.11+、Git（仅管理源码）以及项目内的 LLVM-MinGW 工具链；运行插件不需要 Python、Java 或额外安装 C++ 运行库，使用 Windows 系统 UCRT。依赖源码已固定在 `vendor/`。

```powershell
python bootstrap.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
python tests\smoke_plugin.py
python tests\java_compat.py
python tests\installer_test.py
python tests\limits_test.py
python tests\plugin_list_test.py
python package_release.py
python tests\release_test.py
```

`bootstrap.py` 仅将编译器下载到 `.tools/`，不修改 PATH。`build.ps1` 编译转换核心、执行语义测试、从 `VERSION` 生成 DLL 版本信息，并记录导出表和依赖。`smoke_plugin.py` 在 `.runtime/` 创建本机 Notepad++ 的独立副本，验证真实菜单操作，结束时关闭该测试进程。验证记录位于本地 `evidence/`，不提交到 Git 或源码发布包。

Java 兼容性检查额外需要 JDK 17+。验证基线包含 53 项核心测试、240 组 Java 比对、27 项真实编辑器检查、5 项安装/恢复检查和 7 项资源边界检查；发布准备另增加元数据与压缩包检查。真实编辑器验证使用 Notepad++ 8.9.6.4 x64。运行后结果写入本地 `evidence/`，GitHub CI 的记录作为 Actions 附件保存。

可执行的命令行转换器同时输出到 `build\ypconvert.exe`：

```cmd
build\ypconvert.exe to-properties < application.yaml > application.properties
build\ypconvert.exe to-yaml < application.properties > application.yaml
build\ypconvert.exe to-yaml --literal < flat.properties > flat.yaml
```

## 项目文件与撤销

本项目从空目录新建，转换核心在 `src/converter.cpp`，编辑器适配在 `src/plugin.cpp`，安装/恢复脚本在 `install.ps1`。构建和独立副本验证不会修改现有 Notepad++ 安装。停止测试进程后，可整体移除本项目目录以撤销工作区新增内容；若曾执行安装脚本，先按上面的 `-Restore` 命令恢复。

## 许可

本插件采用 GPL-3.0-or-later，与使用的 Notepad++ SDK 许可一致。yaml-cpp 为 MIT；Scintilla 头文件采用其原许可。参见 `LICENSE` 和 `THIRD_PARTY.md`。
