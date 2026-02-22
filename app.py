import os
import json
import re
import streamlit as st
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()

X_LIMIT = {"日本語": 140, "English": 280}


# ── ユーティリティ ────────────────────────────────────────────

def get_secret(key: str) -> str:
    try:
        return st.secrets.get(key, os.getenv(key, ""))
    except Exception:
        return os.getenv(key, "")


def fetch_url_content(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]
    return "\n".join(lines)[:8000]


def extract_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def build_all_copy_text(results: dict, selected: list) -> str:
    label_map = {"x": "X（Twitter）", "note": "note",
                 "instagram": "Instagram", "threads": "Threads", "facebook": "Facebook"}
    parts = []
    for sns in selected:
        if sns not in results:
            continue
        parts.append(f"=== {label_map.get(sns, sns)} ===")
        if sns == "x":
            for i, post in enumerate(results["x"], 1):
                parts.append(f"[案{i}] {post}")
        elif sns == "instagram":
            parts.append(results["instagram"])
            if results.get("instagram_image_prompt"):
                parts.append("\n--- 画像生成プロンプト ---")
                parts.append(results["instagram_image_prompt"])
        else:
            parts.append(results[sns])
        parts.append("")
    return "\n".join(parts)


# ── プロンプト ────────────────────────────────────────────────

def build_analysis_prompt(article: str, language: str, gais_mode: bool) -> str:
    if language == "日本語":
        score_rule = """
【スコアのメリハリ必須ルール】
- 全員高スコアは禁止。記事との関連が薄いペルソナは素直に低くする（30以下もOK）
- 高スコア（70以上）にできるのは最大3ペルソナまで
- 30〜65の中程度スコアを積極的に使い、差をつける
"""
        if gais_mode:
            gais_instr = """
【GAISモード有効】
- gais_tagsには必ず3〜8個のGAIS関連タグを含める（例: #GAIS #自治体DX #生成AI活用）
- platform_recommendationはGAIS導線として official（公式）と community（会員拡散）の2分類で出力
- トーン方針：協会・実務向け（煽りなし、再現性・現場感重視）
"""
            platform_schema = """\
  "platform_recommendation": {{
    "official": {{
      "top": "X",
      "reason": "50字以内の理由",
      "rankings": ["X", "Facebook", "YouTube", "GAIS公式サイト", "メール会員向け"]
    }},
    "community": {{
      "top": "個人X",
      "reason": "50字以内の理由",
      "rankings": ["個人X", "個人Facebook", "個人note", "Threads", "Instagram"]
    }}
  }},"""
        else:
            gais_instr = ""
            platform_schema = """\
  "platform_recommendation": {{
    "top": "note",
    "reason": "50字以内の理由",
    "rankings": ["note", "X", "Facebook", "Instagram", "Pinterest"]
  }},"""

        return f"""以下の記事を分析し、**JSONのみ**を出力してください。JSON以外のテキストは不要です。
{score_rule}{gais_instr}
【記事】
{article[:4000]}

【出力スキーマ（このフォーマット厳守）】
{{
  "content_type": {{
    "label": "解説記事",
    "confidence": 0.82,
    "candidates": ["解説記事", "ニュース", "HowTo", "事例紹介"]
  }},
  "persona_scores": {{
    "自治体DX担当者": {{ "score": 55, "reason": "30字以内の理由" }},
    "建設・建築業界のDX推進者": {{ "score": 40, "reason": "30字以内の理由" }},
    "中小企業経営者（AI活用検討中）": {{ "score": 80, "reason": "30字以内の理由" }},
    "AI開発者・エンジニア": {{ "score": 30, "reason": "30字以内の理由" }},
    "AI初心者（一般ビジネスパーソン）": {{ "score": 70, "reason": "30字以内の理由" }},
    "教育・人材育成担当": {{ "score": 45, "reason": "30字以内の理由" }},
    "経営層・意思決定者": {{ "score": 65, "reason": "30字以内の理由" }}
  }},
  {platform_schema}
  "content_potential": {{
    "post_count": 5,
    "angles": ["角度1", "角度2", "角度3", "角度4", "角度5"]
  }},
  "gais_tags": ["#GAIS", "#生成AI活用", "#AI活用"],
  "risk_flags": []
}}

制約: scoreは0〜100の整数。post_countとanglesの要素数を必ず一致させる（3〜7本）。gais_tagsは3〜8個。
risk_flagsに問題があれば: [{{"type": "claim", "severity": "low", "message": "内容", "suggestion": "修正案"}}]"""

    else:
        score_rule = """
[Score Variation Rule]
- Avoid giving everyone high scores. Assign low scores (under 30) to personas with little relevance.
- Maximum 3 personas can score 70 or above.
- Use middle scores (30-65) frequently to create contrast.
"""
        if gais_mode:
            gais_instr = """
[GAIS Mode Active]
- Include 3-8 GAIS-related tags in gais_tags
- platform_recommendation must use GAIS channels with "official" and "community" sub-objects
- Tone: Professional, practical, evidence-based (no hype)
"""
            platform_schema = """\
  "platform_recommendation": {{
    "official": {{
      "top": "X",
      "reason": "Brief reason",
      "rankings": ["X", "Facebook", "YouTube", "GAIS Official Site", "Member Email"]
    }},
    "community": {{
      "top": "Personal X",
      "reason": "Brief reason",
      "rankings": ["Personal X", "Personal Facebook", "Personal note", "Threads", "Instagram"]
    }}
  }},"""
        else:
            gais_instr = ""
            platform_schema = """\
  "platform_recommendation": {{
    "top": "Medium",
    "reason": "Brief reason",
    "rankings": ["Medium", "X", "LinkedIn", "Instagram", "Pinterest"]
  }},"""

        return f"""Analyze the article and output **JSON only**. No other text.
{score_rule}{gais_instr}
Article:
{article[:4000]}

Schema (follow exactly):
{{
  "content_type": {{
    "label": "How-To Guide",
    "confidence": 0.82,
    "candidates": ["Explainer", "News", "HowTo", "Case Study"]
  }},
  "persona_scores": {{
    "自治体DX担当者": {{ "score": 55, "reason": "Brief reason" }},
    "建設・建築業界のDX推進者": {{ "score": 40, "reason": "Brief reason" }},
    "中小企業経営者（AI活用検討中）": {{ "score": 80, "reason": "Brief reason" }},
    "AI開発者・エンジニア": {{ "score": 30, "reason": "Brief reason" }},
    "AI初心者（一般ビジネスパーソン）": {{ "score": 70, "reason": "Brief reason" }},
    "教育・人材育成担当": {{ "score": 45, "reason": "Brief reason" }},
    "経営層・意思決定者": {{ "score": 65, "reason": "Brief reason" }}
  }},
  {platform_schema}
  "content_potential": {{
    "post_count": 5,
    "angles": ["Angle 1", "Angle 2", "Angle 3", "Angle 4", "Angle 5"]
  }},
  "gais_tags": ["#GAIS", "#AItools", "#GenerativeAI"],
  "risk_flags": []
}}

Constraints: score integer 0-100. post_count must equal the number of angles (3-7). gais_tags: 3-8 items."""


def build_prompt(article: str, sns: str, language: str, gais_mode: bool) -> str:
    ja = language == "日本語"
    gais_note = "\n※GAISモード: 協会・実務向けのトーンで。煽りを避け、現場での再現性を重視。" if (gais_mode and ja) else (
        "\n[GAIS Mode: Professional, practical tone. No hype. Emphasize reproducibility.]" if gais_mode else "")
    limit = X_LIMIT[language]

    if sns == "x":
        if ja:
            return f"""以下の記事を読み、X（Twitter）用投稿文を3案作成してください。{gais_note}

【条件】
- 各案は{limit}文字以内（厳守・超えたら失格）
- 読者が思わず反応したくなるフックで始める
- 記事の核心的な価値・気づきを簡潔に伝える
- 自然な会話調（硬すぎない）
- ハッシュタグは含めない
- 各案の区切りは「---」のみ。ラベル不要、本文のみ出力

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article and write 3 X (Twitter) post variations.{gais_note}

Rules:
- Each post MUST be under {limit} characters (strictly enforced)
- Open with a scroll-stopping hook
- Convey the key insight concisely
- Natural, conversational tone
- No hashtags
- Separate with "---" only. No labels, body text only.

Article:
{article[:4000]}"""

    elif sns == "note":
        if ja:
            return f"""以下の記事を読み、noteの導入文を作成してください。{gais_note}

【条件】
- 200〜400文字
- 読者が「全部読みたい」と感じる書き出し
- 記事の問いかけや気づきをほのめかす（答えは出さない）
- 体験・感情を交えた温かみのある文体
- 最後は「続きを読む↓」など自然な誘導で締める

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article and write a note/blog introduction.{gais_note}

Rules:
- 150–300 words
- Hook that makes readers want more
- Hint at the key insight without revealing everything
- Warm, personal tone
- End with a natural transition

Article:
{article[:4000]}"""

    elif sns == "instagram":
        gais_ig = "\n- GAIS context: professional / practical / business-friendly / Japanese business setting. Infographic or diagram style. No sci-fi aesthetics." if gais_mode else ""
        if ja:
            return f"""以下の記事を読み、Instagram用キャプションと画像生成プロンプトを作成してください。{gais_note}

【キャプション条件】
- 150〜300文字
- 絵文字を適度に使う（1〜2行に1個程度）
- 保存・シェアしたくなる「学び系」または「共感系」の内容
- 適切な改行で読みやすく
- 末尾にハッシュタグ5〜8個（改行して追記）

【画像生成プロンプト条件（必須要素を全て含めること）】
- 主題（Subject）: 記事テーマを視覚化する被写体・場面
- シーン/構図（Scene）: 具体的な場所・状況（例: Japanese city hall office, construction site, modern classroom）
- スタイル（Style）: infographic / flat design / clean corporate / minimal のいずれか
- カラーパレット（Color）: 記事トーンに合った色指定（例: blue and white corporate palette）
- no text, no letters（文字なし）
- aspect ratio 1:1（Instagram正方形）
- high resolution{gais_ig}

【出力形式（この区切りを厳守）】
=== CAPTION ===
（キャプション本文）

=== IMAGE PROMPT ===
（英語の画像生成プロンプト・上記要素を必ず全て含む）

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article and write an Instagram caption and image generation prompt.{gais_note}

Caption rules:
- 100–250 words
- Use emojis naturally (roughly one per paragraph)
- "Save-worthy" content: key insights or relatable moments
- Good line breaks
- Add 5–8 relevant hashtags at the end on a new line

Image prompt rules (include ALL elements):
- Subject: the main visual representing the article's theme
- Scene/Composition: specific setting (e.g., Japanese city hall office, construction site, modern classroom)
- Style: infographic / flat design / clean corporate / minimal
- Color palette: (e.g., blue and white corporate palette)
- no text, no letters
- aspect ratio 1:1 (Instagram square)
- high resolution{gais_ig}

Output format (follow exactly):
=== CAPTION ===
(caption text)

=== IMAGE PROMPT ===
(English image generation prompt including ALL required elements)

Article:
{article[:4000]}"""

    elif sns == "facebook":
        if ja:
            return f"""以下の記事を読み、Facebook投稿文を作成してください。{gais_note}

【条件】
- 300〜500文字
- 導入で問いかけ or 共感フックを入れる
- 要点を3〜5点で整理（箇条書きも可）
- 読者がシェアしたくなる実務的な内容
- ハッシュタグは末尾に3〜5個

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article and write a Facebook post.{gais_note}

Rules:
- 200–400 words
- Open with a question or empathy hook
- Summarize key points (3–5 points, bullets OK)
- Practical, share-worthy content
- Add 3–5 hashtags at the end

Article:
{article[:4000]}"""

    elif sns == "threads":
        if ja:
            return f"""以下の記事を読み、Threads用投稿文を作成してください。{gais_note}

【条件】
- 200〜300文字
- Xより少し詳しく・深掘りした内容
- 読者がコメントしたくなる問いかけで締める
- ハッシュタグは1〜2個のみ

【記事】
{article[:4000]}"""
        else:
            return f"""Read the article and write a Threads post.{gais_note}

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
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text


def call_claude(prompt: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def generate_all(article: str, sns_list: list, language: str,
                 use_claude: bool, gemini_key: str, claude_key: str,
                 gais_mode: bool) -> dict:
    results = {}
    x_limit = X_LIMIT[language]
    for sns in sns_list:
        prompt = build_prompt(article, sns, language, gais_mode)
        raw = call_claude(prompt, claude_key) if use_claude else call_gemini(prompt, gemini_key)
        if sns == "x":
            parts = [p.strip() for p in raw.split("---") if p.strip()]
            validated = []
            for p in parts[:3]:
                if len(p) > x_limit:
                    p = p[:x_limit - 1] + "…"
                validated.append(p)
            results["x"] = validated
        elif sns == "instagram":
            if "=== IMAGE PROMPT ===" in raw:
                sections = raw.split("=== IMAGE PROMPT ===")
                caption = sections[0].replace("=== CAPTION ===", "").strip()
                image_prompt = sections[1].strip()
            else:
                caption = raw.strip()
                image_prompt = ""
            results["instagram"] = caption
            results["instagram_image_prompt"] = image_prompt
        else:
            results[sns] = raw.strip()
    return results


GAIS_CORRECTIONS = {
    "自治体DX担当者": +10,
    "建設・建築業界のDX推進者": +8,
    "教育・人材育成担当": +5,
    "AI開発者・エンジニア": -5,
}


def apply_gais_corrections(persona_scores: dict) -> dict:
    corrected = {}
    for persona, data in persona_scores.items():
        score = int(data.get("score", 0))
        delta = GAIS_CORRECTIONS.get(persona, 0)
        score = max(0, min(100, score + delta))
        corrected[persona] = {**data, "score": score}
    return corrected


def run_analysis(article: str, language: str, use_claude: bool,
                 gemini_key: str, claude_key: str, gais_mode: bool) -> dict:
    prompt = build_analysis_prompt(article, language, gais_mode)
    last_error = None
    for attempt in range(2):
        try:
            raw = call_claude(prompt, claude_key) if use_claude else call_gemini(prompt, gemini_key)
            result = extract_json(raw)
            if result and "persona_scores" in result:
                if gais_mode:
                    result["persona_scores"] = apply_gais_corrections(result["persona_scores"])
                # Validate post_count / angles consistency
                potential = result.get("content_potential", {})
                if potential:
                    angles = potential.get("angles", [])
                    angles = angles[:7]
                    if len(angles) < 3:
                        angles += [f"角度{i}" for i in range(len(angles) + 1, 4)]
                    result["content_potential"]["angles"] = angles
                    result["content_potential"]["post_count"] = len(angles)
                return result
        except Exception as e:
            last_error = e
    if last_error:
        raise last_error
    return {}


# ── UI ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="コンテンツリパーパシングツール",
    page_icon="📢",
    layout="wide",
)

st.title("📢 コンテンツリパーパシングツール")
st.caption("この記事を **①誰に** **②どこで** **③どう切るか** を60秒で判断し、投稿文を一括生成します。")

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
        ["コスト重視", "品質重視"],
        index=0,
        label_visibility="collapsed",
    )
    use_claude = model_choice == "品質重視"

    st.divider()

    st.subheader("🏛️ GAISモード")
    gais_mode = st.toggle("GAISモード ON", value=False)
    if gais_mode:
        st.info("・協会・実務向けトーン\n・GAISタグを優先出力\n・自治体DX/建設DX/教育を重点評価")

    st.divider()

    if use_claude and not claude_key:
        st.warning("Claude API Keyを入力してください")
    if not use_claude and not gemini_key:
        st.warning("Gemini API Keyを入力してください")

    st.caption(
        "Gemini: [Google AI Studio](https://aistudio.google.com/)\n\n"
        "Claude: [Anthropic Console](https://console.anthropic.com/)"
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
    if gais_mode:
        use_facebook = st.checkbox("👥 Facebook", value=True)
        use_note = False
    else:
        use_note = st.checkbox("📝 note", value=True)
        use_facebook = False
with col3:
    use_instagram = st.checkbox("📸 Instagram", value=False)
with col4:
    use_threads = st.checkbox("🧵 Threads", value=False)

# ── 生成ボタン ──
st.divider()
api_ready = (use_claude and bool(claude_key)) or (not use_claude and bool(gemini_key))
can_generate = bool(article_text.strip()) and api_ready

if st.button("🚀 分析して投稿文を生成する", type="primary",
             use_container_width=True, disabled=not can_generate):
    selected = [s for s, v in [("x", use_x), ("note", use_note),
                                ("facebook", use_facebook), ("instagram", use_instagram),
                                ("threads", use_threads)] if v]
    if not selected:
        st.error("投稿先を1つ以上選択してください")
    else:
        with st.spinner("📊 記事を分析中..."):
            try:
                analysis = run_analysis(
                    article_text, language, use_claude, gemini_key, claude_key, gais_mode
                )
                st.session_state["analysis"] = analysis
            except Exception as e:
                st.warning(f"分析をスキップしました: {e}")
                st.session_state["analysis"] = {}

        with st.spinner("✍️ 投稿文を生成中..."):
            try:
                results = generate_all(
                    article_text, selected, language,
                    use_claude, gemini_key, claude_key, gais_mode,
                )
                st.session_state["results"] = results
                st.session_state["selected"] = selected
            except Exception as e:
                st.error(f"生成に失敗しました: {e}")

# ── 結果表示 ──
if "results" in st.session_state:
    results = st.session_state["results"]
    selected = st.session_state["selected"]
    analysis = st.session_state.get("analysis", {})

    st.subheader("生成結果")

    # 全部コピー
    with st.expander("📋 全SNSをまとめてコピー"):
        st.code(build_all_copy_text(results, selected), language=None)

    # タブ
    label_map = {"x": "𝕏 X", "note": "📝 note", "facebook": "👥 Facebook",
                 "instagram": "📸 Instagram", "threads": "🧵 Threads"}
    result_tabs = st.tabs(["📊 分析"] + [label_map[s] for s in selected])

    # ── 分析タブ ──
    with result_tabs[0]:
        if not analysis:
            st.info("分析データが取得できませんでした")
        else:
            # コンテンツ種別
            ct = analysis.get("content_type", {})
            if ct:
                st.caption(f"コンテンツ種別: **{ct.get('label', '?')}**　確信度 {int(ct.get('confidence', 0) * 100)}%")

            st.markdown("### この記事を **誰に** 届けるべきか")
            persona_scores = analysis.get("persona_scores", {})
            if persona_scores:
                sorted_p = sorted(persona_scores.items(),
                                  key=lambda x: x[1].get("score", 0), reverse=True)
                # Primary Targets（上位2名）
                primary = sorted_p[:2]
                st.markdown("**🎯 Primary Targets**")
                for rank, (persona, data) in enumerate(primary, 1):
                    score = max(0, min(100, int(data.get("score", 0))))
                    st.markdown(f"**{rank}. {persona}** — {score}点　*{data.get('reason', '')}*")
                st.divider()
                # 全ペルソナ
                for persona, data in sorted_p:
                    score = max(0, min(100, int(data.get("score", 0))))
                    reason = data.get("reason", "")
                    icon = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
                    col_a, col_b = st.columns([5, 1])
                    with col_a:
                        st.progress(score / 100, text=f"{icon} {persona}　*{reason}*")
                    with col_b:
                        st.markdown(f"**{score}**")

            st.divider()
            st.markdown("### **どこで** 出すべきか")
            platform = analysis.get("platform_recommendation", {})
            if platform:
                if "official" in platform:
                    # GAISモード: official/community 2分類
                    official = platform.get("official", {})
                    community = platform.get("community", {})
                    col_off, col_com = st.columns(2)
                    with col_off:
                        st.success(f"🏛️ **公式導線** トップ: **{official.get('top', '?')}**")
                        st.caption(official.get("reason", ""))
                        if official.get("rankings"):
                            st.markdown(" ＞ ".join(official["rankings"][:5]))
                    with col_com:
                        st.info(f"👥 **会員拡散** トップ: **{community.get('top', '?')}**")
                        st.caption(community.get("reason", ""))
                        if community.get("rankings"):
                            st.markdown(" ＞ ".join(community["rankings"][:5]))
                else:
                    st.success(f"⭐ **{platform.get('top', '?')}** が最適")
                    st.caption(platform.get("reason", ""))
                    rankings = platform.get("rankings", [])
                    if rankings:
                        st.markdown("推奨順位: " + " ＞ ".join(rankings[:5]))

            st.divider()
            st.markdown("### **どう切る** べきか（ネタ分割プラン）")
            potential = analysis.get("content_potential", {})
            if potential:
                count = potential.get("post_count", 0)
                angles = potential.get("angles", [])
                st.info(f"この記事から **{count}本** の投稿が作れます")
                for i, angle in enumerate(angles, 1):
                    st.markdown(f"**{i}.** {angle}")

            if gais_mode:
                st.divider()
                st.markdown("### 🏛️ GAISタグ候補")
                tags = analysis.get("gais_tags", [])
                if tags:
                    st.markdown("　".join(tags))

            risk_flags = analysis.get("risk_flags", [])
            if risk_flags:
                st.divider()
                st.markdown("### ⚠️ リスクフラグ")
                for flag in risk_flags:
                    severity = flag.get("severity", "low")
                    icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🔵"
                    st.warning(f"{icon} {flag.get('message', '')}　→　{flag.get('suggestion', '')}")

    # ── SNSタブ ──
    x_limit = X_LIMIT[language]
    for i, sns in enumerate(selected):
        with result_tabs[i + 1]:
            if sns == "x":
                st.markdown(f"**X（Twitter）投稿文 — 3案**　（上限: {x_limit}字）")
                for j, post in enumerate(results.get("x", []), 1):
                    count = len(post)
                    status = "🟢" if count <= x_limit else "🔴 超過"
                    st.markdown(f"**案{j}** {status} {count}字")
                    st.code(post, language=None)
            elif sns == "note":
                st.markdown("**note 導入文**")
                body = results.get("note", "")
                st.caption(f"📏 {len(body)}文字")
                st.code(body, language=None)
            elif sns == "instagram":
                st.markdown("**Instagram キャプション**")
                body = results.get("instagram", "")
                st.caption(f"📏 {len(body)}文字")
                st.code(body, language=None)
                image_prompt = results.get("instagram_image_prompt", "")
                if image_prompt:
                    st.markdown("**🎨 画像生成プロンプト**")
                    st.caption("Midjourney / DALL-E / Stable Diffusion などにそのまま貼り付けてください")
                    st.code(image_prompt, language=None)
            elif sns == "facebook":
                st.markdown("**Facebook 投稿文**")
                body = results.get("facebook", "")
                st.caption(f"📏 {len(body)}文字")
                st.code(body, language=None)
            elif sns == "threads":
                st.markdown("**Threads 投稿文**")
                body = results.get("threads", "")
                st.caption(f"📏 {len(body)}文字")
                st.code(body, language=None)
