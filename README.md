# C級審判 合格ノック

6人制バレーボール **C級審判員資格試験** の対策用Webアプリです。
演習問題・模擬試験・苦手問題の復習ができます。ビルド不要の静的サイトなので、
**GitHub Pages で無料公開**できます。

> ⚠️ 本アプリは学習用の非公式教材です。出題内容は(公財)日本バレーボール協会
> 「6人制バレーボール競技規則」を参考に作成していますが、**規則は年度により
> 改定されます**。受験前には必ず最新の公式ルールブック・受験地域(都道府県・
> 市区町村協会)の講習会資料で確認してください。

---

## できること

- **模擬試験モード** — 全カテゴリからランダムに25問、20分の制限時間つきで出題。終了後に合否ライン(目安70%)・カテゴリ別正答率・間違えた問題の解説を表示します。
- **演習モード** — カテゴリ(コート・用具／チーム編成／サービス・ローテーション／プレー・反則／リベロ／得点・セット・タイムアウト／審判員の役割・シグナル／大会運営)を選んで1問ずつ解説つきで学習できます。
- **苦手問題の復習** — これまでに間違えた問題だけを再出題します。
- 学習記録(カテゴリ別正答率・苦手問題)はブラウザの `localStorage` に保存されます(サーバー不要・個人情報の送信なし)。

## 使っている技術

素の **HTML / CSS / JavaScript** のみ。フレームワークやビルドツールは使っていないので、
`index.html` をブラウザで開くだけでも動作します(ローカルで問題データを読み込む場合は
簡易サーバー越しに開くことを推奨。下記参照)。

```
volleyball-c-referee-quiz/
├── index.html                 # アプリの本体(画面の入れ物)
├── style.css                  # デザイン
├── app.js                     # ロジック(出題・採点・保存)
├── questions.json             # 問題データ本体(ここを更新していく)
├── data/source_hashes.json    # 年次更新チェック用のハッシュ保存先(自動生成)
├── scripts/check_rule_updates.py  # ルール情報源の変化を検知するスクリプト
└── .github/workflows/check-rule-updates.yml  # 年1回の自動チェック(GitHub Actions)
```

## ローカルで確認する

ブラウザの `fetch` はローカルファイルを直接開くと制限がかかる場合があるため、
簡易サーバーを立てて確認するのがおすすめです。

```bash
cd volleyball-c-referee-quiz
python3 -m http.server 8000
# ブラウザで http://localhost:8000 を開く
```

## GitHub で公開する手順(GitHub Pages)

1. GitHub に新しいリポジトリを作成する(例: `volleyball-c-referee-quiz`)。
2. このフォルダの中身をリポジトリに push する。

   ```bash
   cd volleyball-c-referee-quiz
   git init
   git add .
   git commit -m "初回コミット: C級審判 合格ノック"
   git branch -M main
   git remote add origin https://github.com/<あなたのユーザー名>/<リポジトリ名>.git
   git push -u origin main
   ```

3. GitHub のリポジトリページで **Settings → Pages** を開く。
4. 「Build and deployment」の Source で **Deploy from a branch** を選択し、
   Branch を `main` / `/(root)` にして **Save**。
5. 数分後、`https://<あなたのユーザー名>.github.io/<リポジトリ名>/` で公開されます。

## 問題を追加・修正する

すべての問題は `questions.json` にまとまっています。1問は以下の形式です。

```json
{
  "id": "q049",
  "category": "play",
  "type": "single",
  "question": "問題文",
  "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
  "answer": 0,
  "explanation": "正解の根拠・解説文",
  "difficulty": "basic"
}
```

- `id` は重複しないユニークな文字列にする。
- `category` は `questions.json` の `categories` に定義されているIDを使う。
- `answer` は `choices` 配列の **0始まりのインデックス**。
- カテゴリ自体を増やしたい場合は `categories` 配列にも追加する。

編集後は `python3 -c "import json;json.load(open('questions.json'))"` などで
JSONとして壊れていないか確認してから push すると安全です。

## 情報を毎年更新する仕組み

バレーボールの競技規則は年度ごとに改定されることがあるため、`questions.json` を
放置すると内容が古くなってしまいます。そこで、このリポジトリには
**年1回(6月1日/講習会シーズン前)自動でチェックする GitHub Actions ワークフロー**
(`.github/workflows/check-rule-updates.yml`)を用意しています。

- 動作: (公財)日本バレーボール協会の公式サイトなど、`scripts/check_rule_updates.py`
  に登録したURLの内容ハッシュを毎年比較し、変化があれば **GitHub Issue を自動作成**します。
- **問題データを自動で書き換えることはしません**(規則の解釈にはレビューが必要なため)。
  Issueが作成されたら、最新のルールブックを確認し、必要に応じて `questions.json` を
  手動で更新してください。
- 監視するURLを増やしたい場合(例: 神奈川県バレーボール協会や相模原バレーボール協会の
  ページ)は `scripts/check_rule_updates.py` の `SOURCES` 辞書に追加してください。
- 手動でチェックを走らせたい場合は、GitHubリポジトリの **Actions** タブから
  「年次ルール更新チェック」を選び、**Run workflow** で実行できます。

## ライセンス

MIT License（`LICENSE` ファイルを参照）。問題文・解説の内容についてはご自身の
受験地域のルールブックと必ず突き合わせたうえでご利用ください。
