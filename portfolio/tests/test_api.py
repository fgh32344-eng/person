"""端到端接口测试：覆盖页面、简历 API、统计、留言与后台管理。

用法：先启动服务（python backend/app.py 或 python backend/server.py），再执行
    python tests/test_api.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
REPORT = Path(__file__).resolve().parent / "test_report.json"
results = []


def call(method, path, body=None, headers=None, raw=False):
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read()
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        status = exc.code
        ctype = exc.headers.get("Content-Type", "")
    if raw:
        return status, payload.decode("utf-8", "replace"), ctype
    try:
        return status, json.loads(payload.decode("utf-8")), ctype
    except Exception:
        return status, payload.decode("utf-8", "replace")[:200], ctype


def check(name, condition, extra=""):
    results.append({"name": name, "ok": bool(condition), "extra": str(extra)[:180]})


# ---------- 页面 ----------
status, html, ctype = call("GET", "/", raw=True)
check("GET / 返回 200", status == 200, status)
check("首页包含姓名", "王耀威" in html, "")
check("首页内联 __SITE_DATA__", "__SITE_DATA__" in html, "")
check("中文编码正确", "charset=utf-8" in ctype.lower(), ctype)

status, html, _ = call("GET", "/admin", raw=True)
check("GET /admin 返回 200", status == 200, status)
check("后台页含登录表单", 'id="loginForm"' in html, "")

status, css, ctype = call("GET", "/static/css/style.css", raw=True)
check("静态 CSS 可访问", status == 200 and "--cyan" in css, status)
status, js, _ = call("GET", "/static/js/main.js", raw=True)
check("静态 JS 可访问", status == 200 and "renderProfile" in js, status)
status, _, ctype = call("GET", "/static/assets/avatar.svg", raw=True)
check("头像 SVG 可访问", status == 200 and "image/svg" in ctype, ctype)
status, _, _ = call("GET", "/favicon.ico", raw=True)
check("favicon 可访问", status == 200, status)
status, _, _ = call("GET", "/static/../backend/app.py", raw=True)
check("静态目录穿越被拦截", status == 404, status)

# ---------- 简历 API ----------
status, resume, _ = call("GET", "/api/resume")
check("GET /api/resume", status == 200 and resume["profile"]["name"] == "王耀威", status)
check("简历含 4 个项目", len(resume.get("projects", [])) == 4, len(resume.get("projects", [])))
status, profile, _ = call("GET", "/api/profile")
check("GET /api/profile", status == 200 and profile["phone"] == "183-2577-3203", status)
status, projects, _ = call("GET", "/api/projects?tag=YOLO")
check("GET /api/projects 过滤生效", status == 200 and projects["total"] >= 1, projects.get("total"))
status, skills, _ = call("GET", "/api/skills")
check("GET /api/skills", status == 200 and len(skills["skills"]) == 5, len(skills.get("skills", [])))

# ---------- 统计 ----------
status, visit, _ = call("POST", "/api/visit", {"path": "/"})
check("POST /api/visit", status == 200 and visit["total_views"] >= 1, visit.get("total_views"))
status, stats, _ = call("GET", "/api/stats")
check("GET /api/stats 有 14 天序列", status == 200 and len(stats["daily"]) == 14, len(stats.get("daily", [])))
check("统计含今日访问", stats.get("today_views", 0) >= 1, stats.get("today_views"))

# ---------- 留言 ----------
status, created, _ = call("POST", "/api/messages",
                          {"name": "测试访客", "contact": "test@example.com", "content": "接口自测留言 ✅"})
check("POST /api/messages 创建成功", status == 201 and created.get("id"), (status, created))
msg_id = created.get("id") if isinstance(created, dict) else None

status, listed, _ = call("GET", "/api/messages?page=1&page_size=5")
check("GET /api/messages 列表", status == 200 and listed["total"] >= 1, listed.get("total"))
check("公开列表不含联系方式", listed["items"] and not listed["items"][0].get("contact"), "")

status, bad, _ = call("POST", "/api/messages", {"name": "x", "content": "   "})
check("空留言被拒绝", status in (400, 422), status)

status, _ , _ = call("POST", "/api/messages", {"name": "刷屏", "content": "spam"})
check("重复留言触发限流或成功", status in (201, 429), status)

# ---------- 后台鉴权 ----------
status, _, _ = call("GET", "/api/admin/overview")
check("未登录访问后台接口返回 401", status == 401, status)

status, login, _ = call("POST", "/api/admin/login", {"username": "admin", "password": "wrong"})
check("错误口令登录失败", status == 401, status)

status, login, _ = call("POST", "/api/admin/login", {"username": "admin", "password": "admin123"})
check("正确口令登录成功", status == 200 and login.get("token"), status)
token = login.get("token", "")
auth = {"x-admin-token": token}

status, overview, _ = call("GET", "/api/admin/overview", headers=auth)
check("后台概览可读", status == 200 and overview["total_views"] >= 1, status)
check("概览含最近访问", len(overview.get("recent_visits", [])) >= 1, len(overview.get("recent_visits", [])))

status, admin_msgs, _ = call("GET", "/api/admin/messages?page=1&page_size=10", headers=auth)
check("后台留言列表可读", status == 200 and admin_msgs["total"] >= 1, status)
check("后台列表含 IP 字段", "ip" in (admin_msgs["items"][0] if admin_msgs["items"] else {}), "")

status, kw, _ = call("GET", "/api/admin/messages?keyword=" + urllib.parse.quote("自测"), headers=auth)
check("后台关键字搜索", status == 200 and kw["total"] >= 1, kw.get("total"))

status, hide, _ = call("PATCH", f"/api/admin/messages/{msg_id}?approved=0", headers=auth)
check("隐藏留言成功", status == 200 and hide.get("approved") is False, (status, hide))

status, public_after, _ = call("GET", "/api/messages?page=1&page_size=50")
visible_ids = [m["id"] for m in public_after["items"]]
check("隐藏后不在公开列表", msg_id not in visible_ids, visible_ids)

status, show, _ = call("PATCH", f"/api/admin/messages/{msg_id}?approved=1", headers=auth)
check("重新公开留言成功", status == 200 and show.get("approved") is True, (status, show))

status, _, _ = call("POST", "/api/admin/logout", headers=auth)
check("登出成功", status == 200, status)
status, _, _ = call("GET", "/api/admin/overview", headers=auth)
check("登出后令牌失效", status == 401, status)

# ---------- 清理与收尾 ----------
status, login2, _ = call("POST", "/api/admin/login", {"username": "admin", "password": "admin123"})
auth2 = {"x-admin-token": login2.get("token", "")}
status, _, _ = call("DELETE", f"/api/admin/messages/{msg_id}", headers=auth2)
check("删除测试留言", status == 200, status)

status, health, _ = call("GET", "/api/health")
check("健康检查", status == 200 and health["status"] == "ok", status)
check("运行模式为 stdlib", health.get("runtime") == "stdlib", health.get("runtime"))

# ---------- 汇总 ----------
failed = [r for r in results if not r["ok"]]
summary = {
    "total": len(results),
    "passed": len(results) - len(failed),
    "failed": len(failed),
    "failures": failed,
}
with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump({"summary": summary, "results": results}, fh, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False))
sys.exit(1 if failed else 0)
