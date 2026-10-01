"""静态一致性检查：确认 JS 里用到的选择器在页面 HTML 中都存在。

浏览器可视化渲染在无沙箱环境不可用时，用这种方式兜住
「选择器写错导致页面空白」这类最常见的问题。

用法：python tests/check_frontend.py
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAGES = {
    "frontend/pages/index.html": "frontend/static/js/main.js",
    "frontend/pages/admin.html": "frontend/static/js/admin.js",
}

ID_RE = re.compile(r"""\$\(\s*['"]#([A-Za-z0-9_-]+)['"]""")
CLASS_RE = re.compile(r"""\$\(\s*['"]\.([A-Za-z0-9_-]+)['"]""")

results = []
ok = True

for page, script in PAGES.items():
    html = (BASE / page).read_text(encoding="utf-8")
    js = (BASE / script).read_text(encoding="utf-8")

    ids_in_html = set(re.findall(r'id="([^"]+)"', html))
    ids_in_js = set(ID_RE.findall(js))
    missing_ids = sorted(ids_in_js - ids_in_html)
    unused_ids = sorted(ids_in_html - ids_in_js)

    classes_in_html = set(re.findall(r'class="([^"]+)"', html))
    flat = set()
    for group in classes_in_html:
        flat.update(group.split())
    classes_in_js = set(CLASS_RE.findall(js))
    missing_classes = sorted(c for c in classes_in_js if c not in flat)

    # JS 里动态拼接的类名/临时元素不算问题，这里只关注 id 缺失
    results.append({
        "page": page,
        "script": script,
        "ids_in_js": len(ids_in_js),
        "missing_ids": missing_ids,
        "missing_classes": missing_classes,
        "unused_ids": unused_ids,
    })
    if missing_ids:
        ok = False

# 首页 <section id> 与导航 href="#..." 对齐，避免导航点了没反应
index = (BASE / "frontend/pages/index.html").read_text(encoding="utf-8")
anchors = set(re.findall(r'href="#([A-Za-z0-9_-]+)"', index))
section_ids = set(re.findall(r'<section[^>]*id="([^"]+)"', index))
broken_anchors = sorted(anchors - section_ids)
if broken_anchors:
    ok = False

# resume.json 结构完整性
resume = json.loads((BASE / "data/resume.json").read_text(encoding="utf-8"))
required = ["profile", "education", "experience", "projects", "skills", "learning", "campus", "about"]
missing_keys = [k for k in required if k not in resume]
if missing_keys:
    ok = False
for project in resume["projects"]:
    for field in ["id", "title", "summary", "tags", "points", "metrics"]:
        if field not in project:
            ok = False
            results.append({"error": f"项目 {project.get('id')} 缺少字段 {field}"})

report = {
    "ok": ok,
    "anchor_check": {"anchors": sorted(anchors), "broken": broken_anchors},
    "resume_missing_keys": missing_keys,
    "pages": results,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
