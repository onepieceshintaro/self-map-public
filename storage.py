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
