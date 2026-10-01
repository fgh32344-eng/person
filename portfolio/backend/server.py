"""
王耀威 · 个人展示网站 —— 零依赖标准库后端

当环境里没有 FastAPI / uvicorn 时使用本文件，接口与 backend/app.py 完全一致，
前端页面不需要任何改动。

运行：python backend\\server.py        访问 http://127.0.0.1:8000

实现要点：
  * http.server.ThreadingHTTPServer 承担 HTTP 服务
  * 路由表 ROUTES 用「方法 + 正则」匹配，path 参数以命名分组传入 handler
  * 页面渲染复用 views 模板替换，并把初始化数据内联进 window.__SITE_DATA__，
    前端检测到该变量时直接使用，省掉一次请求
  * 留言 / 访问统计 / 后台鉴权与 FastAPI 版本共用同一套 SQLite 表结构
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from typing import Any, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import MessageIn, LoginIn, banner, db, say, util, views  # noqa: E402  复用数据层与业务规则

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}


class ApiError(Exception):
    """带 HTTP 状态码的业务异常。"""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


# --------------------------------------------------------------------------
# 路由
# --------------------------------------------------------------------------
ROUTES: list[tuple[str, re.Pattern[str], Callable[..., Any]]] = []


def route(method: str, pattern: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    compiled = re.compile(f"^{pattern}$")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        ROUTES.append((method.upper(), compiled, func))
        return func

    return decorator


# ---------------- 简历 ----------------
@route("GET", r"/api/resume")
def api_resume(ctx: "Context") -> Any:
    return util.read_json(util.RESUME_PATH)


@route("GET", r"/api/profile")
def api_profile(ctx: "Context") -> Any:
    return util.read_json(util.RESUME_PATH)["profile"]


@route("GET", r"/api/projects")
def api_projects(ctx: "Context") -> Any:
    projects = util.read_json(util.RESUME_PATH)["projects"]
    tag = ctx.query_one("tag")
    if tag:
        projects = [p for p in projects if any(tag.lower() in t.lower() for t in p.get("tags", []))]
    return {"total": len(projects), "items": projects}


@route("GET", r"/api/skills")
def api_skills(ctx: "Context") -> Any:
    data = util.read_json(util.RESUME_PATH)
    return {"skills": data["skills"], "learning": data["learning"]}


# ---------------- 统计 ----------------
@route("POST", r"/api/visit")
def api_visit(ctx: "Context") -> Any:
    payload = ctx.json_body(silent=True) or {}
    path = str(payload.get("path") or "/")[:200]
    db.record_visit(path, ctx.ip, ctx.header("user-agent"), ctx.header("referer"))
    stats = db.visit_stats()
    return {
        "ok": True,
        "total_views": stats["total_views"],
        "today_views": stats["today_views"],
        "today_visitors": stats["today_visitors"],
    }


@route("GET", r"/api/stats")
def api_stats(ctx: "Context") -> Any:
    stats = db.visit_stats()
    stats["total_messages"] = db.message_count(approved=1)
    return stats


# ---------------- 留言 ----------------
@route("GET", r"/api/messages")
def api_messages(ctx: "Context") -> Any:
    page = max(1, ctx.query_int("page", 1))
    page_size = min(50, max(1, ctx.query_int("page_size", 20)))
    data = db.list_messages(page=page, page_size=page_size, approved=1, include_private=False)
    data["total_all"] = db.message_count()
    return data


@route("POST", r"/api/messages")
def api_create_message(ctx: "Context") -> Any:
    try:
        payload = MessageIn(**ctx.json_body())
    except ValueError as exc:  # 字段校验失败（含零依赖模式）
        raise ApiError(422, str(exc)) from exc
    if db.recent_messages_by_ip(ctx.ip) >= util.MAX_MESSAGES_PER_HOUR:
        raise ApiError(
            429,
            f"留言过于频繁，同一访客每小时最多 {util.MAX_MESSAGES_PER_HOUR} 条，请稍后再试。",
        )
    return db.add_message(
        name=payload.name,
        contact=payload.contact,
        content=payload.content,
        ip=ctx.ip,
        user_agent=ctx.header("user-agent"),
    )


# ---------------- 后台 ----------------
@route("POST", r"/api/admin/login")
def api_admin_login(ctx: "Context") -> Any:
    try:
        payload = LoginIn(**ctx.json_body())
    except ValueError as exc:
        raise ApiError(422, str(exc)) from exc
    token = views.login(payload.username, payload.password)
    if not token:
        raise ApiError(401, "用户名或密码错误")
    return {"token": token, "expires_in": util.TOKEN_TTL, "user": payload.username}


@route("POST", r"/api/admin/logout")
def api_admin_logout(ctx: "Context") -> Any:
    ctx.require_admin()
    views.revoke(ctx.header("x-admin-token"))
    return {"ok": True}


@route("GET", r"/api/admin/overview")
def api_admin_overview(ctx: "Context") -> Any:
    ctx.require_admin()
    stats = db.visit_stats()
    return {
        "total_views": stats["total_views"],
        "today_views": stats["today_views"],
        "today_visitors": stats["today_visitors"],
        "total_messages": db.message_count(),
        "total_visitors": stats["total_visitors"],
        "daily": stats["daily"],
        "top_pages": stats["top_pages"],
        "recent_visits": stats["recent"],
    }


@route("GET", r"/api/admin/messages")
def api_admin_messages(ctx: "Context") -> Any:
    ctx.require_admin()
    approved_raw = ctx.query_one("approved")
    approved = int(approved_raw) if approved_raw not in (None, "") else None
    return db.list_messages(
        page=max(1, ctx.query_int("page", 1)),
        page_size=min(100, max(1, ctx.query_int("page_size", 10))),
        keyword=(ctx.query_one("keyword") or "").strip(),
        approved=approved,
    )


@route("PATCH", r"/api/admin/messages/(?P<message_id>\d+)")
def api_admin_review(ctx: "Context", message_id: str) -> Any:
    ctx.require_admin()
    approved = (ctx.query_one("approved") or "").lower() in ("1", "true", "yes")
    if not db.set_approved(int(message_id), approved):
        raise ApiError(404, "留言不存在")
    return {"ok": True, "id": int(message_id), "approved": approved}


@route("DELETE", r"/api/admin/messages/(?P<message_id>\d+)")
def api_admin_delete(ctx: "Context", message_id: str) -> Any:
    ctx.require_admin()
    if not db.delete_message(int(message_id)):
        raise ApiError(404, "留言不存在")
    return {"ok": True, "id": int(message_id)}


@route("GET", r"/api/health")
def api_health(ctx: "Context") -> Any:
    return {
        "status": "ok",
        "site": util.SITE_NAME,
        "version": util.VERSION,
        "server_time": util.now(),
        "database": str(util.DB_PATH),
        "admin_user": util.ADMIN_USER,
        "runtime": "stdlib",
    }


# --------------------------------------------------------------------------
# Context：把请求解析与鉴权收在一起
# --------------------------------------------------------------------------
class Context:
    def __init__(self, handler: "Handler", path: str, query: dict[str, list[str]]) -> None:
        self.handler = handler
        self.path = path
        self.query = query

    # -- 请求信息 --
    @property
    def ip(self) -> str:
        return util.client_ip(self.handler)  # type: ignore[arg-type]

    def header(self, name: str, default: str = "") -> str:
        return self.handler.headers.get(name, default) or default

    # -- 查询参数 --
    def query_one(self, key: str) -> Optional[str]:
        values = self.query.get(key)
        return values[0] if values else None

    def query_int(self, key: str, default: int) -> int:
        raw = self.query_one(key)
        try:
            return int(raw) if raw is not None else default
        except ValueError:
            return default

    # -- 请求体 --
    def _drain(self) -> None:
        """把未读的请求体读干净，否则 HTTP/1.1 长连接会串包。"""
        try:
            remaining = int(getattr(self.handler, "_body_remaining", 0) or 0)
        except (TypeError, ValueError):
            remaining = 0
        if remaining > 0:
            self.handler.rfile.read(remaining)
            self.handler._body_remaining = 0  # type: ignore[attr-defined]

    def json_body(self, silent: bool = False) -> dict[str, Any]:
        self._drain()
        length = int(self.handler.headers.get("content-length") or 0)
        if length <= 0:
            if silent:
                return {}
            raise ApiError(400, "请求体为空")
        raw = self.handler.rfile.read(min(length, 64 * 1024))
        self.handler._body_remaining = max(0, length - len(raw))  # type: ignore[attr-defined]
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            if silent:
                return {}
            raise ApiError(400, "请求体不是合法 JSON")
        if not isinstance(data, dict):
            raise ApiError(400, "请求体必须是 JSON 对象")
        return data

    # -- 鉴权 --
    def require_admin(self) -> None:
        if not views.verify(self.header("x-admin-token")):
            raise ApiError(401, "未登录或登录已过期，请重新登录")


# --------------------------------------------------------------------------
# Handler
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = f"PortfolioServer/{util.VERSION}"
    protocol_version = "HTTP/1.1"

    # ---------- 输出 ----------
    def send_payload(self, status: int, payload: Any, content_type: str = "application/json; charset=utf-8") -> None:
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
        else:
            body = bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, status: int, payload: Any) -> None:
        self.send_payload(status, payload)

    def send_error_json(self, status: int, detail: str) -> None:
        self.send_json(status, {"detail": detail})

    # ---------- 文件 ----------
    def send_file(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error_json(404, "文件不存在")
            return
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def render_page(self, page: str, bootstrap: Optional[dict[str, Any]] = None) -> None:
        template_path = util.PAGE_DIR / page
        if not template_path.exists():
            self.send_error_json(404, f"页面不存在: {page}")
            return
        html = Template(template_path.read_text(encoding="utf-8")).safe_substitute(
            site_name=util.SITE_NAME,
            version=util.VERSION,
            year=datetime.now().year,
            client_ip=self.client_address[0] if self.client_address else "unknown",
        )
        if bootstrap is not None:
            inline = (
                "<script>window.__SITE_DATA__ = "
                + json.dumps(bootstrap, ensure_ascii=False)
                + ";</script>"
            )
            html = html.replace("</body>", f"{inline}\n</body>")
        self.send_payload(200, html, "text/html; charset=utf-8")

    # ---------- 分发 ----------
    def handle_request(self) -> None:  # noqa: C901
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)

        # 去掉结尾多余的斜杠（根路径除外）
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        try:
            if self.command in ("GET", "HEAD"):
                if path in ("/", "/index.html"):
                    # 把简历数据内联，首屏不需要额外请求
                    self.render_page("index.html", self.bootstrap_data())
                    return
                if path in ("/admin", "/admin.html"):
                    self.render_page("admin.html", {"brand": util.SITE_NAME})
                    return
                if path == "/favicon.ico":
                    icon = util.STATIC_DIR / "favicon.svg"
                    if icon.exists():
                        self.send_file(icon)
                    else:
                        self.send_error_json(404, "favicon 不存在")
                    return
                if path.startswith("/static/"):
                    self.serve_static(path[len("/static/"):])
                    return
                if path == "/api/docs":
                    self.send_payload(
                        200,
                        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
                        "<title>API 文档</title></head><body style='font-family:system-ui;"
                        "background:#070b16;color:#e8eefc;padding:2.4rem;line-height:1.9'>"
                        "<h1>接口清单</h1>"
                        "<p>零依赖标准库后端不提供 Swagger UI。安装 FastAPI 后运行 "
                        "<code>backend/app.py</code> 可访问 <code>/api/docs</code> 交互式文档。</p>"
                        "<pre style='background:#0b1120;padding:1.2rem;border-radius:12px;overflow:auto'>"
                        + "\n".join(
                            f"{method:7s} {pattern.pattern}"
                            for method, pattern, _ in ROUTES
                        )
                        + "</pre></body></html>",
                        "text/html; charset=utf-8",
                    )
                    return

            for method, pattern, func in ROUTES:
                if method != self.command:
                    continue
                matched = pattern.match(path)
                if not matched:
                    continue
                result = func(Context(self, path, query), **matched.groupdict())
                status = 200
                if self.command == "POST" and path == "/api/messages":
                    status = 201
                self.send_json(status, result)
                return

            self.send_error_json(404, f"接口或页面不存在: {self.command} {path}")

        except ApiError as exc:
            self.send_error_json(exc.status, exc.detail)
        except Exception as exc:  # noqa: BLE001 —— 兜底，避免连接悬挂
            import traceback

            traceback.print_exc()
            self.send_error_json(500, f"服务器内部错误: {exc}")

    def serve_static(self, relative: str) -> None:
        target = (util.STATIC_DIR / relative).resolve()
        if not str(target).startswith(str(util.STATIC_DIR.resolve())) or not target.is_file():
            self.send_error_json(404, "静态资源不存在")
            return
        self.send_file(target)

    @staticmethod
    def bootstrap_data() -> dict[str, Any]:
        """首页首屏数据：简历 + 技能，避免额外的接口往返。"""
        resume = util.read_json(util.RESUME_PATH)
        return {
            "resume": resume,
            "skills": {"skills": resume["skills"], "learning": resume["learning"]},
        }

    def do_GET(self) -> None:  # noqa: N802
        self.handle_request()

    def do_HEAD(self) -> None:  # noqa: N802
        self.handle_request()

    def do_POST(self) -> None:  # noqa: N802
        self.handle_request()

    def do_PATCH(self) -> None:  # noqa: N802
        self.handle_request()

    def do_DELETE(self) -> None:  # noqa: N802
        self.handle_request()

    def log_message(self, fmt: str, *args: Any) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        sys.stdout.write(f"[{stamp}] {self.address_string()} {fmt % args}\n")
        sys.stdout.flush()


def main() -> None:
    util.ensure_dirs()
    db.init()
    server = ThreadingHTTPServer((util.HOST, util.PORT), Handler)
    server.daemon_threads = True

    # 复用 app.py 的横幅与安全打印，避免两处文案/编码处理不一致
    banner("零依赖标准库模式")
    say(f"  已注册接口 {len(ROUTES)} 个，数据库 {util.DB_PATH}")
    say()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        say("\n已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
