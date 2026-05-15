"""🗺️ 自分マップ（self-map-public）

Phase 4「再選択（自己理解）」フェーズの自己理解ツール群を統合するアプリ。

実装済み機能:
- 📋 自分の取扱説明書
- 🧭 働き方の譲れない条件

予定:
- 🌧️ 再発のサインリスト / 💪 強みインベントリ / 🎯 価値観カードソート

設計スタンス：
- 書く・選ぶ系（チャット系ではない）→ UI は「書く系」パターン
- 「自分の言葉」が主、AI 補助は最小限・参考扱い
- 全フィールド任意・空欄 OK
- 1 ユーザー 1 レコード（latest 上書き）：常に最新版を保つ性質
"""
import streamlit as st

from db import init_db
from _user import render_account_sidebar
from storage import (
    save_manual, load_manual,
    save_work_conditions, load_work_conditions,
)


st.set_page_config(
    page_title="自分マップ", page_icon="🗺️", layout="wide",
)

CURRENT_USER_ID = render_account_sidebar()
init_db()

# --- ヘッダー不透明化 ---
st.markdown("""
<style>
header[data-testid="stHeader"] { background: white; }
</style>
""", unsafe_allow_html=True)


# --- サイドバー：ビュー切替 ---
with st.sidebar:
    _hub_url = "https://app-public-qpy8b2ziwgdf9h2vmu5hqp.streamlit.app/"
    if CURRENT_USER_ID:
        _hub_url += f"?u={CURRENT_USER_ID}"
    st.link_button(
        "🏠 HOME に戻る",
        _hub_url,
        use_container_width=True,
    )
    st.link_button(
        "💬 ご意見・感想",
        "https://docs.google.com/forms/d/e/1FAIpQLSetCb_dHG6JFsUzhK9ZYxydgh5cP8w07Q6NRO4ouEM7BvSTRw/viewform",
        use_container_width=True,
    )
    st.divider()
    view = st.radio(
        "表示",
        [
            "📋 自分の取扱説明書",
            "🧭 働き方の譲れない条件",
        ],
        label_visibility="collapsed",
        key="view_radio",
    )
    st.divider()
    st.caption(
        "**🗺️ 自分マップ**\n\n"
        "自己理解を整理するツール群。\n\n"
        "**今後追加予定**：\n"
        "- 🌧️ 再発のサインリスト\n"
        "- 💪 強みインベントリ\n"
        "- 🎯 価値観カードソート"
    )


# --- ヘッダー ---
st.title("🗺️ 自分マップ")
st.caption(
    "**自己理解を整理するツール群**。"
    "5 フェーズの「再選択」期に向けて、自分を見直す材料を作る場所です。"
    "書ける所から少しずつでも OK。全フィールド任意・空欄でも保存できます。"
)


# ============================================================
# View 1: 自分の取扱説明書
# ============================================================
if view == "📋 自分の取扱説明書":
    st.divider()
    st.markdown("## 📋 自分の取扱説明書")
    st.caption(
        "**「自分はこういう人です」を 1 枚にまとめる**ノート。"
        "家族・職場・支援者に渡せる形にも、自分のための見返し材料にもなります。"
        "**判断はせず、自分の言葉をそのまま残す**スタンス。"
    )

    _existing = load_manual(user_id=CURRENT_USER_ID)
    _updated_at = _existing.get("_updated_at")
    if _updated_at:
        try:
            _disp = _updated_at.replace("T", " ")[:16]
            st.caption(f"📅 最終更新：{_disp}")
        except Exception:
            pass

    MANUAL_SECTIONS = [
        {
            "key": "basics",
            "title": "🌱 私について（基本）",
            "placeholder": (
                "例：「データサイエンティスト 6 年目、適応障害の経験あり。"
                "じっくり考えたい派。文字で読む方が頭に入りやすい」"
            ),
            "help": "自分の輪郭を一言で。書けない日はスキップで OK",
        },
        {
            "key": "good_signs",
            "title": "🌤️ 調子がいい時のサイン",
            "placeholder": (
                "例：・朝の散歩に行ける\n"
                "・夕食を作れる\n"
                "・人と話したくなる\n"
                "・新しいことを始めたくなる"
            ),
            "help": "自分が「整っている」と感じる時の特徴。後で「調子悪い時」と比較できます",
        },
        {
            "key": "warning_signs",
            "title": "⚠️ 調子が落ち気味のサイン",
            "placeholder": (
                "例：・朝起きるのがつらくなる\n"
                "・SNS で他人の生活が眩しく見える\n"
                "・好きな食べ物が美味しく感じない\n"
                "・「自分なんて」と思いはじめる"
            ),
            "help": "早めに気づける材料。自分の早期警告システムとして",
        },
        {
            "key": "recovery_methods",
            "title": "🌿 私が回復する方法",
            "placeholder": (
                "例：・朝の散歩 15 分\n"
                "・一日何もしない日を作る\n"
                "・好きな本を読み返す\n"
                "・コーヒーをゆっくり淹れる\n"
                "・〇〇さんに「最近しんどい」と一言送る"
            ),
            "help": "自分にとって効く回復行動のリスト。試したい選択肢として",
        },
        {
            "key": "strengths",
            "title": "💪 自分の強み（実例ベース）",
            "placeholder": (
                "例：・データを構造化して読み取れる（過去の異常検知プロジェクトで…）\n"
                "・当事者目線で言語化できる（連載執筆で…）\n"
                "・コツコツ続けられる（mood-tracker を 1 年継続）"
            ),
            "help": "抽象的な性格より、**過去の実例**から拾うのがコツ",
        },
        {
            "key": "weaknesses",
            "title": "🌧️ 苦手なこと・しんどいこと",
            "placeholder": (
                "例：・急な変更が連続する状況\n"
                "・大人数の飲み会\n"
                "・自分の意見を求められる即興\n"
                "・テキストで攻撃的に書かれること"
            ),
            "help": "弱みではなく「環境との相性」として読むと楽です",
        },
        {
            "key": "asks_to_others",
            "title": "🤝 周りの人にお願いしたいこと",
            "placeholder": (
                "例：・予定変更は前日までに教えてほしい\n"
                "・話を聞いてもらえると助かる（アドバイスはいらない時もある）\n"
                "・「大丈夫？」と聞かれると返事に困る、見守ってほしい"
            ),
            "help": "支援者向けの「使い方ガイド」。共有する用にも、自分のためにも",
        },
        {
            "key": "dont_do",
            "title": "🚫 してほしくないこと",
            "placeholder": (
                "例：・「頑張れ」と言わないでほしい\n"
                "・突然の電話を控えてほしい\n"
                "・他の人と比較しないでほしい"
            ),
            "help": "境界線を言葉にしておくと、自分の負担が減ります",
        },
        {
            "key": "emergency_contacts",
            "title": "🆘 何かあったときの連絡先",
            "placeholder": (
                "例：・家族：〇〇\n"
                "・主治医：〇〇クリニック \n"
                "・職場の相談窓口：〇〇\n"
                "・友人：〇〇"
            ),
            "help": "緊急時の自分への道しるべ。書けるところだけで OK",
        },
        {
            "key": "free_note",
            "title": "✍️ その他（自由記述）",
            "placeholder": "他に書いておきたいこと",
            "help": "テンプレに収まらない自分の言葉",
        },
    ]

    with st.form("manual_form"):
        _values: dict[str, str] = {}
        for _sec in MANUAL_SECTIONS:
            _key = _sec["key"]
            _initial = _existing.get(_key, "") if isinstance(
                _existing.get(_key), str
            ) else ""
            _values[_key] = st.text_area(
                _sec["title"],
                value=_initial,
                placeholder=_sec["placeholder"],
                help=_sec["help"],
                height=140,
            )

        _save = st.form_submit_button(
            "💾 保存する", use_container_width=True,
        )
        if _save:
            try:
                save_manual(_values, user_id=CURRENT_USER_ID)
                st.success("保存しました")
            except Exception as _e:
                st.warning(f"保存に失敗：{_e}")

    # 共有用エクスポート（Markdown）
    st.divider()
    with st.expander(
        "📤 取扱説明書をテキストで取り出す（コピー・共有用）", expanded=False
    ):
        st.caption(
            "家族・支援者・職場に渡す時、テキスト形式で取り出せます。"
            "渡す相手を選ぶのは本人の判断で。"
        )
        _md_lines = ["# 自分の取扱説明書", ""]
        for _sec in MANUAL_SECTIONS:
            _v = _existing.get(_sec["key"], "")
            if isinstance(_v, str) and _v.strip():
                _md_lines.append(f"## {_sec['title']}")
                _md_lines.append("")
                _md_lines.append(_v.strip())
                _md_lines.append("")
        if len(_md_lines) <= 2:
            st.caption("（まだ保存された内容がありません）")
        else:
            _md_text = "\n".join(_md_lines)
            st.text_area(
                "Markdown テキスト",
                value=_md_text,
                height=300,
                label_visibility="collapsed",
            )
            st.download_button(
                "💾 .md ファイルとしてダウンロード",
                data=_md_text.encode("utf-8"),
                file_name="my_manual.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ============================================================
# View 2: 働き方の譲れない条件
# ============================================================
elif view == "🧭 働き方の譲れない条件":
    st.divider()
    st.markdown("## 🧭 働き方の譲れない条件")
    st.caption(
        "**自分にとっての「譲れない条件」と「あれば嬉しい条件」**を整理する場所。"
        "Phase 5（分岐）期の転職・復職判断、カジュアル面談前の整理、"
        "1on1 で伴走者と共有する素材に使えます。"
    )

    WORK_CONDITION_CATEGORIES = {
        "⏰ 時間・働き方": [
            "リモートワーク可",
            "フレックスタイム可",
            "残業 20 時間以内/月",
            "週休 2 日固定",
            "夜勤・休日出勤なし",
            "始業時刻の柔軟性",
            "中抜け可",
        ],
        "📋 業務内容": [
            "専門性を活かせる",
            "成長機会がある",
            "ルーチン業務が中心",
            "業務に裁量がある",
            "業務範囲が明確",
            "新規開発に関われる",
            "判断・決定の責任が重くない",
        ],
        "👥 人間関係": [
            "上司との相性が合う",
            "チームの心理的安全性",
            "顧客と直接接さない",
            "少人数のチーム",
            "リモートでもコミュニケーションが取りやすい",
            "メンター・相談相手がいる",
        ],
        "🏢 環境・場所": [
            "通勤 30 分以内",
            "完全リモート可",
            "都市部勤務",
            "静かなオフィス環境",
            "席が固定（フリーアドレスではない）",
        ],
        "💰 制度・処遇": [
            "現年収維持",
            "年収アップ",
            "賞与あり",
            "福利厚生充実",
            "副業可",
            "メンタルヘルス休暇・配慮制度",
            "在宅補助",
        ],
    }

    PRIORITY_OPTIONS = ["⚪ 不要・気にしない", "🟡 望ましい", "🔴 必須"]
    PRIORITY_KEY_MAP = {
        "⚪ 不要・気にしない": "不要",
        "🟡 望ましい": "望ましい",
        "🔴 必須": "必須",
    }
    PRIORITY_FROM_KEY = {v: k for k, v in PRIORITY_KEY_MAP.items()}

    _existing_wc = load_work_conditions(user_id=CURRENT_USER_ID)
    _updated_at_wc = _existing_wc.get("_updated_at")
    if _updated_at_wc:
        try:
            _disp = _updated_at_wc.replace("T", " ")[:16]
            st.caption(f"📅 最終更新：{_disp}")
        except Exception:
            pass

    st.caption(
        "**🔴 必須**（これが無いと働けない）／"
        "**🟡 望ましい**（あれば嬉しい）／"
        "**⚪ 不要**（気にしない）。デフォルトは「不要」なので必要なものだけ動かせば OK。"
    )

    with st.form("work_conditions_form"):
        _values_wc: dict[str, str] = {}
        for _cat, _items in WORK_CONDITION_CATEGORIES.items():
            st.markdown(f"**{_cat}**")
            for _item in _items:
                _stored_key = _existing_wc.get(_item, "不要")
                _stored_display = PRIORITY_FROM_KEY.get(
                    _stored_key, "⚪ 不要・気にしない"
                )
                _idx = (
                    PRIORITY_OPTIONS.index(_stored_display)
                    if _stored_display in PRIORITY_OPTIONS else 0
                )
                _selected = st.radio(
                    _item,
                    PRIORITY_OPTIONS,
                    index=_idx,
                    horizontal=True,
                    key=f"wc_{_item}",
                )
                _values_wc[_item] = PRIORITY_KEY_MAP.get(_selected, "不要")
            st.write("")

        _free_note_wc = st.text_area(
            "他にあれば（自由記述・任意）",
            value=_existing_wc.get("_free_note", "") if isinstance(
                _existing_wc.get("_free_note"), str
            ) else "",
            placeholder="リストに無い条件・補足・例外などあればここに。書けなくても OK",
            height=100,
        )

        _save_wc = st.form_submit_button(
            "💾 保存する", use_container_width=True,
        )
        if _save_wc:
            try:
                _to_save = dict(_values_wc)
                _to_save["_free_note"] = _free_note_wc
                save_work_conditions(_to_save, user_id=CURRENT_USER_ID)
                st.success("保存しました")
            except Exception as _e:
                st.warning(f"保存に失敗：{_e}")

    # ----- サマリ表示 -----
    st.divider()
    st.markdown("### 📊 自分の条件サマリ")
    _must = [k for k, v in _existing_wc.items()
             if k != "_updated_at" and k != "_free_note" and v == "必須"]
    _nice = [k for k, v in _existing_wc.items()
             if k != "_updated_at" and k != "_free_note" and v == "望ましい"]
    if not _must and not _nice and not _existing_wc.get("_free_note"):
        st.caption("まだ保存された内容がありません。上のフォームから選んで保存してください。")
    else:
        _col_must, _col_nice = st.columns(2)
        with _col_must:
            st.markdown("**🔴 必須（譲れない）**")
            if _must:
                for _m in _must:
                    st.markdown(f"- {_m}")
            else:
                st.caption("（なし）")
        with _col_nice:
            st.markdown("**🟡 望ましい（あれば嬉しい）**")
            if _nice:
                for _n in _nice:
                    st.markdown(f"- {_n}")
            else:
                st.caption("（なし）")
        if _existing_wc.get("_free_note"):
            st.markdown("**✍️ 自由記述**")
            st.markdown(_existing_wc["_free_note"])

    # ----- Markdown エクスポート -----
    st.divider()
    with st.expander(
        "📤 働き方の条件をテキストで取り出す（求人検討・1on1 共有用）",
        expanded=False,
    ):
        _md_lines = ["# 働き方の譲れない条件", ""]
        if _must:
            _md_lines.append("## 🔴 必須（譲れない）")
            _md_lines.append("")
            for _m in _must:
                _md_lines.append(f"- {_m}")
            _md_lines.append("")
        if _nice:
            _md_lines.append("## 🟡 望ましい（あれば嬉しい）")
            _md_lines.append("")
            for _n in _nice:
                _md_lines.append(f"- {_n}")
            _md_lines.append("")
        if _existing_wc.get("_free_note"):
            _md_lines.append("## ✍️ 自由記述")
            _md_lines.append("")
            _md_lines.append(_existing_wc["_free_note"].strip())
            _md_lines.append("")
        if len(_md_lines) <= 2:
            st.caption("（まだ保存された内容がありません）")
        else:
            _md_text = "\n".join(_md_lines)
            st.text_area(
                "Markdown テキスト",
                value=_md_text,
                height=300,
                label_visibility="collapsed",
            )
            st.download_button(
                "💾 .md ファイルとしてダウンロード",
                data=_md_text.encode("utf-8"),
                file_name="my_work_conditions.md",
                mime="text/markdown",
                use_container_width=True,
            )
