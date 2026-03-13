"""Tool 5 — 보정안 생성 입출력 스키마.

대응 전략에 따라 보정된 독립항 초안을 생성한다.
상세설명 근거 확인 + diff 생성까지 포함."""

from pydantic import BaseModel
from schemas.common import ClaimElement


class DescriptionBasis(BaseModel):
    """보정 근거 — 상세설명의 관련 단락"""
    paragraph: str                         # 상세설명 단락 텍스트
    relevance: str                         # 관련성 설명


class AmendmentInput(BaseModel):
    """Tool 5 입력"""
    original_claim: str                    # 원본 독립항 전문
    strategy: str                          # 대응 전략 텍스트
    description_text: str                  # 당사 상세설명 전문


class AmendmentOutput(BaseModel):
    """Tool 5 출력"""
    amended_claim: str                     # 보정된 청구항 전문
    added_elements: list[ClaimElement]     # 추가된 구성요소 리스트
    description_basis: list[DescriptionBasis]  # 보정 근거 상세설명 단락
    diff_text: str                         # 원본 vs 보정본 diff
    warnings: list[str] = []               # 경고 메시지 (근거 없는 보정 등)
