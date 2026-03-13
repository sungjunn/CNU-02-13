"""Tool 4 DSPy Signature — 전략 생성.

Claim Chart 분석 결과와 거절이유를 바탕으로 심사대응 전략을 생성한다.
거절 유형(신규성/진보성)에 따라 다른 논증 방향을 사용한다.
"""

import dspy


class GenerateStrategy(dspy.Signature):
    """Claim Chart 분석 결과와 거절이유를 바탕으로 심사대응 전략을 생성한다.

    거절 유형에 따라 다른 논증 방향을 사용:

    === 신규성 거절 (제29조 제1항) 대응 전략 ===
    - 미매칭 구성요소("없음")를 강조하여 선행특허와의 차이를 주장
    - "선행특허에는 [구성요소 X]가 전혀 개시되지 않았으므로,
       본 발명은 선행특허와 동일하지 않다"는 논리

    === 진보성 거절 (제29조 제2항) 대응 전략 ===
    - 구성요소 조합의 기술적 효과 차이를 강조
    - "구성 A와 B의 조합에 의해 [기술적 효과]가 달성되며,
       이는 선행특허에서 예측할 수 없는 것이다"는 논리
    - 선행특허 조합 동기(motivation to combine) 부재를 주장

    === 기재불비 (제42조) 대응 전략 ===
    - 상세설명에서 근거가 되는 단락을 인용하여 반박
    - 필요시 청구항 보정으로 명확성 개선 제안
    """

    claim_chart_summary: str = dspy.InputField(desc="Claim Chart 요약 (매칭/미매칭 구성요소)")
    rejection_type: str = dspy.InputField(desc="거절 유형: 신규성 또는 진보성")
    examiner_reasoning: str = dspy.InputField(desc="심사관 거절 논리 요약")
    unmatched_elements: str = dspy.InputField(desc="매칭 '없음'인 구성요소 리스트 JSON")
    disputed_elements: str = dspy.InputField(desc="매칭 '유사'인 구성요소 리스트 JSON")

    differences: str = dspy.OutputField(
        desc='차이점 분석 JSON. 각 항목은 {"element": "...", "diff_description": "...", "technical_effect": "..."} 형식.'
    )
    strategy: str = dspy.OutputField(
        desc="대응 전략 텍스트. 의견서에 기재할 논증의 골격."
    )
    rebuttal_points: str = dspy.OutputField(
        desc='반박 포인트 리스트 JSON. 각 항목은 {"point": "...", "basis": "...", "strength": "강/중/약"} 형식.'
    )
