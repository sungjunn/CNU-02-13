"""DB 테이블에 대응하는 Pydantic 모델.
SQLite 테이블 생성과 데이터 검증에 모두 사용."""

from pydantic import BaseModel
from typing import Optional


class PatentDocument(BaseModel):
    """특허 문서 (당사 특허 또는 선행특허)"""
    doc_id: str                        # 고유 ID (예: "KR10-1234567")
    doc_type: str                      # "our_patent" | "prior_art"
    title: str
    claims_text: str                   # 청구항 전문
    description_text: str              # 상세설명 전문
    filing_date: Optional[str] = None
    created_at: str = ""               # DB 저장 시 자동 생성


class OfficeAction(BaseModel):
    """의견제출통지서"""
    action_id: str                     # 고유 ID
    our_patent_id: str                 # 대상 당사 특허 doc_id (FK)
    notice_text: str                   # 통지서 전문
    prior_art_ids: list[str]           # 인용된 선행특허 doc_id 리스트
    received_date: Optional[str] = None


class CaseRecord(BaseModel):
    """심사대응 케이스 (통지서 1건 = 케이스 1건)"""
    case_id: str
    action_id: str                     # 의견제출통지서 ID (FK)
    our_patent_id: str                 # 당사 특허 ID (FK)
    status: str = "in_progress"        # in_progress | completed
    created_at: str = ""


class EvalDataset(BaseModel):
    """검증셋 레코드"""
    eval_id: str
    case_id: str                       # 어떤 케이스의 검증셋인지
    tool_name: str                     # "tool1", "tool2", ...
    expected_json: str                 # 정답 JSON (문자열로 저장)
    eval_type: str                     # "exact_match" | "checklist"
