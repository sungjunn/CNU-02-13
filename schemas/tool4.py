"""Tool 4 — 차이점 분석 + 전략 생성 입출력 스키마.

Claim Chart 결과를 바탕으로 선행특허와의 차이점을 분석하고
거절 유형에 맞는 대응 전략을 생성한다."""

from pydantic import BaseModel
from schemas.common import RejectionType


class RebuttalPoint(BaseModel):
    """반박 포인트 하나"""
    point: str                             # 반박 내용
    basis: str                             # 근거 (상세설명 인용 등)
    strength: str = "중"                   # 강/중/약


class StrategyInput(BaseModel):
    """Tool 4 입력"""
    claim_chart_summary: str               # Claim Chart 요약
    rejection_type: RejectionType          # 거절 유형
    examiner_reasoning: str                # 심사관 거절 논리 요약
    unmatched_elements: list[dict]         # 매칭 "없음"인 구성요소
    disputed_elements: list[dict]          # 매칭 "유사"인 구성요소


class StrategyOutput(BaseModel):
    """Tool 4 출력"""
    differences: list[dict]                # 요소별 차이 분석 [{element, diff_desc, effect}]
    strategy: str                          # 대응 전략 텍스트 (LLM 생성)
    rebuttal_points: list[RebuttalPoint]   # 반박 포인트 리스트
