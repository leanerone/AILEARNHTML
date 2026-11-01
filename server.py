"""EAP 工程师能力测评 · 本地服务（FastAPI + SQLite）

启动：  python server.py        →  浏览器打开 http://127.0.0.1:8090
数据：  assessment.db（与脚本同目录的 SQLite 单文件，备份 = 直接复制它）
依赖：  pip install -r requirements.txt

接口一览（前端「复盘」页在用，也可用 curl/浏览器直接调）：
  POST   /api/attempts            保存一次测评记录
  GET    /api/attempts            记录列表（复盘趋势用）
  GET    /api/attempts/{id}       单条详情（含完整答卷与各板块得分）
  PATCH  /api/attempts/{id}       回填批改结果 { finalScore, reviewNotes }
  DELETE /api/attempts/{id}       删除某次记录
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_PATH = BASE / "assessment.db"

app = FastAPI(title="EAP 能力测评")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at       TEXT    NOT NULL,
                quiz_version     TEXT,
                minutes_spent    INTEGER,
                answered_total   INTEGER,
                total_questions  INTEGER,
                objective_score  INTEGER,   -- 浏览器自动判分的客观题正确数
                objective_total  INTEGER,   -- 客观题总数
                final_score      INTEGER,   -- 批改后的最终正确数（含简答，复盘时回填，可空）
                review_notes     TEXT,      -- 批改备注（可空）
                payload          TEXT NOT NULL  -- 完整答卷 JSON（answers 含自评/偏好/简答原文）
            );
            CREATE TABLE IF NOT EXISTS attempt_sections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id  INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
                section_id  TEXT,
                section_name TEXT,
                correct     INTEGER,
                total       INTEGER,
                answered    INTEGER
            );
            """
        )


class AttemptIn(BaseModel):
    quizVersion: str = ""
    minutesSpent: int = 0
    answeredOfTotal: str = ""
    sectionScores: List[dict] = []
    answers: dict = {}
    exportedAt: str = ""
    extra: Any = None


class ReviewIn(BaseModel):
    finalScore: Optional[int] = None
    reviewNotes: str = ""


@app.post("/api/attempts")
def save_attempt(a: AttemptIn):
    answered, total = _parse_answered(a.answeredOfTotal)
    obj_score = sum(int(s.get("correct", 0) or 0) for s in a.sectionScores)
    obj_total = sum(int(s.get("total", 0) or 0) for s in a.sectionScores)
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = json.dumps(a.model_dump(), ensure_ascii=False)
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO attempts
               (created_at, quiz_version, minutes_spent, answered_total, total_questions,
                objective_score, objective_total, payload)
               VALUES (?,?,?,?,?,?,?,?)""",
            (created, a.quizVersion, a.minutesSpent, answered, total, obj_score, obj_total, payload),
        )
        attempt_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO attempt_sections
               (attempt_id, section_id, section_name, correct, total, answered)
               VALUES (?,?,?,?,?,?)""",
            [
                (attempt_id, s.get("sectionId"), s.get("section"), s.get("correct"), s.get("total"), s.get("answered"))
                for s in a.sectionScores
            ],
        )
    return {"id": attempt_id, "savedAt": created}


@app.get("/api/attempts")
def list_attempts():
    with db() as conn:
        rows = conn.execute(
            """SELECT id, created_at, quiz_version, minutes_spent, answered_total,
                      total_questions, objective_score, objective_total, final_score
               FROM attempts ORDER BY id DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/attempts/{attempt_id}")
def get_attempt(attempt_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "记录不存在")
        sections = conn.execute(
            "SELECT section_id, section_name, correct, total, answered FROM attempt_sections WHERE attempt_id=?",
            (attempt_id,),
        ).fetchall()
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    d["sections"] = [dict(s) for s in sections]
    return d


@app.patch("/api/attempts/{attempt_id}")
def review_attempt(attempt_id: int, r: ReviewIn):
    with db() as conn:
        cur = conn.execute(
            "UPDATE attempts SET final_score=?, review_notes=? WHERE id=?",
            (r.finalScore, r.reviewNotes or None, attempt_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "记录不存在")
    return {"ok": True}


@app.delete("/api/attempts/{attempt_id}")
def delete_attempt(attempt_id: int):
    with db() as conn:
        cur = conn.execute("DELETE FROM attempts WHERE id=?", (attempt_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "记录不存在")
    return {"ok": True}


def _parse_answered(s: str) -> tuple:
    try:
        a, b = str(s).split("/")
        return int(a.strip()), int(b.strip())
    except Exception:
        return 0, 0


@app.get("/")
def index():
    return FileResponse(BASE / "index.html")


@app.get("/questions.js")
def questions_js():
    return FileResponse(BASE / "questions.js", media_type="application/javascript")


init_db()

if __name__ == "__main__":
    print("EAP 能力测评已启动：http://127.0.0.1:8090   （数据文件 assessment.db）")
    uvicorn.run(app, host="127.0.0.1", port=8090, log_level="warning")
