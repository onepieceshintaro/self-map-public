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
    save_warning_signs, load_warning_signs,
    save_warning_checkin, load_warning_checkins, delete_warning_checkin,
    save_strength, update_strength, load_strengths, delete_strength,
    save_values_sort, load_values_sort,
    save_stress_source, load_stress_sources, delete_stress_source,
    save_nonverbal_memo, load_nonverbal_memos, delete_nonverbal_memo,
)
try:
    import chat_engine
    _CHAT_AVAILABLE = chat_engine.is_available()
except Exception:
    chat_engine = None
    _CHAT_AVAILABLE = False

# 危機検出（3 モード判定）
from crisis_detection import detect_mode
from crisis_ui import render_warning_ui, render_critical_ui

import json
import pandas as pd


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
    st.caption("📝 記入系（自分の言葉で）")
    view = st.radio(
        "表示",
        [
            "🌱 言葉にする",
            "🌧️ 再発のサインリスト",
            "📋 自分の取扱説明書",
            "💪 強みインベントリ",
            "🧭 働き方の譲れない条件",
            "🎯 価値観カードソート",
        ],
        captions=[
            "Phase 1：気づき",
            "Phase 3：回復",
            "Phase 4：再選択",
            "Phase 4：再選択",
            "Phase 4：再選択（選ぶ系）",
            "Phase 4：再選択（選ぶ系）",
        ],
        label_visibility="collapsed",
        key="view_radio",
    )
    st.divider()
    st.caption(
        "**🗺️ 自分マップ**\n\n"
        "上 4 つは **記入系**、下 2 つは **選ぶ系**。\n\n"
        "5 フェーズの「再選択」期に向けて、"
        "自分の輪郭を言語化していく場所。"
    )


# --- ヘッダー ---
st.title("🗺️ 自分マップ")
st.caption(
    "**自己理解を整理するツール群**。"
    "5 フェーズの「再選択」期に向けて、自分を見直す材料を作る場所です。"
    "書ける所から少しずつでも OK。全フィールド任意・空欄でも保存できます。"
)


# ============================================================
# View 0: 言葉にする（Phase 1：気づき）
# ============================================================
# CBT 側から self-map に移設。「自分を整理するツール群」として self-map に集約。
# CBT 側からはこの view へのリンクで誘導する（クロスリンク）。
if view == "🌱 言葉にする":
    st.divider()
    st.markdown("## 🌱 言葉にする")
    st.caption(
        "**「何にしんどさを感じているか」** を言葉にする最初の一歩。"
        "他のセクション（取扱説明書 / 強み / 価値観）に進む前の入口にも、"
        "そのままここで終わるのも OK。"
    )

    _phase1_tab = st.radio(
        "切り替え",
        ["🧩 仕事のしんどさ：チェックリスト", "🌫️ 言葉にできないこと（メモ）"],
        label_visibility="collapsed",
        horizontal=True,
        key="phase1_tab",
    )

    # ---------- 1. 仕事ストレス源チェックリスト ----------
    if _phase1_tab == "🧩 仕事のしんどさ：チェックリスト":
        STRESS_CATEGORIES = {
            "仕事の量・働き方": [
                "業務量が多すぎる・過負荷",
                "残業・休日出勤が多い",
                "急な変更・割り込みが多い",
                "期限のプレッシャー",
            ],
            "役割・職務": [
                "自分の役割が曖昧",
                "やりたい仕事とのズレ",
                "スキルが追いついていない感",
                "評価されない感",
            ],
            "人間関係": [
                "上司との関係",
                "同僚との関係",
                "顧客・取引先との関係",
                "コミュニケーションの負担",
            ],
            "制度・評価・処遇": [
                "評価制度への不満",
                "給与・処遇への不満",
                "キャリアパスが見えない",
            ],
            "価値観・将来": [
                "会社・組織との価値観ズレ",
                "将来への不安",
                "仕事の意味を感じない",
            ],
            "環境・生活": [
                "通勤・職場環境",
                "リモートワークの孤独",
                "家庭・育児との両立",
            ],
        }

        st.caption(
            "**当てはまるものをチェック**。何個でも OK。"
            "全部空欄でも「今日はそういう日だった」として保存できます。"
        )

        with st.form("stress_source_form", clear_on_submit=True):
            _selected_ss: list[str] = []
            for _cat, _opts in STRESS_CATEGORIES.items():
                st.markdown(f"**{_cat}**")
                _cols = st.columns(2)
                for _i, _opt in enumerate(_opts):
                    with _cols[_i % 2]:
                        if st.checkbox(_opt, key=f"ss_{_opt}"):
                            _selected_ss.append(_opt)
                st.write("")

            _ss_free_note = st.text_area(
                "他にあれば（任意）",
                placeholder="チェックリストに無い言葉で出てきたものがあれば。書けなくても OK",
                height=80,
            )

            if st.form_submit_button("💾 記録する", use_container_width=True):
                try:
                    save_stress_source(
                        sources=_selected_ss,
                        free_note=_ss_free_note,
                        user_id=CURRENT_USER_ID,
                    )
                    st.success(
                        f"記録しました（{len(_selected_ss)} 項目"
                        f"{ '＋自由記述' if _ss_free_note.strip() else '' }）"
                    )
                except Exception as _e:
                    st.warning(f"保存に失敗：{_e}")

        # 履歴表示
        st.divider()
        st.markdown("#### 📚 これまでの記録")
        try:
            _df_ss = load_stress_sources(user_id=CURRENT_USER_ID, limit=30)
            if _df_ss.empty:
                st.caption("まだ記録はありません。上のフォームから 1 件目を残せます。")
            else:
                st.caption(
                    "**自分が書いた言葉**が並びます。判定や評価はなし。"
                    "「何が積もっているか」を眺める材料として。"
                )
                for _, _row in _df_ss.iterrows():
                    try:
                        _dt = pd.to_datetime(_row["created_at"])
                        _dt_str = _dt.strftime("%m/%d %H:%M")
                    except Exception:
                        _dt_str = str(_row["created_at"])
                    try:
                        _sources_list = json.loads(_row["sources"] or "[]")
                    except Exception:
                        _sources_list = []
                    with st.expander(
                        f"📝 {_dt_str}（{len(_sources_list)} 項目）",
                        expanded=False,
                    ):
                        if _sources_list:
                            for _s in _sources_list:
                                st.markdown(f"- {_s}")
                        if _row.get("free_note"):
                            st.markdown(f"**自由記述**：{_row['free_note']}")
                        if st.button(
                            "🗑️ 削除", key=f"del_ss_{_row['id']}",
                        ):
                            try:
                                delete_stress_source(
                                    int(_row["id"]),
                                    user_id=CURRENT_USER_ID,
                                )
                                st.rerun()
                            except Exception as _e:
                                st.warning(f"削除失敗：{_e}")
        except Exception as _e:
            st.caption(f"履歴の読み込みでエラー：{_e}")

    # ---------- 2. 言葉にできないこと（メモ） ----------
    else:
        STATE_MARKERS = [
            ("🌫️", "ぼんやり"),
            ("🌧️", "どんより"),
            ("🌪️", "ぐちゃぐちゃ"),
            ("😶", "言葉にならない"),
            ("😞", "ちょっとつらい"),
            ("💢", "イライラ"),
            ("🥱", "だるい・無気力"),
            ("💧", "涙が出る"),
            ("🫥", "何も感じない"),
            ("🔥", "燃え尽き感"),
        ]

        st.caption(
            "**書けない日**もあります。絵文字を 1 つ選ぶだけでも記録になります。"
            "自由記述は書きたい時だけ。何も書けない日は **「言葉にならない 😶」を選ぶ** で十分です。"
        )

        with st.form("nonverbal_memo_form", clear_on_submit=True):
            _markers: list[str] = []
            _cols = st.columns(5)
            for _i, (_emoji, _label) in enumerate(STATE_MARKERS):
                with _cols[_i % 5]:
                    if st.checkbox(
                        f"{_emoji} {_label}",
                        key=f"nv_{_label}",
                    ):
                        _markers.append(f"{_emoji} {_label}")

            _nv_content = st.text_area(
                "もし言葉になれば（任意・完全に空欄でも OK）",
                placeholder=(
                    "例: なんとなくしんどい / 朝起きるのがつらい / "
                    "誰にも言えないこと… 書けなければそのままスキップ"
                ),
                height=100,
            )

            if st.form_submit_button("💾 記録する", use_container_width=True):
                if not _markers and not _nv_content.strip():
                    st.warning("絵文字を 1 つ選ぶか、何か書いてみてください")
                else:
                    try:
                        save_nonverbal_memo(
                            state_markers=_markers,
                            content=_nv_content,
                            user_id=CURRENT_USER_ID,
                        )
                        st.success("記録しました")
                    except Exception as _e:
                        st.warning(f"保存に失敗：{_e}")

        # 履歴表示
        st.divider()
        st.markdown("#### 📚 これまでのメモ")
        try:
            _df_nv = load_nonverbal_memos(user_id=CURRENT_USER_ID, limit=30)
            if _df_nv.empty:
                st.caption("まだメモはありません。書けない日の記録としてどうぞ。")
            else:
                st.caption(
                    "**自分の言葉と絵文字**が並びます。"
                    "後から見返すと、自分の状態の変化が見えることがあります。"
                )
                for _, _row in _df_nv.iterrows():
                    try:
                        _dt = pd.to_datetime(_row["created_at"])
                        _dt_str = _dt.strftime("%m/%d %H:%M")
                    except Exception:
                        _dt_str = str(_row["created_at"])
                    try:
                        _markers_list = json.loads(_row["state_markers"] or "[]")
                    except Exception:
                        _markers_list = []
                    _markers_str = " ".join(_markers_list) if _markers_list else ""
                    _title = f"📝 {_dt_str}  {_markers_str}".strip()
                    with st.expander(_title, expanded=False):
                        if _row.get("content"):
                            st.markdown(_row["content"])
                        else:
                            st.caption("（自由記述なし）")
                        if st.button(
                            "🗑️ 削除", key=f"del_nv_{_row['id']}",
                        ):
                            try:
                                delete_nonverbal_memo(
                                    int(_row["id"]),
                                    user_id=CURRENT_USER_ID,
                                )
                                st.rerun()
                            except Exception as _e:
                                st.warning(f"削除失敗：{_e}")
        except Exception as _e:
            st.caption(f"履歴の読み込みでエラー：{_e}")


# ============================================================
# View 1: 自分の取扱説明書
# ============================================================
elif view == "📋 自分の取扱説明書":
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

    # タブ構造：「自分で書く」を第 1（デフォルト）、「AI と整理する」を第 2 に。
    # 「自分の言葉が主、AI は補助」を順序で示す（既存原則 feedback_ai_assist_philosophy）。
    _manual_form_tab, _manual_ai_tab = st.tabs(
        ["📝 自分で書く", "💬 AI と整理する"]
    )

    with _manual_form_tab:
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

    with _manual_ai_tab:
        if not _CHAT_AVAILABLE:
            st.caption(
                "AI 補助は API キーが設定されていない環境では使えません。"
                "「📝 自分で書く」タブから自分で書く形でご利用ください。"
            )
        else:
            st.caption(
                "**AI と対話**しながら、取扱説明書の各セクションに当てはまる内容を引き出します。"
                "AI は質問するだけ。出てきた内容は "
                "**必ず本人が確認してからフォームに反映**してください。"
            )

            _mkey = "chat_manual_messages"
            if _mkey not in st.session_state:
                st.session_state[_mkey] = []

            for _msg in st.session_state[_mkey]:
                with st.chat_message(_msg["role"]):
                    st.markdown(_msg["content"])

            _user_input = st.chat_input("ここに書きながら整理する…")
            if _user_input:
                # 危機検出：入力時点でモード判定
                try:
                    _ai_client = chat_engine._get_client()
                except Exception:
                    _ai_client = None
                _md = detect_mode(
                    _user_input, client=_ai_client, use_llm=True,
                )["mode"]
                if _md == "critical":
                    render_critical_ui()
                    st.stop()
                elif _md == "warning":
                    render_warning_ui(
                        on_resume_key="manual_chat_warning_resume",
                    )
                    st.stop()

                st.session_state[_mkey].append(
                    {"role": "user", "content": _user_input}
                )
                try:
                    with st.spinner("…考えています…"):
                        _ai_reply = chat_engine.chat_manual(
                            st.session_state[_mkey]
                        )
                    st.session_state[_mkey].append(
                        {"role": "assistant", "content": _ai_reply}
                    )
                    st.rerun()
                except Exception as _e:
                    st.warning(f"AI 応答失敗：{_e}")
                    st.session_state[_mkey].pop()

            if len(st.session_state[_mkey]) >= 2:
                _col_ext, _col_clear = st.columns(2)
                with _col_ext:
                    if st.button(
                        "📥 ここまでの会話から取扱説明書に整理する",
                        use_container_width=True,
                        key="manual_chat_extract",
                    ):
                        try:
                            with st.spinner("整理中…"):
                                _extracted_manual = (
                                    chat_engine.extract_manual_from_chat(
                                        st.session_state[_mkey]
                                    )
                                )
                            st.session_state["chat_manual_extracted"] = (
                                _extracted_manual
                            )
                            st.success("整理しました（下に表示）")
                        except Exception as _e:
                            st.warning(f"整理失敗：{_e}")
                with _col_clear:
                    if st.button(
                        "🗑️ チャットをリセット",
                        use_container_width=True,
                        key="manual_chat_reset",
                    ):
                        st.session_state[_mkey] = []
                        st.session_state.pop("chat_manual_extracted", None)
                        st.rerun()

            _extracted_manual = st.session_state.get("chat_manual_extracted")
            if _extracted_manual:
                st.divider()
                st.markdown("#### 📋 抽出結果プレビュー")
                st.caption(
                    "下記が AI が抽出した内容です。"
                    "**「自分の言葉そのまま」** を引き出すようにプロンプトしていますが、"
                    "**必ず本人が確認してからフォームに反映**してください。"
                    "反映時は **「📝 自分で書く」タブのフォームの既存内容に追記**されます（上書きなし）。"
                )
                _has_any = False
                for _sec in MANUAL_SECTIONS:
                    _v = _extracted_manual.get(_sec["key"], "")
                    if isinstance(_v, str) and _v.strip():
                        _has_any = True
                        with st.container(border=True):
                            st.markdown(f"**{_sec['title']}**")
                            st.markdown(_v)
                if not _has_any:
                    st.caption("（抽出できる内容が見つかりませんでした）")
                else:
                    if st.button(
                        "📝 フォームに反映（既存に追記）",
                        use_container_width=True,
                        key="manual_chat_apply",
                    ):
                        try:
                            _merged_manual: dict[str, str] = {}
                            for _sec in MANUAL_SECTIONS:
                                _k = _sec["key"]
                                _ex_v = _existing.get(_k, "") or ""
                                _ext_v = _extracted_manual.get(_k, "") or ""
                                if (
                                    isinstance(_ext_v, str)
                                    and _ext_v.strip()
                                ):
                                    if (
                                        isinstance(_ex_v, str)
                                        and _ex_v.strip()
                                    ):
                                        _merged_manual[_k] = (
                                            _ex_v.rstrip()
                                            + "\n"
                                            + _ext_v.strip()
                                        )
                                    else:
                                        _merged_manual[_k] = _ext_v.strip()
                                else:
                                    _merged_manual[_k] = (
                                        _ex_v
                                        if isinstance(_ex_v, str) else ""
                                    )
                            save_manual(
                                _merged_manual, user_id=CURRENT_USER_ID,
                            )
                            st.session_state.pop(
                                "chat_manual_extracted", None,
                            )
                            st.session_state[_mkey] = []
                            st.success(
                                "フォームに反映しました。再読み込みします…"
                            )
                            st.rerun()
                        except Exception as _e:
                            st.warning(f"反映失敗：{_e}")

    # 共有用エクスポート（Markdown）- タブ外（両モード共通）
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


# ============================================================
# View 3: 再発のサインリスト
# ============================================================
elif view == "🌧️ 再発のサインリスト":
    st.divider()
    st.markdown("## 🌧️ 再発のサインリスト")
    st.caption(
        "**自分のしんどさの早期警告システム**を自分の言葉で作る場所です。"
        "「早期サイン」で気づければ、対処の幅が広がります。"
        "**判定や採点はなし**。自分の観察を残すだけ。"
    )

    _ws_tab = st.radio(
        "切り替え",
        ["📝 サインを書く", "✅ 今チェックする", "📚 チェック履歴"],
        label_visibility="collapsed",
        horizontal=True,
        key="warning_signs_tab",
    )

    _ws_existing = load_warning_signs(user_id=CURRENT_USER_ID)

    # ----- タブ 1: サインを書く -----
    if _ws_tab == "📝 サインを書く":
        _updated_at_ws = _ws_existing.get("_updated_at")
        if _updated_at_ws:
            try:
                _disp = _updated_at_ws.replace("T", " ")[:16]
                st.caption(f"📅 最終更新：{_disp}")
            except Exception:
                pass

        st.caption(
            "**🌱 早期サイン**：「あ、少し疲れてるかも」レベル。早めに気づけると対処しやすい。\n\n"
            "**⚠️ 警戒サイン**：「これが出たら要注意」レベル。セルフケア・誰かに相談を検討。\n\n"
            "**🌪️ きっかけ・トリガー**：自分が崩れやすい外的状況（仕事の波・季節・人間関係など）"
        )

        WARNING_SIGN_SECTIONS = [
            {
                "key": "early",
                "title": "🌱 早期サイン（早めに気づきたい）",
                "placeholder": (
                    "例：\n"
                    "・朝、いつもより布団から出るのに時間がかかる\n"
                    "・好きな YouTube を見ても乗れない\n"
                    "・お風呂が面倒になる\n"
                    "・LINE の返信が遅くなる\n"
                    "・カフェに行きたくなくなる"
                ),
                "help": "「これくらい誰でもある」と思うレベルから書くのがコツ。早期サイン＝軽い段階",
            },
            {
                "key": "warning",
                "title": "⚠️ 警戒サイン（要セルフケア・相談検討）",
                "placeholder": (
                    "例：\n"
                    "・3 日以上、好きな食べ物が美味しく感じない\n"
                    "・人と話す気力がなくなる\n"
                    "・「自分なんて」と思う頻度が増える\n"
                    "・出勤前に動悸がする\n"
                    "・休日も体が休まらない"
                ),
                "help": "「これが出たら一度立ち止まる」自分なりのレッドライン",
            },
            {
                "key": "triggers",
                "title": "🌪️ きっかけ・トリガー（崩れやすい状況）",
                "placeholder": (
                    "例：\n"
                    "・繁忙期（10-12 月、3 月）\n"
                    "・上司との 1on1 が連続する週\n"
                    "・新しいプロジェクト開始から 2 週間目\n"
                    "・家族の体調不良が続いた時\n"
                    "・季節の変わり目（特に春）"
                ),
                "help": "外側の要因の方が観察しやすいことがある。「いつ崩れたか」を振り返ると見えてくる",
            },
            {
                "key": "response",
                "title": "🌿 サインが出た時の対処（自分の処方箋）",
                "placeholder": (
                    "例：\n"
                    "【早期サインが出たら】\n"
                    "・夜の予定を 1 つキャンセル\n"
                    "・湯船に浸かる\n"
                    "・誰かに「最近ちょっとしんどい」と一言送る\n\n"
                    "【警戒サインが出たら】\n"
                    "・週末は予定を空けて完全休養\n"
                    "・主治医に予約を入れる\n"
                    "・職場に「ちょっと負荷下げて」と相談する"
                ),
                "help": "対処を**先に決めておく**と、サインが出た時に迷わない",
            },
        ]

        with st.form("warning_signs_form"):
            _ws_values: dict[str, str] = {}
            for _sec in WARNING_SIGN_SECTIONS:
                _initial = _ws_existing.get(_sec["key"], "") if isinstance(
                    _ws_existing.get(_sec["key"]), str
                ) else ""
                _ws_values[_sec["key"]] = st.text_area(
                    _sec["title"],
                    value=_initial,
                    placeholder=_sec["placeholder"],
                    help=_sec["help"],
                    height=180,
                )
            _save_ws = st.form_submit_button(
                "💾 保存する", use_container_width=True,
            )
            if _save_ws:
                try:
                    save_warning_signs(_ws_values, user_id=CURRENT_USER_ID)
                    st.success("保存しました")
                except Exception as _e:
                    st.warning(f"保存に失敗：{_e}")

        # Markdown エクスポート
        st.divider()
        with st.expander(
            "📤 サインリストをテキストで取り出す（共有用）", expanded=False,
        ):
            _md_lines = ["# 再発のサインリスト", ""]
            for _sec in WARNING_SIGN_SECTIONS:
                _v = _ws_existing.get(_sec["key"], "")
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
                    file_name="my_warning_signs.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

        # === AI 補完提案（書いた後にだけ動く）===
        # 設計意図：
        # - 「いきなり AI 一般例を提示」は anchoring リスク
        # - 本人がまず書いた内容を踏まえて、抜けていそうな観点を補完する
        # - 採用するかは本人の判断（提案は表示のみ、書き込みはしない）
        st.divider()
        st.markdown("### 🤖 AI に抜けを補完してもらう（オプション）")
        if not _CHAT_AVAILABLE:
            st.caption(
                "AI 補助は API キーが設定されていない環境では使えません。"
            )
        else:
            _has_existing_content = any(
                isinstance(_ws_existing.get(_k), str)
                and _ws_existing.get(_k, "").strip()
                for _k in ["early", "warning", "triggers", "response"]
            )
            if not _has_existing_content:
                st.caption(
                    "👆 まず上のフォームで **早期サイン・警戒サイン** を"
                    "少しでも書いて保存してから、AI に補完提案をもらえます。"
                    "「自分の言葉が主、AI は補助」の順序を守るためです。"
                )
            else:
                st.caption(
                    "**書いた内容を踏まえて**、抜けていそうな観点を AI が提案します。"
                    "**自動で追加はしません**。本人が「これは自分の感覚に合う」と思ったものだけ、"
                    "上のフォームに自分で書き写してください。"
                )

                if st.button(
                    "🤖 抜けを補完する提案をもらう",
                    use_container_width=True,
                    key="warning_ai_suggest",
                ):
                    try:
                        with st.spinner("AI が補完候補を考えています…"):
                            # 補助情報：他データを軽く参照
                            _extra: dict = {}
                            try:
                                _ss_df = load_stress_sources(
                                    user_id=CURRENT_USER_ID, limit=5,
                                )
                                if not _ss_df.empty:
                                    _ss_recent = [
                                        ", ".join(
                                            json.loads(r["sources"] or "[]")
                                        )
                                        for _, r in _ss_df.iterrows()
                                    ]
                                    _extra["最近のストレス源（言葉にする）"] = (
                                        " / ".join(
                                            _x for _x in _ss_recent if _x
                                        )
                                    )
                            except Exception:
                                pass
                            try:
                                _nv_df = load_nonverbal_memos(
                                    user_id=CURRENT_USER_ID, limit=5,
                                )
                                if not _nv_df.empty:
                                    _nv_recent = [
                                        " ".join(
                                            json.loads(r["state_markers"] or "[]")
                                        )
                                        + " "
                                        + (r["content"] or "")
                                        for _, r in _nv_df.iterrows()
                                    ]
                                    _extra["最近の状態マーカー（言葉にできないメモ）"] = (
                                        " / ".join(
                                            _x.strip()
                                            for _x in _nv_recent if _x.strip()
                                        )
                                    )
                            except Exception:
                                pass

                            _suggest = chat_engine.suggest_warning_signs(
                                existing=_ws_existing,
                                extra_context=_extra or None,
                            )
                        st.session_state["warning_ai_suggest"] = _suggest
                    except Exception as _e:
                        st.warning(f"提案の取得に失敗：{_e}")

                _suggest = st.session_state.get("warning_ai_suggest")
                if _suggest:
                    st.divider()
                    st.markdown("#### 🤖 補完候補（参考）")
                    st.caption(
                        "下記は **自分の感覚と合うかチェックする材料**。"
                        "**ピンと来たものだけ**、上のフォームに自分で書き写してください。"
                        "ピンと来ないものは無視で OK。"
                    )
                    _sug_early = _suggest.get("suggested_early") or []
                    _sug_warn = _suggest.get("suggested_warning") or []
                    _sug_notes = _suggest.get("notes") or ""

                    if not _sug_early and not _sug_warn:
                        st.caption(
                            "（候補は出ませんでした。"
                            "既に十分書けているか、AI が推測しきれませんでした）"
                        )

                    if _sug_early:
                        with st.container(border=True):
                            st.markdown("**🌱 早期サイン候補**")
                            for _s in _sug_early:
                                st.markdown(f"- {_s}")

                    if _sug_warn:
                        with st.container(border=True):
                            st.markdown("**⚠️ 警戒サイン候補**")
                            for _s in _sug_warn:
                                st.markdown(f"- {_s}")

                    if _sug_notes:
                        st.caption(f"💡 {_sug_notes}")

                    if st.button(
                        "🗑️ 候補を閉じる",
                        key="warning_ai_clear",
                    ):
                        st.session_state.pop("warning_ai_suggest", None)
                        st.rerun()

    # ----- タブ 2: 今チェックする -----
    elif _ws_tab == "✅ 今チェックする":
        st.caption(
            "**自分が書いた早期・警戒サイン**から、今当てはまるものをチェックします。"
            "結果は時系列で保存されるので、後で自分の波を振り返れます。"
            "**判定はなし**、自己観察として。"
        )

        # 書いたサインを行ごとに分解してチェックボックス化
        _early_raw = _ws_existing.get("early", "")
        _warning_raw = _ws_existing.get("warning", "")

        def _split_lines(s: str) -> list[str]:
            if not isinstance(s, str):
                return []
            lines = [
                _ln.strip().lstrip("・-•").strip()
                for _ln in s.split("\n")
            ]
            return [_ln for _ln in lines if _ln]

        _early_list = _split_lines(_early_raw)
        _warning_list = _split_lines(_warning_raw)

        if not _early_list and not _warning_list:
            st.info(
                "まだサインが書かれていません。"
                "「📝 サインを書く」タブで早期・警戒サインを書いてから戻ってきてください。"
            )
        else:
            with st.form("warning_checkin_form", clear_on_submit=True):
                _checked: list[str] = []

                if _early_list:
                    st.markdown("**🌱 早期サイン**")
                    for _sign in _early_list:
                        if st.checkbox(_sign, key=f"chk_e_{_sign}"):
                            _checked.append(f"🌱 {_sign}")
                    st.write("")

                if _warning_list:
                    st.markdown("**⚠️ 警戒サイン**")
                    for _sign in _warning_list:
                        if st.checkbox(_sign, key=f"chk_w_{_sign}"):
                            _checked.append(f"⚠️ {_sign}")
                    st.write("")

                _checkin_note = st.text_area(
                    "今のメモ（任意）",
                    placeholder="今の状況・気付いたこと（書けなくても OK）",
                    height=80,
                )

                _save_checkin = st.form_submit_button(
                    "💾 今の状態を記録する", use_container_width=True,
                )
                if _save_checkin:
                    try:
                        save_warning_checkin(
                            checked_signs=_checked,
                            note=_checkin_note,
                            user_id=CURRENT_USER_ID,
                        )
                        _n_early = sum(1 for c in _checked if c.startswith("🌱"))
                        _n_warn = sum(1 for c in _checked if c.startswith("⚠️"))
                        st.success(
                            f"記録しました（早期 {_n_early} / 警戒 {_n_warn}）"
                        )
                    except Exception as _e:
                        st.warning(f"保存に失敗：{_e}")

            # 対処の参照
            _response = _ws_existing.get("response", "")
            if isinstance(_response, str) and _response.strip():
                st.divider()
                with st.expander(
                    "🌿 自分が書いた「対処（処方箋）」を見る",
                    expanded=False,
                ):
                    st.markdown(_response)

    # ----- タブ 3: チェック履歴 -----
    else:
        st.caption(
            "**過去のセルフチェック履歴**。"
            "波の大きさ・頻度を後から振り返る素材です。**判定はなし**、観察として。"
        )

        try:
            _df_ci = load_warning_checkins(user_id=CURRENT_USER_ID, limit=30)
            if _df_ci.empty:
                st.caption(
                    "まだチェック履歴はありません。"
                    "「✅ 今チェックする」タブで記録できます。"
                )
            else:
                # サマリ：直近 7 日のチェック件数
                try:
                    _df_ci_dt = _df_ci.copy()
                    _df_ci_dt["created_at"] = pd.to_datetime(
                        _df_ci_dt["created_at"], errors="coerce"
                    )
                    _recent = _df_ci_dt[
                        _df_ci_dt["created_at"]
                        >= (pd.Timestamp.now() - pd.Timedelta(days=7))
                    ]
                    st.caption(
                        f"直近 7 日のチェック回数：**{len(_recent)} 回**"
                        f" ／ 全期間：**{len(_df_ci_dt)} 回**"
                    )
                except Exception:
                    pass

                for _, _row in _df_ci.iterrows():
                    try:
                        _dt = pd.to_datetime(_row["created_at"])
                        _dt_str = _dt.strftime("%m/%d %H:%M")
                    except Exception:
                        _dt_str = str(_row["created_at"])
                    try:
                        _signs_list = json.loads(_row["checked_signs"] or "[]")
                    except Exception:
                        _signs_list = []
                    _n_early = sum(1 for s in _signs_list if s.startswith("🌱"))
                    _n_warn = sum(1 for s in _signs_list if s.startswith("⚠️"))
                    _summary = []
                    if _n_early:
                        _summary.append(f"🌱{_n_early}")
                    if _n_warn:
                        _summary.append(f"⚠️{_n_warn}")
                    _summary_str = "  ".join(_summary) or "（チェックなし）"
                    with st.expander(
                        f"📝 {_dt_str}　{_summary_str}", expanded=False,
                    ):
                        if _signs_list:
                            for _s in _signs_list:
                                st.markdown(f"- {_s}")
                        else:
                            st.caption("（当てはまるサインなし）")
                        if _row.get("note"):
                            st.divider()
                            st.markdown(f"**メモ**：{_row['note']}")
                        if st.button(
                            "🗑️ 削除", key=f"del_ci_{_row['id']}",
                        ):
                            try:
                                delete_warning_checkin(
                                    int(_row["id"]),
                                    user_id=CURRENT_USER_ID,
                                )
                                st.rerun()
                            except Exception as _e:
                                st.warning(f"削除失敗：{_e}")
        except Exception as _e:
            st.caption(f"履歴の読み込みでエラー：{_e}")


# ============================================================
# View 4: 強みインベントリ
# ============================================================
elif view == "💪 強みインベントリ":
    st.divider()
    st.markdown("## 💪 強みインベントリ")
    st.caption(
        "**抽象的な性格より、過去の実例から強みを拾う**ためのツール。"
        "STAR 構造（状況 / 行動 / 結果）で書くと、職務経歴書・面接・"
        "1on1 でそのまま使える形になります。**判定なし**、自分の言葉で残すだけ。"
    )

    STRENGTH_CATEGORIES = [
        "—（未分類）",
        "🔧 技術・専門性",
        "🧠 思考・分析",
        "🤝 対人・コミュニケーション",
        "🎯 行動・実行力",
        "💡 創造性・発想",
        "🌱 自己管理・継続",
        "📚 学習・成長",
        "🔍 その他",
    ]

    _strength_tab = st.radio(
        "切り替え",
        ["📝 強みを追加", "💬 AI と整理する", "📚 一覧 / 編集", "📤 エクスポート"],
        label_visibility="collapsed",
        horizontal=True,
        key="strength_tab",
    )

    # ----- タブ 1: 強みを追加 -----
    if _strength_tab == "📝 強みを追加":
        st.caption(
            "**1 件 = 1 強み**として書きます。"
            "「STAR」のうち書けるところだけ書けば OK（全部書く必要はなし）。"
        )

        with st.form("strength_add_form", clear_on_submit=True):
            _name = st.text_input(
                "💪 強みの名前",
                placeholder="例：データを構造化して読み取れる / 当事者目線で言語化できる / コツコツ続けられる",
                help="一言で。後で見返した時に「あ、これね」と分かる名前",
            )
            _category = st.selectbox(
                "カテゴリ（任意）",
                STRENGTH_CATEGORIES,
                index=0,
            )
            _situation = st.text_area(
                "🌅 状況（Situation）— その強みが現れた具体的な場面",
                placeholder=(
                    "例：「2024 年、異常検知システムの精度が悪化していた時。"
                    "原因が複数の特徴量に分散していて、誰も全体像を掴めていなかった」"
                ),
                help="when / where / who の文脈を書くと、後で再利用しやすい",
                height=100,
            )
            _action = st.text_area(
                "🚀 行動（Action）— その時、自分が何をしたか",
                placeholder=(
                    "例：「特徴量を 6 つに絞り込み、CV R² で過学習を可視化。"
                    "ステークホルダーに『数を絞る方が精度上がる』とデータで説明した」"
                ),
                help="**自分が** 何をしたか。チームでやったことでも自分の貢献を書く",
                height=100,
            )
            _result = st.text_area(
                "🎯 結果（Result）— どうなったか・反響",
                placeholder=(
                    "例：「翌週には精度が回復。"
                    "『データで判断する文化が広がった』と PM から言ってもらえた」"
                ),
                help="定量・定性どちらでも。「言ってもらえた」レベルでも貴重",
                height=80,
            )
            _free_note_s = st.text_area(
                "✍️ 補足・関連メモ（任意）",
                placeholder="他の場面でも似たことができた / 言葉では説明しにくい部分 など",
                height=60,
            )

            _save_s = st.form_submit_button(
                "💾 追加する", use_container_width=True,
            )
            if _save_s:
                if not _name.strip():
                    st.warning("強みの名前は必須です")
                else:
                    try:
                        save_strength(
                            name=_name,
                            category=(
                                _category if _category != "—（未分類）" else None
                            ),
                            situation=_situation,
                            action=_action,
                            result=_result,
                            free_note=_free_note_s,
                            user_id=CURRENT_USER_ID,
                        )
                        st.success(f"強み「{_name}」を追加しました")
                    except Exception as _e:
                        st.warning(f"保存に失敗：{_e}")

        # 書き方のヒント
        with st.expander("💡 強みを書く時のヒント", expanded=False):
            st.markdown(
                "- **「自分は◯◯な性格」より「◯◯した時、こうした」**：抽象より実例\n"
                "- **小さな実例で OK**：仕事の大きな成功でなくても、"
                "「友人に頼られた」「家族に感謝された」レベルでも十分\n"
                "- **「結果」が分からなくても書く**：行動だけでも価値あり。"
                "「結果は分からない」と書くのも OK\n"
                "- **後から編集できる**：完璧に書こうとせず、まず 1 件残す"
            )

    # ----- タブ 2: AI と整理する -----
    elif _strength_tab == "💬 AI と整理する":
        if not _CHAT_AVAILABLE:
            st.caption(
                "AI 補助は API キーが設定されていない環境では使えません。"
                "「📝 強みを追加」タブから自分で書く形でご利用ください。"
            )
        else:
            st.caption(
                "**AI と対話**しながら、過去の場面から強み 1 件を STAR 構造で引き出します。"
                "AI は質問するだけ。**最終的な強みは本人の言葉**でフォームに反映してください。"
            )

            _skey = "chat_strength_messages"
            if _skey not in st.session_state:
                st.session_state[_skey] = []

            for _msg in st.session_state[_skey]:
                with st.chat_message(_msg["role"]):
                    st.markdown(_msg["content"])

            _user_input_s = st.chat_input(
                "ここに書きながら強みを引き出す…",
                key="strength_chat_input",
            )
            if _user_input_s:
                # 危機検出
                try:
                    _ai_client = chat_engine._get_client()
                except Exception:
                    _ai_client = None
                _md = detect_mode(
                    _user_input_s, client=_ai_client, use_llm=True,
                )["mode"]
                if _md == "critical":
                    render_critical_ui()
                    st.stop()
                elif _md == "warning":
                    render_warning_ui(
                        on_resume_key="strength_chat_warning_resume",
                    )
                    st.stop()

                st.session_state[_skey].append(
                    {"role": "user", "content": _user_input_s}
                )
                try:
                    with st.spinner("…考えています…"):
                        _ai_reply_s = chat_engine.chat_strength(
                            st.session_state[_skey]
                        )
                    st.session_state[_skey].append(
                        {"role": "assistant", "content": _ai_reply_s}
                    )
                    st.rerun()
                except Exception as _e:
                    st.warning(f"AI 応答失敗：{_e}")
                    st.session_state[_skey].pop()

            if len(st.session_state[_skey]) >= 2:
                _col_es, _col_cs = st.columns(2)
                with _col_es:
                    if st.button(
                        "📥 ここまでの会話から強み 1 件を抽出",
                        use_container_width=True,
                        key="strength_chat_extract",
                    ):
                        try:
                            with st.spinner("抽出中…"):
                                _extracted_s = (
                                    chat_engine.extract_strength_from_chat(
                                        st.session_state[_skey]
                                    )
                                )
                            st.session_state["chat_strength_extracted"] = (
                                _extracted_s
                            )
                            st.success("抽出しました（下に表示）")
                        except Exception as _e:
                            st.warning(f"抽出失敗：{_e}")
                with _col_cs:
                    if st.button(
                        "🗑️ チャットをリセット",
                        use_container_width=True,
                        key="strength_chat_reset",
                    ):
                        st.session_state[_skey] = []
                        st.session_state.pop(
                            "chat_strength_extracted", None,
                        )
                        st.rerun()

            _extracted_s = st.session_state.get("chat_strength_extracted")
            if _extracted_s:
                st.divider()
                st.markdown("#### 💪 抽出結果プレビュー")
                st.caption(
                    "下記が AI が抽出した 1 件です。"
                    "**確認して保存ボタン**を押すと強み一覧に追加されます。"
                    "保存後は「📚 一覧 / 編集」タブで自分の言葉に修正できます。"
                )
                with st.container(border=True):
                    _ex_name = _extracted_s.get("name", "")
                    _ex_cat = _extracted_s.get("category", "—（未分類）")
                    _ex_sit = _extracted_s.get("situation", "")
                    _ex_act = _extracted_s.get("action", "")
                    _ex_res = _extracted_s.get("result", "")
                    _ex_note = _extracted_s.get("free_note", "")
                    st.markdown(f"**💪 名前**：{_ex_name or '（未抽出）'}")
                    st.markdown(f"**カテゴリ**：{_ex_cat}")
                    if _ex_sit:
                        st.markdown(f"**🌅 状況**：{_ex_sit}")
                    if _ex_act:
                        st.markdown(f"**🚀 行動**：{_ex_act}")
                    if _ex_res:
                        st.markdown(f"**🎯 結果**：{_ex_res}")
                    if _ex_note:
                        st.markdown(f"**✍️ 補足**：{_ex_note}")

                if _ex_name.strip():
                    if st.button(
                        "💾 強みとして保存",
                        use_container_width=True,
                        key="strength_chat_save",
                    ):
                        try:
                            save_strength(
                                name=_ex_name,
                                category=(
                                    _ex_cat if _ex_cat != "—（未分類）" else None
                                ),
                                situation=_ex_sit,
                                action=_ex_act,
                                result=_ex_res,
                                free_note=_ex_note,
                                user_id=CURRENT_USER_ID,
                            )
                            st.session_state.pop(
                                "chat_strength_extracted", None,
                            )
                            st.session_state[_skey] = []
                            st.success(
                                f"強み「{_ex_name}」を保存しました。"
                                "「📚 一覧 / 編集」タブで確認・修正できます。"
                            )
                        except Exception as _e:
                            st.warning(f"保存失敗：{_e}")

    # ----- タブ 3: 一覧 / 編集 -----
    elif _strength_tab == "📚 一覧 / 編集":
        try:
            _df_s = load_strengths(user_id=CURRENT_USER_ID, limit=100)
            if _df_s.empty:
                st.info(
                    "まだ強みは登録されていません。"
                    "「📝 強みを追加」から 1 件目を残してください。"
                )
            else:
                st.caption(
                    f"登録済み：**{len(_df_s)} 件**。"
                    "各行を開いて編集・削除できます。"
                )

                # カテゴリ別件数
                if "category" in _df_s.columns:
                    _cat_counts = _df_s["category"].fillna("（未分類）").value_counts()
                    _cat_summary = "  ".join(
                        f"{_c}: {_n}" for _c, _n in _cat_counts.items()
                    )
                    if _cat_summary:
                        st.caption(f"📊 カテゴリ別：{_cat_summary}")

                for _, _row in _df_s.iterrows():
                    _name_d = _row["name"] or "（無題）"
                    _cat_d = _row.get("category") or ""
                    _title = f"💪 {_name_d}"
                    if _cat_d:
                        _title += f"　／　{_cat_d}"
                    with st.expander(_title, expanded=False):
                        # 編集フォーム
                        with st.form(f"strength_edit_{_row['id']}"):
                            _e_name = st.text_input(
                                "強みの名前", value=_name_d,
                                key=f"e_name_{_row['id']}",
                            )
                            _e_cat_idx = 0
                            if _cat_d in STRENGTH_CATEGORIES:
                                _e_cat_idx = STRENGTH_CATEGORIES.index(_cat_d)
                            _e_category = st.selectbox(
                                "カテゴリ", STRENGTH_CATEGORIES,
                                index=_e_cat_idx,
                                key=f"e_cat_{_row['id']}",
                            )
                            _e_situation = st.text_area(
                                "🌅 状況",
                                value=_row.get("situation") or "",
                                height=100,
                                key=f"e_sit_{_row['id']}",
                            )
                            _e_action = st.text_area(
                                "🚀 行動",
                                value=_row.get("action") or "",
                                height=100,
                                key=f"e_act_{_row['id']}",
                            )
                            _e_result = st.text_area(
                                "🎯 結果",
                                value=_row.get("result") or "",
                                height=80,
                                key=f"e_res_{_row['id']}",
                            )
                            _e_note = st.text_area(
                                "✍️ 補足",
                                value=_row.get("free_note") or "",
                                height=60,
                                key=f"e_note_{_row['id']}",
                            )
                            _c1, _c2 = st.columns(2)
                            with _c1:
                                _do_update = st.form_submit_button(
                                    "💾 更新", use_container_width=True,
                                )
                            with _c2:
                                _do_delete = st.form_submit_button(
                                    "🗑️ 削除", use_container_width=True,
                                )
                            if _do_update:
                                if not _e_name.strip():
                                    st.warning("名前は必須です")
                                else:
                                    try:
                                        update_strength(
                                            int(_row["id"]),
                                            name=_e_name,
                                            category=(
                                                _e_category
                                                if _e_category != "—（未分類）"
                                                else None
                                            ),
                                            situation=_e_situation,
                                            action=_e_action,
                                            result=_e_result,
                                            free_note=_e_note,
                                            user_id=CURRENT_USER_ID,
                                        )
                                        st.success("更新しました")
                                        st.rerun()
                                    except Exception as _e:
                                        st.warning(f"更新失敗：{_e}")
                            if _do_delete:
                                try:
                                    delete_strength(
                                        int(_row["id"]),
                                        user_id=CURRENT_USER_ID,
                                    )
                                    st.success("削除しました")
                                    st.rerun()
                                except Exception as _e:
                                    st.warning(f"削除失敗：{_e}")
        except Exception as _e:
            st.caption(f"読み込みでエラー：{_e}")

    # ----- タブ 3: エクスポート -----
    else:
        st.caption(
            "**職務経歴書・面接準備・1on1 共有用**にまとめてテキストで取り出せます。"
        )
        try:
            _df_s = load_strengths(user_id=CURRENT_USER_ID, limit=100)
            if _df_s.empty:
                st.info("まだ強みは登録されていません。")
            else:
                _md_lines = ["# 強みインベントリ", ""]
                # カテゴリでグルーピング
                _df_grouped = _df_s.copy()
                _df_grouped["category"] = (
                    _df_grouped["category"].fillna("（未分類）")
                )
                for _cat, _grp in _df_grouped.groupby(
                    "category", sort=False,
                ):
                    _md_lines.append(f"## {_cat}")
                    _md_lines.append("")
                    for _, _row in _grp.iterrows():
                        _md_lines.append(f"### 💪 {_row['name']}")
                        _md_lines.append("")
                        if _row.get("situation"):
                            _md_lines.append(f"**🌅 状況**：{_row['situation']}")
                            _md_lines.append("")
                        if _row.get("action"):
                            _md_lines.append(f"**🚀 行動**：{_row['action']}")
                            _md_lines.append("")
                        if _row.get("result"):
                            _md_lines.append(f"**🎯 結果**：{_row['result']}")
                            _md_lines.append("")
                        if _row.get("free_note"):
                            _md_lines.append(f"**✍️ 補足**：{_row['free_note']}")
                            _md_lines.append("")
                _md_text = "\n".join(_md_lines)
                st.text_area(
                    "Markdown テキスト",
                    value=_md_text,
                    height=400,
                    label_visibility="collapsed",
                )
                st.download_button(
                    "💾 .md ファイルとしてダウンロード",
                    data=_md_text.encode("utf-8"),
                    file_name="my_strengths.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        except Exception as _e:
            st.caption(f"エクスポートでエラー：{_e}")


# ============================================================
# View 5: 価値観カードソート
# ============================================================
elif view == "🎯 価値観カードソート":
    st.divider()
    st.markdown("## 🎯 価値観カードソート")
    st.caption(
        "**自分が大事にする価値観**を 40 個のカードから選んで、最後に Top 5 に絞り込みます。"
        "5 つまで絞ると、判断・選択の指針として使いやすくなります。"
        "**正解はありません**、自分の今の感覚で選んでみてください。"
    )

    # 価値観カード（40 個・5 カテゴリ）
    VALUE_CARDS = {
        "💼 仕事・キャリア": [
            ("成長", "新しい学び・スキルアップ"),
            ("達成", "目標を達成すること"),
            ("専門性", "一つの分野を深める"),
            ("影響力", "他者・社会への影響"),
            ("自由", "時間・場所の柔軟性"),
            ("安定", "収入・雇用の安定"),
            ("挑戦", "新しいことへの挑戦"),
            ("創造", "新しいものを生み出す"),
            ("貢献", "社会・組織への貢献"),
            ("リーダーシップ", "人を率いる"),
        ],
        "🤝 人間関係": [
            ("家族", "家族との時間"),
            ("友情", "友人との関係"),
            ("パートナーシップ", "パートナーとの関係"),
            ("コミュニティ", "所属感"),
            ("助け合い", "互いに助ける関係"),
            ("信頼", "信頼できる人間関係"),
            ("独立", "一人の時間・空間"),
        ],
        "🌱 自己・成長": [
            ("健康", "心身の健康"),
            ("学び", "生涯学習"),
            ("探究", "好奇心"),
            ("美", "美しいもの・芸術"),
            ("自然", "自然との触れ合い"),
            ("平穏", "穏やかな日常"),
            ("ユーモア", "笑い・楽しさ"),
            ("誠実", "正直さ"),
            ("勇気", "恐れに立ち向かう"),
            ("内省", "自己理解"),
        ],
        "🌍 社会・倫理": [
            ("公正", "公平さ"),
            ("多様性", "違いを尊重"),
            ("環境", "環境への配慮"),
            ("伝統", "伝統・文化を守る"),
            ("革新", "古いものを変える"),
            ("平等", "機会の平等"),
        ],
        "🌌 人生・意味": [
            ("意味", "人生の意味"),
            ("充足", "足るを知る"),
            ("感謝", "感謝の心"),
            ("楽しさ", "人生を楽しむ"),
            ("旅・経験", "新しい場所・経験"),
            ("豊かさ", "経済的・物質的な豊かさ"),
            ("名声", "社会的評価"),
        ],
    }

    # 全価値観のフラットリスト（順序保持）
    ALL_VALUES: list[tuple[str, str]] = []
    for _cat, _items in VALUE_CARDS.items():
        ALL_VALUES.extend(_items)
    ALL_VALUE_NAMES = [_v[0] for _v in ALL_VALUES]

    SORT_OPTIONS = ["⚪ どちらでも", "🟢 重要", "⛔ 重要でない"]
    SORT_KEY_MAP = {
        "⚪ どちらでも": "どちらでも",
        "🟢 重要": "重要",
        "⛔ 重要でない": "重要でない",
    }
    SORT_FROM_KEY = {v: k for k, v in SORT_KEY_MAP.items()}

    _vs_existing = load_values_sort(user_id=CURRENT_USER_ID)
    _vs_sort: dict = _vs_existing.get("sort") or {}
    _vs_top5: list = _vs_existing.get("top5") or []
    _vs_descs: dict = _vs_existing.get("descriptions") or {}

    _vs_tab = st.radio(
        "切り替え",
        ["🃏 仕分け（全 40 枚）", "⭐ Top 5 を選ぶ", "📋 結果・エクスポート"],
        label_visibility="collapsed",
        horizontal=True,
        key="values_sort_tab",
    )

    # ----- タブ 1: 仕分け -----
    if _vs_tab == "🃏 仕分け（全 40 枚）":
        _updated_at_vs = _vs_existing.get("_updated_at")
        if _updated_at_vs:
            try:
                _disp = _updated_at_vs.replace("T", " ")[:16]
                st.caption(f"📅 最終更新：{_disp}")
            except Exception:
                pass

        st.caption(
            "**🟢 重要**（自分にとって大事）／"
            "**⚪ どちらでも**（特に強い思いはない）／"
            "**⛔ 重要でない**（自分には当てはまらない）。"
            "デフォルトは「どちらでも」。Top 5 に進むには、まず **5 個以上を「重要」に**してください。"
        )

        with st.form("values_sort_form"):
            _new_sort: dict[str, str] = {}
            for _cat, _items in VALUE_CARDS.items():
                st.markdown(f"**{_cat}**")
                for _name, _desc in _items:
                    _stored = _vs_sort.get(_name, "どちらでも")
                    _stored_display = SORT_FROM_KEY.get(_stored, "⚪ どちらでも")
                    _idx = (
                        SORT_OPTIONS.index(_stored_display)
                        if _stored_display in SORT_OPTIONS else 0
                    )
                    _selected = st.radio(
                        f"**{_name}**　／　{_desc}",
                        SORT_OPTIONS,
                        index=_idx,
                        horizontal=True,
                        key=f"vs_{_name}",
                    )
                    _new_sort[_name] = SORT_KEY_MAP.get(_selected, "どちらでも")
                st.write("")

            _save_vs = st.form_submit_button(
                "💾 仕分けを保存", use_container_width=True,
            )
            if _save_vs:
                try:
                    _content = {
                        "sort": _new_sort,
                        "top5": _vs_top5,
                        "descriptions": _vs_descs,
                    }
                    save_values_sort(_content, user_id=CURRENT_USER_ID)
                    _n_important = sum(
                        1 for v in _new_sort.values() if v == "重要"
                    )
                    st.success(f"保存しました（🟢 重要：{_n_important} 個）")
                except Exception as _e:
                    st.warning(f"保存に失敗：{_e}")

    # ----- タブ 2: Top 5 を選ぶ -----
    elif _vs_tab == "⭐ Top 5 を選ぶ":
        _important_values = [
            _name for _name in ALL_VALUE_NAMES
            if _vs_sort.get(_name) == "重要"
        ]
        if len(_important_values) < 5:
            st.info(
                f"「🟢 重要」が **{len(_important_values)} 個** です。"
                "**5 個以上**を「重要」にしてから戻ってきてください。"
                "（「🃏 仕分け」タブで選び直せます）"
            )
        else:
            st.caption(
                f"**🟢 重要**に選んだ **{len(_important_values)} 個** から、"
                "**Top 5** を選んでください。同じ「成長」でも、人によって意味は違います。"
                "**自分にとってどういう意味か** を書くと、後で見返した時に効きます。"
            )

            with st.form("values_top5_form"):
                _selected_top5 = st.multiselect(
                    "Top 5（5 つまで）",
                    _important_values,
                    default=[v for v in _vs_top5 if v in _important_values][:5],
                    max_selections=5,
                )

                _new_descs: dict[str, str] = {}
                if _selected_top5:
                    st.markdown("---")
                    st.markdown("**📝 自分にとっての意味（任意）**")
                    st.caption(
                        "それぞれの価値観が、自分にとって**どういう意味か**を一言で。"
                        "書けないものは空欄で OK。"
                    )
                    for _v in _selected_top5:
                        # 説明文（カード定義側）を補助として表示
                        _ref_desc = next(
                            (d for n, d in ALL_VALUES if n == _v), ""
                        )
                        _existing_desc = _vs_descs.get(_v, "")
                        _new_descs[_v] = st.text_area(
                            f"💎 {_v}　（一般的には：{_ref_desc}）",
                            value=_existing_desc,
                            placeholder="自分にとってこの価値観は…",
                            height=70,
                            key=f"desc_{_v}",
                        )

                _save_top5 = st.form_submit_button(
                    "💾 Top 5 を保存", use_container_width=True,
                )
                if _save_top5:
                    try:
                        # descriptions は新規分とマージ（古いものは残す）
                        _merged_descs = dict(_vs_descs)
                        _merged_descs.update(_new_descs)
                        _content = {
                            "sort": _vs_sort,
                            "top5": _selected_top5,
                            "descriptions": _merged_descs,
                        }
                        save_values_sort(_content, user_id=CURRENT_USER_ID)
                        st.success(
                            f"Top 5 を保存しました（{len(_selected_top5)} 個）"
                        )
                    except Exception as _e:
                        st.warning(f"保存に失敗：{_e}")

    # ----- タブ 3: 結果・エクスポート -----
    else:
        if not _vs_top5:
            st.info(
                "まだ Top 5 が保存されていません。"
                "「🃏 仕分け」→「⭐ Top 5 を選ぶ」を進めてください。"
            )
        else:
            st.markdown("### 💎 自分の Top 5 価値観")
            st.caption(
                "判断に迷った時の指針として。"
                "**この 5 つが自分の選び方の軸**になります。"
            )

            for _i, _v in enumerate(_vs_top5, 1):
                _ref_desc = next((d for n, d in ALL_VALUES if n == _v), "")
                _my_desc = _vs_descs.get(_v, "")
                with st.container(border=True):
                    st.markdown(f"### {_i}. 💎 {_v}")
                    st.caption(f"一般的には：{_ref_desc}")
                    if _my_desc.strip():
                        st.markdown(f"**自分にとっての意味**：{_my_desc}")
                    else:
                        st.caption("（自分にとっての意味は未記入）")

            # サマリ統計
            st.divider()
            _n_imp = sum(1 for v in _vs_sort.values() if v == "重要")
            _n_neu = sum(1 for v in _vs_sort.values() if v == "どちらでも")
            _n_not = sum(1 for v in _vs_sort.values() if v == "重要でない")
            st.caption(
                f"仕分け統計：🟢 重要 {_n_imp} ／ "
                f"⚪ どちらでも {_n_neu} ／ ⛔ 重要でない {_n_not}"
            )

            # Markdown エクスポート
            st.divider()
            with st.expander(
                "📤 価値観マップをテキストで取り出す", expanded=False,
            ):
                _md_lines = ["# 自分の価値観マップ", ""]
                _md_lines.append("## 💎 Top 5 価値観")
                _md_lines.append("")
                for _i, _v in enumerate(_vs_top5, 1):
                    _ref_desc = next((d for n, d in ALL_VALUES if n == _v), "")
                    _my_desc = _vs_descs.get(_v, "")
                    _md_lines.append(f"### {_i}. {_v}")
                    _md_lines.append("")
                    _md_lines.append(f"- 一般的には：{_ref_desc}")
                    if _my_desc.strip():
                        _md_lines.append(f"- 自分にとって：{_my_desc}")
                    _md_lines.append("")

                # 全 🟢 重要 一覧
                _all_imp = [
                    _name for _name in ALL_VALUE_NAMES
                    if _vs_sort.get(_name) == "重要"
                ]
                if _all_imp:
                    _md_lines.append("## 🟢 重要に選んだ全項目")
                    _md_lines.append("")
                    for _name in _all_imp:
                        _ref_desc = next(
                            (d for n, d in ALL_VALUES if n == _name), ""
                        )
                        _md_lines.append(f"- **{_name}**：{_ref_desc}")
                    _md_lines.append("")

                _md_text = "\n".join(_md_lines)
                st.text_area(
                    "Markdown テキスト",
                    value=_md_text,
                    height=400,
                    label_visibility="collapsed",
                )
                st.download_button(
                    "💾 .md ファイルとしてダウンロード",
                    data=_md_text.encode("utf-8"),
                    file_name="my_values_map.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
