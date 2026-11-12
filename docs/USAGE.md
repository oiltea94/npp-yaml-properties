# 使用指南

[返回首页](../README.md) · [从源码构建](DEVELOPMENT.md)

## 界面语言

插件菜单、配置保存失败提示和“关于 / 转换规则”跟随 Notepad++ 的界面语言，不需要单独设置：

- 中文简体显示简体中文；台灣繁體、香港繁體显示繁体中文。
- English 显示英文；其他语言或未加载语言文件时回退英文。
- 在 Notepad++ 的首选项中切换语言后立即生效，无需重启，原有配置和勾选状态保持不变。

下文使用简体中文菜单名；例如英文界面的输出设置为 `Open conversion result in a new tab`，排序设置为 `Sort keys during conversion`。“关于”中列出的转换规则一致，转换核心的错误诊断目前仍使用英文。

## 安装与升级

下载手动安装包（按 Notepad++ 架构选择 `-x86.zip`、`-x64.zip` 或 `-arm64.zip`），关闭 Notepad++，解压并将 `YamlProperties` 文件夹复制到 Notepad++ 的 `plugins` 目录，再启动编辑器。

也可在解压目录运行安装脚本；目标位于 Program Files 时，使用管理员 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

脚本会核对 DLL 与 Notepad++ 的架构，并备份已有的同名 DLL。架构不匹配时，在修改安装目录前报错。需要回退时，先关闭 Notepad++，再使用同一份脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Restore
```

自定义安装目录时，两条命令均加 `-NotepadDir 'D:\Apps\Notepad++'`。首次安装的回退只移除本插件 DLL；升级回退则恢复原 DLL。保留安装包旁的 `.install-state.json` 和 `.backups` 目录。

GitHub Actions 的构建产物需要登录 GitHub 后下载。外层构建包中包含手动安装包、Plugins Admin 专用包和源码包；手动安装时，按 Notepad++ 架构选择 `-x86.zip`、`-x64.zip` 或 `-arm64.zip`。Plugins Admin 专用包用于官方插件目录安装，相关流程见[发布指南](RELEASING.md)。

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

空文档或仅包含空格、制表符、换行的选区会提示“没有可转换的文本”，不新建结果标签页、不替换原文。手动和自动转换、两种输出方式均适用；`key=` 这种有键但值为空的内容仍正常转换。

优先使用 `.yaml`、`.yml`、`.properties` 扩展名；没有这些扩展名时再判断内容：

- 无扩展名的 `key: value` 默认视为 YAML，`key=value` 视为 Properties。
- 冒号分隔的 Properties 可保存为 `.properties`，或使用手动命令消除歧义。
- 判断为 YAML 后若解析失败，会显示错误，不会悄悄换成 Properties 解析。
- 无扩展名的纯注释文本，需要选择手动转换方向。

原位转换保留文件名。内容格式变化后，原扩展名可能不再匹配；再次转换时使用对应的手动命令，或另存为匹配的扩展名。

## 键名展开规则

统一使用点号和零基下标展开约定：

```properties
server.port=8080
servers[0]=localhost
servers[1]=example.com
code=00123
```

转换为：

```yaml
server:
  port: 8080
servers:
  - localhost
  - example.com
code: 00123
```

YAML 中的 `com.example` 等带点键可以展开为 Properties。反向转换默认按点号展开层级；Properties 不记录点号原先属于键名还是层级，因此不保证恢复原来的键名分组。引号默认遵循输入写法，例如 `off` 输出为 `off`，`"off"` 输出为 `"off"`。

`logging.level.` 是特例：该前缀后面的完整包名或类名作为一个键，保留大小写和点号，允许父包和具体类分别配置日志级别。例如：

```properties
logging.level.com.example=debug
logging.level.com.example.dao.Mapper=off
```

转换为：

```yaml
logging:
  level:
    com.example: debug
    com.example.dao.Mapper: off
```

其他配置继续展开层级和数组。`a=1` 与 `a.b=2` 等普通父子冲突仍报错；`logging.level=info` 与具体日志名称同时出现也会报错。

## 引号规则

Properties 原本带单引号或双引号，输出就保留；原本没有引号，输出也不添加。数字、布尔值、日期及空值同样遵循输入写法，不做自动补引号处理。

例如 `name=demo`、`profile=${profileActive}`、`code=00123` 输出：

```yaml
name: demo
profile: ${profileActive}
code: 00123
```

保留原有引号的例子：

```properties
name="demo"
profile='${profileActive}'
logging.pattern.file="%d{HH:mm:ss} %m%n"
```

输出：

```yaml
name: "demo"
profile: '${profileActive}'
logging:
  pattern:
    file: "%d{HH:mm:ss} %m%n"
```

转换直接写出 Properties 解析后的键和值，不额外校验或修复其 YAML 标量语法。已有引号作为 YAML 语法使用；未加引号的数字、布尔值、空值、注释符号等由 YAML 读取器解释，因此不保证字符串类型或往返值完全不变。Java Properties 转义和续行仍按原规则解析。

该规则固定适用于手动和自动转换及两种输出位置，无需配置。命令行使用 `ypconvert to-yaml`。

YAML → Properties 也保留值原有的双引号。例如：

```yaml
name: "demo"
profile: "${profileActive}"
code: "00123"
plain: demo
text: "line\nnext"
```

输出：

```properties
name="demo"
profile="${profileActive}"
code="00123"
plain=demo
text="line\\nnext"
```

双引号值中的 YAML 转义写法会保留，反斜杠按 Java Properties 规则再转义一次，因此再转回 YAML 时仍是原来的引号和转义，不会重复包裹。跨行双引号值按照 YAML 的折行规则解析后，整理为带双引号的单行值。锚点、标签与别名不影响双引号保留。此规则只保留值的双引号语法；YAML 单引号值、块文本和键名仍按原规则取解析后的文本。命令行使用 `ypconvert to-properties`。

## 转换规则

- **引号**：按输入保留已有引号，不添加新引号。点号层级与数组下标始终展开，`logging.level` 下保留完整日志名称。
- **值的类型**：保留源文本写法，由 YAML 读取器判断类型。
- **文本与编码**：支持 UTF-8、中文、表情、`\uXXXX`、UTF-16 代理对、Java 转义、`=` / `:` / 空白分隔符、续行和 CR/LF/CRLF。
- **特殊键名**：支持点号、中文、空格、`:`、`=`、`#`、`!`、斜杠、反斜杠及 `name[prod]` 等文本方括号；需要转义的 Properties 字符自动转义。`a[0]` 等数字后缀仍表示数组。
- **结构与冲突**：YAML 根节点须为映射。重复键、父子路径冲突、展开后的同名键、稀疏数组、负数或非规范下标、空路径段会报错。
- **有损结构**：YAML → Properties 遇到 `null`、空嵌套映射和空数组会报错；显式空字符串 `""` 可以转换。
- **YAML 特性**：普通无循环别名展开为值；递归别名、多文档、合并键和自定义标签会报错。注释、排版、YAML 原始类型和锚点名称不保留。
- **Spring 配置**：使用常见的点号与下标约定，未实现 Spring 全部 relaxed binding、Map 键保留语法或 profile 合并行为。
- **处理上限**：输入 8 MiB、输出 16 MiB、深度 64、100,000 节点、数组最大下标 9,999。

新标签页输出使用 UTF-8，原位替换保持文档编码。Java 读取时使用匹配编码的 `Reader`；`Properties.load(InputStream)` 使用 ISO-8859-1，不适合直接读取 UTF-8 输出中的中文。

转换仅在本机内存中处理，插件没有联网功能。

## 可选自动排序

勾选 **插件 → YamlProperties → 转换时按键名排序** 即可开启，默认关闭，重启后记忆设置。

- 在手动或自动转换时生效，YAML → Properties、Properties → YAML 均适用；编辑和保存时不触发。
- 对每层映射的键分别升序排列，保留层级分组；不是对最终 Properties 全文按行排序。
- 区分大小写，按 Unicode 字符顺序比较，不按拼音；普通键名中 `key10` 排在 `key2` 前面。
- 数组元素位置不变，下标维持 `[0]`、`[1]`、`[2]`…的数值顺序。数组中对象的成员键可以排序。
- 值、引号和转义沿用现有转换规则。关闭后恢复原来的键顺序处理。

例如开启后，`server.port=8080`、`spring.profiles.active="${profileActive}"`、`server.address=localhost` 输出为：

```yaml
server:
  address: localhost
  port: 8080
spring:
  profiles:
    active: "${profileActive}"
```

该设置适用于插件；命令行保持默认不排序。

## 配置保存

输出位置和排序开关保存在 Notepad++ 插件配置目录的 `YamlProperties.ini`：

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `NewTab` | `1` | `1` 新标签页输出；`0` 原位替换 |
| `SortKeys` | `0` | `1` 转换时按每层键名升序排序；`0` 保持原有键顺序处理 |

旧配置缺少 `NewTab` 时默认开启，缺少 `SortKeys` 时默认关闭。旧版引号和完整键名设置不再读取，保存设置时会移除。两个开关同时原子保存；保存失败时，当前选项和菜单勾选状态保持不变。
