"""eval 실행 스크립트.

사용법:
    uv run python -m evals.eval_runner --tool tool1 --case case_01
    uv run python -m evals.eval_runner --all --case case_01

동작:
1. DB에서 해당 case의 입력 데이터 + 검증셋 로드
2. 현재 Module로 Tool 실행
3. metric 함수로 점수 계산
4. 결과를 evals/results/ 에 JSON으로 저장
"""

import argparse
import json
import os
from datetime import datetime

import dspy

from evals.datasets import load_eval_dataset
from evals.metrics import (
    tool1_metric, tool2_metric, tool3_metric,
    tool4_metric, tool5_metric,
)

# Tool별 metric 매핑
_METRICS = {
    "tool1": tool1_metric,
    "tool2": tool2_metric,
    "tool3": tool3_metric,
    "tool4": tool4_metric,
    "tool5": tool5_metric,
}

# Tool별 Module 가져오기
_MODULES = {
    "tool1": lambda: __import__("modules.tool1_module", fromlist=["NoticeAnalyzerModule"]).NoticeAnalyzerModule(),
    "tool2": lambda: __import__("modules.tool2_module", fromlist=["ClaimParserModule"]).ClaimParserModule(),
    "tool3": lambda: __import__("modules.tool3_module", fromlist=["ClaimChartModule"]).ClaimChartModule(),
    "tool4": lambda: __import__("modules.tool4_module", fromlist=["StrategyModule"]).StrategyModule(),
    "tool5": lambda: __import__("modules.tool5_module", fromlist=["AmendmentModule"]).AmendmentModule(),
}


def evaluate_tool(tool_name: str, case_id: str = None, db_path: str = "db/patent_agent.db"):
    """특정 Tool을 평가하고 결과를 저장.

    Args:
        tool_name: "tool1" ~ "tool5"
        case_id: 특정 케이스만 평가 (None이면 전체)
        db_path: DB 파일 경로

    Returns:
        평가 결과 dict
    """
    print(f"\n=== {tool_name} 평가 시작 ===")

    # 검증셋 로드
    dataset = load_eval_dataset(tool_name, db_path)
    if not dataset:
        print(f"[경고] {tool_name}의 검증셋이 없습니다.")
        return None

    # Module 생성
    module = _MODULES[tool_name]()
    metric = _METRICS[tool_name]

    # 평가 실행
    scores = []
    failures = []

    for i, example in enumerate(dataset):
        try:
            # Module 실행 (with_inputs()에 지정된 필드만 전달)
            input_fields = dict(example.inputs())
            prediction = module(**input_fields)

            # metric 계산
            score = metric(example, prediction)
            scores.append(score)

            print(f"  [{i+1}/{len(dataset)}] 점수: {score:.2f}")

            if score < 1.0:
                failures.append({
                    "index": i,
                    "score": score,
                    "example_keys": list(example.keys()),
                })

        except Exception as e:
            print(f"  [{i+1}/{len(dataset)}] 오류: {e}")
            scores.append(0.0)
            failures.append({"index": i, "error": str(e)})

    # 결과 구성
    overall_score = sum(scores) / len(scores) if scores else 0.0
    current_lm = dspy.settings.lm
    model_name = getattr(current_lm, "model", "unknown") if current_lm else "unknown"

    result = {
        "tool": tool_name,
        "case": case_id or "all",
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "overall_score": round(overall_score, 4),
        "num_examples": len(dataset),
        "scores": [round(s, 4) for s in scores],
        "failures": failures,
    }

    # 결과 저장
    result_dir = "evals/results"
    os.makedirs(result_dir, exist_ok=True)
    result_path = os.path.join(
        result_dir,
        f"{tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n총점: {overall_score:.2f} ({len(dataset)}건)")
    print(f"결과 저장: {result_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Tool별 평가 실행")
    parser.add_argument("--tool", help="평가할 Tool (tool1~tool5)")
    parser.add_argument("--all", action="store_true", help="모든 Tool 평가")
    parser.add_argument("--case", help="특정 케이스만 평가")
    parser.add_argument("--db-path", default="db/patent_agent.db")
    args = parser.parse_args()

    if args.all:
        for tool_name in ["tool1", "tool2", "tool3", "tool4", "tool5"]:
            evaluate_tool(tool_name, args.case, args.db_path)
    elif args.tool:
        evaluate_tool(args.tool, args.case, args.db_path)
    else:
        parser.error("--tool 또는 --all을 지정하세요.")


if __name__ == "__main__":
    main()
