"""에이전트 실행기.

사용법:
    uv run python run_agent.py --case case_01

동작:
1. DSPy LM 설정
2. Langfuse + OpenInference DSPy instrumentation 설정 (API 키 있을 때만)
3. LangGraph 그래프 실행
4. review_* 노드에서 interrupt 시 사용자 입력 대기
5. Command(resume=...) 패턴으로 재개

Human-in-the-loop 옵션:
    review_chart:     approve / exit
    review_strategy:  approve / redo_strategy / exit
    review_amendment: approve / redo_amendment / redo_strategy / exit

    redo 선택 시 추가 지시 텍스트 입력 가능 (Enter면 생략).
"""

import argparse
import os

from dotenv import load_dotenv
from langgraph.types import Command

from agent import build_graph
from pipeline import load_case_data, setup_lm


# =============================================================================
# Langfuse + OpenInference 설정
# =============================================================================

def setup_observability():
    """Langfuse + OpenInference DSPy instrumentation 설정.

    LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY 있을 때만 활성화.
    패키지 없으면 경고 후 스킵.
    """
    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")

    if not (pk and sk):
        print("[Langfuse] API 키 미설정 — 트레이싱 비활성화")
        return

    try:
        import base64
        from openinference.instrumentation.dspy import DSPyInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry import trace

        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
        exporter = OTLPSpanExporter(
            endpoint=f"{host}/api/public/otel/v1/traces",
            headers={"Authorization": f"Basic {auth}"},
        )

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # DSPy 내부 LLM 호출 전체 추적
        DSPyInstrumentor().instrument()
        print("[Langfuse] 트레이싱 활성화")

    except ImportError as e:
        print(f"[Langfuse] 패키지 없음 — 트레이싱 비활성화: {e}")


# =============================================================================
# 실행기
# =============================================================================

def run_agent(case_id: str, checkpoint_db: str = "db/checkpoints.db"):
    """에이전트 실행.

    Args:
        case_id: 케이스 ID (예: "case_01")
        checkpoint_db: SqliteSaver DB 경로
    """
    data = load_case_data(case_id)
    graph = build_graph(checkpoint_db)

    # pydantic 객체 역직렬화 경고 제거 (보안 허용 목록 등록)
    config = {
        "configurable": {
            "thread_id": case_id,
        }
    }

    initial_state = {
        "case_id": case_id,
        "notice_text": data["notice_text"],
        "our_claims_text": data["our_claims_text"],
        "our_description_text": data["our_description_text"],
        "prior_art_claims": data["prior_art_claims"],
        "user_feedback": "",
        "error_message": None,
        "tool1_result": None,
        "tool2_our": None,
        "tool2_prior": None,
        "tool3_result": None,
        "tool4_result": None,
        "tool5_result": None,
    }

    print(f"\n{'='*60}")
    print(f"  특허 심사대응 에이전트 — 케이스: {case_id}")
    print(f"{'='*60}\n")

    # 초기 실행 (첫 번째 interrupt까지)
    _stream_until_interrupt(graph, initial_state, config)

    # Human-in-the-loop 루프
    while True:
        state = graph.get_state(config)

        # 더 이상 중단점 없으면 종료
        if not state.next:
            break

        # 현재 중단 노드 확인
        interrupted_node = state.next[0] if state.next else ""
        vals = state.values

        _print_review_context(interrupted_node, vals)

        options = _get_options(interrupted_node)
        print(f"옵션: {' / '.join(options)}")

        user_input = _get_user_input(options)
        if user_input is None:
            continue

        # redo 선택 시 추가 지시 텍스트 입력
        feedback = user_input
        if user_input in ("redo_strategy", "redo_amendment"):
            detail = input("수정 지시 입력 (없으면 Enter) > ").strip()
            if detail:
                feedback = detail  # 자유 텍스트로 LLM에 전달

        # 재개
        _stream_until_interrupt(graph, Command(resume=feedback), config)

        if user_input == "exit":
            break

    print(f"\n{'='*60}")
    print("  에이전트 완료!")
    print(f"{'='*60}\n")


def _stream_until_interrupt(graph, input_or_command, config: dict):
    """그래프를 스트림 실행하며 노드 완료를 출력."""
    for event in graph.stream(input_or_command, config=config,
                               stream_mode="updates"):
        for node_name, result in event.items():
            if not isinstance(result, dict):
                continue
            err = result.get("error_message")
            if err:
                print(f"  ❌ {node_name}: {err}")
                return
            if node_name not in ("review_chart", "review_strategy",
                                  "review_amendment"):
                print(f"  ✓ {node_name} 완료")


def _print_review_context(node: str, vals: dict):
    """현재 검토 단계에 맞는 결과 요약 출력."""
    print(f"\n{'─'*60}")
    if node == "review_chart":
        t3 = vals.get("tool3_result") or {}
        print(f"[Claim Chart 요약]\n{t3.get('summary', '없음')}")

    elif node == "review_strategy":
        t4 = vals.get("tool4_result") or {}
        print(f"[전략]\n{t4.get('strategy', '없음')[:500]}")
        pts = t4.get("rebuttal_points", [])
        if pts:
            print(f"[반박 포인트] {pts}")

    elif node == "review_amendment":
        t5 = vals.get("tool5_result") or {}
        print(f"[보정안]\n{t5.get('amended_claim', '없음')[:500]}")
        diff = t5.get("diff_text", "")
        if diff:
            print(f"[Diff]\n{diff[:300]}")
    print(f"{'─'*60}")


def _get_options(node: str) -> list[str]:
    mapping = {
        "review_chart":     ["approve", "exit"],
        "review_strategy":  ["approve", "redo_strategy", "exit"],
        "review_amendment": ["approve", "redo_amendment", "redo_strategy", "exit"],
    }
    return mapping.get(node, ["approve", "exit"])


def _get_user_input(options: list[str]) -> str | None:
    raw = input("선택 > ").strip().lower()
    if raw not in options:
        print(f"  잘못된 입력입니다. ({' / '.join(options)})")
        return None
    return raw


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="특허 심사대응 에이전트")
    parser.add_argument("--case", required=True, help="케이스 ID (예: case_01)")
    parser.add_argument("--checkpoint-db", default="db/checkpoints.db",
                        help="SqliteSaver DB 경로 (기본: db/checkpoints.db)")
    args = parser.parse_args()

    load_dotenv()
    setup_lm()
    setup_observability()

    run_agent(args.case, args.checkpoint_db)


if __name__ == "__main__":
    main()
