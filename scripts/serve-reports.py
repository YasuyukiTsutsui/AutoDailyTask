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
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

REPORTS_DIR = Path(__file__).parent.parent / "reports"
PROJECT_DIR = Path(__file__).parent.parent

# スキル定義: (表示名, アイコン, 引数なしで実行可能か, プライベート)
SKILLS = {
    "ai-report":            ("AI動向レポート", "🤖", True, False),
    "trading-card-release": ("トレカ新発売情報", "🃏", True, False),
    "vtuber-riona":         ("VTuber推し活", "🎤", True, True),
    "fashion-report":       ("ファッションレポート", "👗", False, True),
    "gift-concierge":       ("プレゼント提案", "🎁", False, False),
    "travel-plan":          ("国内旅行プラン", "✈️", False, True),
    "cleanup-reports":      ("レポート整理", "🧹", True, False),
}

# スキル実行ジョブの管理
# スキルごとのヒアリングフォーム定義
# フィールド: (field_id, label, input_type, placeholder, required, options)
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

_jobs = {}  # type: dict

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
  .sidebar { width: 260px; min-height: 100vh; background: white; border-right: 1px solid #e2e8f0;
             display: flex; flex-direction: column; position: fixed; top: 0; left: 0;
             z-index: 100; transition: transform .25s; }
  .sidebar-header { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white;
                    padding: 20px; }
  .sidebar-header h1 { font-size: 1.05rem; font-weight: 700; }
  .sidebar-header p  { font-size: 0.75rem; opacity: 0.8; margin-top: 4px; }
  .sidebar-section { padding: 12px 16px; border-bottom: 1px solid #f1f5f9; }
  .sidebar-section-title { font-size: 0.68rem; font-weight: 700; letter-spacing: .08em;
                           text-transform: uppercase; color: #94a3b8; margin-bottom: 8px; }
  .search { width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
            font-size: 0.85rem; outline: none; }
  .search:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,.12); }

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
  .content { margin-left: 260px; flex: 1; padding: 24px; min-height: 100vh; }

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
  .private-badge { font-size: 0.65rem; background: #fef3c3; color: #854d0e;
                   padding: 2px 6px; border-radius: 8px; font-weight: 600; }

  /* --- date group --- */
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
  .badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 10px; margin-left: 6px;
           font-weight: 700; text-transform: uppercase; vertical-align: middle; }
  .badge.pdf  { background: #fee2e2; color: #991b1b; }
  .badge.html { background: #dcfce7; color: #166534; }

  /* --- delete button --- */
  .delete-btn { flex-shrink: 0; width: 30px; height: 30px; border: none; border-radius: 6px;
                background: transparent; color: #94a3b8; cursor: pointer; font-size: 0.9rem;
                display: flex; align-items: center; justify-content: center;
                transition: all .15s; margin-left: 8px; }
  .delete-btn:hover { background: #fee2e2; color: #dc2626; }

  /* --- confirm dialog --- */
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

  /* --- grid view --- */
  .grid-view .date-group { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
  .grid-view .date-label { grid-column: 1 / -1; }
  .grid-view .card { flex-direction: column; align-items: flex-start; padding: 16px; }
  .grid-view .card .icon { margin: 0 0 8px 0; font-size: 1.6rem; }
  .grid-view .card .name { white-space: normal; word-break: break-all; }
  .grid-view .delete-btn { position: absolute; top: 8px; right: 8px; }

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
  .skill-btn .needs-cli { font-size: 0.6rem; color: #94a3b8; }

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
<button class="hamburger" id="hamburger">☰</button>

<!-- sidebar -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <h1>AutoDailyTask</h1>
    <p><span id="visible-count">{count}</span> 件のレポート</p>
  </div>

  <div class="sidebar-section">
    <input class="search" type="text" placeholder="検索…" id="search">
  </div>

  <div class="sidebar-section">
    <div class="sidebar-section-title">カテゴリ</div>
    <div id="filters">
      <div class="nav-item active" data-category="all">
        <span class="nav-icon">📋</span><span class="nav-label">すべて</span>
      </div>
      {nav_items}
    </div>
  </div>

  <div class="sidebar-section">
    <div class="sidebar-section-title">表示設定</div>
    <div class="toggle-row" id="privacy-toggle" title="プライベートなレポートの表示/非表示">
      <span>🔒 プライベート表示</span>
      <div class="toggle-track"><div class="toggle-thumb"></div></div>
    </div>
    <div class="view-row" style="margin-top: 8px;">
      <button class="view-btn active" data-view="list">☰ リスト</button>
      <button class="view-btn" data-view="grid">⊞ グリッド</button>
    </div>
  </div>

  <div class="sidebar-section">
    <div class="sidebar-section-title">スキル実行</div>
    <div id="skill-list">
      {skill_buttons}
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
<script>window.__SKILL_FORMS = {skill_forms_json};</script>

<!-- main content -->
<div class="content" id="main">
{body}
<p class="no-results" id="no-results">該当するレポートが見つかりません</p>
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

<script>
(function() {
  const search = document.getElementById('search');
  const main = document.getElementById('main');
  const noResults = document.getElementById('no-results');
  const visibleCount = document.getElementById('visible-count');
  const navItems = document.querySelectorAll('.nav-item');
  const viewBtns = document.querySelectorAll('.view-btn');
  const privacyToggle = document.getElementById('privacy-toggle');
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');

  let activeCategory = 'all';
  let showPrivate = false;

  // --- restore privacy state from localStorage ---
  if (localStorage.getItem('showPrivate') === 'true') {
    showPrivate = true;
    privacyToggle.classList.add('on');
  }

  // --- hamburger (mobile) ---
  hamburger.addEventListener('click', () => sidebar.classList.toggle('open'));
  main.addEventListener('click', () => sidebar.classList.remove('open'));

  // --- category collapse ---
  document.querySelectorAll('.category-header').forEach(h => {
    h.addEventListener('click', () => h.parentElement.classList.toggle('collapsed'));
  });

  // --- sidebar nav filter ---
  navItems.forEach(btn => {
    btn.addEventListener('click', () => {
      navItems.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.category;
      applyFilters();
    });
  });

  // --- search ---
  search.addEventListener('input', () => applyFilters());

  // --- privacy toggle ---
  privacyToggle.addEventListener('click', () => {
    showPrivate = !showPrivate;
    privacyToggle.classList.toggle('on', showPrivate);
    localStorage.setItem('showPrivate', showPrivate);
    applyFilters();
  });

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

    // サイドバーのカテゴリナビもプライベートトグルに連動
    navItems.forEach(nav => {
      const isPrivate = nav.dataset.private === 'true';
      nav.classList.toggle('hidden', isPrivate && !showPrivate);
    });

    // スキルボタンもプライベートトグルに連動
    document.querySelectorAll('.skill-btn').forEach(btn => {
      const isPrivate = btn.dataset.private === 'true';
      btn.classList.toggle('hidden', isPrivate && !showPrivate);
    });

    // プライベート非表示中にプライベートカテゴリが選択されていたら「すべて」にリセット
    const activeNav = document.querySelector('.nav-item.active');
    if (activeNav && activeNav.dataset.private === 'true' && !showPrivate) {
      navItems.forEach(b => b.classList.remove('active'));
      document.querySelector('.nav-item[data-category="all"]').classList.add('active');
      activeCategory = 'all';
    }

    document.querySelectorAll('.category').forEach(cat => {
      const catName = cat.dataset.category;
      const isPrivate = cat.dataset.private === 'true';
      const catMatch = activeCategory === 'all' || catName === activeCategory;
      const privacyMatch = !isPrivate || showPrivate;

      cat.querySelectorAll('.date-group').forEach(dg => {
        let groupVisible = 0;
        dg.querySelectorAll('.card').forEach(card => {
          const text = card.dataset.name.toLowerCase();
          const show = catMatch && privacyMatch && (!q || text.includes(q));
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

  // --- delete ---
  const deleteDialog = document.getElementById('delete-dialog');
  const deleteTargetName = document.getElementById('delete-target-name');
  const deleteCancel = document.getElementById('delete-cancel');
  const deleteConfirm = document.getElementById('delete-confirm');
  let pendingDeleteCard = null;

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.delete-btn');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    pendingDeleteCard = btn.closest('.card');
    deleteTargetName.textContent = pendingDeleteCard.dataset.name;
    deleteDialog.classList.remove('hidden');
  });

  deleteCancel.addEventListener('click', () => {
    deleteDialog.classList.add('hidden');
    pendingDeleteCard = null;
  });

  deleteDialog.addEventListener('click', (e) => {
    if (e.target === deleteDialog) {
      deleteDialog.classList.add('hidden');
      pendingDeleteCard = null;
    }
  });

  deleteConfirm.addEventListener('click', async () => {
    if (!pendingDeleteCard) return;
    const filename = pendingDeleteCard.dataset.name;
    deleteConfirm.disabled = true;
    deleteConfirm.textContent = '削除中…';

    try {
      const res = await fetch('/api/delete?file=' + encodeURIComponent(filename), { method: 'DELETE' });
      if (res.ok) {
        pendingDeleteCard.remove();
        // clean up empty date groups and categories
        document.querySelectorAll('.date-group').forEach(dg => {
          if (!dg.querySelector('.card')) dg.remove();
        });
        document.querySelectorAll('.category').forEach(cat => {
          if (!cat.querySelector('.card')) cat.remove();
        });
        applyFilters();
      } else {
        alert('削除に失敗しました: ' + (await res.text()));
      }
    } catch (err) {
      alert('削除に失敗しました: ' + err.message);
    }

    deleteDialog.classList.add('hidden');
    deleteConfirm.disabled = false;
    deleteConfirm.textContent = '削除する';
    pendingDeleteCard = null;
  });

  // --- skill form modal ---
  var FORMS = window.__SKILL_FORMS || {};
  var formDialog = document.getElementById('skill-form-dialog');
  var formTitle = document.getElementById('skill-form-title');
  var formDesc = document.getElementById('skill-form-desc');
  var formBody = document.getElementById('skill-form-body');
  var formCancelBtn = document.getElementById('skill-form-cancel');
  var formSubmitBtn = document.getElementById('skill-form-submit');
  var activeFormSkill = null;

  function openSkillForm(skillKey) {
    var def = FORMS[skillKey];
    if (!def) return;
    activeFormSkill = skillKey;
    formTitle.textContent = def.icon + ' ' + def.title;
    formDesc.textContent = def.description;
    var h = '';
    def.fields.forEach(function(f) {
      var id = 'sf-' + f[0], reqMark = f[4] ? '<span class="req">*</span>' : '';
      h += '<div class="form-field"><label for="' + id + '">' + f[1] + reqMark + '</label>';
      if (f[2] === 'select' && f[5]) {
        h += '<select id="' + id + '" data-field="' + f[0] + '"' + (f[4] ? ' required' : '') + '>';
        h += '<option value="">選択してください</option>';
        f[5].forEach(function(o) { h += '<option value="' + o[0] + '">' + o[1] + '</option>'; });
        h += '</select>';
      } else {
        h += '<input id="' + id + '" data-field="' + f[0] + '" type="text" placeholder="' + (f[3]||'') + '"' + (f[4] ? ' required' : '') + '>';
      }
      h += '</div>';
    });
    formBody.innerHTML = h;
    formDialog.classList.remove('hidden');
  }

  function closeSkillForm() { formDialog.classList.add('hidden'); activeFormSkill = null; }
  formCancelBtn.addEventListener('click', closeSkillForm);
  formDialog.addEventListener('click', function(e) { if (e.target === formDialog) closeSkillForm(); });

  function runFormSkill() {
    if (!activeFormSkill) return;
    var def = FORMS[activeFormSkill], valid = true;
    def.fields.forEach(function(f) {
      if (f[4]) {
        var el = document.getElementById('sf-' + f[0]);
        if (!el || !el.value.trim()) { valid = false; el.style.borderColor = '#ef4444'; }
        else { el.style.borderColor = ''; }
      }
    });
    if (!valid) { showToast('必須項目を入力してください'); return; }
    var args = [];
    def.fields.forEach(function(f) {
      var el = document.getElementById('sf-' + f[0]);
      if (el && el.value.trim()) args.push(el.value.trim());
    });
    var sk = activeFormSkill;
    closeSkillForm();
    var btn = document.querySelector('.skill-btn[data-skill="' + sk + '"]');
    if (btn) { btn.disabled = true; btn.classList.add('running'); btn.querySelector('.skill-status').textContent = '実行中…'; }
    showToast('/' + sk + ' を実行中…', 4000);
    fetch('/api/run-skill', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({skill: sk, args: args.join(' ')})
    }).then(function(res) { return res.json().then(function(d) { return {ok:res.ok, data:d}; }); })
    .then(function(r) {
      if (!r.ok) {
        if (btn) { btn.classList.remove('running'); btn.classList.add('error'); btn.querySelector('.skill-status').textContent = 'エラー'; }
        showToast('エラー: ' + (r.data.error||'不明'), 5000);
        if (btn) setTimeout(function() { btn.disabled=false; btn.classList.remove('error'); btn.querySelector('.skill-status').textContent='📝'; }, 5000);
        return;
      }
      var jobId = r.data.job_id;
      var poll = setInterval(function() {
        fetch('/api/skill-status?id=' + jobId).then(function(sr){return sr.json();}).then(function(sd) {
          if (sd.status==='done') { clearInterval(poll);
            if(btn){btn.classList.remove('running');btn.classList.add('done');btn.querySelector('.skill-status').textContent='完了';}
            showToast('/'+sk+' が完了しました。ページを更新してください。');
            if(btn) setTimeout(function(){btn.disabled=false;btn.classList.remove('done');btn.querySelector('.skill-status').textContent='📝';},8000);
          } else if (sd.status==='error') { clearInterval(poll);
            if(btn){btn.classList.remove('running');btn.classList.add('error');btn.querySelector('.skill-status').textContent='エラー';}
            showToast('/'+sk+' がエラーで終了',5000);
            if(btn) setTimeout(function(){btn.disabled=false;btn.classList.remove('error');btn.querySelector('.skill-status').textContent='📝';},8000);
          }
        });
      }, 3000);
    }).catch(function(err) {
      if(btn){btn.disabled=false;btn.classList.remove('running');btn.querySelector('.skill-status').textContent='📝';}
      showToast('通信エラー: '+err.message,5000);
    });
  }
  formSubmitBtn.addEventListener('click', runFormSkill);
  document.querySelectorAll('.skill-btn[data-runnable="form"]').forEach(function(btn) {
    btn.addEventListener('click', function() { openSkillForm(btn.dataset.skill); });
  });

  // --- skills ---
  const toast = document.getElementById('toast');
  function showToast(msg, duration = 3000) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
  }

  document.querySelectorAll('.skill-btn[data-runnable="true"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const skill = btn.dataset.skill;
      btn.disabled = true;
      btn.classList.add('running');
      btn.querySelector('.skill-status').textContent = '実行中…';
      showToast('/' + skill + ' を実行中…', 4000);

      try {
        const res = await fetch('/api/run-skill', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ skill })
        });
        const data = await res.json();
        if (!res.ok) {
          btn.classList.remove('running');
          btn.classList.add('error');
          btn.querySelector('.skill-status').textContent = 'エラー';
          showToast('エラー: ' + (data.error || '不明'), 5000);
          setTimeout(() => { btn.disabled = false; btn.classList.remove('error'); btn.querySelector('.skill-status').textContent = '▶'; }, 5000);
          return;
        }
        const jobId = data.job_id;
        // poll for completion
        const poll = setInterval(async () => {
          const sr = await fetch('/api/skill-status?id=' + jobId);
          const sd = await sr.json();
          if (sd.status === 'done') {
            clearInterval(poll);
            btn.classList.remove('running');
            btn.classList.add('done');
            btn.querySelector('.skill-status').textContent = '完了';
            showToast('/' + skill + ' が完了しました。ページを更新してください。');
            setTimeout(() => { btn.disabled = false; btn.classList.remove('done'); btn.querySelector('.skill-status').textContent = '▶'; }, 8000);
          } else if (sd.status === 'error') {
            clearInterval(poll);
            btn.classList.remove('running');
            btn.classList.add('error');
            btn.querySelector('.skill-status').textContent = 'エラー';
            showToast('/' + skill + ' がエラーで終了: ' + (sd.output || ''), 5000);
            setTimeout(() => { btn.disabled = false; btn.classList.remove('error'); btn.querySelector('.skill-status').textContent = '▶'; }, 8000);
          }
        }, 3000);
      } catch (err) {
        btn.disabled = false;
        btn.classList.remove('running');
        showToast('通信エラー: ' + err.message, 5000);
        btn.querySelector('.skill-status').textContent = '▶';
      }
    });
  });

  // initial filter
  applyFilters();
})();
</script>
</body>
</html>
"""

# カテゴリ定義: ファイル名プレフィックス → (表示名, アイコン, プライベートフラグ)
CATEGORIES = {
    "ai-report":             ("AI動向レポート", "🤖", False),
    "trading-card-release":  ("トレカ新発売情報", "🃏", False),
    "fashion-report":        ("ファッションレポート", "👗", True),
    "travel-plan":           ("国内旅行プラン", "✈️", True),
    "vtuber-riona":          ("VTuber推し活", "🎀", True),
}
DEFAULT_CATEGORY = ("その他", "📝", False)


def run_skill_async(job_id, skill_name, args=""):
    """サブプロセスでclaude CLIを実行してスキルを起動する"""
    job = _jobs[job_id]
    job["status"] = "running"
    job["started_at"] = time.time()
    prompt = "/%s %s" % (skill_name, args) if args else "/%s" % skill_name
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--verbose"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )
        job["status"] = "done" if result.returncode == 0 else "error"
        job["exit_code"] = result.returncode
        # 最後の数行だけ保持
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


def extract_summary(path: Path, max_len: int = 120) -> str:
    """HTMLファイルから概要テキストを抽出する"""
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


def classify(filename: str) -> str:
    """ファイル名からカテゴリキーを判定する"""
    for prefix in sorted(CATEGORIES.keys(), key=len, reverse=True):
        if filename.startswith(prefix):
            return prefix
    return "_other"


def build_skill_buttons() -> str:
    """サイドバーのスキル実行ボタンを生成する"""
    buttons = []
    for skill_key, (label, icon, runnable, private) in SKILLS.items():
        priv_attr = "true" if private else "false"
        if runnable:
            buttons.append(
                f'<button class="skill-btn" data-skill="{skill_key}" data-runnable="true" data-private="{priv_attr}">'
                f'<span class="skill-icon">{icon}</span>'
                f'<span class="skill-name">{label}</span>'
                f'<span class="skill-status">▶</span>'
                f'</button>'
            )
        else:
            buttons.append(
                f'<button class="skill-btn" data-skill="{skill_key}" data-runnable="form" data-private="{priv_attr}">'
                f'<span class="skill-icon">{icon}</span>'
                f'<span class="skill-name">{label}</span>'
                f'<span class="skill-status">📝</span>'
                f'</button>'
            )
    return "\n      ".join(buttons)


def _render(count: int, body: str, nav_items: str = "") -> str:
    """INDEX_HTML のプレースホルダを安全に置換する"""
    return (INDEX_HTML
            .replace("{count}", str(count))
            .replace("{body}", body)
            .replace("{nav_items}", nav_items)
            .replace("{skill_buttons}", build_skill_buttons())
            .replace("{skill_forms_json}", json.dumps(SKILL_FORMS, ensure_ascii=False)))


def build_index():
    if not REPORTS_DIR.exists():
        return _render(0, '<p class="empty">reports/ ディレクトリが見つかりません</p>')

    tree = {}  # type: dict
    for f in sorted(REPORTS_DIR.iterdir()):
        if f.suffix not in (".pdf", ".html"):
            continue
        cat = classify(f.name)
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        date_key = m.group() if m else "日付なし"
        tree.setdefault(cat, {}).setdefault(date_key, []).append(f)

    if not tree:
        return _render(0, '<p class="empty">レポートがまだありません</p>')

    nav_items = []
    cat_order = [k for k in CATEGORIES if k in tree]
    if "_other" in tree:
        cat_order.append("_other")

    for cat_key in cat_order:
        label, icon, is_private = CATEGORIES.get(cat_key, DEFAULT_CATEGORY)
        n = sum(len(fs) for fs in tree[cat_key].values())
        private_attr = "true" if is_private else "false"
        nav_items.append(
            f'<div class="nav-item" data-category="{cat_key}" data-private="{private_attr}">'
            f'<span class="nav-icon">{icon}</span>'
            f'<span class="nav-label">{label}</span>'
            f'<span class="nav-count">{n}</span>'
            f'</div>'
        )

    rows = []
    total = 0

    for cat_key in cat_order:
        dates = tree[cat_key]
        label, icon, is_private = CATEGORIES.get(cat_key, DEFAULT_CATEGORY)
        cat_count = sum(len(fs) for fs in dates.values())
        private_attr = "true" if is_private else "false"
        private_badge = ' <span class="private-badge">プライベート</span>' if is_private else ""

        rows.append(f'<div class="category" data-category="{cat_key}" data-private="{private_attr}">')
        rows.append(
            f'<div class="category-header">'
            f'<span class="category-icon">{icon}</span>'
            f'<span class="category-name">{label}{private_badge}</span>'
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
                    f'<button class="delete-btn" title="削除">🗑</button>'
                    f'</a>'
                )
                total += 1

            rows.append('</div>')

        rows.append('</div></div>')

    body_html = "\n".join(rows)
    nav_html = "\n      ".join(nav_items)

    return _render(total, body_html, nav_html)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def send_json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

        if path == "/api/skill-status":
            query = unquote(self.path.split("?", 1)[1]) if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
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

        if path.startswith("/reports/"):
            filename = path[len("/reports/"):]
            filepath = REPORTS_DIR / filename
            if filepath.exists() and filepath.parent == REPORTS_DIR:
                self.send_file(filepath)
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        path = unquote(self.path.split("?")[0])

        if path == "/api/run-skill":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            skill_name = body.get("skill", "")
            args = body.get("args", "")

            if skill_name not in SKILLS:
                self.send_json(400, {"error": f"不明なスキル: {skill_name}"})
                return

            _, _, runnable, _ = SKILLS[skill_name]
            if not runnable and not args:
                self.send_json(400, {"error": "このスキルはフォーム入力が必要です"})
                return

            # 同じスキルが実行中なら拒否
            for job in _jobs.values():
                if job["skill"] == skill_name and job["status"] == "running":
                    self.send_json(409, {"error": f"{skill_name} は既に実行中です"})
                    return

            job_id = str(uuid.uuid4())[:8]
            _jobs[job_id] = {"skill": skill_name, "status": "queued"}
            thread = threading.Thread(target=run_skill_async, args=(job_id, skill_name, args), daemon=True)
            thread.start()
            print(f"  スキル実行開始: /{skill_name} (job={job_id})")
            self.send_json(200, {"job_id": job_id, "skill": skill_name})
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        path = unquote(self.path.split("?")[0])
        query = unquote(self.path.split("?", 1)[1]) if "?" in self.path else ""

        if path == "/api/delete":
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            filename = params.get("file", "")

            if not filename or "/" in filename or "\\" in filename:
                self.send_json(400, {"error": "不正なファイル名"})
                return

            filepath = REPORTS_DIR / filename
            if not filepath.exists() or filepath.parent != REPORTS_DIR:
                self.send_json(404, {"error": "ファイルが見つかりません"})
                return

            if filepath.suffix not in (".pdf", ".html"):
                self.send_json(403, {"error": "削除できないファイル形式"})
                return

            try:
                filepath.unlink()
                print(f"  削除: {filepath}")
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
    url = f"http://localhost:{args.port}"
    print(f"レポートビューア起動中: {url}")
    print("終了するには Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました")


if __name__ == "__main__":
    main()
