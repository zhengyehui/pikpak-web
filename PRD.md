# PikPak 网盘文件大小分布分析工具 — PRD

## 1. 项目概述

- **名称**: PikPak Storage Analyzer
- **目标**: 可视化分析 PikPak 网盘中 ~10TB / 万级文件的大小分布
- **用户**: 个人使用（快速原型）
- **输出形式**: 本地 Web 服务，浏览器实时查看 HTML 图表

## 2. 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 语言 | Python 3.10+ | pikpakapi 依赖 |
| PikPak API | pikpakapi (v0.1.11) | 社区最活跃的 Python 库 |
| Web 框架 | FastAPI + WebSocket | 异步友好，支持实时推送扫描进度 |
| 前端图表 | ECharts (CDN) | 单 HTML 文件，Treemap/饼图/柱状图都支持 |
| 数据缓存 | SQLite | 万级文件元数据本地缓存，避免重复扫描 |

## 3. 鉴权方案

pikpakapi **不支持 Google OAuth**，需手动获取 token：

1. 用户在浏览器登录 PikPak 网页端 (mypikpak.com)
2. 从浏览器 DevTools → Application → Local Storage 或网络请求中提取 `access_token` + `refresh_token`
3. 将 token 粘贴到工具的配置页面（首页输入框）
4. 工具通过 `encoded_token` 参数初始化 pikpakapi，自动续期

**备选方案**: 如果用户在 PikPak 设置了邮箱+密码，也可直接用账密登录。

## 4. 核心功能

### 4.1 文件扫描

- 递归遍历全盘目录，获取每个文件的 `name`、`size`、`mime_type`、`parent_id`、`created_time`
- 分页拉取（每页 100 条），支持断点续扫（记录已扫描的 folder_id）
- 扫描进度通过 WebSocket 实时推送到前端（已扫描文件数 / 当前目录）
- 扫描结果写入 SQLite 缓存，下次启动可直接加载

### 4.2 文件大小分布图（柱状图）

- X 轴：体积区间（<1MB, 1-10MB, 10-100MB, 100MB-1GB, 1-5GB, 5-10GB, >10GB）
- Y 轴：文件数量
- 支持点击某区间展开查看具体文件列表

### 4.3 文件类型占比（饼图）

- 按 mime_type 大类聚合：视频 / 图片 / 音频 / 文档 / 压缩包 / 其他
- 显示每类的文件数量和总大小

### 4.4 目录空间占用（Treemap）

- 可视化每个文件夹的空间占用比例
- 支持点击下钻到子目录

### 4.5 大文件排行榜（表格）

- Top 50 最大文件，显示：文件名、大小、路径、类型、创建时间
- 支持按大小/时间排序

## 5. 页面结构

单页应用，布局：

```
┌─────────────────────────────────────────┐
│  Header: PikPak Storage Analyzer        │
│  [Token 输入框] [开始扫描] [进度条]       │
├────────────────────┬────────────────────┤
│  文件大小分布(柱状图) │  文件类型占比(饼图)  │
├────────────────────┴────────────────────┤
│  目录空间占用 (Treemap)                   │
├─────────────────────────────────────────┤
│  大文件排行榜 (Table)                     │
└─────────────────────────────────────────┘
```

## 6. 数据模型

### SQLite: `files` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | PikPak 文件 ID |
| name | TEXT | 文件名 |
| size | INTEGER | 字节数 |
| mime_type | TEXT | MIME 类型 |
| kind | TEXT | drive#file / drive#folder |
| parent_id | TEXT | 父目录 ID |
| path | TEXT | 完整路径 |
| created_time | TEXT | 创建时间 |
| scan_time | TEXT | 扫描时间 |

### SQLite: `scan_state` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| folder_id | TEXT PK | 已扫描的目录 ID |
| status | TEXT | done / in_progress |
| updated_at | TEXT | 更新时间 |

## 7. API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 主页（HTML） |
| POST | `/api/auth` | 提交 token 或账密 |
| POST | `/api/scan/start` | 开始扫描 |
| GET | `/api/scan/stop` | 停止扫描 |
| WS | `/ws/scan` | 扫描进度推送 |
| GET | `/api/stats/size-distribution` | 大小分布数据 |
| GET | `/api/stats/type-distribution` | 类型分布数据 |
| GET | `/api/stats/treemap` | 目录树数据 |
| GET | `/api/stats/top-files?limit=50` | 大文件排行 |

## 8. 性能考量

- **万级文件遍历**: 每页 100 条，预计 100+ 次 API 请求，串行约需 3-5 分钟
- **并发优化**: 可对多个子目录并发请求（控制并发数 ≤ 5，避免触发限流）
- **增量扫描**: 通过 `scan_state` 表实现断点续扫，无需每次全量
- **SQLite 缓存**: 扫描完成后，图表查询全部走本地 DB，毫秒级响应

## 9. 启动方式

```bash
cd pikpak
pip install -r requirements.txt
python main.py
# 浏览器打开 http://localhost:8080
```

## 10. 项目结构

```
pikpak/
├── main.py              # FastAPI 入口
├── scanner.py           # PikPak 文件扫描逻辑
├── database.py          # SQLite 操作
├── requirements.txt     # 依赖
├── static/
│   └── index.html       # 单页前端（ECharts）
└── PRD.md               # 本文档
```
