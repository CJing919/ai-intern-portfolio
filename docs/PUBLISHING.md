# 发布到 GitHub

仓库已经包含一个不依赖本地 `git` 的发布脚本，使用 GitHub Git Data API 一次性上传所有文件。

## 方式 A：空仓库 + token 文件（推荐）

当前环境访问 `github.com` 的设备授权页可能超时，但 `api.github.com` 可用。用 token 文件最稳。

### 1. 创建空仓库

打开 <https://github.com/new>：

- Repository name：`ai-intern-portfolio`
- 选 Public
- **不要**勾选 Add a README / .gitignore / license
- Create repository

### 2. 创建 token

打开 <https://github.com/settings/personal-access-tokens/new>：

- Repository access：Only select repositories → `ai-intern-portfolio`
- Permissions：Contents = Read and write；Metadata = Read
- 生成后复制 token（只显示一次）

如果更习惯 classic token：<https://github.com/settings/tokens/new>，勾选 `repo`，设置 7 天过期。

### 3. 在本地安全保存 token

**方式 1：命令行安全输入**

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\save_github_token.ps1
```

按提示粘贴 token，输入不会回显。文件会保存到 `.secrets/github_token.txt`，该目录已 gitignore，不会被上传。

**方式 2：本地浏览器表单**

```bash
python scripts/token_server.py
```

打开 <http://127.0.0.1:8765>，粘贴 token，点击“校验并保存”。服务只绑定 `127.0.0.1`，校验通过后写入 `.secrets/github_token.txt`，不会打印 token。

### 4. 预览并发布

```bash
python scripts/publish_github.py --repo ai-intern-portfolio --visibility public --dry-run
python scripts/publish_github.py --repo ai-intern-portfolio --visibility public
```

脚本会识别当前 token 的账号，向已有空仓库上传 81 个文件，创建 `main` 分支和初始 commit。

## 方式 B：设备授权（如果 github.com 可访问）

### 1. 登录

```bash
python scripts/github_device_login.py
```

终端会输出：

```text
请在浏览器打开： https://github.com/login/device
输入一次性代码： XXXX-XXXX
```

在浏览器完成授权。授权页显示 **GitHub CLI** 是正常的，因为脚本使用的是 GitHub CLI 的公开 OAuth client id。脚本不会读取密码，token 会写入 `.secrets/github_token.txt`（已 gitignore）。

### 2. 创建仓库并发布

```bash
python scripts/publish_github.py --repo ai-intern-portfolio --visibility public
```

## 方式 C：使用已有仓库

如果已经有空仓库，把 `--repo` 改成仓库名，或先手动创建一个空仓库：

```bash
python scripts/publish_github.py --owner your-name --repo your-repo --visibility private
```

要求仓库为空；如果已有内容，脚本会停止，避免覆盖。

## 方式 D：手动上传 ZIP

1. 在 GitHub 新建空仓库（不要勾选 README）。
2. 把本目录打包成 zip。
3. 在仓库页面选择 **Add file → Upload files**，上传解压后的内容。
4. 确认 `.github/workflows/ci.yml`、`docs/`、`reports/` 都在。

## 安全说明

- 不要把 `.secrets/github_token.txt` 提交到仓库。
- 不要截图或粘贴 token。
- 发布后可以在 GitHub → Settings → Applications 撤销 GitHub CLI 授权，或在 Personal access tokens 页面撤销 token。
- 如果仓库要公开，先确认 `reports/` 和 `data/` 中没有真实客户数据；本仓库全部为合成数据。

## 发布后检查

- [ ] README 能正常显示
- [ ] `reports/eval_report.md`、`reports/content_report.md` 可打开
- [ ] GitHub Actions 的 CI 通过
- [ ] 仓库描述、Topics 已填写（`ai-product`, `rag`, `agent`, `workflow`, `portfolio`）
- [ ] 如果要用于简历，把仓库链接加到简历作品集一栏
- [ ] 确认没有把合成数据描述成真实企业数据
