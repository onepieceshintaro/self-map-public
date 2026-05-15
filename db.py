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

        # user_nicknames（3アプリ共通・プレフィックス無し）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_nicknames (
                user_id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
