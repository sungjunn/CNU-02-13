"""Tool 4 래퍼 — 전략 생성.

StrategyModule을 감싸서 Pydantic 입출력 검증을 수행한다."""

from pydantic import ValidationError

from schemas.tool4 import StrategyInput, StrategyOutput, RebuttalPoint
from modules.tool4_module import StrategyModule
from tools.base import ToolBase

MAX_RETRIES = 3


class StrategyTool(ToolBase):
    """전략 생성 Tool."""

    def __init__(self):
        self.module = StrategyModule()

    def run(self, input_data: StrategyInput) -> StrategyOutput:
        """전략 생성 실행.

        Args:
            input_data: StrategyInput

        Returns:
            StrategyOutput
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                # unmatched/disputed 요소를 claim_chart 형식으로 재구성
                element_matches = [
                    {"our_element": el, "prior_element": None,
                     "match_level": "없음", "reasoning": ""}
                    for el in input_data.unmatched_elements
                ] + [
                    {"our_element": el, "prior_element": {},
                     "match_level": "유사", "reasoning": ""}
                    for el in input_data.disputed_elements
                ]
                claim_chart = {
                    "charts": [{"element_matches": element_matches}] if element_matches else [],
                    "summary": input_data.claim_chart_summary,
                }

                prediction = self.module(
                    claim_chart=claim_chart,
                    rejection_type=input_data.rejection_type.value
                        if hasattr(input_data.rejection_type, "value")
                        else input_data.rejection_type,
                    examiner_reasoning=input_data.examiner_reasoning,
                )

                # 반박 포인트 변환
                rebuttal_points = []
                for rp in prediction.rebuttal_points:
                    if isinstance(rp, dict):
                        rebuttal_points.append(RebuttalPoint(
                            point=rp.get("point", rp.get("raw", "")),
                            basis=rp.get("basis", ""),
                            strength=rp.get("strength", "중"),
                        ))

                return StrategyOutput(
                    differences=prediction.differences,
                    strategy=prediction.strategy,
                    rebuttal_points=rebuttal_points,
                )

            except (ValidationError, Exception) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    continue

        raise RuntimeError(
            f"Tool 4 실행 실패 ({MAX_RETRIES}회 재시도 후): {last_error}"
        )
