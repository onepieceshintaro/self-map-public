"""DB抽象レイヤー（自分マップ・公開版）。
共有 Supabase 上のテーブル prefix: `selfmap_`

優先順位：
  1. st.secrets["DATABASE_URL"]  （Streamlit Cloud）
  2. 環境変数 DATABASE_URL         （ローカル .env など）
  3. sqlite:///self_map.db         （フォールバック・ローカル）
"""
import os
from functools import lru_cache

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _get_database_url() -> str:
    try:
        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    return "sqlite:///self_map.db"


def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = _normalize_url(_get_database_url())
    return create_engine(url, pool_pre_ping=True, future=True)


def is_postgres() -> bool:
    return "postgresql" in str(get_engine().url)


def init_db() -> None:
    """テーブルを作成（冪等）。SQLite/Postgres両方で動く構文を使う。"""
    engine = get_engine()
    pg = is_postgres()

    with engine.begin() as conn:
        # selfmap_manuals（自分の取扱説明書）
        # 1ユーザー1レコード（latest 上書き）方式：取扱説明書は「常に最新版を持つ」性質。
        # JSON 1 カラムでセクションごとの内容を保持する。スキーマ進化に強い。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_manuals (
                user_id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            )
        """))

        # selfmap_work_conditions（働き方の譲れない条件）
        # 1ユーザー1レコード方式（常に最新版）。
        # content は dict（項目名 → "必須"/"望ましい"/"不要"）＋ "_free_note"。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_work_conditions (
                user_id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            )
        """))

        # selfmap_warning_signs（再発のサインリスト）
        # 早期サイン / 警戒サイン / きっかけ をユーザーが自分の言葉で書く。
        # 取扱説明書とは別管理：再発予防に特化、段階分けで対処を変えやすくする。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_warning_signs (
                user_id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            )
        """))

        # selfmap_warning_checkins（再発サインの「今チェック」ログ）
        # 「今、自分のサインに何個当てはまるか」を時系列で残す。
        # 履歴で自分の波が見える → β 期の伴走素材にもなる。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_warning_checkins (
                id {"BIGSERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"},
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                checked_signs TEXT,
                note TEXT
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_selfmap_warning_checkins_user "
            "ON selfmap_warning_checkins(user_id, created_at)"
        ))

        # selfmap_strengths（強みインベントリ）
        # 1 強み = 1 レコード。STAR 構造（Situation / Action / Result）。
        # 抽象的な性格より過去の実例から拾う方が後で使える（職務経歴書・面接・1on1）。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_strengths (
                id {"BIGSERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"},
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                situation TEXT,
                action TEXT,
                result TEXT,
                free_note TEXT
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_selfmap_strengths_user "
            "ON selfmap_strengths(user_id, created_at)"
        ))

        # selfmap_stress_sources（Phase 1: 仕事ストレス源チェックリスト）
        # 元は CBT 側に置いていたが、self-map に「自己理解ツール」として集約。
        # 何にしんどさを感じているかを言語化する第一歩。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_stress_sources (
                id {"BIGSERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"},
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sources TEXT,
                free_note TEXT
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_selfmap_stress_sources_user "
            "ON selfmap_stress_sources(user_id, created_at)"
        ))

        # selfmap_nonverbal_memos（Phase 1: 「言葉にできないこと」専用メモ）
        # 元は CBT 側に置いていたが、self-map に集約。
        # 書ける前提の UI が罠になる場合のフォールバック。
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_nonverbal_memos (
                id {"BIGSERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"},
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                state_markers TEXT,
                content TEXT
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_selfmap_nonverbal_memos_user "
            "ON selfmap_nonverbal_memos(user_id, created_at)"
        ))

        # selfmap_values_sort（価値観カードソート）
        # 1ユーザー1レコード。3 段階仕分け + Top 5 + 自分の言葉での定義を JSON で保持。
        # content: {
        #   "sort": {value_name: "重要"/"どちらでも"/"重要でない"},
        #   "top5": [value_name, ...],
        #   "descriptions": {value_name: "自分にとっての意味"}
        # }
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS selfmap_values_sort (
                user_id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            )
        """))

        # user_nicknames（3アプリ共通・プレフィックス無し）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_nicknames (
                user_id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
