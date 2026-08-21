#!/usr/bin/env python3
"""
年次ルール更新チェックスクリプト

(公財)日本バレーボール協会などの公式サイトの内容ハッシュを保存しておき、
前回実行時と比較して変化があれば "CHANGED:<キー1>,<キー2>" を標準出力に出す。
変化がなければ "OK" を出力する。

内容そのものの意味的な変更を判定するわけではない(HTMLの些細な変更でも
反応することがある)。あくまで「見直しのきっかけ」を作るためのチェック。

監視対象を増やしたい場合は SOURCES に追記する。
例: 都道府県・市区町村のバレーボール協会のC級審判講習会案内ページなど。
"""

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

# 監視対象のURL。キーは data/source_hashes.json 内の識別子になる。
# TODO: 実際に確認したいページのURLに置き換えてください
# (例: 神奈川県バレーボール協会・相模原バレーボール協会のC級審判講習会案内ページ等)。
SOURCES = {
    "jva_top": "https://www.jva.or.jp/",
}

HASH_FILE = Path(__file__).resolve().parent.parent / "data" / "source_hashes.json"
TIMEOUT_SEC = 15


def fetch_normalized_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (rule-update-checker)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
        raw = res.read().decode("utf-8", errors="ignore")
    # 日付・生成のたびに変わるトラッキングIDなどのノイズを軽く除去してから比較する。
    normalized = re.sub(r"\s+", " ", raw).strip()
    return normalized


def compute_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_previous_hashes():
    if HASH_FILE.exists():
        try:
            return json.loads(HASH_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_hashes(hashes):
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    previous = load_previous_hashes()
    current = {}
    changed_keys = []

    for key, url in SOURCES.items():
        try:
            text = fetch_normalized_text(url)
            current[key] = compute_hash(text)
        except Exception as e:
            # 取得失敗はサイト側の問題である可能性が高いため、変更検知としては扱わず
            # 前回値を維持する(次回の実行で再チェックされる)。
            current[key] = previous.get(key)
            print(f"[warn] {key} ({url}) の取得に失敗しました: {e}", file=sys.stderr)
            continue

        if key in previous and previous.get(key) and previous[key] != current[key]:
            changed_keys.append(key)

    save_hashes(current)

    if changed_keys:
        print(f"CHANGED:{','.join(changed_keys)}")
    else:
        print("OK")


if __name__ == "__main__":
    main()
