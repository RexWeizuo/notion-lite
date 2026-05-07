# Notion-Lite — 类 Notion 块编辑器笔记工具

本地自托管的 Notion 风格笔记应用。

**功能：**
- 📁 页面树形层级（无限嵌套）
- ✍️ TipTap 块编辑器（H1/H2/H3、段落、列表、代码块、引用、分割线）
- 🖱️ 页面拖拽排序 & 移动父节点
- 📥 Markdown 导入 / 📤 Markdown 导出
- 🖼️ 图片上传（拖入编辑器）
- 🔄 自动保存（500ms 防抖）

## 前置条件

- **PostgreSQL 16**（WSL 中安装）
- Python 3.12 + Node.js 18+

### 安装 PostgreSQL（仅首次）

```bash
# WSL 中执行
sudo apt update && sudo apt install -y postgresql postgresql-contrib
sudo service postgresql start

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER notionuser WITH PASSWORD 'notionpass';"
sudo -u postgres psql -c "CREATE DATABASE notionlite OWNER notionuser;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE notionlite TO notionuser;"
```

## 一次性搭建（仅首次）

```powershell
# === Windows PowerShell ===
cd D:\study\notion-lite

# 1. 安装 Python 依赖（使用共享 venv）
D:\study\.venv-wsl\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 执行数据库迁移（WSL 中）
# wsl -d <your-distro>
# cd /mnt/d/study/notion-lite
# alembic upgrade head

# 3. 安装前端依赖 + 构建
cd D:\study\notion-lite\frontend
npm install
npm run build
```

> **注意：** 数据库迁移只需要执行一次，应用启动时也会自动 `CREATE TABLE IF NOT EXISTS`。

## 日常启动

### 1. 启动 PostgreSQL（WSL 中）

```bash
sudo service postgresql start
```

### 2. 启动应用（一条命令）

```powershell
# Windows PowerShell
D:\study\.venv-wsl\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8123
```

或 WSL 中：

```bash
cd /mnt/d/study/notion-lite
/mnt/d/study/.venv-wsl/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8123
```

### 3. 访问

浏览器打开 http://localhost:8123

## 开发模式（前后端分离）

```bash
# Term 1: 后端
cd /mnt/d/study/notion-lite
/mnt/d/study/.venv-wsl/bin/python -m uvicorn app.main:app --port 8123 --reload

# Term 2: 前端
cd /mnt/d/study/notion-lite/frontend
npm run dev
```

访问 http://localhost:8124（Vite 开发服务器，自动代理 API 到 8123）

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/pages/tree` | 页面树（含嵌套子页面） |
| GET | `/api/pages/{id}` | 页面详情 |
| POST | `/api/pages` | 新建页面 |
| PUT | `/api/pages/{id}` | 更新页面标题 |
| DELETE | `/api/pages/{id}` | 删除页面（含子页面） |
| GET | `/api/pages/{id}/blocks` | 页面块列表 |
| POST | `/api/pages/{id}/blocks` | 新建块 |
| PUT | `/api/pages/{id}/blocks/{bid}` | 更新块 |
| DELETE | `/api/pages/{id}/blocks/{bid}` | 删除块 |
| PUT | `/api/pages/{id}/blocks/reorder` | 批量排序 |
| PUT | `/api/pages/{id}/move` | 移动页面（拖拽排序） |
| GET | `/api/pages/{id}/export/markdown` | 导出 Markdown |
| POST | `/api/pages/import/markdown` | 导入 Markdown |
| POST | `/api/upload` | 上传图片 |

## 项目结构

```
notion-lite/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置（数据库连接）
│   ├── database.py        # 数据库引擎 + 会话
│   ├── models.py          # ORM 模型（Page, Block）
│   ├── schemas.py         # Pydantic 验证
│   ├── markdown_utils.py  # Markdown ↔ TipTap JSON 转换
│   └── routes/
│       ├── pages.py       # 页面 CRUD + 树 API + 移动
│       ├── blocks.py      # 块 CRUD + 排序
│       ├── markdown.py    # Markdown 导入导出
│       └── upload.py      # 图片上传
├── frontend/
│   ├── src/
│   │   ├── App.vue                # 主布局 + 导入导出
│   │   ├── components/
│   │   │   ├── Sidebar.vue       # 侧边栏页面树
│   │   │   ├── PageTreeItem.vue  # 递归页面树节点 + 拖拽
│   │   │   └── BlockEditor.vue   # TipTap 块编辑器 + 图片上传
│   │   └── api/
│   │       └── index.js          # API 客户端
│   └── dist/                      # 构建产物
├── uploads/                       # 上传的图片
├── alembic/                       # 数据库迁移
├── requirements.txt
└── README.md
```

## 已知限制

1. **PostgreSQL 管理开销** — 每次 WSL 重启后需 `sudo service postgresql start`
2. **块同步策略简单** — 目前编辑器保存时全量删除+重建，后续可优化为增量 diff
3. **单用户** — 无实时协作，纯本地工具
