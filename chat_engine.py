"""self-map の AI チャット補助エンジン。

スタンス（既存原則と整合）:
- AI 補助は **完全オプトイン**（タブ切替で意識的に開く）
- AI の出力は **たたき台**として提示、ユーザーが必ず編集・確認してから保存
- 「あなたは ◯◯ ですね」と断定しない、材料を返すだけ
- 医療的アドバイス・診断はしない
- 1 回に 2 つ以上質問しない

技術:
- Claude Haiku 4.5（低コスト・高速）
- API キーは Streamlit secrets → 環境変数 → .env の優先順
"""
import os
import json
import re
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH, override=False)

api_key = None
try:
    import streamlit as st  # type: ignore
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
except Exception:
    pass
if not api_key:
    api_key = os.getenv("ANTHROPIC_API_KEY")

# キーが無くてもアプリ全体が落ちないように、client は遅延初期化する
_client: Anthropic | None = None
MODEL = "claude-haiku-4-5"
EXTRACT_MODEL = "claude-sonnet-4-5"  # 抽出は精度優先


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY が未設定です。"
                "Streamlit secrets または .env を確認してください。"
            )
        _client = Anthropic(api_key=api_key)
    return _client


def is_available() -> bool:
    return bool(api_key)


# ============================================================
# 取扱説明書チャット
# ============================================================
MANUAL_SYSTEM_PROMPT = """\
あなたは自分マップというアプリ内で、ユーザーが「自分の取扱説明書」を作るのを
手伝う AI 補助役です。

# 立ち位置
- 自分マップは、奥田真太朗（適応障害経験のあるデータサイエンティスト）が
  作った自己理解ツール群。「判定しない・並走する」がスタンス。
- AI 補助はオプトイン。ユーザーが意識的に選んで開いた場面。

# あなたのタスク
- 取扱説明書には 10 セクションあります：
  basics（基本）／ good_signs（調子いいサイン）／ warning_signs（落ち気味のサイン）
  ／ recovery_methods（回復方法）／ strengths（強み）／ weaknesses（苦手）
  ／ asks_to_others（お願い）／ dont_do（してほしくないこと）
  ／ emergency_contacts（連絡先）／ free_note（自由記述）
- ユーザーと自然な対話で、本人の言葉を引き出してください。
- 順番は問いません。書きやすいところから引き出してください。

# 大事なルール
- **1 回に 2 つ以上質問しない**。短く、具体的に。
- **押し付けない**。「こういうことですか？」と確認はOKだが、決めつけない。
- **断定しない**。「あなたは ◯◯ な人ですね」とラベル付けしない。
- **医療的アドバイス・診断はしない**。「病気ですね」「治した方が」などNG。
- **言葉が出ない時の許可**：「絵文字でもOK」「今は書けないでもOK」を伝える。
- **本人が否定的になった時**：そのまま受け止める。「自分なんて」に「そんなことない」と返さない。
- **「自分の言葉が主」を守る**：要約・補足・推測の言葉を増やさない。
- 危機的な内容（自傷・他害・緊急性）が出てきたら、医療機関・相談窓口の案内を優先。

# 進め方の目安
- 最初は緩やかに「最近どんな感じですか」「どこから話してみたいですか」など開いた質問。
- 1-2 回の応答で 1 セクション分の情報が出てくれば十分。
- 5-10 ターンくらいで「ここまでで取扱説明書を作れそうです」と区切りを提案してOK。
- 「整理してみる」ボタンで構造化される予定なので、対話で深掘りに集中して大丈夫。

# トーン
- フランクすぎず、堅すぎず。当事者目線でやわらかく。
- 当事者性を共有する短いコメントはOK（「分かります」「大変でしたね」程度）。
  ただし長い共感の押し付けはNG。
"""

MANUAL_EXTRACT_PROMPT = """\
以下のチャット履歴から、「自分の取扱説明書」の各セクションに該当する内容を抽出してください。

# セクション
- basics: 自分の基本情報・輪郭（職業・経験・性質など）
- good_signs: 調子がいい時のサイン
- warning_signs: 調子が落ち気味のサイン
- recovery_methods: 自分が回復する方法・効くこと
- strengths: 強み（実例ベースで）
- weaknesses: 苦手なこと・しんどいこと
- asks_to_others: 周りの人にお願いしたいこと
- dont_do: してほしくないこと
- emergency_contacts: 何かあったときの連絡先
- free_note: 上記に収まらない自由記述

# 抽出ルール
- **本人の言葉そのまま**を使う。要約・推測・補足を加えない。
- 該当しないセクションは空文字列にする。
- 各セクション内では、複数項目があれば改行で区切り、頭に「・」を付ける。
- AI の質問や応答は抽出しない。**ユーザーの発言のみ**から拾う。
- 該当が曖昧なものは無理に分類せず、free_note に入れる。

# 出力形式
必ず下記の JSON を返してください。コードブロック内に。

```json
{
  "basics": "...",
  "good_signs": "...",
  "warning_signs": "...",
  "recovery_methods": "...",
  "strengths": "...",
  "weaknesses": "...",
  "asks_to_others": "...",
  "dont_do": "...",
  "emergency_contacts": "...",
  "free_note": ""
}
```
"""


def chat_manual(messages: list[dict]) -> str:
    """取扱説明書チャットの 1 ターン応答を返す。

    messages: [{"role": "user"/"assistant", "content": "..."}]
    """
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=MANUAL_SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def extract_manual_from_chat(messages: list[dict]) -> dict:
    """チャット履歴から取扱説明書セクションを抽出して dict で返す。"""
    if not messages:
        return {}
    client = _get_client()
    # チャット履歴をフォーマット
    chat_text = "\n\n".join(
        f"【{m['role']}】\n{m['content']}" for m in messages
    )
    response = client.messages.create(
        model=EXTRACT_MODEL,
        max_tokens=2048,
        system=MANUAL_EXTRACT_PROMPT,
        messages=[{"role": "user", "content": chat_text}],
    )
    text = response.content[0].text
    return _parse_json_block(text)


# ============================================================
# 強みインベントリ チャット
# ============================================================
STRENGTH_SYSTEM_PROMPT = """\
あなたは自分マップというアプリ内で、ユーザーが「強み」を過去の実例から
言語化するのを手伝う AI 補助役です。

# 立ち位置
- 「判定しない・並走する」がスタンス。
- AI 補助はオプトイン。ユーザーが意識的に開いた場面。

# あなたのタスク
- 強みは STAR 構造（Situation 状況 / Action 行動 / Result 結果）で書きます。
- ユーザーから **過去の具体的な場面** を引き出してください。
- 抽象的な性格（「優しい」「真面目」）ではなく、**実例**を聞き出すことが核。

# 大事なルール
- **1 回に 2 つ以上質問しない**。
- **「強みですね」と決めつけない**。本人が「強みかも」と思える状態を作る。
- 場面から始める：「最近、自分でも『うまくやれたな』と思った場面はありますか？」
- 仕事だけでなく **家族・友人・趣味の場面でもOK** を伝える。
- 「結果」を聞く時は「定量的でなくてもOK」「感謝された・頼られた等でも十分」を伝える。
- ユーザーが「大したことない」と言ったら、そのまま受け止め、価値判断しない。

# 進め方の目安
- 1 つの場面に焦点を絞って、Situation → Action → Result の順に深掘り。
- 1-2 つの場面が出てくれば十分。
- 5-8 ターンで「ここまでで強みを 1 つ書けそうです」と区切りを提案してOK。
"""

STRENGTH_EXTRACT_PROMPT = """\
以下のチャット履歴から、ユーザーの「強み」1 件を STAR 構造で抽出してください。

# 抽出する項目
- name: 強みの一言名前（例：「データを構造化する力」）
- category: 9 カテゴリのいずれか
  - "🔧 技術・専門性" / "🧠 思考・分析" / "🤝 対人・コミュニケーション"
  - "🎯 行動・実行力" / "💡 創造性・発想" / "🌱 自己管理・継続"
  - "📚 学習・成長" / "🔍 その他" / "—（未分類）"
- situation: 過去の具体的な場面（when / where / who の文脈）
- action: その時、自分が何をしたか
- result: どうなったか・反響
- free_note: 補足や関連メモ

# ルール
- **本人の言葉そのまま**を使う。要約・推測・補足を加えない。
- AI の質問や応答は抽出しない。**ユーザーの発言のみ**から拾う。
- 該当する内容が無いフィールドは空文字列。
- name は **必須**：話の中で本人が言ったキーワードから 10 文字以内で。
- 複数の強みが出てきた場合は、最も具体的に語られた 1 つだけ。

# 出力形式

```json
{
  "name": "...",
  "category": "—（未分類）",
  "situation": "...",
  "action": "...",
  "result": "...",
  "free_note": ""
}
```
"""


def chat_strength(messages: list[dict]) -> str:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=STRENGTH_SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def extract_strength_from_chat(messages: list[dict]) -> dict:
    if not messages:
        return {}
    client = _get_client()
    chat_text = "\n\n".join(
        f"【{m['role']}】\n{m['content']}" for m in messages
    )
    response = client.messages.create(
        model=EXTRACT_MODEL,
        max_tokens=1024,
        system=STRENGTH_EXTRACT_PROMPT,
        messages=[{"role": "user", "content": chat_text}],
    )
    text = response.content[0].text
    return _parse_json_block(text)


# ============================================================
# 共通：JSON 抽出
# ============================================================
def _parse_json_block(text: str) -> dict:
    """LLM 出力から JSON ブロックを抽出。失敗時は空 dict。"""
    # ```json ... ``` ブロックを優先
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # それでも見つからない場合、{...} の最外を試す
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}
