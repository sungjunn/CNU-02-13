"""공통 타입 정의 — 여러 Tool에서 공유하는 기본 모델."""

from enum import Enum
from pydantic import BaseModel


class MatchLevel(str, Enum):
    """구성요소 매칭 수준 (Claim Chart에서 사용)"""
    IDENTICAL = "동일"      # 실질적으로 같은 기술 내용
    SIMILAR = "유사"        # 관련은 있으나 차이 존재
    ABSENT = "없음"         # 대응 요소 없음


class RejectionType(str, Enum):
    """거절 유형 — 법조항 기반 자동 분류"""
    NOVELTY = "신규성"          # 제29조 제1항 — 동일 선행기술 존재
    INVENTIVE_STEP = "진보성"   # 제29조 제2항 — 선행기술 조합으로 용이 도출
    UNKNOWN = "기타"            # 기타 법조항


class ClaimElement(BaseModel):
    """청구항 구성요소 하나.

    독립항을 세미콜론(;)으로 분리하면 나오는 기술적 구성 단위.
    예: "트레드부에 형성된 홈 패턴", "사이드월부" 등"""
    element_id: str           # 구성요소 ID (예: "e1", "e2")
    text: str                 # 구성요소 원문 텍스트
    label: str = ""           # 한국어 의미 라벨 (LLM이 부여)


class ClaimType(str, Enum):
    """청구항 유형"""
    INDEPENDENT = "독립항"
    DEPENDENT = "종속항"
