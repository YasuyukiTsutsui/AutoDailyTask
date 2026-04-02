#!/usr/bin/env python3
"""
serve-reports.py
reports/ ディレクトリのレポートを閲覧できる Web サーバー

使用方法:
    python3 scripts/serve-reports.py [--port 8080]
"""

import argparse
import html as html_mod
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

REPORTS_DIR = Path(__file__).parent.parent / "reports"

INDEX_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AutoDailyTask レポート一覧</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f1f5f9; color: #1e293b; min-height: 100vh; }

  /* --- header --- */
  header { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white;
           padding: 24px 32px; }
  header h1 { font-size: 1.3rem; font-weight: 700; }
  header p  { font-size: 0.82rem; opacity: 0.8; margin-top: 4px; }

  /* --- toolbar --- */
  .toolbar { max-width: 960px; margin: 20px auto 0; padding: 0 16px;
             display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .search  { flex: 1; min-width: 180px; padding: 9px 14px; border: 1px solid #e2e8f0;
             border-radius: 8px; font-size: 0.88rem; outline: none; }
  .search:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,.12); }
  .filters { display: flex; gap: 6px; flex-wrap: wrap; }
  .filter-btn { padding: 6px 14px; border: 1px solid #e2e8f0; border-radius: 20px;
                background: white; font-size: 0.78rem; font-weight: 600; cursor: pointer;
                transition: all .15s; color: #475569; }
  .filter-btn:hover { border-color: #4f46e5; color: #4f46e5; }
  .filter-btn.active { background: #4f46e5; color: white; border-color: #4f46e5; }
  .view-toggle { display: flex; border: 1px solid #e2e8f0; border-radius: 8px;
                 overflow: hidden; background: white; }
  .view-btn { padding: 6px 10px; border: none; background: transparent;
              cursor: pointer; font-size: 0.85rem; color: #64748b; }
  .view-btn.active { background: #4f46e5; color: white; }

  /* --- layout --- */
  main { max-width: 960px; margin: 16px auto 32px; padding: 0 16px; }

  /* --- category --- */
  .category { margin-bottom: 28px; }
  .category-header { display: flex; align-items: center; gap: 10px; cursor: pointer;
                     padding: 10px 0; user-select: none; }
  .category-icon { font-size: 1.3rem; }
  .category-name { font-size: 1rem; font-weight: 700; color: #1e293b; }
  .category-count { font-size: 0.72rem; background: #e2e8f0; color: #475569;
                    padding: 2px 8px; border-radius: 10px; font-weight: 600; }
  .category-toggle { margin-left: auto; font-size: 0.8rem; color: #94a3b8;
                     transition: transform .2s; }
  .category.collapsed .category-toggle { transform: rotate(-90deg); }
  .category.collapsed .category-body { display: none; }

  /* --- date group --- */
  .date-group { margin-left: 8px; margin-bottom: 16px; }
  .date-label { font-size: 0.72rem; font-weight: 700; letter-spacing: .06em;
                color: #94a3b8; margin-bottom: 6px; padding-left: 4px; }

  /* --- card (list view) --- */
  .card { background: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
          display: flex; align-items: center; padding: 12px 16px; margin-bottom: 6px;
          text-decoration: none; color: inherit; transition: all .15s; }
  .card:hover { box-shadow: 0 4px 14px rgba(79,70,229,.15); transform: translateY(-1px); }
  .card .icon { font-size: 1.3rem; margin-right: 12px; flex-shrink: 0; }
  .card .info { flex: 1; min-width: 0; }
  .card .name { font-weight: 600; font-size: 0.88rem; white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }
  .card .meta { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
  .card .preview { font-size: 0.78rem; color: #64748b; margin-top: 4px;
                   line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2;
                   -webkit-box-orient: vertical; overflow: hidden; }
  .badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 10px;
           margin-left: 6px; font-weight: 700; text-transform: uppercase;
           vertical-align: middle; }
  .badge.pdf  { background: #fee2e2; color: #991b1b; }
  .badge.html { background: #dcfce7; color: #166534; }

  /* --- grid view --- */
  .grid-view .date-group { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
                           gap: 10px; }
  .grid-view .date-label { grid-column: 1 / -1; }
  .grid-view .card { flex-direction: column; align-items: flex-start; padding: 16px; }
  .grid-view .card .icon { margin: 0 0 8px 0; font-size: 1.6rem; }
  .grid-view .card .name { white-space: normal; word-break: break-all; }

  /* --- empty / hidden --- */
  .empty { color: #94a3b8; text-align: center; padding: 48px; }
  .hidden { display: none !important; }
  .no-results { text-align: center; color: #94a3b8; padding: 32px; display: none; }
  .no-results.visible { display: block; }
</style>
</head>
<body>

<header>
  <h1>AutoDailyTask レポート一覧</h1>
  <p><span id="visible-count">{count}</span> 件のレポート</p>
</header>

<div class="toolbar">
  <input class="search" type="text" placeholder="レポートを検索…" id="search">
  <div class="filters" id="filters">
    <button class="filter-btn active" data-category="all">すべて</button>
  </div>
  <div class="view-toggle">
    <button class="view-btn active" data-view="list" title="リスト表示">☰</button>
    <button class="view-btn" data-view="grid" title="グリッド表示">⊞</button>
  </div>
</div>

<main id="main">
{body}
<p class="no-results" id="no-results">該当するレポートが見つかりません</p>
</main>

<script>
(function() {
  const search = document.getElementById('search');
  const main = document.getElementById('main');
  const noResults = document.getElementById('no-results');
  const visibleCount = document.getElementById('visible-count');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const viewBtns = document.querySelectorAll('.view-btn');

  let activeCategory = 'all';

  // --- category collapse ---
  document.querySelectorAll('.category-header').forEach(h => {
    h.addEventListener('click', () => h.parentElement.classList.toggle('collapsed'));
  });

  // --- filter ---
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.category;
      applyFilters();
    });
  });

  // --- search ---
  search.addEventListener('input', () => applyFilters());

  // --- view toggle ---
  viewBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      viewBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      main.classList.toggle('grid-view', btn.dataset.view === 'grid');
    });
  });

  function applyFilters() {
    const q = search.value.toLowerCase();
    let count = 0;

    document.querySelectorAll('.category').forEach(cat => {
      const catName = cat.dataset.category;
      const catMatch = activeCategory === 'all' || catName === activeCategory;
      let catVisible = 0;

      cat.querySelectorAll('.date-group').forEach(dg => {
        let groupVisible = 0;
        dg.querySelectorAll('.card').forEach(card => {
          const text = card.dataset.name.toLowerCase();
          const show = catMatch && (!q || text.includes(q));
          card.classList.toggle('hidden', !show);
          if (show) { groupVisible++; count++; }
        });
        // hide date label if no cards visible
        dg.classList.toggle('hidden', groupVisible === 0);
      });

      cat.classList.toggle('hidden', !catMatch || catVisible === 0 && !cat.querySelector('.card:not(.hidden)'));
    });

    visibleCount.textContent = count;
    noResults.classList.toggle('visible', count === 0);
  }
})();
</script>
</body>
</html>
"""

# カテゴリ定義: ファイル名プレフィックス → (表示名, アイコン)
CATEGORIES = {
    "ai-report":             ("AI動向レポート", "🤖"),
    "trading-card-release":  ("トレカ新発売情報", "🃏"),
    "fashion-report":        ("ファッションレポート", "👗"),
    "travel-plan":           ("国内旅行プラン", "✈️"),
}
DEFAULT_CATEGORY = ("その他", "📝")


def extract_summary(path: Path, max_len: int = 120) -> str:
    """HTMLファイルから概要テキストを抽出する"""
    if path.suffix != ".html":
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        # .summary div の中身を優先
        m = re.search(r'<div class="summary"[^>]*>(.*?)</div>', text, re.DOTALL)
        if m:
            snippet = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)
            if len(snippet) > max_len:
                snippet = snippet[:max_len] + "…"
            return snippet
        # fallback: <title>
        m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    except Exception:
        pass
    return ""


def classify(filename: str) -> str:
    """ファイル名からカテゴリキーを判定する"""
    for prefix in sorted(CATEGORIES.keys(), key=len, reverse=True):
        if filename.startswith(prefix):
            return prefix
    return "_other"


def _render(count: int, body: str) -> str:
    """INDEX_HTML のプレースホルダを安全に置換する（CSS/JS の {} を壊さない）"""
    return INDEX_HTML.replace("{count}", str(count)).replace("{body}", body)


def build_index():
    if not REPORTS_DIR.exists():
        return _render(0, '<p class="empty">reports/ ディレクトリが見つかりません</p>')

    # ファイルを カテゴリ → 日付 → [Path] の構造に整理
    tree: dict[str, dict[str, list[Path]]] = {}
    for f in sorted(REPORTS_DIR.iterdir()):
        if f.suffix not in (".pdf", ".html"):
            continue
        cat = classify(f.name)
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        date_key = m.group() if m else "日付なし"
        tree.setdefault(cat, {}).setdefault(date_key, []).append(f)

    if not tree:
        return _render(0, '<p class="empty">レポートがまだありません</p>')

    # フィルタボタン生成
    filter_buttons = []
    # カテゴリ順: 定義順 → _other は末尾
    cat_order = [k for k in CATEGORIES if k in tree]
    if "_other" in tree:
        cat_order.append("_other")

    for cat_key in cat_order:
        label, _ = CATEGORIES.get(cat_key, DEFAULT_CATEGORY)
        n = sum(len(fs) for fs in tree[cat_key].values())
        filter_buttons.append(
            f'<button class="filter-btn" data-category="{cat_key}">{label} ({n})</button>'
        )

    # カテゴリ → 日付 → カードの HTML 生成
    rows = []
    total = 0

    for cat_key in cat_order:
        dates = tree[cat_key]
        label, icon = CATEGORIES.get(cat_key, DEFAULT_CATEGORY)
        cat_count = sum(len(fs) for fs in dates.values())

        rows.append(f'<div class="category" data-category="{cat_key}">')
        rows.append(
            f'<div class="category-header">'
            f'<span class="category-icon">{icon}</span>'
            f'<span class="category-name">{label}</span>'
            f'<span class="category-count">{cat_count}</span>'
            f'<span class="category-toggle">▼</span>'
            f'</div>'
            f'<div class="category-body">'
        )

        for date_key in sorted(dates.keys(), reverse=True):
            file_list = dates[date_key]
            rows.append(f'<div class="date-group">')
            rows.append(f'<div class="date-label">{date_key}</div>')

            for f in sorted(file_list, key=lambda p: (p.suffix != ".pdf", p.name)):
                size_kb = f.stat().st_size // 1024
                ext = f.suffix
                file_icon = "📄" if ext == ".pdf" else "🌐"
                badge_cls = "pdf" if ext == ".pdf" else "html"
                ext_label = ext.lstrip(".").upper()
                summary = html_mod.escape(extract_summary(f))
                preview_html = f'<div class="preview">{summary}</div>' if summary else ""
                rows.append(
                    f'<a class="card" href="/reports/{f.name}" target="_blank" data-name="{f.name}">'
                    f'<span class="icon">{file_icon}</span>'
                    f'<div class="info">'
                    f'<div class="name">{f.name}<span class="badge {badge_cls}">{ext_label}</span></div>'
                    f'<div class="meta">{size_kb} KB</div>'
                    f'{preview_html}'
                    f'</div>'
                    f'</a>'
                )
                total += 1

            rows.append('</div>')  # .date-group

        rows.append('</div></div>')  # .category-body .category

    # フィルタボタンをツールバーに挿入（テンプレートの「すべて」ボタンの後に追加）
    body_html = "\n".join(rows)
    filter_html = "\n".join(filter_buttons)

    html = _render(total, body_html)
    # 「すべて」ボタンの直後にカテゴリボタンを挿入
    html = html.replace(
        '<button class="filter-btn active" data-category="all">すべて</button>',
        '<button class="filter-btn active" data-category="all">すべて</button>\n    ' + filter_html,
    )
    return html


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def send_file(self, path: Path):
        ext = path.suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".html": "text/html; charset=utf-8",
        }
        ctype = content_types.get(ext, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = unquote(self.path.split("?")[0])

        if path in ("/", "/index.html"):
            html = build_index().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if path.startswith("/reports/"):
            filename = path[len("/reports/"):]
            filepath = REPORTS_DIR / filename
            if filepath.exists() and filepath.parent == REPORTS_DIR:
                self.send_file(filepath)
                return

        self.send_error(404, "Not Found")


def main():
    parser = argparse.ArgumentParser(description="AutoDailyTask レポートビューア")
    parser.add_argument("--port", type=int, default=8080, help="ポート番号 (default: 8080)")
    args = parser.parse_args()

    server = HTTPServer(("localhost", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"レポートビューア起動中: {url}")
    print("終了するには Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました")


if __name__ == "__main__":
    main()
