"""Tool 3 — Claim Chart 생성 입출력 스키마.

당사 청구항과 선행특허 청구항의 구성요소를 1:1 비교하여
매칭 수준(동일/유사/없음)을 판정한다."""

from pydantic import BaseModel
from schemas.common import ClaimElement, MatchLevel


class ElementMatch(BaseModel):
    """구성요소 매칭 결과 하나"""
    our_element: ClaimElement              # 당사 구성요소
    prior_element: ClaimElement | None     # 선행특허 대응 구성요소 (없음이면 None)
    match_level: MatchLevel                # 동일 / 유사 / 없음
    reasoning: str                         # 판정 근거 (LLM 생성)


class ClaimChartEntry(BaseModel):
    """청구항 쌍 하나에 대한 Claim Chart"""
    our_claim_number: int                  # 당사 청구항 번호
    prior_claim_number: int                # 선행특허 청구항 번호
    element_matches: list[ElementMatch]    # 구성요소별 매칭 결과


class ClaimChartInput(BaseModel):
    """Tool 3 입력"""
    our_claims: list[dict]                 # 당사 파싱된 청구항 (ParsedClaim.model_dump())
    prior_claims: list[dict]               # 선행특허 파싱된 청구항
    our_description: str                   # 당사 상세설명 (매칭 근거 참조용)


class ClaimChartOutput(BaseModel):
    """Tool 3 출력"""
    charts: list[ClaimChartEntry]          # 청구항 쌍별 Claim Chart
    summary: str                           # 전체 매칭 요약 (코드 생성)
