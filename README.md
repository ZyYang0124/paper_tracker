# 🧬 论文追踪脚本  **Paper Tracker**

自动从 PubMed 检索指定期刊/关键词的最新论文，调用 **Qwen 大模型** 生成中文摘要，并通过邮件推送每日简报。

---

## ✨ 功能亮点

- 📰 支持多期刊 + 多关键词组合检索（支持通配符 `*` 和引号短语）  
- 🤖 使用 **Qwen-Max** 自动生成简洁中文摘要（100字以内）  
- 📧 自动去重 + 邮件推送（支持 QQ 邮箱、Gmail、Outlook 等 SMTP 服务）  
- ⏱️ 可指定时间范围（如最近 1/3/7 天）  
- 🔁 基于 PMID 缓存，避免重复推送  
- 📄 输出 Markdown 报告文件，便于归档或分享  

---

## 🛠 前期准备

### 1️⃣ 安装 Python 环境

要求：**Python ≥ 3.8**  
建议使用虚拟环境：

```bash
python -m venv evol_env
source evol_env/bin/activate        # Linux/macOS
# 或
evol_env\Scripts\activate           # Windows
````

### 2️⃣ 安装依赖库

```bash
pip install requests dashscope
```

💡 `dashscope` 是阿里云百炼平台 SDK，用于调用 Qwen 模型。

---

### 3️⃣ 获取 DashScope API Key

1. 登录 [DashScope 控制台](https://dashscope.aliyun.com/)
2. 创建 **API Key**（确保已开通 Qwen-Max 权限）
3. 将 Key 填入脚本中的：

```python
DASHSCOPE_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

### 4️⃣ 配置邮箱（以 QQ 邮箱为例）

1. 登录 QQ 邮箱
2. 进入「设置」→「账户」
3. 开启 **SMTP 服务**（系统会生成一个 16 位授权码）
4. 修改脚本中的 `EMAIL_CONFIG`：

```python
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "port": 465,
    "sender_email": "yourname@qq.com",        # 发件人邮箱
    "password": "your_16_digit_auth_code",    # 授权码（不是登录密码！）
    "receiver_email": "recipient@example.com" # 收件人邮箱
}
```

✅ 支持其他 SMTP 邮箱（如 Outlook、163、Gmail）
只需修改服务器和端口配置。

---

## ⚙ 默认配置（可被命令行覆盖）

| 配置项    | 默认值                                                                                                                                                                                                                           |
| :----- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 期刊列表   | `["Nature", "Science", "Cell", "PNAS", "Syst Biol", "Nat Ecol Evol", "Nat Genet", "Mol Biol Evol", "Cladistics", "Curr Biol"]`                                                                                                |
| 关键词列表  | `["phylogen*", "systematic*", "evolution*", "genom*", "\"phenotypic plasticity\"", "adaptive radiation", "speciation", "molecular clock", "ancestral state reconstruction", "comparative genomics", "gene family evolution"]` |
| 检索时间范围 | 最近 7 天                                                                                                                                                                                                                        |
| 缓存文件   | `processed_pmids.json`                                                                                                                                                                                                        |
| 报告文件名  | `evol_summary_YYYY-MM-DD.md`                                                                                                                                                                                                  |
| 是否发送邮件 | 是（除非加 `-n` 参数）                                                                                                                                                                                                                |

---

## 📋 命令行参数说明

| 参数   | 长参数             | 说明          | 示例                          |
| :--- | :-------------- | :---------- | :-------------------------- |
| `-j` | `--journals`    | 指定期刊（逗号分隔）  | `-j "Nature,Science"`       |
| `-k` | `--keywords`    | 指定关键词（逗号分隔） | `-k "speciation,phylogeny"` |
| `-d` | `--days`        | 检索最近 N 天的论文 | `-d 3`                      |
| `-n` | `--no-email`    | 不发送邮件，仅生成报告 | `-n`                        |
| `-c` | `--cache-file`  | 自定义缓存文件路径   | `-c my_cache.json`          |
| `-o` | `--report-file` | 自定义报告输出文件名  | `-o today.md`               |
| `-h` | `--help`        | 显示帮助信息      | `-h`                        |

💡 所有参数可自由组合。

---

## ▶️ 运行方法

### 基础运行（使用默认配置）

```bash
python evol_paper_tracker.py
```

### 常见使用场景

1️⃣ 查最近 1 天 Nature/Science 中关于 “speciation” 的论文并发邮件：

```bash
python evol_paper_tracker.py -j "Nature,Science" -k "speciation" -d 1
```

2️⃣ 调试模式（不发邮件，只生成报告）：

```bash
python evol_paper_tracker.py -n -d 7
```

3️⃣ 自定义输出与缓存（适合多任务隔离）：

```bash
python evol_paper_tracker.py -j "Mol Biol Evol" -c molbio_cache.json -o molbio_report.md -n
```

4️⃣ 查看帮助：

```bash
python evol_paper_tracker.py -h
```

---

## ⏰ 自动化运行（定时任务）

### Linux / macOS（使用 `crontab`）

```bash
# 编辑定时任务
crontab -e

# 每天上午 9 点运行（请替换为你的路径）
0 9 * * * cd /path/to/script && /usr/bin/python3 evol_paper_tracker.py -d 1 >> tracker.log 2>&1
```

### Windows（使用任务计划程序）

创建批处理文件 `run_tracker.bat`：

```bat
@echo off
cd /d "C:\path\to\script"
python evol_paper_tracker.py -d 1
```

然后通过 **任务计划程序** 设置每天自动运行该 `.bat` 文件。

---

## ❓ 常见问题

### Q1: 邮件收到了，但终端报错 `(-1, b'\x00\x00\x00')`？

✅ 这是 **QQ 邮箱 SMTP** 的正常行为，邮件已成功发送。
可安全忽略，或使用改进版脚本自动屏蔽此提示。

---

### Q2: 为什么报告篇数少于检索结果？

* 已在 `processed_pmids.json` 中存在的论文会被跳过（防重复）
* 无摘要的论文会被过滤

---

### Q3: 如何强制重新处理所有论文？

删除或重命名缓存文件：

```bash
rm processed_pmids.json
```

---

### Q4: 能否改用 Gmail 或企业邮箱？

可以，只需修改 SMTP 配置，例如 Gmail：

```python
"smtp_server": "smtp.gmail.com",
"port": 465,  # 或 587（需 STARTTLS）
"password": "your_app_password"  # Gmail 需开启两步验证并生成应用专用密码
```

---

## 📄 输出示例（Markdown 报告片段）

```markdown
# 🧬 进化生物学每日简报 (2025-11-07)

## 📰 Nature

### [Rapid speciation in island birds driven by sexual selection](https://doi.org/10.xxxx/xxxx)
**AI 总结**：研究发现性选择加速了岛屿鸟类的物种形成，基因组分析揭示了与羽毛颜色相关的快速进化区域。  
PMID: [12345678](https://pubmed.ncbi.nlm.nih.gov/12345678/)
---
```

---

## 📜 许可证

**MIT License** — 可自由用于学术与个人用途。

---

## 🙌 欢迎贡献

如果你在使用中发现问题或有改进建议，欢迎提交 Issue 或 PR！

---
