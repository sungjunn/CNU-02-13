"""Tool 4 모듈 — 전략 생성기.

차이점 분석 + 전략: 규칙 분기(코드 20%) + 논증 생성(LLM 80%).

처리 흐름:
1. 코드로 전처리: Claim Chart에서 미매칭/유사 요소 자동 추출
2. 거절 유형에 따라 LLM 호출: 신규성이면 미매칭 강조, 진보성이면 효과 강조
"""

import json
import dspy

from signatures.tool4_sig import GenerateStrategy


class StrategyModule(dspy.Module):
    """전략 생성 모듈.

    Claim Chart 결과를 바탕으로 차이점을 분석하고
    거절 유형에 맞는 대응 전략을 생성한다.
    """

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GenerateStrategy)

    def forward(self, claim_chart: dict, rejection_type: str, examiner_reasoning: str):
        """전략 생성 실행.

        Args:
            claim_chart: Claim Chart 결과 (charts + summary)
            rejection_type: 거절 유형 ("신규성" 또는 "진보성")
            examiner_reasoning: 심사관 거절 논리 요약

        Returns:
            dspy.Prediction: {
                "differences": [...],
                "strategy": "...",
                "rebuttal_points": [...],
            }
        """
        # === 1단계: 코드로 전처리 ===
        unmatched = []  # 매칭 "없음" 요소
        disputed = []   # 매칭 "유사" 요소

        charts = claim_chart.get("charts", [])
        for chart in charts:
            for em in chart.get("element_matches", []):
                level = em.get("match_level", "")
                if level == "없음":
                    unmatched.append({
                        "element": em.get("our_element", {}),
                        "reasoning": em.get("reasoning", ""),
                    })
                elif level == "유사":
                    disputed.append({
                        "our_element": em.get("our_element", {}),
                        "prior_element": em.get("prior_element", {}),
                        "reasoning": em.get("reasoning", ""),
                    })

        # Claim Chart 요약
        summary = claim_chart.get("summary", "")

        # === 2단계: LLM 호출 ===
        result = self.generate(
            claim_chart_summary=summary,
            rejection_type=rejection_type,
            examiner_reasoning=examiner_reasoning,
            unmatched_elements=json.dumps(unmatched, ensure_ascii=False),
            disputed_elements=json.dumps(disputed, ensure_ascii=False),
        )

        # LLM 출력 파싱
        try:
            differences = json.loads(result.differences)
        except (json.JSONDecodeError, AttributeError):
            differences = [{"raw": result.differences}]

        try:
            rebuttal_points = json.loads(result.rebuttal_points)
        except (json.JSONDecodeError, AttributeError):
            rebuttal_points = [{"raw": result.rebuttal_points}]

        return dspy.Prediction(
            differences=differences,
            strategy=result.strategy,
            rebuttal_points=rebuttal_points,
        )
