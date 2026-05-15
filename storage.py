"""保存・読み込みヘルパー（自分マップ・公開版）。"""
import json
from sqlalchemy import text

from db import get_engine, init_db as _init_db
from time_utils import now_jst_naive


def init_db() -> None:
    _init_db()


def _owner_user_id() -> str:
    from _user import get_or_create_user_id
    return get_or_create_user_id()


# ========== 自分の取扱説明書 ==========
def save_manual(content: dict, user_id: str | None = None) -> None:
    """取扱説明書を保存（同一ユーザーは上書き）。content は dict。"""
    if user_id is None:
        user_id = _owner_user_id()
    content_json = json.dumps(content or {}, ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_manuals (user_id, content, updated_at)
        VALUES (:user_id, :content, :updated_at)
        ON CONFLICT (user_id) DO UPDATE SET
            content = EXCLUDED.content,
            updated_at = EXCLUDED.updated_at
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {
            "user_id": user_id,
            "content": content_json,
            "updated_at": now_jst_naive().isoformat(),
        })


def load_manual(user_id: str | None = None) -> dict:
    """取扱説明書を読み込む。無ければ空 dict。"""
    if user_id is None:
        user_id = _owner_user_id()
    sql = text(
        "SELECT content, updated_at FROM selfmap_manuals "
        "WHERE user_id = :user_id"
    )
    with get_engine().connect() as conn:
        row = conn.execute(sql, {"user_id": user_id}).fetchone()
    if not row or not row[0]:
        return {"_updated_at": None}
    try:
        data = json.loads(row[0])
        if isinstance(data, dict):
            data["_updated_at"] = row[1]
            return data
    except Exception:
        pass
    return {"_updated_at": None}


# ========== 働き方の譲れない条件 ==========
def save_work_conditions(content: dict, user_id: str | None = None) -> None:
    """働き方条件を保存（同一ユーザーは上書き）。"""
    if user_id is None:
        user_id = _owner_user_id()
    content_json = json.dumps(content or {}, ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_work_conditions (user_id, content, updated_at)
        VALUES (:user_id, :content, :updated_at)
        ON CONFLICT (user_id) DO UPDATE SET
            content = EXCLUDED.content,
            updated_at = EXCLUDED.updated_at
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {
            "user_id": user_id,
            "content": content_json,
            "updated_at": now_jst_naive().isoformat(),
        })


def load_work_conditions(user_id: str | None = None) -> dict:
    """働き方条件を読み込む。無ければ空 dict。"""
    if user_id is None:
        user_id = _owner_user_id()
    sql = text(
        "SELECT content, updated_at FROM selfmap_work_conditions "
        "WHERE user_id = :user_id"
    )
    with get_engine().connect() as conn:
        row = conn.execute(sql, {"user_id": user_id}).fetchone()
    if not row or not row[0]:
        return {"_updated_at": None}
    try:
        data = json.loads(row[0])
        if isinstance(data, dict):
            data["_updated_at"] = row[1]
            return data
    except Exception:
        pass
    return {"_updated_at": None}


# ========== 再発のサインリスト ==========
def save_warning_signs(content: dict, user_id: str | None = None) -> None:
    """再発サインリストを保存（同一ユーザーは上書き）。"""
    if user_id is None:
        user_id = _owner_user_id()
    content_json = json.dumps(content or {}, ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_warning_signs (user_id, content, updated_at)
        VALUES (:user_id, :content, :updated_at)
        ON CONFLICT (user_id) DO UPDATE SET
            content = EXCLUDED.content,
            updated_at = EXCLUDED.updated_at
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {
            "user_id": user_id,
            "content": content_json,
            "updated_at": now_jst_naive().isoformat(),
        })


def load_warning_signs(user_id: str | None = None) -> dict:
    """再発サインリストを読み込む。無ければ空 dict。"""
    if user_id is None:
        user_id = _owner_user_id()
    sql = text(
        "SELECT content, updated_at FROM selfmap_warning_signs "
        "WHERE user_id = :user_id"
    )
    with get_engine().connect() as conn:
        row = conn.execute(sql, {"user_id": user_id}).fetchone()
    if not row or not row[0]:
        return {"_updated_at": None}
    try:
        data = json.loads(row[0])
        if isinstance(data, dict):
            data["_updated_at"] = row[1]
            return data
    except Exception:
        pass
    return {"_updated_at": None}


# ========== 再発サインの「今チェック」ログ ==========
def save_warning_checkin(
    checked_signs: list[str],
    note: str | None = None,
    user_id: str | None = None,
) -> int:
    """今のセルフチェック結果を時系列で保存。"""
    if user_id is None:
        user_id = _owner_user_id()
    signs_json = json.dumps(checked_signs or [], ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_warning_checkins
        (user_id, created_at, checked_signs, note)
        VALUES
        (:user_id, :created_at, :checked_signs, :note)
    """)
    with get_engine().begin() as conn:
        result = conn.execute(sql, {
            "user_id": user_id,
            "created_at": now_jst_naive().isoformat(),
            "checked_signs": signs_json,
            "note": (note or "").strip() or None,
        })
        try:
            return int(result.lastrowid or 0)
        except Exception:
            return 0


def load_warning_checkins(
    user_id: str | None = None, limit: int = 30,
):
    """チェックイン履歴を取得（DataFrame）。"""
    import pandas as pd
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT id, created_at, checked_signs, note "
                "FROM selfmap_warning_checkins "
                "WHERE user_id = :user_id "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            conn, params={"user_id": user_id, "limit": int(limit)},
        )
    return df


def delete_warning_checkin(record_id: int, user_id: str | None = None) -> None:
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM selfmap_warning_checkins "
                 "WHERE id = :id AND user_id = :user_id"),
            {"id": int(record_id), "user_id": user_id},
        )
