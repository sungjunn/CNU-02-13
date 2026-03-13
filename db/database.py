"""SQLite 기반 특허 데이터 관리.

ORM 없이 직접 SQL 작성. 간단한 CRUD 중심.
테이블은 첫 연결 시 자동 생성된다."""

import sqlite3
import json
from datetime import datetime
from typing import Optional

from schemas.db_models import PatentDocument, OfficeAction, CaseRecord, EvalDataset


# === 테이블 생성 SQL ===
_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS patent_documents (
    doc_id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,          -- 'our_patent' 또는 'prior_art'
    title TEXT NOT NULL,
    claims_text TEXT NOT NULL,
    description_text TEXT NOT NULL,
    filing_date TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS office_actions (
    action_id TEXT PRIMARY KEY,
    our_patent_id TEXT NOT NULL,
    notice_text TEXT NOT NULL,
    prior_art_ids TEXT NOT NULL,     -- JSON 배열 문자열
    received_date TEXT,
    FOREIGN KEY (our_patent_id) REFERENCES patent_documents(doc_id)
);

CREATE TABLE IF NOT EXISTS case_records (
    case_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    our_patent_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress',
    created_at TEXT NOT NULL,
    FOREIGN KEY (action_id) REFERENCES office_actions(action_id),
    FOREIGN KEY (our_patent_id) REFERENCES patent_documents(doc_id)
);

CREATE TABLE IF NOT EXISTS eval_datasets (
    eval_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    expected_json TEXT NOT NULL,
    eval_type TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES case_records(case_id)
);
"""


class PatentDB:
    """SQLite 기반 특허 데이터 관리.

    사용법:
        db = PatentDB("db/patent_agent.db")
        db.insert_patent(PatentDocument(...))
        doc = db.get_patent("KR10-1234567")
    """

    def __init__(self, db_path: str = "db/patent_agent.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """테이블이 없으면 생성"""
        self.conn.executescript(_CREATE_TABLES)
        self.conn.commit()

    def close(self):
        """DB 연결 종료"""
        self.conn.close()

    # === 문서 CRUD ===

    def insert_patent(self, doc: PatentDocument):
        """특허 문서 삽입"""
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT OR REPLACE INTO patent_documents
               (doc_id, doc_type, title, claims_text, description_text, filing_date, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (doc.doc_id, doc.doc_type, doc.title, doc.claims_text,
             doc.description_text, doc.filing_date, now),
        )
        self.conn.commit()

    def get_patent(self, doc_id: str) -> Optional[PatentDocument]:
        """특허 문서 조회. 없으면 None 반환."""
        row = self.conn.execute(
            "SELECT * FROM patent_documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return None
        return PatentDocument(**dict(row))

    def list_patents(self, doc_type: str = None) -> list[PatentDocument]:
        """특허 문서 목록 조회. doc_type 필터 가능."""
        if doc_type:
            rows = self.conn.execute(
                "SELECT * FROM patent_documents WHERE doc_type = ?", (doc_type,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM patent_documents").fetchall()
        return [PatentDocument(**dict(r)) for r in rows]

    # === 통지서 CRUD ===

    def insert_office_action(self, action: OfficeAction):
        """의견제출통지서 삽입"""
        self.conn.execute(
            """INSERT OR REPLACE INTO office_actions
               (action_id, our_patent_id, notice_text, prior_art_ids, received_date)
               VALUES (?, ?, ?, ?, ?)""",
            (action.action_id, action.our_patent_id, action.notice_text,
             json.dumps(action.prior_art_ids, ensure_ascii=False), action.received_date),
        )
        self.conn.commit()

    def get_office_action(self, action_id: str) -> Optional[OfficeAction]:
        """통지서 조회. 없으면 None 반환."""
        row = self.conn.execute(
            "SELECT * FROM office_actions WHERE action_id = ?", (action_id,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["prior_art_ids"] = json.loads(d["prior_art_ids"])
        return OfficeAction(**d)

    # === 케이스 관리 ===

    def create_case(self, case: CaseRecord):
        """케이스 생성"""
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT OR REPLACE INTO case_records
               (case_id, action_id, our_patent_id, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (case.case_id, case.action_id, case.our_patent_id, case.status, now),
        )
        self.conn.commit()

    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        """케이스 조회. 없으면 None 반환."""
        row = self.conn.execute(
            "SELECT * FROM case_records WHERE case_id = ?", (case_id,)
        ).fetchone()
        if row is None:
            return None
        return CaseRecord(**dict(row))

    def list_cases(self) -> list[CaseRecord]:
        """전체 케이스 목록 조회"""
        rows = self.conn.execute("SELECT * FROM case_records").fetchall()
        return [CaseRecord(**dict(r)) for r in rows]

    # === 검증셋 ===

    def insert_eval(self, eval_data: EvalDataset):
        """검증셋 레코드 삽입"""
        self.conn.execute(
            """INSERT OR REPLACE INTO eval_datasets
               (eval_id, case_id, tool_name, expected_json, eval_type)
               VALUES (?, ?, ?, ?, ?)""",
            (eval_data.eval_id, eval_data.case_id, eval_data.tool_name,
             eval_data.expected_json, eval_data.eval_type),
        )
        self.conn.commit()

    def get_evals_for_tool(self, tool_name: str) -> list[EvalDataset]:
        """특정 Tool의 검증셋 조회"""
        rows = self.conn.execute(
            "SELECT * FROM eval_datasets WHERE tool_name = ?", (tool_name,)
        ).fetchall()
        return [EvalDataset(**dict(r)) for r in rows]

    def get_evals_for_case(self, case_id: str) -> list[EvalDataset]:
        """특정 케이스의 검증셋 조회"""
        rows = self.conn.execute(
            "SELECT * FROM eval_datasets WHERE case_id = ?", (case_id,)
        ).fetchall()
        return [EvalDataset(**dict(r)) for r in rows]
