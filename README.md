# 📢 コンテンツリパーパシングツール

記事・ブログをX、note、Instagram、Threadsの投稿文に一括変換するAIツール。

GAIS AI DEVCON 2026 応募作品。

## セットアップ

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# APIキーの設定
cp .env.example .env
# .env を編集して GEMINI_API_KEY を記入
```

## 起動

```bash
streamlit run app.py
```

## 使い方

1. サイドバーにAPIキーを入力
2. 言語（日本語 / English）を選択
3. モデルを選択（Gemini Flash: コスト重視 / Claude Haiku: 品質重視）
4. 記事テキストを貼り付け、またはURLを入力
5. 投稿先SNSを選択
6. 「投稿文を生成する」をクリック
7. 生成されたテキストをコピーして投稿

## 対応SNS

| SNS | 出力内容 |
|---|---|
| X（Twitter） | 140字以内 × 3案 |
| note | 導入文（200〜400字） |
| Instagram | キャプション＋ハッシュタグ |
| Threads | 投稿文（200〜300字） |

## 対応言語

- 日本語
- English

## 使用API

- Gemini API（Google）— デフォルト
- Claude API（Anthropic）— オプション

## デプロイ（Streamlit Community Cloud）

1. GitHubにリポジトリをpush
2. [share.streamlit.io](https://share.streamlit.io) でデプロイ
3. Settings → Secrets に `GEMINI_API_KEY` を設定
