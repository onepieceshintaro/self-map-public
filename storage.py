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


# ========== 強みインベントリ ==========
def save_strength(
    name: str,
    category: str | None = None,
    situation: str | None = None,
    action: str | None = None,
    result: str | None = None,
    free_note: str | None = None,
    user_id: str | None = None,
) -> int:
    """強み 1 件を新規保存（追記）。"""
    if user_id is None:
        user_id = _owner_user_id()
    sql = text("""
        INSERT INTO selfmap_strengths
        (user_id, created_at, name, category, situation, action, result, free_note)
        VALUES
        (:user_id, :created_at, :name, :category, :situation, :action, :result, :free_note)
    """)
    with get_engine().begin() as conn:
        result_ins = conn.execute(sql, {
            "user_id": user_id,
            "created_at": now_jst_naive().isoformat(),
            "name": (name or "").strip(),
            "category": (category or "").strip() or None,
            "situation": (situation or "").strip() or None,
            "action": (action or "").strip() or None,
            "result": (result or "").strip() or None,
            "free_note": (free_note or "").strip() or None,
        })
        try:
            return int(result_ins.lastrowid or 0)
        except Exception:
            return 0


def update_strength(
    record_id: int,
    name: str,
    category: str | None = None,
    situation: str | None = None,
    action: str | None = None,
    result: str | None = None,
    free_note: str | None = None,
    user_id: str | None = None,
) -> None:
    """既存の強み 1 件を上書き更新。"""
    if user_id is None:
        user_id = _owner_user_id()
    sql = text("""
        UPDATE selfmap_strengths
        SET name = :name, category = :category, situation = :situation,
            action = :action, result = :result, free_note = :free_note
        WHERE id = :id AND user_id = :user_id
    """)
    with get_engine().begin() as conn:
        conn.execute(sql, {
            "id": int(record_id),
            "user_id": user_id,
            "name": (name or "").strip(),
            "category": (category or "").strip() or None,
            "situation": (situation or "").strip() or None,
            "action": (action or "").strip() or None,
            "result": (result or "").strip() or None,
            "free_note": (free_note or "").strip() or None,
        })


def load_strengths(user_id: str | None = None, limit: int = 100):
    """強み一覧を取得（DataFrame・新しい順）。"""
    import pandas as pd
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT id, created_at, name, category, situation, "
                "action, result, free_note FROM selfmap_strengths "
                "WHERE user_id = :user_id "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            conn, params={"user_id": user_id, "limit": int(limit)},
        )
    return df


def delete_strength(record_id: int, user_id: str | None = None) -> None:
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM selfmap_strengths "
                 "WHERE id = :id AND user_id = :user_id"),
            {"id": int(record_id), "user_id": user_id},
        )


# ========== 仕事ストレス源チェックリスト ==========
def save_stress_source(
    sources: list[str],
    free_note: str | None = None,
    user_id: str | None = None,
) -> int:
    if user_id is None:
        user_id = _owner_user_id()
    sources_json = json.dumps(sources or [], ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_stress_sources
        (user_id, created_at, sources, free_note)
        VALUES
        (:user_id, :created_at, :sources, :free_note)
    """)
    with get_engine().begin() as conn:
        result = conn.execute(sql, {
            "user_id": user_id,
            "created_at": now_jst_naive().isoformat(),
            "sources": sources_json,
            "free_note": (free_note or "").strip() or None,
        })
        try:
            return int(result.lastrowid or 0)
        except Exception:
            return 0


def load_stress_sources(
    user_id: str | None = None, limit: int = 50,
):
    import pandas as pd
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT id, created_at, sources, free_note "
                "FROM selfmap_stress_sources "
                "WHERE user_id = :user_id "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            conn, params={"user_id": user_id, "limit": int(limit)},
        )
    return df


def delete_stress_source(record_id: int, user_id: str | None = None) -> None:
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM selfmap_stress_sources "
                 "WHERE id = :id AND user_id = :user_id"),
            {"id": int(record_id), "user_id": user_id},
        )


# ========== 「言葉にできないこと」専用メモ ==========
def save_nonverbal_memo(
    state_markers: list[str] | None = None,
    content: str | None = None,
    user_id: str | None = None,
) -> int:
    if user_id is None:
        user_id = _owner_user_id()
    markers_json = json.dumps(state_markers or [], ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_nonverbal_memos
        (user_id, created_at, state_markers, content)
        VALUES
        (:user_id, :created_at, :state_markers, :content)
    """)
    with get_engine().begin() as conn:
        result = conn.execute(sql, {
            "user_id": user_id,
            "created_at": now_jst_naive().isoformat(),
            "state_markers": markers_json,
            "content": (content or "").strip() or None,
        })
        try:
            return int(result.lastrowid or 0)
        except Exception:
            return 0


def load_nonverbal_memos(
    user_id: str | None = None, limit: int = 50,
):
    import pandas as pd
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT id, created_at, state_markers, content "
                "FROM selfmap_nonverbal_memos "
                "WHERE user_id = :user_id "
                "ORDER BY created_at DESC LIMIT :limit"
            ),
            conn, params={"user_id": user_id, "limit": int(limit)},
        )
    return df


def delete_nonverbal_memo(record_id: int, user_id: str | None = None) -> None:
    if user_id is None:
        user_id = _owner_user_id()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM selfmap_nonverbal_memos "
                 "WHERE id = :id AND user_id = :user_id"),
            {"id": int(record_id), "user_id": user_id},
        )


# ========== 価値観カードソート ==========
def save_values_sort(content: dict, user_id: str | None = None) -> None:
    """価値観カードソートを保存（同一ユーザーは上書き）。"""
    if user_id is None:
        user_id = _owner_user_id()
    content_json = json.dumps(content or {}, ensure_ascii=False)
    sql = text("""
        INSERT INTO selfmap_values_sort (user_id, content, updated_at)
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


def load_values_sort(user_id: str | None = None) -> dict:
    """価値観カードソートを読み込む。無ければ空 dict。"""
    if user_id is None:
        user_id = _owner_user_id()
    sql = text(
        "SELECT content, updated_at FROM selfmap_values_sort "
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
