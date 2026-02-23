# 📢 コンテンツリパーパシングツール

記事・ブログをSNS投稿文に一括変換 ＋ 意思決定支援（誰に・どこで・どう切るか）するAIツール。

**GAIS AI DEVCON 2026 応募作品。**

## 🚀 デモ

**[https://content-repurpose-tool-wjudcgntehoksmbykrmbv3.streamlit.app/](https://content-repurpose-tool-wjudcgntehoksmbykrmbv3.streamlit.app/)**

※ 利用にはGemini APIキー（無料）またはClaude APIキーが必要です。

## 概要

記事URLまたはテキストを入力するだけで：

1. **分析** — 誰に届けるべきか（ペルソナスコア）、どこで出すべきか（配信導線）、何本に切れるか（ネタ分割）を60秒で判断
2. **生成** — X・Facebook・Instagram・note・Threads向けの投稿文を一括生成

### GAISモード
GAIS（生成AI協会）向けに特化した出力モード。自治体DX・建設DX・教育担当者へのスコアを重点評価し、公式導線（X/Facebook/YouTube/公式サイト/メール）と会員拡散導線を分けて提示。

## 対応SNS

| SNS | 出力内容 |
|---|---|
| X（Twitter） | 140字以内（日本語）/ 280字以内（英語）× 3案 |
| Facebook | 投稿文（300〜500字） |
| Instagram | キャプション＋ハッシュタグ＋**画像生成プロンプト** |
| note | 導入文（200〜400字） |
| Threads | 投稿文（200〜300字） |

## 使い方

1. サイドバーにAPIキーを入力（Gemini または Claude）
2. 言語（日本語 / English）を選択
3. モデルを選択（コスト重視: Gemini / 品質重視: Claude Sonnet）
4. 記事テキストを貼り付け、またはURLを入力
5. 投稿先SNSを選択
6. 「分析して投稿文を生成する」をクリック

## 使用API

- **Gemini API**（Google）— デフォルト・コスト重視
- **Claude API**（Anthropic）— オプション・品質重視

APIキーはユーザーが入力する方式のため、ホスティングコストはゼロ。

## セットアップ（ローカル実行）

```bash
pip install -r requirements.txt
cp .env.example .env
# .env を編集して GEMINI_API_KEY を記入
streamlit run app.py
```

## 技術スタック

| 項目 | 内容 |
|---|---|
| フレームワーク | Streamlit |
| テキスト生成 | Gemini Flash / Claude Sonnet 4.6 |
| スクレイピング | requests + BeautifulSoup |
| デプロイ | Streamlit Community Cloud |
