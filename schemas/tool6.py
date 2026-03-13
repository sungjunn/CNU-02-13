"""Tool 6 — 차수 관리 입출력 스키마.

100% 코드 기반 (DSPy 미사용).
차수별 심사대응 결과를 저장/로드하고 diff를 생성한다."""

from pydantic import BaseModel
from typing import Optional


class VersionRecord(BaseModel):
    """차수별 결과 레코드"""
    version: int                           # 차수 번호 (1, 2, 3, ...)
    timestamp: str                         # 저장 시각 (ISO 8601)
    case_id: str                           # 케이스 ID
    rejection_summary: str                 # 거절이유 요약
    strategy_summary: str                  # 전략 요약
    original_claim: str                    # 원본 청구항
    amended_claim: str                     # 보정된 청구항
    diff_text: str                         # 원본 vs 보정본 diff
    notes: str = ""                        # 메모


class VersionHistory(BaseModel):
    """차수 이력 전체"""
    case_id: str
    versions: list[VersionRecord]
    latest_version: int = 0
    diff_between_versions: Optional[str] = None  # 직전 차수와의 diff
