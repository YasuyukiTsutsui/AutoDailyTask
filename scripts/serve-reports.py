#!/usr/bin/env python3
"""
serve-reports.py
reports/ ディレクトリのレポートを閲覧できる Web サーバー

機能:
  - ダッシュボード（最新レポート・統計・ピン留め）
  - カテゴリ別ブラウズ（お気に入り・タグ・メモ付き）
  - レポート本文の全文検索
  - レポート差分比較
  - PDF一括エクスポート（ZIP）
  - スキル実行

使用方法:
    python3 scripts/serve-reports.py [--port 8080]
"""

import argparse
import difflib
import html as html_mod
import io
import json
import re
import subprocess
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

REPORTS_DIR = Path(__file__).parent.parent / "reports"
PROJECT_DIR = Path(__file__).parent.parent
METADATA_PATH = REPORTS_DIR / ".metadata.json"

# ---------------------------------------------------------------------------
# スキル定義: (表示名, アイコン, 引数なしで実行可能か, プライベート)
# ---------------------------------------------------------------------------
SKILLS = {
    "ai-report":            ("AI動向レポート", "🤖", True, False),
    "trading-card-release": ("トレカ新発売情報", "🃏", True, False),
    "restock-watch":        ("再販ウォッチ", "🔄", True, False),
    "vtuber-riona":         ("VTuber推し活", "🎤", True, True),
    "fashion-report":       ("ファッションレポート", "👗", False, True),
    "gift-concierge":       ("プレゼント提案", "🎁", False, False),
    "travel-plan":          ("国内旅行プラン", "✈️", False, True),
    "cleanup-reports":      ("レポート整理", "🧹", True, False),
}

SKILL_FORMS = {
    "fashion-report": {
        "title": "ファッションレポート",
        "icon": "👗",
        "description": "好みやシーンに合わせたファッション提案を生成します",
        "fields": [
            ("gender", "性別", "select", "", True,
             [("メンズ", "メンズ"), ("レディース", "レディース")]),
            ("age", "年代", "select", "", False,
             [("10代", "10代"), ("20代", "20代"), ("30代", "30代"),
              ("40代", "40代"), ("50代", "50代")]),
            ("body_type", "体型", "text", "例: 170cm 細身", False, None),
            ("style", "好みのスタイル", "text", "例: きれいめ、カジュアル、モード", True, None),
            ("scene", "利用シーン", "text", "例: 通勤、デート、休日", True, None),
            ("item", "気になるアイテム", "text", "例: ジャケット、スニーカー", False, None),
        ],
    },
    "gift-concierge": {
        "title": "プレゼント提案",
        "icon": "🎁",
        "description": "相手の情報をもとにギフト提案レポートを生成します",
        "fields": [
            ("relationship", "相手との関係", "text", "例: 恋人、友人、上司、同僚", True, None),
            ("target", "相手の性別・年代", "text", "例: 女性30代", True, None),
            ("occasion", "贈るシーン", "text", "例: 誕生日、結婚祝い、手土産", True, None),
            ("budget", "予算", "text", "例: 5000円、1万円〜2万円", True, None),
            ("personality", "相手の印象・性格", "text", "例: おしゃれ好き、アウトドア派", False, None),
            ("hobby", "趣味・ライフスタイル", "text", "例: カフェ巡り、ゴルフ", False, None),
            ("ng", "避けたいもの", "text", "例: 食品アレルギーあり、香りNG", False, None),
        ],
    },
    "travel-plan": {
        "title": "国内旅行プラン",
        "icon": "✈️",
        "description": "旅行プランを松竹梅グレード別に提案します",
        "fields": [
            ("destination", "行き先", "text", "例: 箱根、京都（未定なら「おまかせ」）", True, None),
            ("period", "時期・日数", "text", "例: GW 1泊2日、7月 2泊3日", True, None),
            ("party", "人数・構成", "text", "例: カップル、家族4人、友人3人", True, None),
            ("budget", "予算（1人あたり）", "text", "例: 3万円、5万円", False, None),
            ("priority", "重視するポイント", "text", "例: グルメ、温泉、観光、のんびり", False, None),
            ("departure", "出発地", "text", "例: 東京、大阪", False, None),
        ],
    },
}

# カテゴリ定義: ファイル名プレフィックス → (表示名, アイコン, プライベートフラグ)
CATEGORIES = {
    "ai-report":             ("AI動向レポート", "🤖", False),
    "trading-card-release":  ("トレカ新発売情報", "🃏", False),
    "restock-watch":         ("再販ウォッチ", "🔄", False),
    "fashion-report":        ("ファッションレポート", "👗", True),
    "travel-plan":           ("国内旅行プラン", "✈️", True),
    "vtuber-riona":          ("VTuber推し活", "🎀", True),
    "gift-concierge":        ("プレゼント提案", "🎁", False),
}
DEFAULT_CATEGORY = ("その他", "📝", False)

# スキル実行ジョブ管理
_jobs = {}  # type: dict

# ---------------------------------------------------------------------------
# メタデータ (お気に入り / ピン / タグ / メモ)
# ---------------------------------------------------------------------------

def load_metadata():
    if METADATA_PATH.exists():
        try:
            return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"favorites": [], "pins": [], "tags": {}, "memos": {}}


def save_metadata(data):
    METADATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def extract_summary(path, max_len=120):
    if path.suffix != ".html":
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<div class="summary"[^>]*>(.*?)</div>', text, re.DOTALL)
        if m:
            snippet = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            snippet = re.sub(r"\s+", " ", snippet)
            if len(snippet) > max_len:
                snippet = snippet[:max_len] + "…"
            return snippet
        m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    except Exception:
        pass
    return ""


def extract_text(path):
    """HTMLファイルからプレーンテキストを抽出"""
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        # body だけ取得
        m = re.search(r"<body[^>]*>(.*)</body>", raw, re.DOTALL | re.IGNORECASE)
        text = m.group(1) if m else raw
        # script/style 除去
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return ""


def classify(filename):
    for prefix in sorted(CATEGORIES.keys(), key=len, reverse=True):
        if filename.startswith(prefix):
            return prefix
    return "_other"


def search_reports(query, max_results=50):
    results = []
    q_lower = query.lower()
    if not REPORTS_DIR.exists():
        return results
    for f in sorted(REPORTS_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        if f.suffix != ".html":
            continue
        plain = extract_text(f)
        idx = plain.lower().find(q_lower)
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(plain), idx + len(query) + 80)
            snippet = plain[start:end].strip()
            cat = classify(f.name)
            label, icon, is_private = CATEGORIES.get(cat, DEFAULT_CATEGORY)
            results.append({
                "file": f.name,
                "snippet": snippet,
                "category": cat,
                "icon": icon,
                "label": label,
                "private": is_private,
            })
            if len(results) >= max_results:
                break
    return results


def generate_diff(file_a, file_b):
    path_a = REPORTS_DIR / file_a
    path_b = REPORTS_DIR / file_b
    if not path_a.exists() or not path_b.exists():
        return None
    text_a = extract_text(path_a)
    text_b = extract_text(path_b)
    lines_a = text_a.split(". ")
    lines_b = text_b.split(". ")
    diff = list(difflib.unified_diff(
        lines_a, lines_b, fromfile=file_a, tofile=file_b, lineterm=""
    ))
    return "\n".join(diff)


def export_zip(filenames):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in filenames:
            path = REPORTS_DIR / name
            if path.exists() and path.parent.resolve() == REPORTS_DIR.resolve():
                zf.write(path, name)
    buf.seek(0)
    return buf.read()


def run_skill_async(job_id, skill_name, args=""):
    job = _jobs[job_id]
    job["status"] = "running"
    job["started_at"] = time.time()
    prompt = "/%s %s" % (skill_name, args) if args else "/%s" % skill_name
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--verbose"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, timeout=600,
        )
        job["status"] = "done" if result.returncode == 0 else "error"
        job["exit_code"] = result.returncode
        output = result.stdout or result.stderr or ""
        lines = output.strip().split("\n")
        job["output"] = "\n".join(lines[-10:])
    except subprocess.TimeoutExpired:
        job["status"] = "error"
        job["output"] = "タイムアウト（10分）"
    except FileNotFoundError:
        job["status"] = "error"
        job["output"] = "claude CLI が見つかりません。PATH を確認してください。"
    except Exception as e:
        job["status"] = "error"
        job["output"] = str(e)
    job["finished_at"] = time.time()


# ---------------------------------------------------------------------------
# HTML テンプレート
# ---------------------------------------------------------------------------

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
         background: #f1f5f9; color: #1e293b; min-height: 100vh; display: flex; }

  /* --- sidebar --- */
  .sidebar { width: 260px; height: 100vh; background: white; border-right: 1px solid #e2e8f0;
             display: flex; flex-direction: column; position: fixed; top: 0; left: 0;
             z-index: 100; transition: transform .25s; overflow-y: auto; }
  .sidebar-header { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white;
                    padding: 20px; }
  .sidebar-header h1 { font-size: 1.05rem; font-weight: 700; }
  .sidebar-header p  { font-size: 0.75rem; opacity: 0.8; margin-top: 4px; }
  .sidebar-section { border-bottom: 1px solid #f1f5f9; }
  .sidebar-section-title { font-size: 0.68rem; font-weight: 700; letter-spacing: .08em;
                           text-transform: uppercase; color: #94a3b8; padding: 12px 16px;
                           margin: 0; cursor: pointer; display: flex; align-items: center;
                           justify-content: space-between; user-select: none; }
  .sidebar-section-title:hover { background: #f8fafc; }
  .sidebar-section-title::after { content: '\\25B2'; font-size: 0.55rem; transition: transform .2s; }
  .sidebar-section.collapsed .sidebar-section-title::after { transform: rotate(180deg); }
  .sidebar-section-body { padding: 0 16px 12px; }
  .sidebar-section.collapsed .sidebar-section-body { display: none; }
  .search { width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
            font-size: 0.85rem; outline: none; }
  .search:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,.12); }

  /* --- view tabs in sidebar --- */
  .view-tabs { display: flex; border-bottom: 1px solid #e2e8f0; }
  .view-tab { flex: 1; padding: 10px 4px; text-align: center; font-size: 0.72rem; font-weight: 600;
              cursor: pointer; color: #64748b; border-bottom: 2px solid transparent;
              transition: all .15s; background: none; border-top: none; border-left: none; border-right: none; }
  .view-tab:hover { color: #4f46e5; background: #f8fafc; }
  .view-tab.active { color: #4f46e5; border-bottom-color: #4f46e5; }

  /* --- sidebar nav items --- */
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px;
              border-radius: 8px; cursor: pointer; font-size: 0.85rem; color: #475569;
              transition: all .12s; font-weight: 500; }
  .nav-item:hover { background: #f1f5f9; }
  .nav-item.active { background: #eef2ff; color: #4f46e5; font-weight: 600; }
  .nav-icon { font-size: 1.1rem; width: 24px; text-align: center; flex-shrink: 0; }
  .nav-label { flex: 1; }
  .nav-count { font-size: 0.7rem; background: #e2e8f0; color: #64748b;
               padding: 1px 6px; border-radius: 8px; font-weight: 600; }
  .nav-item.active .nav-count { background: #c7d2fe; color: #4338ca; }

  /* --- toggle row --- */
  .toggle-row { display: flex; align-items: center; justify-content: space-between;
                padding: 8px 12px; border-radius: 8px; cursor: pointer;
                user-select: none; font-size: 0.85rem; color: #475569; }
  .toggle-row:hover { background: #f1f5f9; }
  .toggle-track { width: 36px; height: 20px; border-radius: 10px; background: #cbd5e1;
                  position: relative; transition: background .2s; flex-shrink: 0; }
  .toggle-thumb { width: 16px; height: 16px; border-radius: 50%; background: white;
                  position: absolute; top: 2px; left: 2px; transition: left .2s;
                  box-shadow: 0 1px 3px rgba(0,0,0,.15); }
  .toggle-row.on .toggle-track { background: #4f46e5; }
  .toggle-row.on .toggle-thumb { left: 18px; }

  /* --- view buttons in sidebar --- */
  .view-row { display: flex; gap: 6px; padding: 4px 12px; }
  .view-btn { flex: 1; padding: 6px; border: 1px solid #e2e8f0; border-radius: 8px;
              background: white; cursor: pointer; font-size: 0.82rem; color: #64748b;
              text-align: center; transition: all .12s; }
  .view-btn:hover { border-color: #4f46e5; color: #4f46e5; }
  .view-btn.active { background: #4f46e5; color: white; border-color: #4f46e5; }

  /* --- mobile hamburger --- */
  .hamburger { display: none; position: fixed; top: 12px; left: 12px; z-index: 200;
               width: 40px; height: 40px; border-radius: 10px; border: none;
               background: #4f46e5; color: white; font-size: 1.2rem; cursor: pointer;
               box-shadow: 0 2px 8px rgba(0,0,0,.15); }
  @media (max-width: 768px) {
    .sidebar { transform: translateX(-100%); }
    .sidebar.open { transform: translateX(0); box-shadow: 4px 0 20px rgba(0,0,0,.1); }
    .hamburger { display: flex; align-items: center; justify-content: center; }
    .content { margin-left: 0 !important; }
  }

  /* --- content area --- */
  .content { margin-left: 260px; flex: 1; padding: 24px; min-height: 100vh; display: none; }
  .content.active { display: block; }

  /* --- dashboard --- */
  .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
               gap: 12px; margin-bottom: 24px; }
  .stat-card { background: white; border-radius: 10px; padding: 16px; text-align: center;
               box-shadow: 0 1px 3px rgba(0,0,0,.06); }
  .stat-value { font-size: 1.8rem; font-weight: 700; color: #4f46e5; }
  .stat-label { font-size: 0.78rem; color: #64748b; margin-top: 4px; }
  .dash-section { margin-bottom: 28px; }
  .dash-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 12px;
                        padding-bottom: 6px; border-bottom: 2px solid #e2e8f0; }
  .dash-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .dash-card { background: white; border-radius: 10px; padding: 16px;
               box-shadow: 0 1px 3px rgba(0,0,0,.06); text-decoration: none; color: inherit;
               transition: all .15s; display: block; border-left: 4px solid #e2e8f0; }
  .dash-card:hover { box-shadow: 0 4px 14px rgba(79,70,229,.15); transform: translateY(-1px); }
  .dash-card.pinned { border-left-color: #f59e0b; background: #fffbeb; }
  .dash-card .dc-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .dash-card .dc-icon { font-size: 1.3rem; }
  .dash-card .dc-cat { font-size: 0.72rem; color: #64748b; }
  .dash-card .dc-title { font-weight: 600; font-size: 0.88rem; margin-bottom: 4px; }
  .dash-card .dc-date { font-size: 0.75rem; color: #94a3b8; }
  .dash-card .dc-preview { font-size: 0.78rem; color: #64748b; margin-top: 6px; line-height: 1.5;
                           display: -webkit-box; -webkit-line-clamp: 2;
                           -webkit-box-orient: vertical; overflow: hidden; }

  /* --- category (browse) --- */
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
  .private-badge { font-size: 0.65rem; background: #fef3c3; color: #854d0e;
                   padding: 2px 6px; border-radius: 8px; font-weight: 600; }
  .date-group { margin-left: 8px; margin-bottom: 16px; }
  .date-label { font-size: 0.72rem; font-weight: 700; letter-spacing: .06em;
                color: #94a3b8; margin-bottom: 6px; padding-left: 4px; }

  /* --- card --- */
  .card { background: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
          display: flex; align-items: center; padding: 12px 16px; margin-bottom: 6px;
          text-decoration: none; color: inherit; transition: all .15s; position: relative; }
  .card:hover { box-shadow: 0 4px 14px rgba(79,70,229,.15); transform: translateY(-1px); }
  .card .icon { font-size: 1.3rem; margin-right: 12px; flex-shrink: 0; }
  .card .info { flex: 1; min-width: 0; }
  .card .name { font-weight: 600; font-size: 0.88rem; white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }
  .card .meta { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
  .card .preview { font-size: 0.78rem; color: #64748b; margin-top: 4px; line-height: 1.5;
                   display: -webkit-box; -webkit-line-clamp: 2;
                   -webkit-box-orient: vertical; overflow: hidden; }
  .card .card-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
  .card .card-tag { font-size: 0.65rem; padding: 1px 6px; border-radius: 6px;
                    background: #e0e7ff; color: #3730a3; font-weight: 600; }
  .card .card-memo { font-size: 0.72rem; color: #f59e0b; margin-top: 2px;
                     font-style: italic; white-space: nowrap; overflow: hidden;
                     text-overflow: ellipsis; max-width: 300px; }
  .badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 10px; margin-left: 6px;
           font-weight: 700; text-transform: uppercase; vertical-align: middle; }
  .badge.pdf  { background: #fee2e2; color: #991b1b; }
  .badge.html { background: #dcfce7; color: #166534; }

  /* --- card action buttons --- */
  .card-actions { display: flex; gap: 4px; align-items: center; flex-shrink: 0; margin-left: 8px; }
  .card-action { width: 28px; height: 28px; border: none; border-radius: 6px;
                 background: transparent; cursor: pointer; font-size: 0.85rem;
                 display: flex; align-items: center; justify-content: center;
                 transition: all .15s; color: #94a3b8; }
  .card-action:hover { background: #f1f5f9; }
  .card-action.fav-btn.active { color: #f59e0b; }
  .card-action.pin-btn.active { color: #4f46e5; }
  .card-action.tag-btn.has-tags { color: #6366f1; }
  .card-action.memo-btn.has-memo { color: #f59e0b; }
  .card-action.compare-cb { color: #64748b; }
  .card-action.compare-cb.checked { color: #4f46e5; background: #eef2ff; }
  .delete-btn { color: #94a3b8; }
  .delete-btn:hover { background: #fee2e2; color: #dc2626; }

  /* --- bulk action bar --- */
  .bulk-bar { position: sticky; top: 0; z-index: 50; background: #4f46e5; color: white;
              padding: 10px 16px; border-radius: 10px; margin-bottom: 16px;
              display: flex; align-items: center; gap: 12px;
              box-shadow: 0 4px 12px rgba(79,70,229,.3); }
  .bulk-bar.hidden { display: none; }
  .bulk-bar span { font-size: 0.85rem; font-weight: 600; }
  .bulk-btn { padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,.3);
              background: rgba(255,255,255,.15); color: white; cursor: pointer;
              font-size: 0.82rem; font-weight: 600; transition: all .15s; }
  .bulk-btn:hover { background: rgba(255,255,255,.25); }
  .bulk-btn:disabled { opacity: .4; cursor: not-allowed; }

  /* --- search view --- */
  .search-header { margin-bottom: 20px; }
  .search-full { width: 100%; padding: 14px 18px; border: 2px solid #e2e8f0; border-radius: 12px;
                 font-size: 1rem; outline: none; }
  .search-full:focus { border-color: #4f46e5; box-shadow: 0 0 0 4px rgba(79,70,229,.1); }
  .search-hint { font-size: 0.78rem; color: #94a3b8; margin-top: 6px; }
  .search-result { background: white; border-radius: 10px; padding: 14px 16px; margin-bottom: 8px;
                   box-shadow: 0 1px 3px rgba(0,0,0,.06); }
  .search-result a { text-decoration: none; color: #4f46e5; font-weight: 600; font-size: 0.9rem; }
  .search-result a:hover { text-decoration: underline; }
  .search-result .sr-cat { font-size: 0.75rem; color: #64748b; margin-top: 2px; }
  .search-result .sr-snippet { font-size: 0.82rem; color: #475569; margin-top: 6px; line-height: 1.6; }
  .search-result .sr-snippet mark { background: #fef08a; border-radius: 2px; padding: 0 2px; }

  /* --- diff view --- */
  .diff-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5);
                  display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .diff-overlay.hidden { display: none; }
  .diff-dialog { background: white; border-radius: 12px; max-width: 900px; width: 95%;
                 max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,.2); }
  .diff-dialog-header { padding: 20px 24px; border-bottom: 1px solid #e2e8f0;
                        display: flex; align-items: center; justify-content: space-between; }
  .diff-dialog-header h3 { font-size: 1rem; }
  .diff-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #64748b; }
  .diff-body { padding: 16px 24px; font-family: monospace; font-size: 0.8rem; white-space: pre-wrap;
               line-height: 1.6; max-height: 65vh; overflow-y: auto; }
  .diff-body .diff-add { background: #dcfce7; color: #166534; }
  .diff-body .diff-del { background: #fee2e2; color: #991b1b; }
  .diff-body .diff-hdr { color: #6366f1; font-weight: 700; }

  /* --- modals --- */
  .dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4);
                    display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .dialog-overlay.hidden { display: none; }
  .dialog { background: white; border-radius: 12px; padding: 24px; max-width: 400px;
            width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,.2); }
  .dialog h3 { font-size: 1rem; margin-bottom: 8px; }
  .dialog p { font-size: 0.85rem; color: #64748b; margin-bottom: 16px; word-break: break-all; }
  .dialog-actions { display: flex; gap: 8px; justify-content: flex-end; }
  .dialog-actions button { padding: 8px 18px; border-radius: 8px; font-size: 0.85rem;
                           font-weight: 600; cursor: pointer; border: 1px solid #e2e8f0; }
  .btn-cancel { background: white; color: #475569; }
  .btn-cancel:hover { background: #f1f5f9; }
  .btn-delete { background: #dc2626; color: white; border-color: #dc2626; }
  .btn-delete:hover { background: #b91c1c; }

  /* --- tag edit modal --- */
  .tag-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4);
                 display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .tag-overlay.hidden { display: none; }
  .tag-dialog { background: white; border-radius: 12px; padding: 24px; max-width: 420px;
                width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,.2); }
  .tag-dialog h3 { font-size: 1rem; margin-bottom: 12px; }
  .tag-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; min-height: 28px; }
  .tag-item { font-size: 0.78rem; padding: 3px 10px; border-radius: 12px;
              background: #e0e7ff; color: #3730a3; font-weight: 600; cursor: pointer;
              display: flex; align-items: center; gap: 4px; }
  .tag-item:hover { background: #fee2e2; color: #991b1b; }
  .tag-input-row { display: flex; gap: 6px; }
  .tag-input { flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
               font-size: 0.85rem; outline: none; }
  .tag-add-btn { padding: 8px 14px; background: #4f46e5; color: white; border: none;
                 border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }

  /* --- memo edit modal --- */
  .memo-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4);
                  display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .memo-overlay.hidden { display: none; }
  .memo-dialog { background: white; border-radius: 12px; padding: 24px; max-width: 420px;
                 width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,.2); }
  .memo-dialog h3 { font-size: 1rem; margin-bottom: 12px; }
  .memo-textarea { width: 100%; min-height: 80px; padding: 10px 12px; border: 1px solid #e2e8f0;
                   border-radius: 8px; font-size: 0.85rem; outline: none; resize: vertical;
                   font-family: inherit; }
  .memo-textarea:focus { border-color: #4f46e5; }
  .memo-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }

  /* --- skill form modal --- */
  .form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4);
                  display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .form-overlay.hidden { display: none; }
  .form-dialog { background: white; border-radius: 12px; max-width: 480px; width: 90%;
                 max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,.2); }
  .form-dialog-header { padding: 20px 24px 0; }
  .form-dialog-header h3 { font-size: 1.05rem; margin-bottom: 4px; }
  .form-dialog-header p { font-size: 0.8rem; color: #64748b; }
  .form-dialog-body { padding: 16px 24px; }
  .form-field { margin-bottom: 14px; }
  .form-field label { display: block; font-size: 0.82rem; font-weight: 600; color: #374151;
                      margin-bottom: 4px; }
  .form-field label .req { color: #ef4444; margin-left: 2px; }
  .form-field input, .form-field select {
    width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
    font-size: 0.85rem; outline: none; background: white; }
  .form-field input:focus, .form-field select:focus {
    border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,.12); }
  .form-dialog-footer { padding: 0 24px 20px; display: flex; gap: 8px; justify-content: flex-end; }
  .btn-submit { background: #4f46e5; color: white; border: none; padding: 8px 20px;
                border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; }
  .btn-submit:hover { background: #4338ca; }
  .btn-submit:disabled { opacity: .5; cursor: not-allowed; }

  /* --- skill buttons --- */
  .skill-btn { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px;
               border: 1px solid #e2e8f0; border-radius: 8px; background: white;
               cursor: pointer; font-size: 0.82rem; color: #475569; text-align: left;
               transition: all .12s; margin-bottom: 4px; }
  .skill-btn:hover { border-color: #4f46e5; color: #4f46e5; }
  .skill-btn:disabled { opacity: .5; cursor: not-allowed; }
  .skill-btn .skill-icon { font-size: 1rem; width: 22px; text-align: center; flex-shrink: 0; }
  .skill-btn .skill-name { flex: 1; font-weight: 500; }
  .skill-btn .skill-status { font-size: 0.7rem; flex-shrink: 0; }
  .skill-btn.running { border-color: #f59e0b; background: #fffbeb; }
  .skill-btn.done { border-color: #22c55e; background: #f0fdf4; }
  .skill-btn.error { border-color: #ef4444; background: #fef2f2; }

  /* --- grid view --- */
  .grid-view .date-group { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
  .grid-view .date-label { grid-column: 1 / -1; }
  .grid-view .card { flex-direction: column; align-items: flex-start; padding: 16px; }
  .grid-view .card .icon { margin: 0 0 8px 0; font-size: 1.6rem; }
  .grid-view .card .name { white-space: normal; word-break: break-all; }
  .grid-view .card .card-actions { position: absolute; top: 8px; right: 8px; }

  /* --- toast --- */
  .toast { position: fixed; bottom: 20px; right: 20px; background: #1e293b; color: white;
           padding: 12px 20px; border-radius: 10px; font-size: 0.85rem;
           box-shadow: 0 4px 20px rgba(0,0,0,.2); z-index: 2000;
           transform: translateY(80px); opacity: 0; transition: all .3s; }
  .toast.show { transform: translateY(0); opacity: 1; }

  /* --- empty / hidden --- */
  .empty { color: #94a3b8; text-align: center; padding: 48px; }
  .hidden { display: none !important; }
  .no-results { text-align: center; color: #94a3b8; padding: 32px; display: none; }
  .no-results.visible { display: block; }
</style>
</head>
<body>

<!-- mobile hamburger -->
<button class="hamburger" id="hamburger">&#9776;</button>

<!-- sidebar -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <h1>AutoDailyTask</h1>
    <p><span id="visible-count">{count}</span> 件のレポート</p>
  </div>

  <div class="view-tabs">
    <button class="view-tab active" data-view="dashboard">&#128202; ダッシュボード</button>
    <button class="view-tab" data-view="browse">&#128193; ブラウズ</button>
    <button class="view-tab" data-view="search">&#128269; 検索</button>
  </div>

  <div id="browse-sidebar-sections">
    <div class="sidebar-section">
      <div class="sidebar-section-body">
        <input class="search" type="text" placeholder="ファイル名で絞り込み…" id="search">
      </div>
    </div>

    <div class="sidebar-section" id="section-category">
      <div class="sidebar-section-title">カテゴリ</div>
      <div class="sidebar-section-body">
        <div id="filters">
          <div class="nav-item active" data-category="all">
            <span class="nav-icon">&#128203;</span><span class="nav-label">すべて</span>
          </div>
          <div class="nav-item" data-category="__favorites">
            <span class="nav-icon">&#11088;</span><span class="nav-label">お気に入り</span>
            <span class="nav-count" id="fav-count">0</span>
          </div>
          {nav_items}
        </div>
      </div>
    </div>

    <div class="sidebar-section" id="section-display">
      <div class="sidebar-section-title">表示設定</div>
      <div class="sidebar-section-body">
        <div class="toggle-row" id="privacy-toggle" title="プライベートなレポートの表示/非表示">
          <span>&#128274; プライベート表示</span>
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
        </div>
        <div class="view-row" style="margin-top: 8px;">
          <button class="view-btn active" data-view="list">&#9776; リスト</button>
          <button class="view-btn" data-view="grid">&#8862; グリッド</button>
        </div>
      </div>
    </div>
  </div>

  <div class="sidebar-section" id="section-skills">
    <div class="sidebar-section-title">スキル実行</div>
    <div class="sidebar-section-body">
      <div id="skill-list">
        {skill_buttons}
      </div>
    </div>
  </div>
</aside>

<!-- skill form modal -->
<div class="form-overlay hidden" id="skill-form-dialog">
  <div class="form-dialog">
    <div class="form-dialog-header">
      <h3 id="skill-form-title"></h3>
      <p id="skill-form-desc"></p>
    </div>
    <div class="form-dialog-body" id="skill-form-body"></div>
    <div class="form-dialog-footer">
      <button class="btn-cancel" id="skill-form-cancel">キャンセル</button>
      <button class="btn-submit" id="skill-form-submit">実行する</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>
<script>
  window.__SKILL_FORMS = {skill_forms_json};
  window.__METADATA = {metadata_json};
</script>

<!-- ===== Dashboard View ===== -->
<div class="content active" id="view-dashboard">
  {dashboard_content}
</div>

<!-- ===== Browse View ===== -->
<div class="content" id="view-browse">
  <div class="bulk-bar hidden" id="bulk-bar">
    <span id="bulk-count">0</span><span>件選択中</span>
    <button class="bulk-btn" id="bulk-compare" disabled>&#128200; 比較</button>
    <button class="bulk-btn" id="bulk-export">&#128230; ZIPエクスポート</button>
    <button class="bulk-btn" id="bulk-clear">&#10005; 選択解除</button>
  </div>
  {body}
  <p class="no-results" id="no-results">該当するレポートが見つかりません</p>
</div>

<!-- ===== Search View ===== -->
<div class="content" id="view-search">
  <div class="search-header">
    <input class="search-full" type="text" placeholder="レポート本文を全文検索…" id="search-full">
    <p class="search-hint">レポートの本文テキストを横断検索します。Enter で検索開始。</p>
  </div>
  <div id="search-results"></div>
</div>

<!-- delete confirm dialog -->
<div class="dialog-overlay hidden" id="delete-dialog">
  <div class="dialog">
    <h3>レポートを削除</h3>
    <p>「<span id="delete-target-name"></span>」を削除しますか？この操作は取り消せません。</p>
    <div class="dialog-actions">
      <button class="btn-cancel" id="delete-cancel">キャンセル</button>
      <button class="btn-delete" id="delete-confirm">削除する</button>
    </div>
  </div>
</div>

<!-- diff dialog -->
<div class="diff-overlay hidden" id="diff-dialog">
  <div class="diff-dialog">
    <div class="diff-dialog-header">
      <h3 id="diff-title">レポート比較</h3>
      <button class="diff-close" id="diff-close">&#10005;</button>
    </div>
    <div class="diff-body" id="diff-body"></div>
  </div>
</div>

<!-- tag edit dialog -->
<div class="tag-overlay hidden" id="tag-dialog">
  <div class="tag-dialog">
    <h3>&#127991; タグ編集: <span id="tag-target-name"></span></h3>
    <div class="tag-list" id="tag-list"></div>
    <div class="tag-input-row">
      <input class="tag-input" id="tag-input" placeholder="新しいタグを入力…">
      <button class="tag-add-btn" id="tag-add">追加</button>
    </div>
    <div class="memo-actions" style="margin-top:12px">
      <button class="btn-cancel" id="tag-close">閉じる</button>
    </div>
  </div>
</div>

<!-- memo edit dialog -->
<div class="memo-overlay hidden" id="memo-dialog">
  <div class="memo-dialog">
    <h3>&#128221; メモ: <span id="memo-target-name"></span></h3>
    <textarea class="memo-textarea" id="memo-textarea" placeholder="メモを入力…"></textarea>
    <div class="memo-actions">
      <button class="btn-cancel" id="memo-cancel">キャンセル</button>
      <button class="btn-submit" id="memo-save">保存</button>
    </div>
  </div>
</div>

<script>
(function() {
  var searchInput = document.getElementById('search');
  var browseCont = document.getElementById('view-browse');
  var noResults = document.getElementById('no-results');
  var visibleCount = document.getElementById('visible-count');
  var navItems = document.querySelectorAll('.nav-item');
  var viewBtns = document.querySelectorAll('.view-btn');
  var privacyToggle = document.getElementById('privacy-toggle');
  var sidebar = document.getElementById('sidebar');
  var hamburger = document.getElementById('hamburger');
  var viewTabs = document.querySelectorAll('.view-tab');
  var browseSections = document.getElementById('browse-sidebar-sections');
  var meta = window.__METADATA || {favorites:[], pins:[], tags:{}, memos:{}};

  var activeCategory = 'all';
  var showPrivate = false;
  var selectedFiles = [];

  // --- restore states ---
  if (localStorage.getItem('showPrivate') === 'true') {
    showPrivate = true;
    privacyToggle.classList.add('on');
  }
  var savedView = localStorage.getItem('activeView') || 'dashboard';

  // --- view tab switching ---
  function switchView(viewName) {
    viewTabs.forEach(function(t) { t.classList.toggle('active', t.dataset.view === viewName); });
    document.querySelectorAll('.content').forEach(function(c) { c.classList.remove('active'); });
    var target = document.getElementById('view-' + viewName);
    if (target) target.classList.add('active');
    browseSections.style.display = viewName === 'browse' ? '' : 'none';
    localStorage.setItem('activeView', viewName);
    if (viewName === 'search') {
      setTimeout(function() { document.getElementById('search-full').focus(); }, 100);
    }
  }
  viewTabs.forEach(function(tab) {
    tab.addEventListener('click', function() { switchView(tab.dataset.view); });
  });
  switchView(savedView);

  // --- hamburger ---
  hamburger.addEventListener('click', function() { sidebar.classList.toggle('open'); });
  document.querySelectorAll('.content').forEach(function(c) {
    c.addEventListener('click', function() { sidebar.classList.remove('open'); });
  });

  // --- category collapse ---
  document.querySelectorAll('.category-header').forEach(function(h) {
    h.addEventListener('click', function() { h.parentElement.classList.toggle('collapsed'); });
  });

  // --- sidebar section collapse ---
  document.querySelectorAll('.sidebar-section-title').forEach(function(t) {
    t.addEventListener('click', function() {
      var section = t.parentElement;
      section.classList.toggle('collapsed');
      var id = section.id;
      if (id) {
        var state = JSON.parse(localStorage.getItem('sidebarCollapsed') || '{}');
        state[id] = section.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', JSON.stringify(state));
      }
    });
  });
  var collapseState = JSON.parse(localStorage.getItem('sidebarCollapsed') || '{}');
  Object.keys(collapseState).forEach(function(id) {
    if (collapseState[id]) { var el = document.getElementById(id); if (el) el.classList.add('collapsed'); }
  });

  // --- sidebar nav filter ---
  navItems.forEach(function(btn) {
    btn.addEventListener('click', function() {
      navItems.forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      activeCategory = btn.dataset.category;
      applyFilters();
    });
  });

  // --- search ---
  searchInput.addEventListener('input', function() { applyFilters(); });

  // --- privacy toggle ---
  privacyToggle.addEventListener('click', function() {
    showPrivate = !showPrivate;
    privacyToggle.classList.toggle('on', showPrivate);
    localStorage.setItem('showPrivate', showPrivate);
    applyFilters();
  });

  // --- view toggle ---
  viewBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      viewBtns.forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      browseCont.classList.toggle('grid-view', btn.dataset.view === 'grid');
    });
  });

  // --- initialize card metadata decorations ---
  function initCardMeta() {
    document.querySelectorAll('.card[data-name]').forEach(function(card) {
      var name = card.dataset.name;
      var favBtn = card.querySelector('.fav-btn');
      var pinBtn = card.querySelector('.pin-btn');
      var tagBtn = card.querySelector('.tag-btn');
      var memoBtn = card.querySelector('.memo-btn');
      if (favBtn && meta.favorites.indexOf(name) >= 0) favBtn.classList.add('active');
      if (pinBtn && meta.pins.indexOf(name) >= 0) pinBtn.classList.add('active');
      if (tagBtn && meta.tags[name] && meta.tags[name].length > 0) {
        tagBtn.classList.add('has-tags');
        var tagsDiv = card.querySelector('.card-tags');
        if (tagsDiv) meta.tags[name].forEach(function(t) {
          var sp = document.createElement('span'); sp.className='card-tag'; sp.textContent=t;
          tagsDiv.appendChild(sp);
        });
      }
      if (memoBtn && meta.memos[name]) {
        memoBtn.classList.add('has-memo');
        var memoDiv = card.querySelector('.card-memo');
        if (memoDiv) memoDiv.textContent = meta.memos[name];
      }
    });
    updateFavCount();
  }
  initCardMeta();

  function updateFavCount() {
    var el = document.getElementById('fav-count');
    if (el) el.textContent = meta.favorites.length;
  }

  function saveMeta() {
    fetch('/api/metadata', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(meta)
    });
  }

  function applyFilters() {
    var q = searchInput.value.toLowerCase();
    var count = 0;

    navItems.forEach(function(nav) {
      var isPrivate = nav.dataset.private === 'true';
      nav.classList.toggle('hidden', isPrivate && !showPrivate);
    });
    document.querySelectorAll('.skill-btn').forEach(function(btn) {
      var isPrivate = btn.dataset.private === 'true';
      btn.classList.toggle('hidden', isPrivate && !showPrivate);
    });
    var activeNav = document.querySelector('.nav-item.active');
    if (activeNav && activeNav.dataset.private === 'true' && !showPrivate) {
      navItems.forEach(function(b) { b.classList.remove('active'); });
      document.querySelector('.nav-item[data-category="all"]').classList.add('active');
      activeCategory = 'all';
    }

    var isFavFilter = activeCategory === '__favorites';

    document.querySelectorAll('.category').forEach(function(cat) {
      var catName = cat.dataset.category;
      var isPrivate = cat.dataset.private === 'true';
      var catMatch = activeCategory === 'all' || catName === activeCategory || isFavFilter;
      var privacyMatch = !isPrivate || showPrivate;

      cat.querySelectorAll('.date-group').forEach(function(dg) {
        var groupVisible = 0;
        dg.querySelectorAll('.card').forEach(function(card) {
          var text = card.dataset.name.toLowerCase();
          var matchFav = !isFavFilter || meta.favorites.indexOf(card.dataset.name) >= 0;
          var show = catMatch && privacyMatch && matchFav && (!q || text.indexOf(q) >= 0);
          card.classList.toggle('hidden', !show);
          if (show) { groupVisible++; count++; }
        });
        dg.classList.toggle('hidden', groupVisible === 0);
      });

      cat.classList.toggle('hidden', !catMatch || !privacyMatch || !cat.querySelector('.card:not(.hidden)'));
    });

    visibleCount.textContent = count;
    noResults.classList.toggle('visible', count === 0);
  }

  // --- favorite toggle ---
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.fav-btn');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    var card = btn.closest('.card');
    var name = card.dataset.name;
    var idx = meta.favorites.indexOf(name);
    if (idx >= 0) { meta.favorites.splice(idx, 1); btn.classList.remove('active'); }
    else { meta.favorites.push(name); btn.classList.add('active'); }
    updateFavCount(); saveMeta();
    if (activeCategory === '__favorites') applyFilters();
  });

  // --- pin toggle ---
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.pin-btn');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    var card = btn.closest('.card');
    var name = card.dataset.name;
    var idx = meta.pins.indexOf(name);
    if (idx >= 0) { meta.pins.splice(idx, 1); btn.classList.remove('active'); }
    else { meta.pins.push(name); btn.classList.add('active'); }
    saveMeta(); showToast(idx >= 0 ? 'ピン解除しました' : 'ピン留めしました');
  });

  // --- compare checkbox ---
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.compare-cb');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    var card = btn.closest('.card');
    var name = card.dataset.name;
    btn.classList.toggle('checked');
    if (btn.classList.contains('checked')) {
      if (selectedFiles.indexOf(name) < 0) selectedFiles.push(name);
    } else {
      selectedFiles = selectedFiles.filter(function(f) { return f !== name; });
    }
    updateBulkBar();
  });

  function updateBulkBar() {
    var bar = document.getElementById('bulk-bar');
    var countEl = document.getElementById('bulk-count');
    var compareBtn = document.getElementById('bulk-compare');
    if (selectedFiles.length > 0) {
      bar.classList.remove('hidden');
      countEl.textContent = selectedFiles.length;
      compareBtn.disabled = selectedFiles.length !== 2;
    } else {
      bar.classList.add('hidden');
    }
  }

  document.getElementById('bulk-clear').addEventListener('click', function() {
    selectedFiles = [];
    document.querySelectorAll('.compare-cb.checked').forEach(function(b) { b.classList.remove('checked'); });
    updateBulkBar();
  });

  // --- bulk export ---
  document.getElementById('bulk-export').addEventListener('click', function() {
    if (selectedFiles.length === 0) return;
    fetch('/api/export', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({files: selectedFiles})
    }).then(function(res) {
      if (!res.ok) throw new Error('export failed');
      return res.blob();
    }).then(function(blob) {
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'reports-export.zip';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      showToast(selectedFiles.length + '件をZIPでエクスポートしました');
    }).catch(function(err) { showToast('エクスポートに失敗: ' + err.message, 5000); });
  });

  // --- bulk compare ---
  document.getElementById('bulk-compare').addEventListener('click', function() {
    if (selectedFiles.length !== 2) return;
    openDiff(selectedFiles[0], selectedFiles[1]);
  });

  // --- diff ---
  function openDiff(fileA, fileB) {
    document.getElementById('diff-title').textContent = fileA + ' vs ' + fileB;
    document.getElementById('diff-body').textContent = '読み込み中…';
    document.getElementById('diff-dialog').classList.remove('hidden');
    fetch('/api/diff?a=' + encodeURIComponent(fileA) + '&b=' + encodeURIComponent(fileB))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.error) { document.getElementById('diff-body').textContent = d.error; return; }
        var html = '';
        d.lines.forEach(function(line) {
          var cls = '';
          if (line.charAt(0) === '+') cls = 'diff-add';
          else if (line.charAt(0) === '-') cls = 'diff-del';
          else if (line.charAt(0) === '@') cls = 'diff-hdr';
          var escaped = line.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
          html += cls ? '<span class="' + cls + '">' + escaped + '</span>\\n' : escaped + '\\n';
        });
        document.getElementById('diff-body').innerHTML = html || '差分なし';
      }).catch(function(err) { document.getElementById('diff-body').textContent = 'エラー: ' + err.message; });
  }
  document.getElementById('diff-close').addEventListener('click', function() {
    document.getElementById('diff-dialog').classList.add('hidden');
  });
  document.getElementById('diff-dialog').addEventListener('click', function(e) {
    if (e.target === document.getElementById('diff-dialog')) document.getElementById('diff-dialog').classList.add('hidden');
  });

  // --- tag edit ---
  var tagTargetFile = null;
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.tag-btn');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    var card = btn.closest('.card');
    tagTargetFile = card.dataset.name;
    document.getElementById('tag-target-name').textContent = tagTargetFile;
    renderTagList();
    document.getElementById('tag-dialog').classList.remove('hidden');
  });
  function renderTagList() {
    var list = document.getElementById('tag-list');
    list.innerHTML = '';
    var tags = meta.tags[tagTargetFile] || [];
    tags.forEach(function(t) {
      var el = document.createElement('span');
      el.className = 'tag-item'; el.textContent = t + ' ✕';
      el.addEventListener('click', function() {
        meta.tags[tagTargetFile] = (meta.tags[tagTargetFile]||[]).filter(function(x){return x!==t;});
        saveMeta(); renderTagList(); refreshCardTags(tagTargetFile);
      });
      list.appendChild(el);
    });
  }
  document.getElementById('tag-add').addEventListener('click', function() { addTag(); });
  document.getElementById('tag-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') addTag();
  });
  function addTag() {
    var input = document.getElementById('tag-input');
    var val = input.value.trim();
    if (!val || !tagTargetFile) return;
    if (!meta.tags[tagTargetFile]) meta.tags[tagTargetFile] = [];
    if (meta.tags[tagTargetFile].indexOf(val) < 0) meta.tags[tagTargetFile].push(val);
    input.value = '';
    saveMeta(); renderTagList(); refreshCardTags(tagTargetFile);
  }
  function refreshCardTags(name) {
    var card = document.querySelector('.card[data-name="'+name+'"]');
    if (!card) return;
    var tagsDiv = card.querySelector('.card-tags');
    var tagBtn = card.querySelector('.tag-btn');
    if (tagsDiv) {
      tagsDiv.innerHTML = '';
      (meta.tags[name]||[]).forEach(function(t) {
        var sp = document.createElement('span'); sp.className='card-tag'; sp.textContent=t;
        tagsDiv.appendChild(sp);
      });
    }
    if (tagBtn) tagBtn.classList.toggle('has-tags', (meta.tags[name]||[]).length > 0);
  }
  document.getElementById('tag-close').addEventListener('click', function() {
    document.getElementById('tag-dialog').classList.add('hidden');
  });
  document.getElementById('tag-dialog').addEventListener('click', function(e) {
    if (e.target === document.getElementById('tag-dialog')) document.getElementById('tag-dialog').classList.add('hidden');
  });

  // --- memo edit ---
  var memoTargetFile = null;
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.memo-btn');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    var card = btn.closest('.card');
    memoTargetFile = card.dataset.name;
    document.getElementById('memo-target-name').textContent = memoTargetFile;
    document.getElementById('memo-textarea').value = meta.memos[memoTargetFile] || '';
    document.getElementById('memo-dialog').classList.remove('hidden');
  });
  document.getElementById('memo-save').addEventListener('click', function() {
    var val = document.getElementById('memo-textarea').value.trim();
    if (val) meta.memos[memoTargetFile] = val;
    else delete meta.memos[memoTargetFile];
    saveMeta();
    var card = document.querySelector('.card[data-name="'+memoTargetFile+'"]');
    if (card) {
      var memoDiv = card.querySelector('.card-memo');
      var memoBtn = card.querySelector('.memo-btn');
      if (memoDiv) memoDiv.textContent = val;
      if (memoBtn) memoBtn.classList.toggle('has-memo', !!val);
    }
    document.getElementById('memo-dialog').classList.add('hidden');
    showToast('メモを保存しました');
  });
  document.getElementById('memo-cancel').addEventListener('click', function() {
    document.getElementById('memo-dialog').classList.add('hidden');
  });
  document.getElementById('memo-dialog').addEventListener('click', function(e) {
    if (e.target === document.getElementById('memo-dialog')) document.getElementById('memo-dialog').classList.add('hidden');
  });

  // --- delete ---
  var pendingDeleteCard = null;
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.delete-btn');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    pendingDeleteCard = btn.closest('.card');
    document.getElementById('delete-target-name').textContent = pendingDeleteCard.dataset.name;
    document.getElementById('delete-dialog').classList.remove('hidden');
  });
  document.getElementById('delete-cancel').addEventListener('click', function() {
    document.getElementById('delete-dialog').classList.add('hidden'); pendingDeleteCard = null;
  });
  document.getElementById('delete-dialog').addEventListener('click', function(e) {
    if (e.target === document.getElementById('delete-dialog')) {
      document.getElementById('delete-dialog').classList.add('hidden'); pendingDeleteCard = null;
    }
  });
  document.getElementById('delete-confirm').addEventListener('click', function() {
    if (!pendingDeleteCard) return;
    var filename = pendingDeleteCard.dataset.name;
    var btn = document.getElementById('delete-confirm');
    btn.disabled = true; btn.textContent = '削除中…';
    fetch('/api/delete?file=' + encodeURIComponent(filename), { method: 'DELETE' })
      .then(function(res) {
        if (res.ok) {
          pendingDeleteCard.remove();
          document.querySelectorAll('.date-group').forEach(function(dg) { if (!dg.querySelector('.card')) dg.remove(); });
          document.querySelectorAll('.category').forEach(function(cat) { if (!cat.querySelector('.card')) cat.remove(); });
          applyFilters();
        } else { res.text().then(function(t) { alert('削除に失敗: ' + t); }); }
      }).catch(function(err) { alert('削除に失敗: ' + err.message); });
    document.getElementById('delete-dialog').classList.add('hidden');
    btn.disabled = false; btn.textContent = '削除する'; pendingDeleteCard = null;
  });

  // --- full-text search ---
  var searchFull = document.getElementById('search-full');
  var searchResults = document.getElementById('search-results');
  var searchTimer = null;
  searchFull.addEventListener('input', function() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(doSearch, 400);
  });
  searchFull.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { clearTimeout(searchTimer); doSearch(); }
  });
  function doSearch() {
    var q = searchFull.value.trim();
    if (!q) { searchResults.innerHTML = ''; return; }
    searchResults.innerHTML = '<p style="color:#94a3b8">検索中…</p>';
    fetch('/api/search?q=' + encodeURIComponent(q))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.results || data.results.length === 0) {
          searchResults.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:32px">結果が見つかりませんでした</p>';
          return;
        }
        var html = '';
        data.results.forEach(function(r) {
          if (r.private && !showPrivate) return;
          var snippet = r.snippet.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
          var re = new RegExp('(' + q.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&') + ')', 'gi');
          snippet = snippet.replace(re, '<mark>$1</mark>');
          html += '<div class="search-result">' +
            '<a href="/reports/' + r.file + '" target="_blank">' + r.icon + ' ' + r.file + '</a>' +
            '<div class="sr-cat">' + r.label + '</div>' +
            '<div class="sr-snippet">' + snippet + '</div></div>';
        });
        searchResults.innerHTML = html || '<p style="color:#94a3b8;text-align:center;padding:32px">結果が見つかりませんでした</p>';
      }).catch(function(err) {
        searchResults.innerHTML = '<p style="color:#ef4444">検索エラー: ' + err.message + '</p>';
      });
  }

  // --- skill form modal ---
  var FORMS = window.__SKILL_FORMS || {};
  var formDialog = document.getElementById('skill-form-dialog');
  var formTitle = document.getElementById('skill-form-title');
  var formDesc = document.getElementById('skill-form-desc');
  var formBody = document.getElementById('skill-form-body');
  var activeFormSkill = null;

  function openSkillForm(skillKey) {
    var def = FORMS[skillKey]; if (!def) return;
    activeFormSkill = skillKey;
    formTitle.textContent = def.icon + ' ' + def.title;
    formDesc.textContent = def.description;
    var h = '';
    def.fields.forEach(function(f) {
      var id = 'sf-' + f[0], reqMark = f[4] ? '<span class="req">*</span>' : '';
      h += '<div class="form-field"><label for="'+id+'">'+f[1]+reqMark+'</label>';
      if (f[2]==='select' && f[5]) {
        h += '<select id="'+id+'" data-field="'+f[0]+'"'+(f[4]?' required':'')+'>';
        h += '<option value="">選択してください</option>';
        f[5].forEach(function(o){h+='<option value="'+o[0]+'">'+o[1]+'</option>';});
        h += '</select>';
      } else {
        h += '<input id="'+id+'" data-field="'+f[0]+'" type="text" placeholder="'+(f[3]||'')+'"'+(f[4]?' required':'')+'>';
      }
      h += '</div>';
    });
    formBody.innerHTML = h;
    formDialog.classList.remove('hidden');
  }
  function closeSkillForm() { formDialog.classList.add('hidden'); activeFormSkill = null; }
  document.getElementById('skill-form-cancel').addEventListener('click', closeSkillForm);
  formDialog.addEventListener('click', function(e) { if (e.target===formDialog) closeSkillForm(); });

  function runFormSkill() {
    if (!activeFormSkill) return;
    var def = FORMS[activeFormSkill], valid = true;
    def.fields.forEach(function(f) {
      if (f[4]) {
        var el = document.getElementById('sf-'+f[0]);
        if (!el || !el.value.trim()) { valid=false; el.style.borderColor='#ef4444'; }
        else { el.style.borderColor=''; }
      }
    });
    if (!valid) { showToast('必須項目を入力してください'); return; }
    var args = [];
    def.fields.forEach(function(f) {
      var el = document.getElementById('sf-'+f[0]);
      if (el && el.value.trim()) args.push(el.value.trim());
    });
    var sk = activeFormSkill;
    closeSkillForm();
    launchSkill(sk, args.join(' '));
  }
  document.getElementById('skill-form-submit').addEventListener('click', runFormSkill);
  document.querySelectorAll('.skill-btn[data-runnable="form"]').forEach(function(btn) {
    btn.addEventListener('click', function() { openSkillForm(btn.dataset.skill); });
  });

  // --- skill launch ---
  function launchSkill(skill, args) {
    var btn = document.querySelector('.skill-btn[data-skill="'+skill+'"]');
    if (btn) { btn.disabled=true; btn.classList.add('running'); btn.querySelector('.skill-status').textContent='実行中…'; }
    showToast('/'+skill+' を実行中…', 4000);
    fetch('/api/run-skill', { method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({skill:skill,args:args||''})
    }).then(function(res){return res.json().then(function(d){return {ok:res.ok,data:d};});})
    .then(function(r) {
      if (!r.ok) {
        if(btn){btn.classList.remove('running');btn.classList.add('error');btn.querySelector('.skill-status').textContent='エラー';}
        showToast('エラー: '+(r.data.error||'不明'),5000);
        if(btn) setTimeout(function(){btn.disabled=false;btn.classList.remove('error');btn.querySelector('.skill-status').textContent=btn.dataset.runnable==='form'?'\\uD83D\\uDCDD':'\\u25B6';},5000);
        return;
      }
      var jobId = r.data.job_id;
      var poll = setInterval(function() {
        fetch('/api/skill-status?id='+jobId).then(function(sr){return sr.json();}).then(function(sd) {
          if (sd.status==='done') { clearInterval(poll);
            if(btn){btn.classList.remove('running');btn.classList.add('done');btn.querySelector('.skill-status').textContent='完了';}
            showToast('/'+skill+' が完了しました。ページを更新してください。');
            if(btn) setTimeout(function(){btn.disabled=false;btn.classList.remove('done');btn.querySelector('.skill-status').textContent=btn.dataset.runnable==='form'?'\\uD83D\\uDCDD':'\\u25B6';},8000);
          } else if (sd.status==='error') { clearInterval(poll);
            if(btn){btn.classList.remove('running');btn.classList.add('error');btn.querySelector('.skill-status').textContent='エラー';}
            showToast('/'+skill+' がエラーで終了',5000);
            if(btn) setTimeout(function(){btn.disabled=false;btn.classList.remove('error');btn.querySelector('.skill-status').textContent=btn.dataset.runnable==='form'?'\\uD83D\\uDCDD':'\\u25B6';},8000);
          }
        });
      }, 3000);
    }).catch(function(err) {
      if(btn){btn.disabled=false;btn.classList.remove('running');btn.querySelector('.skill-status').textContent=btn.dataset.runnable==='form'?'\\uD83D\\uDCDD':'\\u25B6';}
      showToast('通信エラー: '+err.message,5000);
    });
  }
  document.querySelectorAll('.skill-btn[data-runnable="true"]').forEach(function(btn) {
    btn.addEventListener('click', function() { launchSkill(btn.dataset.skill); });
  });

  // --- toast ---
  var toastEl = document.getElementById('toast');
  function showToast(msg, duration) {
    duration = duration || 3000;
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(function() { toastEl.classList.remove('show'); }, duration);
  }

  applyFilters();
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# ビルダー
# ---------------------------------------------------------------------------

def build_skill_buttons():
    buttons = []
    for skill_key, (label, icon, runnable, private) in SKILLS.items():
        priv_attr = "true" if private else "false"
        run_attr = "true" if runnable else "form"
        status = "\u25B6" if runnable else "\U0001F4DD"
        buttons.append(
            '<button class="skill-btn" data-skill="%s" data-runnable="%s" data-private="%s">'
            '<span class="skill-icon">%s</span>'
            '<span class="skill-name">%s</span>'
            '<span class="skill-status">%s</span>'
            '</button>' % (skill_key, run_attr, priv_attr, icon, label, status)
        )
    return "\n      ".join(buttons)


def _render(count, body, nav_items="", dashboard_content=""):
    meta = load_metadata()
    return (INDEX_HTML
            .replace("{count}", str(count))
            .replace("{body}", body)
            .replace("{nav_items}", nav_items)
            .replace("{skill_buttons}", build_skill_buttons())
            .replace("{skill_forms_json}", json.dumps(SKILL_FORMS, ensure_ascii=False))
            .replace("{metadata_json}", json.dumps(meta, ensure_ascii=False))
            .replace("{dashboard_content}", dashboard_content))


def build_dashboard():
    """ダッシュボード用のHTMLを生成"""
    if not REPORTS_DIR.exists():
        return '<p class="empty">reports/ が見つかりません</p>'

    meta = load_metadata()
    all_files = sorted(
        [f for f in REPORTS_DIR.iterdir() if f.suffix in (".html", ".pdf")],
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    total = len(all_files)
    cat_set = set()
    dates_set = set()
    for f in all_files:
        cat_set.add(classify(f.name))
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        if m:
            dates_set.add(m.group())
    latest_date = max(dates_set) if dates_set else "—"

    rows = []
    # stats
    rows.append('<div class="stats-row">')
    rows.append('<div class="stat-card"><div class="stat-value">%d</div><div class="stat-label">レポート数</div></div>' % total)
    rows.append('<div class="stat-card"><div class="stat-value">%d</div><div class="stat-label">カテゴリ</div></div>' % len(cat_set))
    rows.append('<div class="stat-card"><div class="stat-value">%d</div><div class="stat-label">お気に入り</div></div>' % len(meta.get("favorites", [])))
    rows.append('<div class="stat-card"><div class="stat-value">%s</div><div class="stat-label">最新レポート</div></div>' % html_mod.escape(latest_date))
    rows.append('</div>')

    # pinned section
    pinned = meta.get("pins", [])
    if pinned:
        rows.append('<div class="dash-section">')
        rows.append('<div class="dash-section-title">\U0001F4CC ピン留め</div>')
        rows.append('<div class="dash-grid">')
        for name in pinned:
            path = REPORTS_DIR / name
            if not path.exists():
                continue
            cat = classify(name)
            label, icon, is_private = CATEGORIES.get(cat, DEFAULT_CATEGORY)
            summary = html_mod.escape(extract_summary(path))
            m = re.search(r"\d{4}-\d{2}-\d{2}", name)
            date_str = m.group() if m else ""
            rows.append(
                '<a class="dash-card pinned" href="/reports/%s" target="_blank">'
                '<div class="dc-header"><span class="dc-icon">%s</span><span class="dc-cat">%s</span></div>'
                '<div class="dc-title">%s</div>'
                '<div class="dc-date">%s</div>'
                '%s</a>'
                % (name, icon, html_mod.escape(label), html_mod.escape(name), date_str,
                   ('<div class="dc-preview">%s</div>' % summary) if summary else "")
            )
        rows.append('</div></div>')

    # latest per category
    rows.append('<div class="dash-section">')
    rows.append('<div class="dash-section-title">\U0001F195 各カテゴリの最新レポート</div>')
    rows.append('<div class="dash-grid">')
    seen_cats = set()
    for f in all_files:
        cat = classify(f.name)
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        label, icon, is_private = CATEGORIES.get(cat, DEFAULT_CATEGORY)
        summary = html_mod.escape(extract_summary(f))
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        date_str = m.group() if m else ""
        priv_attr = ' data-private="true"' if is_private else ""
        rows.append(
            '<a class="dash-card%s" href="/reports/%s" target="_blank"%s>'
            '<div class="dc-header"><span class="dc-icon">%s</span><span class="dc-cat">%s</span></div>'
            '<div class="dc-title">%s</div>'
            '<div class="dc-date">%s</div>'
            '%s</a>'
            % ("", f.name, priv_attr, icon, html_mod.escape(label), html_mod.escape(f.name),
               date_str, ('<div class="dc-preview">%s</div>' % summary) if summary else "")
        )
    rows.append('</div></div>')

    # recent reports
    rows.append('<div class="dash-section">')
    rows.append('<div class="dash-section-title">\U0001F4C5 最近のレポート</div>')
    rows.append('<div class="dash-grid">')
    for f in all_files[:12]:
        cat = classify(f.name)
        label, icon, is_private = CATEGORIES.get(cat, DEFAULT_CATEGORY)
        summary = html_mod.escape(extract_summary(f))
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        date_str = m.group() if m else ""
        priv_attr = ' data-private="true"' if is_private else ""
        rows.append(
            '<a class="dash-card" href="/reports/%s" target="_blank"%s>'
            '<div class="dc-header"><span class="dc-icon">%s</span><span class="dc-cat">%s</span></div>'
            '<div class="dc-title">%s</div>'
            '<div class="dc-date">%s</div>'
            '%s</a>'
            % (f.name, priv_attr, icon, html_mod.escape(label), html_mod.escape(f.name),
               date_str, ('<div class="dc-preview">%s</div>' % summary) if summary else "")
        )
    rows.append('</div></div>')

    return "\n".join(rows)


def build_index():
    if not REPORTS_DIR.exists():
        return _render(0, '<p class="empty">reports/ ディレクトリが見つかりません</p>',
                       dashboard_content=build_dashboard())

    tree = {}  # type: dict
    for f in sorted(REPORTS_DIR.iterdir()):
        if f.suffix not in (".pdf", ".html"):
            continue
        cat = classify(f.name)
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        date_key = m.group() if m else "日付なし"
        tree.setdefault(cat, {}).setdefault(date_key, []).append(f)

    if not tree:
        return _render(0, '<p class="empty">レポートがまだありません</p>',
                       dashboard_content=build_dashboard())

    nav_items = []
    cat_order = [k for k in CATEGORIES if k in tree]
    if "_other" in tree:
        cat_order.append("_other")

    for cat_key in cat_order:
        label, icon, is_private = CATEGORIES.get(cat_key, DEFAULT_CATEGORY)
        n = sum(len(fs) for fs in tree[cat_key].values())
        private_attr = "true" if is_private else "false"
        nav_items.append(
            '<div class="nav-item" data-category="%s" data-private="%s">'
            '<span class="nav-icon">%s</span>'
            '<span class="nav-label">%s</span>'
            '<span class="nav-count">%d</span>'
            '</div>' % (cat_key, private_attr, icon, label, n)
        )

    rows = []
    total = 0

    for cat_key in cat_order:
        dates = tree[cat_key]
        label, icon, is_private = CATEGORIES.get(cat_key, DEFAULT_CATEGORY)
        cat_count = sum(len(fs) for fs in dates.values())
        private_attr = "true" if is_private else "false"
        private_badge = ' <span class="private-badge">プライベート</span>' if is_private else ""

        rows.append('<div class="category" data-category="%s" data-private="%s">' % (cat_key, private_attr))
        rows.append(
            '<div class="category-header">'
            '<span class="category-icon">%s</span>'
            '<span class="category-name">%s%s</span>'
            '<span class="category-count">%d</span>'
            '<span class="category-toggle">\u25BC</span>'
            '</div>'
            '<div class="category-body">' % (icon, label, private_badge, cat_count)
        )

        for date_key in sorted(dates.keys(), reverse=True):
            file_list = dates[date_key]
            rows.append('<div class="date-group">')
            rows.append('<div class="date-label">%s</div>' % date_key)

            for f in sorted(file_list, key=lambda p: (p.suffix != ".pdf", p.name)):
                size_kb = f.stat().st_size // 1024
                ext = f.suffix
                file_icon = "\U0001F4C4" if ext == ".pdf" else "\U0001F310"
                badge_cls = "pdf" if ext == ".pdf" else "html"
                ext_label = ext.lstrip(".").upper()
                summary = html_mod.escape(extract_summary(f))
                preview_html = '<div class="preview">%s</div>' % summary if summary else ""
                rows.append(
                    '<a class="card" href="/reports/%s" target="_blank" data-name="%s">'
                    '<span class="icon">%s</span>'
                    '<div class="info">'
                    '<div class="name">%s<span class="badge %s">%s</span></div>'
                    '<div class="meta">%d KB</div>'
                    '%s'
                    '<div class="card-tags"></div>'
                    '<div class="card-memo"></div>'
                    '</div>'
                    '<div class="card-actions">'
                    '<button class="card-action fav-btn" title="お気に入り">&#9734;</button>'
                    '<button class="card-action pin-btn" title="ピン留め">&#128204;</button>'
                    '<button class="card-action tag-btn" title="タグ">&#127991;</button>'
                    '<button class="card-action memo-btn" title="メモ">&#128221;</button>'
                    '<button class="card-action compare-cb" title="比較選択">&#9744;</button>'
                    '<button class="card-action delete-btn" title="削除">&#128465;</button>'
                    '</div>'
                    '</a>'
                    % (f.name, f.name, file_icon, f.name, badge_cls, ext_label,
                       size_kb, preview_html)
                )
                total += 1

            rows.append('</div>')
        rows.append('</div></div>')

    body_html = "\n".join(rows)
    nav_html = "\n      ".join(nav_items)

    return _render(total, body_html, nav_html, build_dashboard())


# ---------------------------------------------------------------------------
# HTTP ハンドラ
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("  %s %s" % (self.address_string(), fmt % args))

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
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

    def _parse_query(self):
        query = unquote(self.path.split("?", 1)[1]) if "?" in self.path else ""
        return dict(p.split("=", 1) for p in query.split("&") if "=" in p)

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

        if path == "/api/skill-status":
            params = self._parse_query()
            job_id = params.get("id", "")
            job = _jobs.get(job_id)
            if not job:
                self.send_json(404, {"error": "ジョブが見つかりません"})
                return
            self.send_json(200, {
                "status": job["status"],
                "skill": job["skill"],
                "output": job.get("output", ""),
            })
            return

        if path == "/api/search":
            params = self._parse_query()
            q = params.get("q", "")
            if not q:
                self.send_json(400, {"error": "検索クエリが必要です"})
                return
            results = search_reports(q)
            self.send_json(200, {"results": results, "query": q})
            return

        if path == "/api/diff":
            params = self._parse_query()
            file_a = params.get("a", "")
            file_b = params.get("b", "")
            if not file_a or not file_b:
                self.send_json(400, {"error": "比較する2つのファイルを指定してください"})
                return
            diff_text = generate_diff(file_a, file_b)
            if diff_text is None:
                self.send_json(404, {"error": "ファイルが見つかりません"})
                return
            lines = diff_text.split("\n") if diff_text else []
            self.send_json(200, {"lines": lines, "file_a": file_a, "file_b": file_b})
            return

        if path == "/api/metadata":
            self.send_json(200, load_metadata())
            return

        if path.startswith("/reports/"):
            filename = path[len("/reports/"):]
            filepath = REPORTS_DIR / filename
            if filepath.exists() and filepath.parent.resolve() == REPORTS_DIR.resolve():
                self.send_file(filepath)
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        path = unquote(self.path.split("?")[0])
        length = int(self.headers.get("Content-Length", 0))

        if path == "/api/run-skill":
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            skill_name = body.get("skill", "")
            args = body.get("args", "")

            if skill_name not in SKILLS:
                self.send_json(400, {"error": "不明なスキル: %s" % skill_name})
                return

            _, _, runnable, _ = SKILLS[skill_name]
            if not runnable and not args:
                self.send_json(400, {"error": "このスキルはフォーム入力が必要です"})
                return

            for job in _jobs.values():
                if job["skill"] == skill_name and job["status"] == "running":
                    self.send_json(409, {"error": "%s は既に実行中です" % skill_name})
                    return

            job_id = str(uuid.uuid4())[:8]
            _jobs[job_id] = {"skill": skill_name, "status": "queued"}
            thread = threading.Thread(target=run_skill_async, args=(job_id, skill_name, args), daemon=True)
            thread.start()
            print("  スキル実行開始: /%s (job=%s)" % (skill_name, job_id))
            self.send_json(200, {"job_id": job_id, "skill": skill_name})
            return

        if path == "/api/metadata":
            data = json.loads(self.rfile.read(length)) if length > 0 else {}
            save_metadata(data)
            self.send_json(200, {"ok": True})
            return

        if path == "/api/export":
            data = json.loads(self.rfile.read(length)) if length > 0 else {}
            filenames = data.get("files", [])
            if not filenames:
                self.send_json(400, {"error": "ファイルが指定されていません"})
                return
            zip_data = export_zip(filenames)
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", "attachment; filename=reports-export.zip")
            self.send_header("Content-Length", str(len(zip_data)))
            self.end_headers()
            self.wfile.write(zip_data)
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        path = unquote(self.path.split("?")[0])

        if path == "/api/delete":
            params = self._parse_query()
            filename = params.get("file", "")

            if not filename or "/" in filename or "\\" in filename:
                self.send_json(400, {"error": "不正なファイル名"})
                return

            filepath = REPORTS_DIR / filename
            if not filepath.exists() or filepath.parent.resolve() != REPORTS_DIR.resolve():
                self.send_json(404, {"error": "ファイルが見つかりません"})
                return

            if filepath.suffix not in (".pdf", ".html"):
                self.send_json(403, {"error": "削除できないファイル形式"})
                return

            try:
                filepath.unlink()
                print("  削除: %s" % filepath)
                self.send_json(200, {"ok": True, "deleted": filename})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_error(404, "Not Found")


def main():
    parser = argparse.ArgumentParser(description="AutoDailyTask レポートビューア")
    parser.add_argument("--port", type=int, default=8080, help="ポート番号 (default: 8080)")
    args = parser.parse_args()

    server = HTTPServer(("localhost", args.port), Handler)
    url = "http://localhost:%d" % args.port
    print("レポートビューア起動中: %s" % url)
    print("終了するには Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました")


if __name__ == "__main__":
    main()
