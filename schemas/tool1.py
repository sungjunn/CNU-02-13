"""Tool 1 — 통지서 분석 입출력 스키마.

의견제출통지서를 분석하여 거절이유, 법조항, 선행특허 정보를 추출한다.
정규식(확정적 데이터)과 LLM(요약)의 결과가 합쳐진 최종 출력."""

from pydantic import BaseModel
from schemas.common import RejectionType


class NoticeAnalysisInput(BaseModel):
    """Tool 1 입력"""
    notice_text: str                       # 의견제출통지서 원문 텍스트
    case_id: str = ""                      # 케이스 ID (옵션)


class RejectionDetail(BaseModel):
    """개별 거절이유 상세"""
    rejection_type: RejectionType          # 신규성 / 진보성 / 기타
    legal_basis: str                       # 법조항 (예: "제29조 제2항")
    target_claims: list[int]               # 해당 청구항 번호 리스트
    prior_art_ids: list[str]               # 관련 선행특허 번호
    summary: str                           # 거절이유 요약 (LLM 생성)


class NoticeAnalysisOutput(BaseModel):
    """Tool 1 출력 — 정규식 결과 + LLM 요약 통합"""
    rejection_articles: list[str]          # 거절 법조항 리스트 (정규식)
    prior_art_numbers: list[str]           # 선행특허 번호 리스트 (정규식)
    rejected_claim_numbers: list[int]      # 거절 대상 청구항 번호 (정규식)
    rejection_type: RejectionType          # 주된 거절 유형 (정규식 → 자동 분류)
    examiner_reasoning: str                # 심사관 거절 논리 요약 (LLM)
    rejection_details: list[RejectionDetail]  # 거절이유별 상세 분석 (LLM)
