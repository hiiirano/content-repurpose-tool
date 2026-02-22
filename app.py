import os
import streamlit as st
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()


# ── ユーティリティ ────────────────────────────────────────────

def get_secret(key: str) -> str:
    """st.secrets → 環境変数 の順で取得"""
    try:
        return st.secrets.get(key, os.getenv(key, ""))
    except Exception:
        return os.getenv(key, "")


def fetch_url_content(url: str) -> str:
    """URLから記事テキストを取得・整形"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]
    return "\n".join(lines)[:8000]


# ── プロンプト ────────────────────────────────────────────────

def build_prompt(article: str, sns: str, language: str) -> str:
    ja = language == "日本語"

    if sns == "x":
        if ja:
            return f"""以下の記事を読み、X（Twitter）用投稿文を3案作成してください。

【条件】
- 各案は140文字以内（厳守）
- 読者が思わず反応したくなるフックで始める
- 記事の核心的な価値・気づきを簡潔に伝える
- 自然な会話調（硬すぎない）
- ハッシュタグは含めない
- 各案の区切りは「---」のみ。ラベル不要、本文のみ出力

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article below and write 3 X (Twitter) post variations.

Rules:
- Each post must be under 280 characters (strictly enforced)
- Open with a hook that stops the scroll
- Convey the key insight concisely
- Natural, conversational tone
- No hashtags
- Separate variations with "---" only. No labels, body text only.

Article:
{article[:4000]}"""

    elif sns == "note":
        if ja:
            return f"""以下の記事を読み、noteの導入文を作成してください。

【条件】
- 200〜400文字
- 読者が「全部読みたい」と感じる書き出し
- 記事の問いかけや気づきをほのめかす（答えは出さない）
- 体験・感情を交えた温かみのある文体
- 最後は「続きを読む↓」など自然な誘導で締める

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article below and write an introduction for a note/Medium-style post.

Rules:
- 150–300 words
- Open with a hook that makes readers want more
- Hint at the key insight without revealing everything
- Warm, personal tone with a hint of your own experience
- End with a natural transition (e.g., "Here's what I discovered...")

Article:
{article[:4000]}"""

    elif sns == "instagram":
        if ja:
            return f"""以下の記事を読み、Instagram用キャプションを作成してください。

【条件】
- キャプション本文: 150〜300文字
- 絵文字を適度に使う（1〜2行に1個程度）
- 保存・シェアしたくなる「学び系」または「共感系」の内容
- 適切な改行で読みやすく
- 末尾にハッシュタグ5〜8個（改行して追記）

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article below and write an Instagram caption.

Rules:
- Main caption: 100–250 words
- Use emojis naturally (roughly one per paragraph)
- "Save-worthy" content: key insights or relatable moments
- Good line breaks for readability
- Add 5–8 relevant hashtags at the end (on a new line)

Article:
{article[:4000]}"""

    elif sns == "threads":
        if ja:
            return f"""以下の記事を読み、Threads用投稿文を作成してください。

【条件】
- 200〜300文字
- Xより少し詳しく・深掘りした内容
- 読者がコメントしたくなる問いかけで締める
- ハッシュタグは1〜2個のみ

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article below and write a Threads post.

Rules:
- 150–250 words
- Slightly more detailed than a tweet; share a genuine perspective
- End with a question that invites engagement
- 1–2 hashtags only

Article:
{article[:4000]}"""

    return ""


# ── LLM 呼び出し ─────────────────────────────────────────────

def call_gemini(prompt: str, api_key: str) -> str:
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


def call_claude(prompt: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def generate_all(article: str, sns_list: list, language: str,
                 use_claude: bool, gemini_key: str, claude_key: str) -> dict:
    results = {}
    for sns in sns_list:
        prompt = build_prompt(article, sns, language)
        raw = call_claude(prompt, claude_key) if use_claude else call_gemini(prompt, gemini_key)

        if sns == "x":
            parts = [p.strip() for p in raw.split("---") if p.strip()]
            results["x"] = parts[:3]
        else:
            results[sns] = raw.strip()
    return results


# ── UI ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="コンテンツリパーパシングツール",
    page_icon="📢",
    layout="wide",
)

st.title("📢 コンテンツリパーパシングツール")
st.caption("記事・ブログをSNS投稿文に一括変換")

# ── サイドバー ──
with st.sidebar:
    st.header("⚙️ 設定")

    st.subheader("🔑 APIキー")
    gemini_key = st.text_input(
        "Gemini API Key",
        value=get_secret("GEMINI_API_KEY"),
        type="password",
        placeholder="AIza...",
    )
    claude_key = st.text_input(
        "Claude API Key（オプション）",
        value=get_secret("CLAUDE_API_KEY"),
        type="password",
        placeholder="sk-ant-...",
    )

    st.subheader("🌐 言語")
    language = st.radio("出力言語", ["日本語", "English"],
                        index=0, label_visibility="collapsed")

    st.subheader("🤖 モデル")
    model_choice = st.radio(
        "モデル選択",
        ["コスト重視（Gemini Flash）", "品質重視（Claude Haiku）"],
        index=0,
        label_visibility="collapsed",
    )
    use_claude = "Claude" in model_choice

    if use_claude and not claude_key:
        st.warning("Claude API Keyを入力してください")
    if not use_claude and not gemini_key:
        st.warning("Gemini API Keyを入力してください")

    st.divider()
    st.caption(
        "Gemini APIキーは [Google AI Studio](https://aistudio.google.com/) で取得\n\n"
        "Claude APIキーは [Anthropic Console](https://console.anthropic.com/) で取得"
    )

# ── 入力 ──
article_text = ""
tab_text, tab_url = st.tabs(["📋 テキスト貼り付け", "🔗 URLから取得"])

with tab_text:
    article_text = st.text_area(
        "記事テキスト",
        height=250,
        placeholder="記事・ブログのテキストをここに貼り付けてください",
        label_visibility="collapsed",
    )

with tab_url:
    url_input = st.text_input(
        "URL",
        placeholder="https://example.com/article",
        label_visibility="collapsed",
    )
    if st.button("🔍 取得する", disabled=not url_input):
        with st.spinner("記事を取得中..."):
            try:
                fetched = fetch_url_content(url_input)
                st.session_state["fetched_text"] = fetched
                st.success(f"取得完了（{len(fetched)}文字）")
            except Exception as e:
                st.error(f"取得に失敗しました: {e}")

    if "fetched_text" in st.session_state:
        article_text = st.session_state["fetched_text"]
        with st.expander("取得したテキスト（確認用）"):
            st.text(article_text[:1500] + ("..." if len(article_text) > 1500 else ""))

# ── SNS選択 ──
st.subheader("投稿先を選ぶ")
col1, col2, col3, col4 = st.columns(4)
with col1:
    use_x = st.checkbox("𝕏  X（Twitter）", value=True)
with col2:
    use_note = st.checkbox("📝 note", value=True)
with col3:
    use_instagram = st.checkbox("📸 Instagram", value=False)
with col4:
    use_threads = st.checkbox("🧵 Threads", value=False)

# ── 生成ボタン ──
st.divider()
api_ready = (use_claude and bool(claude_key)) or (not use_claude and bool(gemini_key))
can_generate = bool(article_text.strip()) and api_ready

if st.button("🚀 投稿文を生成する", type="primary",
             use_container_width=True, disabled=not can_generate):
    selected = [s for s, v in [("x", use_x), ("note", use_note),
                                ("instagram", use_instagram), ("threads", use_threads)] if v]
    if not selected:
        st.error("投稿先を1つ以上選択してください")
    else:
        with st.spinner("生成中..."):
            try:
                results = generate_all(
                    article_text, selected, language,
                    use_claude, gemini_key, claude_key,
                )
                st.session_state["results"] = results
                st.session_state["selected"] = selected
            except Exception as e:
                st.error(f"生成に失敗しました: {e}")

# ── 結果表示 ──
if "results" in st.session_state:
    results = st.session_state["results"]
    selected = st.session_state["selected"]

    st.subheader("生成結果")

    label_map = {"x": "𝕏 X", "note": "📝 note",
                 "instagram": "📸 Instagram", "threads": "🧵 Threads"}
    tab_labels = [label_map[s] for s in selected]
    result_tabs = st.tabs(tab_labels)

    for i, sns in enumerate(selected):
        with result_tabs[i]:
            if sns == "x":
                st.markdown("**X（Twitter）投稿文 — 3案**")
                for j, post in enumerate(results.get("x", []), 1):
                    count = len(post)
                    status = "🟢" if count <= 140 else "🔴"
                    st.markdown(f"**案{j}** {status} {count}字")
                    st.code(post, language=None)
            elif sns == "note":
                st.markdown("**note 導入文**")
                body = results.get("note", "")
                st.markdown(f"📏 {len(body)}文字")
                st.code(body, language=None)
            elif sns == "instagram":
                st.markdown("**Instagram キャプション**")
                body = results.get("instagram", "")
                st.markdown(f"📏 {len(body)}文字")
                st.code(body, language=None)
            elif sns == "threads":
                st.markdown("**Threads 投稿文**")
                body = results.get("threads", "")
                st.markdown(f"📏 {len(body)}文字")
                st.code(body, language=None)
