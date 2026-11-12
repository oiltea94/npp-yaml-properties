# GitHub 与 Notepad++ 官方插件目录发布

本项目发布版本由根目录 `VERSION` 文件指定，提供 Windows x86、x64、ARM64 构建。项目仓库为 [oiltea94/npp-yaml-properties](https://github.com/oiltea94/npp-yaml-properties)。正式 Release 与官方插件目录收录按下文流程完成；作者署名由维护者在生成目录条目时填写。

## 1. 哪些内容提交到 GitHub

建议以当前目录作为仓库根目录，不必再套一层同名目录：

```text
YamlProperties/
├── .github/workflows/ci.yml   # Windows 三架构编译、测试、打包；版本标签自动发布
├── docs/RELEASING.md          # 本文
├── scripts/                  # 官方插件目录条目生成工具
├── src/                      # 转换核心、编辑器适配、DLL 版本资源
├── tests/                    # 核心、真实编辑器、Java、发布产物验证
├── vendor/                   # 固定版本依赖和许可证
├── VERSION                   # 唯一的程序版本来源
├── CHANGELOG.md
├── README.md
├── SPEC.md
├── LICENSE
├── THIRD_PARTY.md
├── .gitignore
├── .gitattributes
├── bootstrap.py
├── build.ps1
├── build.py
├── install.ps1
└── package_release.py
```

以下内容保留本地，由 `.gitignore` 排除：`.tools/`（编译器）、`build/`、`dist/`、`.runtime/`（测试编辑器与配置）、`.backups/`、`evidence/`（可能含本机绝对路径的日志）、Python 缓存和安装状态。**发布 ZIP 上传到 GitHub Releases，不提交到 Git 源码树。**

第三方 `vendor/` 暂保留原始源码和许可证，使克隆后可直接构建。日后若改为依赖下载，需同步加入固定版本、完整性校验和离线说明；当前无需为缩减目录而删除依赖文件。

`evidence/` 原先已有文件进入暂存区，仅增加 ignore 规则不会取消跟踪。本次整理已将该目录从索引移出，磁盘日志仍保留；Git 索引在本地备份中。其余源码暂存内容未自动更新，首次提交前执行 `git add .`。

## 2. 创建并首次提交 GitHub 仓库

在 GitHub 创建 **Public** 仓库（可命名 `YamlProperties`），不要再自动初始化 README、License 或 `.gitignore`。在本项目根目录打开 PowerShell：

```powershell
$repository = Read-Host '输入刚创建的 GitHub 仓库 HTTPS 地址'
git add .
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add native YAML and Properties converter for Notepad++"
git remote add origin $repository
git push -u origin main
```

以上命令适用于新建仓库。本项目分支为 `main`，`origin` 已指向 `oiltea94/npp-yaml-properties`；已有远程地址时跳过 `git remote add`，需要更换地址则使用 `git remote set-url origin $repository`。后续提交沿用 `git add`、`git commit` 和 `git push`。提交前检查暂存列表中没有本机运行环境、备份、日志或发布 ZIP。

## 3. GitHub Actions 自动发布

正式发布由 `.github/workflows/ci.yml` 完成，本机无需编译或上传 ZIP。

1. 修改 `VERSION`，在 `CHANGELOG.md` 中添加对应版本的非空发布记录（例如 `## 0.4.1 — 2026-11-12`），提交并推送到 `main`。
2. 确认该版本还未发布，创建并推送与 `VERSION` 一致的标签：

   ```powershell
   $releaseVersion = (Get-Content VERSION -Raw).Trim()
   git tag -a "v$releaseVersion" -m "Release v$releaseVersion"
   git push origin "v$releaseVersion"
   ```

3. Actions 分别在 Windows x86、x64、原生 ARM64 环境编译、测试和打包。全部通过后，汇总并核验 10 个附件，读取该版本的更新记录，自动创建公开的 GitHub Release。

普通分支推送、PR 和界面上的 **Run workflow** 只验证并保存附件，不公开发布。发布需要推送新的 `v*` 标签；已存在的版本不会覆盖。重试失败的发布时，先检查是否留下了 Release 草稿并核对其附件，再决定后续处理；不要替换已经公开的版本附件。

发布任务使用 GitHub 自动提供的 `GITHUB_TOKEN`，只给该任务 `contents: write` 权限，无需配置个人访问令牌。任一构建或汇总检查失败，发布任务就不会执行。在 Actions 下载 `release-assets` 可查看准备发布的附件，`release-notes` 保存发布说明。

### 自动提交官方目录 PR（一次性配置）

Release 成功发布后，工作流自动调用 `.github/workflows/catalog.yml`，下载公开的三架构 Plugins Admin 包及校验文件，核对 ZIP/DLL 哈希、DLL 架构、目录格式，然后更新 `oiltea94/nppPluginList` 分支并向 `notepad-plus-plus/nppPluginList` 提交 PR。

- 当前有未合并的 YamlProperties PR：更新原分支和 PR，兼容现有 `add-yamlproperties-x64` 分支。
- 上次 PR 已合并或关闭：创建 `yamlproperties-v版本号` 分支和新 PR。
- 官方目录已与该版本一致：不重复创建 PR。
- 旧版本重试不会覆盖目录或未合并 PR 中的新版本；已发布版本的 ZIP 哈希发生变化也会停止。

**跨仓库提交需额外配置 Secret；发布当前仓库的 Release 仍使用内置令牌。**

1. 使用 `oiltea94` 账号创建 GitHub **Personal access token (classic)**，权限选择 `public_repo`，设置合适的有效期。该令牌用于推送公开的 fork 并向官方公开仓库创建或更新 PR。
2. 打开本项目 GitHub 的 **Settings → Secrets and variables → Actions → New repository secret**。
3. 名称填写 **`NPP_PLUGIN_LIST_TOKEN`**，值填写该令牌。不要把令牌写进源码、PR、Issue 或聊天。

也可以在本机终端执行下面的命令，按提示输入令牌：

```powershell
gh secret set NPP_PLUGIN_LIST_TOKEN --repo oiltea94/npp-yaml-properties
```

未配置 Secret 时，Release 仍然发布成功，后续目录任务会明确报错。配置完成后，进入 **Actions → Submit official plugin catalog PR → Run workflow**，填写已发布的标签并取消勾选 **dry_run**，即可补交官方 PR，无需重新打包或发布。保留 **dry_run** 勾选则只验证和生成提案，不修改任何 GitHub 分支或 PR；提案保存在 `official-catalog-proposal` 附件中。

PR 仍由官方维护者审核，自动提交不会自动合并。自动化也不替代 Plugins Admin 的搜索、安装、卸载、更新识别测试；PR 中会保留这一验证范围说明。最低实测 Notepad++ 文件版本当前为 `8.9.6.4`，更换测试宿主后需同步检查脚本中的兼容性设置。

下面的命令用于本地开发和排障，日常发布无需在本机重复执行：

```powershell
python bootstrap.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
python tests\java_compat.py
python tests\limits_test.py
python tests\plugin_list_test.py
python tests\smoke_plugin.py
python tests\installer_test.py
python package_release.py
python tests\release_test.py
```

真实编辑器和安装器测试通过 `NPP_TEST_DIR` 选择测试宿主，在项目 `.runtime/` 内运行独立副本。GitHub CI 按 x86 / x64 / ARM64 分别下载对应架构的固定版 Notepad++，执行编译、核心测试、Java 比对、资源边界、真实编辑器、安装回退和打包验证。ARM64 使用原生 Windows ARM runner。工作流已写好，本地执行相关命令通过不等于 GitHub 托管运行已通过；首次推送后查看 Actions 结果。

产物用途：

| 文件 | 用途 |
|---|---|
| `YamlProperties-0.4.0-x64.zip` | 手动安装包，含 `YamlProperties/YamlProperties.dll`、安装脚本和源码压缩包 |
| `YamlProperties-0.4.0-x64-plugin-admin.zip` | **官方目录下载目标**，根目录直接包含 `YamlProperties.dll` |
| `YamlProperties-0.4.0-source.zip` | 对应源码、依赖、文档和构建脚本，不含本机日志 |
| `checksums.json` | 上述各 ZIP 与 DLL 的 SHA-256；官方条目使用 plugin-admin ZIP 的值 |

推送对应版本标签后，Actions 自动创建正式 Release，并上传上述 ZIP 和校验文件。不要把 GitHub 自动生成的 “Source code (zip)” 当作插件安装包，也不要将 Actions 下载附件的外层 ZIP 当作 Plugins Admin ZIP。Release 说明取自 `CHANGELOG.md` 的对应版本。各架构的正式附件分别上传，不覆盖已发布的旧版本。

后续版本只改 `VERSION` 并更新变更记录，构建时同步生成关于窗口、Windows DLL 版本信息和 manifest。每次生成新版本下载 URL；已公开并提交目录的版本附件保持不变。重建的 ZIP 可能因时间戳而改变哈希，**先确定最终附件，再计算并提交条目**。

对 x86 / ARM64，先设置 `$env:YP_ARCH = 'x86'` 或 `'arm64'`，构建、测试、打包命令会选择对应架构。也可对构建使用 `-Architecture`、对打包及条目生成器使用 `--arch`。

x64 输出保留在 `dist/`；另外两种架构分别输出到 `dist/x86/`、`dist/arm64/`，包名中的 `x64` 换成 `x86` / `arm64`。每个架构拥有自己的 manifest 与 checksums；发布时保留各架构校验文件，避免相互覆盖。源码 ZIP 内容共用。发布前为新版本更新 `VERSION`，不要上传当前开发构建覆盖既有版本。

正式发布使用对应标签 CI 的候选附件，由 `scripts/assemble_release.py` 自动汇总并验证。输出共 10 个附件：3 个手动安装包、3 个 Plugins Admin 包、1 个源码包、3 个校验文件。校验文件分别命名为 `checksums-x86.json`、`checksums-x64.json` 和 `checksums-arm64.json`。三个源码 ZIP 的内容须逐文件一致；若 ZIP 时间戳导致哈希不同，选用 x64 的源码 ZIP 作为公共附件，并将三个公开校验文件中的源码项统一为该附件的实际哈希。安装包与 Plugins Admin ZIP 保持 CI 原始字节，安装包内嵌源码 ZIP 也不重打包。

## 4. 官方插件目录的硬性要求

官方目录是 `notepad-plus-plus/nppPluginList`，不托管插件源码，也不替维护者发布 DLL。

- x86 对应 `src/pl.x86.json`，x64 对应 `src/pl.x64.json`，ARM64 对应 `src/pl.arm64.json`；每个条目使用各自架构的 ZIP 与哈希。
- `folder-name` 必须唯一，并与 DLL 去掉扩展名后的名称一致：本项目为 `YamlProperties`。
- ZIP 根目录必须是 `YamlProperties.dll`，不能再包一层 `YamlProperties/`。
- `id` 是**整个 ZIP 的 SHA-256**，不是 DLL 的 SHA-256。
- `version` 应与 DLL 的 Windows 版本资源一致。`0.4.0` 对应固定版本字段 `0.4.0.0`，末尾零在数值比较时等价。
- `repository` 是可公开直接下载的 ZIP URL；`homepage` 才是项目主页。
- 填写真实作者署名和英文功能简介。
- 用 `npp-compatible-versions` 声明实测兼容边界。当前本机宿主文件版本为 `8.9.6.4`，未完成更早版本矩阵测试；不要默认宣称支持所有 Notepad++ 版本。

本次核对官方 x64 列表时未发现 `YamlProperties` 同名条目；实际提交前仍需再次检查。

## 5. 生成条目并核对正式下载

发布 ZIP 后，在本项目根目录执行：

```powershell
$repository = Read-Host 'GitHub 仓库 HTTPS 地址'
$author = Read-Host '插件作者署名'
$minimumNpp = Read-Host '已验证的最低 Notepad++ 版本'
python scripts\plugin_list_entry.py --repository $repository --author $author --min-npp $minimumNpp --verify-download
```

默认输出 `dist/nppPluginList-entry-x64.json`；`--arch x86` 输出 `dist/x86/nppPluginList-entry-x86.json`，`--arch arm64` 输出 `dist/arm64/nppPluginList-entry-arm64.json`。工具读取当前 manifest，验证 ZIP 根目录及内部 DLL 哈希，生成版本化下载地址，并下载公开附件比对 ZIP 哈希。尚未公开 Release 时可省略 `--verify-download` 生成本地草稿；提交前必须再运行带下载验证的命令。

## 6. 本地 Plugins Admin 测试及提交 PR

1. 按官方手册准备单独的 Notepad++ **Debug** 测试目录和 Debug GUP；不同架构使用匹配文件。日常使用的 release 版会验证签名，不适合直接改它的插件列表。
2. 取得完整 `src/pl.x64.json`，将新条目按现有顺序加入 `npp-plugins` 数组。保留整份列表，不要把单个生成条目当作整份 JSON。
3. 将完整列表放入 Debug 目录的 `plugins/config/nppPluginList.json`，测试插件显示、下载、安装、启动加载、卸载；已有旧版本时再测更新识别。
4. Fork `notepad-plus-plus/nppPluginList`，新建分支，仅修改所需 JSON（`src/pl.x86.json`、`src/pl.x64.json`、`src/pl.arm64.json`），提交 PR。遵循该仓库当时的模板和 CI 结果，不提交本项目 DLL 或源码到它的仓库。
5. 等待维护者审查合并和后续官方列表分发；合并不会即时刷新所有用户本机列表。之后每次发布新版，更新条目的版本、ZIP URL 和 ZIP SHA-256，并再次提交 PR。

**发布前需完成的外部验证：**确认 GitHub Actions 对目标提交通过，发布正式附件并核验公开下载，执行 Debug Plugins Admin 安装/卸载/更新测试，提交官方 PR 并等待审核。当前本机独立编辑器冒烟测试及自带安装脚本测试，并不替代官方要求的 Plugins Admin 测试。实际提交和 CI 状态以仓库页面为准。

## 官方资料

- [Notepad++ 插件手册：本地测试、收录规则与 PR](https://npp-user-manual.org/docs/plugins/#test-your-plugins-locally)
- [官方插件目录 README](https://github.com/notepad-plus-plus/nppPluginList)
- [官方 x64 JSON](https://github.com/notepad-plus-plus/nppPluginList/blob/master/src/pl.x64.json)
- [官方 JSON Schema](https://github.com/notepad-plus-plus/nppPluginList/blob/master/pl.schema)
- [GitHub：创建 Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

资料核对日期：2026-11-11。官方手册、schema 和列表的本次下载快照保留在本地 `evidence/official-*` 中，未纳入源码发布包。
