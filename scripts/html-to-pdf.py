#!/usr/bin/env python3
"""
html-to-pdf.py
HTMLファイルをPDFに変換する

使用方法:
    python3 scripts/html-to-pdf.py <input.html> [output.pdf]
"""

import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 scripts/html-to-pdf.py <input.html> [output.pdf]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 出力パスの決定（指定なければ同名の.pdf）
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_suffix(".pdf")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()

        # PDF向け追加CSS（日本語フォント・ページサイズ・印刷調整）
        pdf_css = CSS(string="""
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;600;700&display=swap');
            @page {
                size: A4;
                margin: 15mm 12mm;
            }
            body {
                font-family: 'Noto Sans JP', 'Hiragino Kaku Gothic ProN',
                             'Meiryo', sans-serif !important;
                font-size: 10px;
                padding: 0;
                max-width: 100%;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .header { page-break-inside: avoid; }
            .card { page-break-inside: avoid; }
            .grid-3, .grid-2 { page-break-inside: auto; }
            a { color: inherit; text-decoration: none; }
        """, font_config=font_config)

        html = HTML(filename=str(input_path))
        html.write_pdf(
            str(output_path),
            stylesheets=[pdf_css],
            font_config=font_config,
            presentational_hints=True,
        )

        size_kb = output_path.stat().st_size // 1024
        print(f"✅ PDF生成完了: {output_path} ({size_kb} KB)")
        print(str(output_path))  # 最終行にパスを出力（スクリプトから読み取り用）

    except ImportError:
        print("エラー: weasyprint がインストールされていません", file=sys.stderr)
        print("実行: pip3 install weasyprint", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: PDF生成に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
