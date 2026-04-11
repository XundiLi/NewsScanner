# 📰 Sina 7x24 News Scanner & Intelligence System

这是一个基于 Python 的新浪 7x24 快讯抓取与智能分析系统。它支持实时同步、语义搜索、数据持久化，并集成了飞书通知功能。

---

## 🌟 核心功能

- **实时同步**：自动补全缺失的新闻数据，支持按天或按时间段抓取。
- **语义搜索**：内置 `paraphrase-multilingual-MiniLM-L12-v2` 模型，支持跨语言语义匹配（不只是关键词匹配）。
- **数据持久化**：新闻以 `JSONL` 格式存储在本地 `news_data` 目录，方便后续分析。
- **飞书集成**：任务完成后自动发送同步报告至飞书群组。
- **可视化界面**：基于 Streamlit 的交互式 Web 搜索与展示界面。

---

## 📂 项目结构

```text
news_scanner/
├── auto_sync_news.py      # 定时同步脚本 (主入口)
├── app_streamlit.py       # 可视化搜索界面
├── news_scanner_utils.py  # 核心逻辑与功能函数
├── news_scanner_engine.py # 抓取引擎与模型管理
├── news_data/             # 本地新闻数据库 (JSONL)
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

*注意：如果 `model.safetensors` 文件仅有 1KB 左右（指针文件），程序运行时会报错 `SafetensorError: Error while deserializing header`，请务必执行以上拉取步骤。*

### 3. 安装依赖
在项目根目录下运行：

```bash
pip install requests torch pandas sentence-transformers streamlit
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
