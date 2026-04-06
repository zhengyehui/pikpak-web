# PikPak Storage Analyzer

A WinDirStat-style web tool for visualizing PikPak cloud storage file size distribution. Scan your entire PikPak drive and explore space usage with interactive charts and drill-down treemaps.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Drill-down Treemap** — Click into any folder to explore nested directories, just like WinDirStat
- **Folder Size Ranking** — All folders across every level, ranked by total size
- **File Size Ranking** — Find the largest files instantly
- **Size Distribution** — Bar chart showing file count by size range
- **Type Distribution** — Pie chart breaking down storage by file type (video, image, audio, etc.)
- **Real-time Scanning** — WebSocket-powered live progress updates during scan
- **Incremental Scan** — Resume from where you left off; only scan new folders
- **In-memory Cache** — All stats pre-computed after scan, instant page loads
- **SQLite Cache** — Scan results persist locally, no need to re-scan on restart

## Screenshot

```
┌─────────────────────────────────────────┐
│  PikPak Storage Analyzer                │
│  [Scan] [Stop] [Full Rescan] [Refresh]  │
├────────────────────┬────────────────────┤
│  Size Distribution │  Type Distribution │
├────────────────────┴────────────────────┤
│  Treemap (click to drill down)          │
├─────────────────────────────────────────┤
│  Folder / File Ranking Table            │
└─────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- A PikPak account with email/password login

### Install & Run

```bash
git clone https://github.com/zhengyehui/pikpak-web.git
cd pikpak-web

# Create .env from template and fill in your credentials
cp .env.example .env
# Edit .env with your PikPak email and password

# Setup and run
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open http://localhost:8080 in your browser.

### Run Again Later

```bash
cd pikpak-web
source .venv/bin/activate
python main.py
```

> `source .venv/bin/activate` activates the virtual environment where project dependencies are installed. Without it, the system Python will be used and imports will fail. You only need to run `pip install` once — after that, just activate and run.

### LAN Access

The server binds to `0.0.0.0:8080` by default, so you can access it from any device on your local network using your machine's IP address.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.10+ | pikpakapi requirement |
| PikPak API | pikpakapi | Most active community Python library |
| Web Framework | FastAPI + WebSocket | Async-friendly, real-time progress push |
| Frontend Charts | ECharts (CDN) | Treemap, bar, pie — all in one library |
| Data Cache | SQLite + In-memory | Persistent scan data + instant queries |

## Authentication

This tool uses [pikpakapi](https://github.com/Quan666/PikPakAPI) which supports **email + password** login only (no Google OAuth).

If you signed up via Google, go to PikPak Settings → Account Security → Set Password first.

## Project Structure

```
pikpak-web/
├── main.py              # FastAPI entry point & API routes
├── scanner.py           # PikPak recursive file scanner
├── database.py          # SQLite operations
├── stats_cache.py       # In-memory pre-computed stats
├── requirements.txt     # Python dependencies
├── .env                 # Your credentials (not in git)
├── static/
│   └── index.html       # Single-page frontend (ECharts)
└── PRD.md               # Product requirements document
```

## License

MIT

---

# PikPak 网盘空间分析工具

类似 WinDirStat 的网页工具，可视化分析 PikPak 网盘文件大小分布。扫描整个网盘，通过交互式图表和可下钻的 Treemap 探索空间占用情况。

## 功能特性

- **可下钻 Treemap** — 点击任意目录进入子目录，像 WinDirStat 一样逐层探索
- **全层级目录排行** — 所有层级的目录按总大小排序，一眼找到最占空间的文件夹
- **全层级文件排行** — 快速定位最大的文件
- **文件大小分布** — 柱状图展示各体积区间的文件数量
- **文件类型占比** — 饼图展示视频/图片/音频/文档/压缩包等分类占比
- **实时扫描进度** — WebSocket 实时推送扫描进度
- **增量扫描** — 支持断点续扫，只扫描新目录
- **内存缓存** — 扫描后所有统计数据预计算，页面秒开
- **SQLite 持久化** — 扫描结果本地保存，重启无需重新扫描

## 快速开始

### 环境要求

- Python 3.10+
- PikPak 账号（需要邮箱+密码登录方式）

### 安装运行

```bash
git clone https://github.com/zhengyehui/pikpak-web.git
cd pikpak-web

# 从模板创建配置文件，填入你的账号密码
cp .env.example .env
# 编辑 .env 填入你的 PikPak 邮箱和密码

# 安装依赖并启动
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

浏览器打开 http://localhost:8080

### 后续启动

```bash
cd pikpak-web
source .venv/bin/activate
python main.py
```

> `source .venv/bin/activate` 用于激活 Python 虚拟环境，项目依赖都装在 `.venv` 目录里。不激活的话会使用系统 Python，缺少依赖会报错。`pip install` 只需要首次运行一次，之后每次只需激活环境然后启动即可。

### 局域网访问

服务默认绑定 `0.0.0.0:8080`，局域网内其他设备可以通过本机 IP 直接访问。

## 认证说明

本工具使用 [pikpakapi](https://github.com/Quan666/PikPakAPI)，仅支持**邮箱+密码**登录（不支持 Google OAuth）。

如果你是通过 Google 注册的，需要先到 PikPak 设置 → 账号安全 → 设置密码。
