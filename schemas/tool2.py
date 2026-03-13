"""Tool 2 — 청구항 파싱 입출력 스키마.

청구항 텍스트를 개별 청구항으로 분리하고,
각 청구항을 구성요소 단위로 파싱한다."""

from pydantic import BaseModel
from schemas.common import ClaimElement, ClaimType


class ClaimParseInput(BaseModel):
    """Tool 2 입력"""
    claims_text: str                       # 청구항 전문 텍스트


class ParsedClaim(BaseModel):
    """파싱된 개별 청구항"""
    claim_number: int                      # 청구항 번호
    claim_type: ClaimType                  # 독립항 / 종속항
    depends_on: int | None = None          # 종속항이 참조하는 청구항 번호
    original_text: str                     # 원문 텍스트
    elements: list[ClaimElement]           # 구성요소 리스트


class ClaimParseOutput(BaseModel):
    """Tool 2 출력"""
    total_claims: int                      # 총 청구항 수
    independent_claims: list[int]          # 독립항 번호 리스트
    dependent_claims: dict[str, int]       # {"종속항번호": 참조청구항번호}
    claims: list[ParsedClaim]              # 파싱된 청구항 리스트
