"""LangGraph 기반 특허 심사대응 에이전트.

그래프 흐름:
    START → tool1 → tool2 → tool3
          → review_chart (Claim Chart 검토)
          → tool4
          → review_strategy (전략 검토 + redo 루프)
          → tool5
          → review_amendment (보정안 검토 + redo 루프)
          → tool6 → END

Human-in-the-loop:
    review_* 노드에서 interrupt() 호출 → 사용자 입력 대기
    Command(resume=...) 패턴으로 재개

체크포인트:
    SqliteSaver → db/checkpoints.db (PatentDB와 분리)
"""

import sqlite3
from typing import Literal

from langfuse import observe
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

from pipeline import load_optimized_module, save_intermediate
from schemas.agent_state import AgentState
from schemas.common import MatchLevel
from schemas.tool1 import NoticeAnalysisInput
from schemas.tool2 import ClaimParseInput
from schemas.tool3 import ClaimChartInput
from schemas.tool4 import StrategyInput
from schemas.tool5 import AmendmentInput
from tools.tool1_notice_analyzer import NoticeAnalyzerTool
from tools.tool2_claim_parser import ClaimParserTool
from tools.tool3_claim_chart import ClaimChartTool
from tools.tool4_strategy import StrategyTool
from tools.tool5_amendment import AmendmentTool
from tools.tool6_version_manager import VersionManagerTool


# =============================================================================
# Tool 인스턴스 (모듈 레벨 캐시 — 최적화 모듈 포함)
# =============================================================================

_tools: dict = {}


def _get_tools() -> tuple:
    """Tool 인스턴스를 최초 1회 생성하여 캐시로 반환."""
    if not _tools:
        t1 = NoticeAnalyzerTool(); t1.module = load_optimized_module("tool1")
        t2 = ClaimParserTool();    t2.module = load_optimized_module("tool2")
        t3 = ClaimChartTool();     t3.module = load_optimized_module("tool3")
        t4 = StrategyTool();       t4.module = load_optimized_module("tool4")
        t5 = AmendmentTool();      t5.module = load_optimized_module("tool5")
        _tools.update({"t1": t1, "t2": t2, "t3": t3, "t4": t4, "t5": t5})
    return (_tools["t1"], _tools["t2"], _tools["t3"],
            _tools["t4"], _tools["t5"])


# =============================================================================
# 노드 함수
# =============================================================================

@observe()
def node_tool1(state: AgentState) -> dict:
    """노드 1: 통지서 분석."""
    tool1, *_ = _get_tools()
    try:
        result = tool1.run(NoticeAnalysisInput(
            notice_text=state["notice_text"],
            case_id=state["case_id"],
        ))
        dumped = result.model_dump()
        save_intermediate(state["case_id"], "tool1", dumped)
        print(f"  거절 유형: {result.rejection_type.value} | 법조항: {result.rejection_articles}")
        return {"tool1_result": dumped}
    except Exception as e:
        return {"error_message": f"Tool1 실패: {e}"}


@observe()
def node_tool2(state: AgentState) -> dict:
    """노드 2: 청구항 파싱 (당사 + 선행특허).

    가드레일: 당사 독립항 0개 → error_message 설정 → END 분기.
    """
    _, tool2, *_ = _get_tools()
    try:
        result_our = tool2.run(ClaimParseInput(claims_text=state["our_claims_text"]))

        if not result_our.independent_claims:
            return {"error_message": "독립항이 없습니다. 파이프라인 중단."}

        prior_parsed = []
        for pa in state["prior_art_claims"]:
            r = tool2.run(ClaimParseInput(claims_text=pa["claims_text"]))
            prior_parsed.append(r.model_dump())

        our_dumped = result_our.model_dump()
        save_intermediate(state["case_id"], "tool2",
                          {"our": our_dumped, "prior": prior_parsed})
        print(f"  당사 청구항: {result_our.total_claims}개 (독립항: {result_our.independent_claims})")
        return {"tool2_our": our_dumped, "tool2_prior": prior_parsed}
    except Exception as e:
        return {"error_message": f"Tool2 실패: {e}"}


@observe()
def node_tool3(state: AgentState) -> dict:
    """노드 3: Claim Chart 생성."""
    _, _, tool3, *_ = _get_tools()
    try:
        our_data = state.get("tool2_our") or {}
        our_independent = [
            c for c in our_data.get("claims", [])
            if c.get("claim_type") == "독립항"
        ]
        prior_independent = [
            c
            for pd in (state.get("tool2_prior") or [])
            for c in pd.get("claims", [])
            if c.get("claim_type") == "독립항"
        ]

        result = tool3.run(ClaimChartInput(
            our_claims=our_independent,
            prior_claims=prior_independent,
            our_description=state["our_description_text"],
        ))
        dumped = result.model_dump()
        save_intermediate(state["case_id"], "tool3", dumped)

        all_identical = all(
            em.match_level == MatchLevel.IDENTICAL
            for chart in result.charts
            for em in chart.element_matches
        )
        if all_identical:
            print("  경고: 모든 매칭이 '동일'입니다. 결과를 재검토하세요.")

        print(f"  {result.summary}")
        return {"tool3_result": dumped}
    except Exception as e:
        return {"error_message": f"Tool3 실패: {e}"}


def node_review_chart(state: AgentState) -> dict:
    """Human-in-the-loop: Claim Chart 검토.

    옵션: approve / exit
    approve → tool4, exit → END
    """
    t3 = state.get("tool3_result") or {}
    feedback = interrupt({
        "stage": "claim_chart",
        "summary": t3.get("summary", ""),
        "options": ["approve", "exit"],
    })
    return {"user_feedback": feedback}


@observe()
def node_tool4(state: AgentState) -> dict:
    """노드 4: 전략 생성.

    user_feedback이 자유 텍스트면 examiner_reasoning에 포함하여 LLM에 전달.
    """
    _, _, _, tool4, _ = _get_tools()
    try:
        t1 = state.get("tool1_result") or {}
        t3 = state.get("tool3_result") or {}

        unmatched, disputed = [], []
        for chart in t3.get("charts", []):
            for em in chart.get("element_matches", []):
                if em.get("match_level") == "없음":
                    unmatched.append(em.get("our_element", {}))
                elif em.get("match_level") == "유사":
                    disputed.append(em.get("our_element", {}))

        examiner_reasoning = t1.get("examiner_reasoning", "")
        feedback = state.get("user_feedback", "")
        if feedback and feedback not in ("approve", "redo_strategy",
                                         "redo_amendment", "exit"):
            examiner_reasoning = f"{examiner_reasoning}\n[사용자 지시]: {feedback}"

        result = tool4.run(StrategyInput(
            claim_chart_summary=t3.get("summary", ""),
            rejection_type=t1.get("rejection_type", "기타"),
            examiner_reasoning=examiner_reasoning,
            unmatched_elements=unmatched,
            disputed_elements=disputed,
        ))
        dumped = result.model_dump()
        save_intermediate(state["case_id"], "tool4", dumped)
        print(f"  반박 포인트: {len(result.rebuttal_points)}개")
        return {"tool4_result": dumped, "user_feedback": ""}
    except Exception as e:
        return {"error_message": f"Tool4 실패: {e}"}


def node_review_strategy(state: AgentState) -> dict:
    """Human-in-the-loop: 전략 검토.

    옵션: approve / redo_strategy / exit
    approve → tool5, redo_strategy → tool4 (재실행), exit → END
    """
    t4 = state.get("tool4_result") or {}
    feedback = interrupt({
        "stage": "strategy",
        "strategy": t4.get("strategy", ""),
        "rebuttal_points": t4.get("rebuttal_points", []),
        "options": ["approve", "redo_strategy", "exit"],
    })
    return {"user_feedback": feedback}


@observe()
def node_tool5(state: AgentState) -> dict:
    """노드 5: 보정안 생성.

    가드레일: 보정안 빈 문자열 → error_message 설정.
    user_feedback이 자유 텍스트면 strategy에 포함.
    """
    _, _, _, _, tool5 = _get_tools()
    try:
        our_data = state.get("tool2_our") or {}
        original_claim = ""
        for c in our_data.get("claims", []):
            if c.get("claim_type") == "독립항":
                original_claim = c.get("original_text", "")
                break

        t4 = state.get("tool4_result") or {}
        strategy = t4.get("strategy", "")
        feedback = state.get("user_feedback", "")
        if feedback and feedback not in ("approve", "redo_strategy",
                                         "redo_amendment", "exit"):
            strategy = f"{strategy}\n[사용자 지시]: {feedback}"

        result = tool5.run(AmendmentInput(
            original_claim=original_claim,
            strategy=strategy,
            description_text=state["our_description_text"],
        ))

        if not result.amended_claim.strip():
            return {"error_message": "보정안이 비어있습니다."}

        if result.amended_claim.strip() == original_claim.strip():
            print("  경고: 보정안이 원본과 동일합니다.")

        for w in result.warnings:
            print(f"  {w}")

        dumped = result.model_dump()
        save_intermediate(state["case_id"], "tool5", dumped)
        return {"tool5_result": dumped, "user_feedback": ""}
    except Exception as e:
        return {"error_message": f"Tool5 실패: {e}"}


def node_review_amendment(state: AgentState) -> dict:
    """Human-in-the-loop: 보정안 검토.

    옵션: approve / redo_amendment / redo_strategy / exit
    approve → tool6, redo_amendment → tool5, redo_strategy → tool4, exit → END
    """
    t5 = state.get("tool5_result") or {}
    feedback = interrupt({
        "stage": "amendment",
        "amended_claim": t5.get("amended_claim", ""),
        "diff_text": t5.get("diff_text", ""),
        "options": ["approve", "redo_amendment", "redo_strategy", "exit"],
    })
    return {"user_feedback": feedback}


@observe()
def node_tool6(state: AgentState) -> dict:
    """노드 6: 차수 저장."""
    tool6 = VersionManagerTool()
    t1 = state.get("tool1_result") or {}
    t4 = state.get("tool4_result") or {}
    t5 = state.get("tool5_result") or {}
    our_claims = (state.get("tool2_our") or {}).get("claims", [])

    version = tool6.save_version(
        case_id=state["case_id"],
        rejection_summary=t1.get("examiner_reasoning", ""),
        strategy_summary=t4.get("strategy", "")[:500],
        original_claim=our_claims[0].get("original_text", "") if our_claims else "",
        amended_claim=t5.get("amended_claim", ""),
        diff_text=t5.get("diff_text", ""),
    )
    print(f"  차수 {version.version} 저장 완료 ({version.timestamp})")
    return {}


# =============================================================================
# 조건부 엣지
# =============================================================================

def _route_on_error(state: AgentState, next_node: str) -> str:
    if state.get("error_message"):
        return END
    return next_node


def route_after_tool1(state: AgentState) -> Literal["tool2", "__end__"]:
    return _route_on_error(state, "tool2")


def route_after_tool2(state: AgentState) -> Literal["tool3", "__end__"]:
    return _route_on_error(state, "tool3")


def route_after_tool3(state: AgentState) -> Literal["review_chart", "__end__"]:
    return _route_on_error(state, "review_chart")


def route_after_tool4(state: AgentState) -> Literal["review_strategy", "__end__"]:
    return _route_on_error(state, "review_strategy")


def route_after_tool5(state: AgentState) -> Literal["review_amendment", "__end__"]:
    return _route_on_error(state, "review_amendment")


def route_after_chart_review(state: AgentState) -> Literal["tool4", "__end__"]:
    feedback = state.get("user_feedback", "approve")
    if feedback == "exit":
        return END
    return "tool4"


def route_after_strategy_review(
    state: AgentState,
) -> Literal["tool5", "tool4", "__end__"]:
    feedback = state.get("user_feedback", "approve")
    if feedback == "redo_strategy":
        return "tool4"
    if feedback == "exit":
        return END
    return "tool5"


def route_after_amendment_review(
    state: AgentState,
) -> Literal["tool6", "tool5", "tool4", "__end__"]:
    feedback = state.get("user_feedback", "approve")
    if feedback == "redo_amendment":
        return "tool5"
    if feedback == "redo_strategy":
        return "tool4"
    if feedback == "exit":
        return END
    return "tool6"


# =============================================================================
# 그래프 빌드
# =============================================================================

def build_graph(checkpoint_db: str = "db/checkpoints.db"):
    """LangGraph 그래프를 빌드하고 반환.

    Args:
        checkpoint_db: SqliteSaver DB 경로 (PatentDB와 분리)

    Returns:
        컴파일된 CompiledGraph
    """
    graph = StateGraph(AgentState)

    # 노드 등록
    graph.add_node("tool1", node_tool1)
    graph.add_node("tool2", node_tool2)
    graph.add_node("tool3", node_tool3)
    graph.add_node("review_chart", node_review_chart)
    graph.add_node("tool4", node_tool4)
    graph.add_node("review_strategy", node_review_strategy)
    graph.add_node("tool5", node_tool5)
    graph.add_node("review_amendment", node_review_amendment)
    graph.add_node("tool6", node_tool6)

    # 엣지
    graph.add_edge(START, "tool1")
    graph.add_conditional_edges("tool1", route_after_tool1,
                                {"tool2": "tool2", END: END})
    graph.add_conditional_edges("tool2", route_after_tool2,
                                {"tool3": "tool3", END: END})
    graph.add_conditional_edges("tool3", route_after_tool3,
                                {"review_chart": "review_chart", END: END})
    graph.add_conditional_edges("review_chart", route_after_chart_review,
                                {"tool4": "tool4", END: END})
    graph.add_conditional_edges("tool4", route_after_tool4,
                                {"review_strategy": "review_strategy", END: END})
    graph.add_conditional_edges("review_strategy", route_after_strategy_review,
                                {"tool5": "tool5", "tool4": "tool4", END: END})
    graph.add_conditional_edges("tool5", route_after_tool5,
                                {"review_amendment": "review_amendment", END: END})
    graph.add_conditional_edges("review_amendment", route_after_amendment_review,
                                {"tool6": "tool6", "tool5": "tool5",
                                 "tool4": "tool4", END: END})
    graph.add_edge("tool6", END)

    # SqliteSaver — PatentDB(patent_agent.db)와 다른 파일
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return graph.compile(checkpointer=checkpointer)
