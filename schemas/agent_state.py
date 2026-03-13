"""LangGraph AgentState 정의.

파이프라인 전체 상태를 담는 TypedDict.
모든 Tool 결과 필드는 초기값 None.
"""

from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """특허 심사대응 에이전트 전체 상태."""

    # 케이스 식별자
    case_id: str

    # 입력 데이터 (load_case_data에서 채움)
    notice_text: str
    our_claims_text: str
    our_description_text: str
    prior_art_claims: list[dict]

    # Tool 결과 (초기값 None)
    tool1_result: Optional[dict]   # NoticeAnalysisOutput
    tool2_our: Optional[dict]      # ClaimParseOutput (당사)
    tool2_prior: Optional[list]    # list[ClaimParseOutput] (선행특허)
    tool3_result: Optional[dict]   # ClaimChartOutput
    tool4_result: Optional[dict]   # StrategyOutput
    tool5_result: Optional[dict]   # AmendmentOutput

    # Human-in-the-loop 피드백
    # "approve" | "redo_strategy" | "redo_amendment" | "exit" | 자유 텍스트
    user_feedback: str

    # 가드레일 위반 또는 Tool 실패 메시지 — 있으면 즉시 END
    error_message: Optional[str]
