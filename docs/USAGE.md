# 使用指南

[返回首页](../README.md) · [从源码构建](DEVELOPMENT.md)

## 安装与升级

下载手动安装包（名称以 `-x64.zip` 结尾），关闭 Notepad++，解压并将 `YamlProperties` 文件夹复制到 Notepad++ 的 `plugins` 目录，再启动编辑器。

也可在解压目录运行安装脚本；目标位于 Program Files 时，使用管理员 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

脚本会备份已有的同名 DLL。需要回退时，先关闭 Notepad++，再使用同一份脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Restore
```

自定义安装目录时，两条命令均加 `-NotepadDir 'D:\Apps\Notepad++'`。首次安装的回退只移除本插件 DLL；升级回退则恢复原 DLL。保留安装包旁的 `.install-state.json` 和 `.backups` 目录。

GitHub Actions 的构建产物需要登录 GitHub 后下载。外层构建包中包含手动安装包、Plugins Admin 专用包和源码包；手动安装使用名称以 `-x64.zip` 结尾的 ZIP。Plugins Admin 专用包用于官方插件目录安装，相关流程见[发布指南](RELEASING.md)。

## 转换命令

在 **插件 → YamlProperties** 中选择：

| 命令 | 输入 → 输出 |
|---|---|
| YAML → Properties | YAML 映射 → Properties 键值对 |
| Properties → YAML | Properties 键值对 → YAML 映射 |
| 自动识别并转换 | 根据扩展名或内容选择方向 |

有单个连续选区时转换选区，否则转换当前文档。多选区和矩形选区会提示改为连续选区。

### 输出位置

**在新标签页打开转换结果** 默认开启，新标签页使用 UTF-8，源文档保持不变。

取消勾选后，结果替换当前选区或全文，不自动保存文件；按 **Ctrl+Z** 可一次撤销转换文本。选区外的内容保持不变，替换结果继续保持选中。全文转换会切换语法高亮，选区转换保留当前高亮；撤销文本不撤销高亮类型。

原位替换保持文档编码与换行符。只读文档、转换错误或原编码无法准确表示结果时，提示错误并保留原文，可改用新标签页输出。

### 自动识别

优先使用 `.yaml`、`.yml`、`.properties` 扩展名；没有这些扩展名时再判断内容：

- 无扩展名的 `key: value` 默认视为 YAML，`key=value` 视为 Properties。
- 冒号分隔的 Properties 可保存为 `.properties`，或使用手动命令消除歧义。
- 判断为 YAML 后若解析失败，会显示错误，不会悄悄换成 Properties 解析。
- 无扩展名的空白或纯注释文本，需要选择手动转换方向。

原位转换保留文件名。内容格式变化后，原扩展名可能不再匹配；再次转换时使用对应的手动命令，或另存为匹配的扩展名。

## 键名模式

默认使用点号和零基下标展开约定：

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

开启 **保留完整键名（不拆分点号和下标）** 后，`server.port`、`servers[0]` 都作为普通完整键名，输出扁平 YAML 映射。该模式下，YAML 输入也需为扁平标量映射。

YAML 中的 `com.his` 等带点键可以展开为 Properties。反向转换默认按点号展开层级；Properties 不记录点号原先属于键名还是层级，因此不保证恢复原来的键名分组。`off` 保留为字符串，不转换为布尔值。

## 转换规则

- **字符串值**：Properties 的值全部是字符串，YAML 输出明确加双引号，保留 `00123`、`true`、日期等文本，不自动猜类型。
- **文本与编码**：支持 UTF-8、中文、表情、`\uXXXX`、UTF-16 代理对、Java 转义、`=` / `:` / 空白分隔符、续行和 CR/LF/CRLF。
- **特殊键名**：支持点号、中文、空格、`:`、`=`、`#`、`!`、斜杠、反斜杠及 `name[prod]` 等文本方括号；需要转义的 Properties 字符自动转义。`a[0]` 等数字后缀仍表示数组。
- **结构与冲突**：YAML 根节点须为映射。重复键、父子路径冲突、展开后的同名键、稀疏数组、负数或非规范下标、空路径段会报错。
- **有损结构**：`null`、空嵌套映射和空数组会报错；显式空字符串 `""` 可以转换。
- **YAML 特性**：普通无循环别名展开为值；递归别名、多文档、合并键和自定义标签会报错。注释、排版、YAML 原始类型和锚点名称不保留。
- **Spring 配置**：使用常见的点号与下标约定，未实现 Spring 全部 relaxed binding、Map 键保留语法或 profile 合并行为。
- **处理上限**：输入 8 MiB、输出 16 MiB、深度 64、100,000 节点、数组最大下标 9,999。

新标签页输出使用 UTF-8，原位替换保持文档编码。Java 读取时使用匹配编码的 `Reader`；`Properties.load(InputStream)` 使用 ISO-8859-1，不适合直接读取 UTF-8 输出中的中文。

转换仅在本机内存中处理，插件没有联网功能。

## 配置保存

两个开关保存在 Notepad++ 插件配置目录的 `YamlProperties.ini`：

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `LiteralKeys` | `0` | `1` 保留完整键名；`0` 展开点号与数组下标 |
| `NewTab` | `1` | `1` 新标签页输出；`0` 原位替换 |

旧配置缺少 `NewTab` 时默认开启。设置保存失败时，当前选项保持不变。
