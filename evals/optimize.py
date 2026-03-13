"""DSPy 자동 프롬프트 최적화 스크립트.

사용법:
    uv run python -m evals.optimize --tool tool1
    uv run python -m evals.optimize --tool tool3 --optimizer miprov2
    uv run python -m evals.optimize --tool tool1 --auto heavy

동작:
1. DB에서 해당 Tool의 전체 검증셋 로드
2. DSPy MIPROv2 optimizer 실행
3. 최적화된 Module을 파일로 저장
4. 최적화 전후 점수 비교 로그

주의사항:
- 검증셋이 최소 10건은 있어야 의미 있는 최적화 가능
- LLM 호출이 수십~수백 번 발생 → 비용 주의
- auto="light" (적은 호출), "medium", "heavy" (많은 호출) 선택 가능
"""

import argparse
import os

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


def optimize_tool(tool_name: str, auto: str = "medium", db_path: str = "db/patent_agent.db"):
    """특정 Tool의 프롬프트를 자동 최적화.

    Args:
        tool_name: "tool1" ~ "tool5"
        auto: "light" | "medium" | "heavy" — 최적화 강도
        db_path: DB 파일 경로
    """
    print(f"\n=== {tool_name} 최적화 시작 (auto={auto}) ===")

    # 검증셋 로드
    trainset = load_eval_dataset(tool_name, db_path)
    if len(trainset) < 5:
        print(f"[경고] 검증셋이 {len(trainset)}건으로 부족합니다. 최소 10건 권장.")
        if not trainset:
            print("[중단] 검증셋이 없어 최적화를 실행할 수 없습니다.")
            return

    # Module과 metric 가져오기
    module = _MODULES[tool_name]()
    metric = _METRICS[tool_name]

    # === 최적화 전 점수 ===
    print("\n--- 최적화 전 평가 ---")
    evaluator = dspy.Evaluate(devset=trainset, metric=metric, num_threads=1)
    before_score = evaluator(module)
    print(f"최적화 전 점수: {before_score:.4f}")

    # === DSPy MIPROv2 optimizer 실행 ===
    print(f"\n--- MIPROv2 최적화 실행 (auto={auto}) ---")
    optimizer = dspy.MIPROv2(metric=metric, auto=auto)
    optimized = optimizer.compile(module, trainset=trainset)

    # === 최적화 후 점수 ===
    print("\n--- 최적화 후 평가 ---")
    after_score = evaluator(optimized)
    print(f"최적화 후 점수: {after_score:.4f}")
    print(f"개선: {before_score:.4f} → {after_score:.4f} "
          f"({'+' if after_score >= before_score else ''}{after_score - before_score:.4f})")

    # === 최적화 결과 저장 ===
    save_dir = f"optimized_modules/{tool_name}"
    os.makedirs(save_dir, exist_ok=True)
    optimized.save(save_dir)
    print(f"\n최적화 결과 저장: {save_dir}/")

    # === 최적화된 프롬프트 확인 안내 ===
    print("\n💡 최적화된 프롬프트를 확인하려면:")
    print(f"   dspy.inspect_history(n=3)")

    return optimized


def main():
    parser = argparse.ArgumentParser(description="DSPy 프롬프트 자동 최적화")
    parser.add_argument("--tool", required=True, help="최적화할 Tool (tool1~tool5)")
    parser.add_argument("--auto", default="medium", choices=["light", "medium", "heavy"],
                        help="최적화 강도 (default: medium)")
    parser.add_argument("--db-path", default="db/patent_agent.db")
    args = parser.parse_args()

    optimize_tool(args.tool, args.auto, args.db_path)


if __name__ == "__main__":
    main()
