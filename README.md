# 📰 Jedi News Scanner

这是一个基于 Python 的新浪 7x24 快讯抓取与查询系统。它支持实时同步、语义搜索、数据持久化。

---

## 🌟 核心功能

- **实时同步**：自动补全缺失的新闻数据，支持按天或按时间段抓取。
- **语义搜索**：内置 `bge-small-zh-v1.5` 模型，支持中文语义匹配（不只是关键词匹配）。
- **数据持久化**：新闻以 `JSONL` 格式存储在本地 `news_data` 目录，方便后续分析。
- **AI 格式转换**：支持将新闻数据转换为 AI 可读的 chunk 格式，输出到 `news_text/` 按日期归档。
- **双模式抓取**：`sync_to_ai.py` 支持从本地 jsonl 或实时 API 抓取两种模式。
- **可视化界面**：基于 Streamlit 的交互式 Web 搜索与展示界面。

---

## 📂 项目结构

```text
news_scanner/
├── auto_sync_news.py      # 定时同步脚本 (主入口，带飞书通知)
├── sync_to_ai.py          # AI 格式转换工具 (支持 jsonl/live 双模式)
├── app_streamlit.py       # 可视化搜索界面
├── news_scanner_utils.py  # 核心逻辑与功能函数
├── news_scanner_engine.py # 抓取引擎与模型管理
├── news_data/             # 本地新闻数据库 (JSONL)
├── news_text/             # AI 格式新闻文本 (按日期分目录)
│   └── YYYY-MM-DD/
│       └── news_ai_YYYY-MM-DD.txt
└── transformer_models/    # 预置语义模型 (无需单独下载)
```

---

## 🛠️ 安装与配置

### 1. 准备环境
建议使用 Python 3.9+ 环境。如果你使用 Anaconda：

```bash
conda create -n news_scanner python=3.10
conda activate news_scanner
```

### 2. 下载并安装 Git LFS
由于本项目包含较大的预训练模型文件（存储在 `transformer_models/` 目录），需要使用 Git LFS (Large File Storage) 来下载完整模型文件。

1. **安装 Git LFS**：
   - macOS (Homebrew): `brew install git-lfs`
   - Linux (Ubuntu/Debian): `sudo apt-get install git-lfs`
2. **在项目目录下激活并拉取文件**：
   ```bash
   git lfs install
   git lfs pull
   ```

*注意：如果 `model_optimized.onnx` 文件仅有 1KB 左右（指针文件），程序运行时会报错，请务必执行以上拉取步骤。*

### 3. 安装依赖
在项目根目录下运行：

```bash
pip install requests pandas streamlit fastembed
```

### 3. 配置飞书通知 (可选)
本项目默认通过 `openclaw` 命令行工具发送通知。若未安装 OpenClaw，脚本会打印日志但跳过发送。

---

## 🚀 运行指南

### A. 运行可视化界面 (推荐)
在终端执行：
```bash
streamlit run app_streamlit.py
```
运行后会自动打开浏览器，进入新闻搜索与监控界面。

### B. 执行一次手动同步
如果你想同步今天的数据：
```bash
python auto_sync_news.py
```

### C. 转换为 AI 格式 (sync_to_ai.py)
将原始 JSONL 数据或实时抓取的新闻转换为 AI 可读的 chunk 格式，输出到 `news_text/{YYYY-MM-DD}/news_ai_{YYYY-MM-DD}.txt`。

**两种数据源模式**：

| 模式 | 数据来源 | 适用场景 |
|------|---------|---------|
| `jsonl` (默认) | 读取本地 `news_data/` 目录的 JSONL 文件 | 日常转换已抓取的新闻 |
| `live` | 直接从新浪快讯接口抓取（内存处理，不保存） | 快速转换当天新闻，无需先跑 sync |

**使用方式**：

```bash
# jsonl 模式 — 处理今天（从本地 jsonl 读取）
python sync_to_ai.py

# jsonl 模式 — 处理指定日期
python sync_to_ai.py 2026-04-18

# live 模式 — 直接从 API 抓取并转换指定日期（不保存 jsonl）
python sync_to_ai.py 2026-04-18 live
```

**输出路径**：
```
news_text/
└── 2026-04-18/
    └── news_ai_2026-04-18.txt
```
日期文件夹会自动创建，文件包含按 chunk 分组的新闻数据（正序排列，带 Chunk ID 标记）。

**注意事项**：
- `live` 模式内置 3 次重试机制，适合快速转换当天新闻
- 如果当天已经跑过 `auto_sync_news.py`，或者想要转换历史新闻，使用 `jsonl` 模式

---

## ⏰ 如何配置本地新闻自动刷新？

为了保证本地数据库是最新的，你可以配置 **macOS 系统的定时任务 (crontab)**：

1. 打开终端，输入 `crontab -e`。
2. 添加以下行（建议可以每日定时运行）：

```bash
# 每30分钟同步一次新浪快讯
*/30 * * * * /opt/anaconda3/bin/python "/Users/lixundi/Desktop/Data & Codes/news_scanner/auto_sync_news.py" >> "/Users/lixundi/Desktop/Data & Codes/news_scanner/sync.log" 2>&1
```

*注意：请根据你的实际 python 路径和项目路径进行修改。*

---

## 📝 开发者备注
- 本项目已完全适配 **相对路径逻辑**。
- `transformer_models` 已内置在仓库中，无需额外配置即可直接运行语义搜索。
