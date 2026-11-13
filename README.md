# 生成AIパスポート 模擬試験アプリ

個人学習用の模擬試験アプリです（この端末だけで使用し、公開・配布しません）。
問題データ（`data/`）と公式シラバス（`syllabus/`）は著作権への配慮から Git 管理外です。

## 機能

- 全章からランダムに60問を出題（選択肢の順序もシャッフル）
- 1問回答するごとに正誤・正解・解説を表示（前の問題に戻って再回答はできない）
- 結果ページで、スコア（60問中の正解数）、章別・中項目別・形式別の正答率、60問の正誤一覧、誤答の解説を表示
- Gemini API による総評と回答傾向のフィードバック

## セットアップ

1. 仮想環境（venv）を作成し、依存パッケージをインストールする（`.venv/` は Git 追跡対象外）。
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
2. `.env.example` を `.env` にコピーし、`GEMINI_API_KEY` を設定する（`.env` は Git 追跡対象外）。
3. `data/all.json` を配置する（`tools/merge.py` で生成）。

## 起動

```powershell
$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe app.py
```

ブラウザで http://127.0.0.1:5000/ を開く。

## テスト

```powershell
$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

テストはダミーデータのみを使い、本物の問題文は含めません。

## PWA版（iPhone 用・GitHub Pages で配信）

`pwa/` は Flask 版と同じ機能をブラウザだけで動かす版です。配信 URL: https://3sss-a-nagasawa.github.io/study-aipass/

- 配信されるのはアプリのコードのみ。問題データ・APIキー・履歴は端末のブラウザ内（localStorage）にのみ保存する。
- `main` への push で `.github/workflows/pages.yml` が配信する。配信前にテストと、JSON・APIキーが含まれないことの確認を行う。
- アプリを更新したら `pwa/sw.js` の `CACHE_VERSION` を上げる（端末のキャッシュを更新するため）。

### iPhone での使い方

1. Safari で配信 URL を開き、「共有 → ホーム画面に追加」。
2. `data/all.json` を iCloud Drive などに置き、アプリの「問題データを取り込む」で選ぶ。
3. 「設定」で Gemini の APIキーを入力する。
4. 端末のデータは長期間使わないと消えることがあるため、「設定 → 受験履歴のバックアップ」で定期的に書き出す。

### APIキーの安全設定（Google Cloud コンソール）

- PWA 専用のキーを AI Studio で発行する。新形式の認証キー（`AQ.…`）は既定で Gemini API のみに制限されている。
- 認証キーはウェブサイト（HTTP リファラー）制限に対応していないため、アプリケーションの制限は「なし」とする。
- 代わりに次で被害を抑える。
  - キーはコード・GitHub に含めず、端末の設定画面でのみ入力する。
  - Generative Language API の割り当てで「1日あたりのリクエスト数」を低く（例: 50）設定する。
  - 課金を有効にしている場合は予算アラートを設定する。
  - 漏えいの疑いがあれば AI Studio でキーを削除し、作り直して端末に入れ直す。

### テスト

```powershell
node pwa/tests/run.js
```

## 構成

| ファイル | 役割 |
|---|---|
| `app.py` | Flask のルーティング |
| `config.py` | `.env` からの設定読み込み |
| `quiz.py` | 出題・採点・集計（画面に依存しない） |
| `feedback.py` | Gemini API による総評生成 |
| `templates/`, `static/` | 画面 |
| `tools/` | 問題データの検証・統合スクリプト、アイコン生成 |
| `pwa/` | PWA版（`js/quiz.js` は `quiz.py` の移植） |

## 使用モデル

既定は `gemini-3.5-flash-lite`（`.env` の `GEMINI_MODEL` で変更可）。

## 採点・送信の仕様

- 複数選択は、正解をすべて選び、余計な選択肢を選んでいない場合のみ正解。
- Gemini へは正誤の集計、全問の問題文、誤答した問題の選択肢・回答・正解を送信する（解説は送らない）。
- 試験の状態はアプリのメモリ上に保持する（アプリを再起動すると受験中の試験は消える）。
