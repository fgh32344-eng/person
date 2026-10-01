# 王耀威 · 个人展示网站

> 宿州学院人工智能专业 2027 届本科生 · 个人主页 + 后端接口服务
> 技术栈：Python（FastAPI / 标准库 HTTP 服务器）· SQLite · 原生 HTML/CSS/JavaScript

一个**真正带后端**的个人展示网页：简历内容由 API 提供、留言写入数据库、
访问量实时统计，并提供后台管理页查看留言与站点数据。

---

## 一、快速开始

### 方式 A：一键启动（推荐）

Windows 双击 `start.bat`；macOS / Linux 执行：

```bash
./start.sh
```

然后在浏览器打开 <http://127.0.0.1:8000>。

启动脚本会自动判断环境：装了 FastAPI 就用 FastAPI，没装就用零依赖标准库服务器，
**两种情况页面和接口完全一致**。启动脚本按 `py` → `python` → DSH 随附运行时的顺序
寻找 Python 解释器。

> **⚠️ 修改 `start.bat` 时必读（曾经踩过的坑）**
>
> `cmd.exe` 按系统 ANSI 代码页**逐字节**解析 `.bat` 文件。如果文件存成 UTF-8，
> 中文字节会被解码成乱码，而乱码字节可能等于命令分隔符，把 `set` / `if` / `goto`
> 拆碎——双击后表现为满屏
> 「`'xxx'` 不是内部或外部命令，也不是可运行的程序或批处理文件」。
>
> 因此本项目遵循三条约定：
>
> 1. **`start.bat` 里不写中文**，命令逻辑与提示语全部使用 ASCII；
> 2. **不加 `chcp 65001`**。文件按 CP936 落盘时，`chcp 65001` 会把 cmd 读出的
>    CP936 字符再按 UTF-8 输出，中文变成 `鐜嬭€€濞�` 这类**双重编码乱码**
>    （比第一类 bug 更隐蔽：不报错，只是显示全乱）；
> 3. **中文横幅由 Python 打印**（`backend/app.py` 的 `banner()`），
>    Python 会按当前控制台编码自行处理，必要时降级为 `?` 而不是崩溃。
>
> `start.bat` 是生成产物，请**改源文件再重新生成**：
>
> ```bash
> # 1. 编辑 start.bat.utf8（UTF-8 源文件，可正常读改写）
> # 2. 生成 CP936 的 start.bat
> python tests/build_bat.py
> # 3. 校验编码与结构是否合规
> python tests/fix_bat_encoding.py
> ```
>
> `fix_bat_encoding.py` 会检查：BOM 是否存在、逻辑行是否全 ASCII、
> 是否误加 `chcp` 命令、关键命令是否齐全，并自动把 UTF-8 版本修回 CP936。
>
> `start.sh` 相反：UTF-8 编码 + LF 换行，供 bash 使用。

### 方式 B：手动启动

```bash
# 零依赖，任何 Python 3.10+ 都能直接跑
python backend/server.py

# 或（推荐，会自动选择可用后端）
python backend/app.py
```

### 方式 C：启用 FastAPI（获得交互式接口文档）

```bash
pip install -r backend/requirements.txt
python backend/app.py
# 然后访问 http://127.0.0.1:8000/api/docs
```

---

## 二、访问入口

| 地址 | 说明 |
| --- | --- |
| <http://127.0.0.1:8000/> | 个人主页（简历展示 + 留言板 + 实时访问量） |
| <http://127.0.0.1:8000/admin> | 后台管理页（默认 `admin` / `admin123`） |
| <http://127.0.0.1:8000/api/docs> | Swagger 交互式接口文档（需安装 FastAPI） |
| <http://127.0.0.1:8000/api/health> | 健康检查 |

可通过环境变量覆盖配置：

```bash
# Windows PowerShell
$env:PORTFOLIO_PORT="9000"; $env:PORTFOLIO_ADMIN_PASSWORD="你的新口令"; python backend/app.py

# macOS / Linux
PORTFOLIO_PORT=9000 PORTFOLIO_ADMIN_PASSWORD=你的新口令 python backend/app.py
```

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| `PORTFOLIO_HOST` | `127.0.0.1` | 监听地址（局域网访问填 `0.0.0.0`） |
| `PORTFOLIO_PORT` | `8000` | 监听端口 |
| `PORTFOLIO_ADMIN_USER` | `admin` | 后台用户名 |
| `PORTFOLIO_ADMIN_PASSWORD` | `admin123` | 后台密码 |

---

## 三、接口一览

简历数据（公开）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/resume` | 完整结构化简历数据 |
| GET | `/api/profile` | 个人信息卡片 |
| GET | `/api/projects?tag=YOLO` | 项目列表，可按技术栈过滤 |
| GET | `/api/skills` | 技能矩阵与在学清单 |

访问统计（公开）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/visit` | 上报一次访问，返回累计/今日访问量 |
| GET | `/api/stats` | 站点统计（含最近 14 天趋势、热门页面） |

留言板（公开）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/messages?page=1&page_size=20` | 公开留言分页列表（**不含**联系方式与 IP） |
| POST | `/api/messages` | 提交留言，限同一 IP 每小时 6 条 |

后台管理（需要 `x-admin-token` 请求头）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/admin/login` | 登录，返回 6 小时有效令牌 |
| POST | `/api/admin/logout` | 登出并吊销令牌 |
| GET | `/api/admin/overview` | 后台概览（KPI + 趋势 + 热门页面 + 最近访问） |
| GET | `/api/admin/messages` | 留言管理列表，支持关键字与状态筛选 |
| PATCH | `/api/admin/messages/{id}?approved=0\|1` | 公开 / 隐藏留言 |
| DELETE | `/api/admin/messages/{id}` | 删除留言 |

命令行自测示例：

```bash
curl http://127.0.0.1:8000/api/profile
curl -X POST http://127.0.0.1:8000/api/messages \
     -H "Content-Type: application/json" \
     -d "{\"name\":\"访客\",\"content\":\"你好\"}"
```

---

## 四、目录结构

```
portfolio/
├── backend/
│   ├── app.py             # 业务与数据层 + FastAPI 应用（可选依赖）
│   ├── server.py          # 零依赖标准库服务器，复用 app.py 的数据层
│   └── requirements.txt   # FastAPI 方案的可选依赖
├── frontend/
│   ├── pages/
│   │   ├── index.html     # 主页模板
│   │   └── admin.html     # 后台页模板
│   └── static/
│       ├── css/style.css  # 主页样式
│       ├── css/admin.css  # 后台样式
│       ├── js/main.js     # 主页逻辑（渲染简历、留言、访问统计）
│       ├── js/admin.js    # 后台逻辑（登录、KPI、图表、留言管理）
│       ├── assets/avatar.svg
│       └── favicon.svg
├── data/
│   ├── resume.json        # 简历内容（改这个文件即可更新整站展示）
│   └── portfolio.db       # SQLite 数据库（首次运行自动生成）
├── start.bat / start.sh   # 一键启动脚本
└── README.md
```

---

## 五、数据库

SQLite，首次运行自动建表，位置 `data/portfolio.db`。三张表：

- `visits` —— 每次访问的路径、IP、User-Agent、日期
- `messages` —— 访客留言（含 IP、设备、审核状态）
- `counters` —— 累计访问计数

想清空演示数据，直接删除 `data/portfolio.db*` 后重启即可。

---

## 六、改成你自己的内容

1. **改简历内容**：编辑 `data/resume.json`，主页会自动渲染，无需改代码。
   结构调整时对照 `frontend/static/js/main.js` 里的 `renderXxx` 函数即可。
2. **换头像**：把你的照片放到 `frontend/static/assets/`（例如 `photo.jpg`），
   再把 `data/resume.json` 里 `profile.avatar` 改成 `/static/assets/photo.jpg`。
3. **改后台口令**：启动前设置 `PORTFOLIO_ADMIN_PASSWORD` 环境变量。
4. **部署到公网**：建议用 uvicorn 多进程或反向代理（Nginx），
   并务必修改后台默认口令、把"后台"入口从导航里去掉或限制来源 IP。

```bash
# 生产启动示例
pip install -r backend/requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 2
```

> 注意：留言是公开的，后台令牌保存在服务端内存中，**重启服务后需要重新登录**。

---

## 七、已验证项

- 40 项端到端接口测试全部通过（页面与静态资源、简历 API、统计、留言增删改查、
  限流、后台鉴权与令牌失效、目录穿越拦截等）。
- 主页 42 处、后台 19 处 JS 选择器与 HTML 元素一一对应，导航锚点与区块 id 全部匹配。
- 公开留言接口已确认不返回联系方式与 IP（仅后台可见）。
