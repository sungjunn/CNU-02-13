"""Tool 2 DSPy Signature — 청구항 구성요소 정제.

정규식으로 1차 분리된 청구항 구성요소를 의미 단위로 정제하고 라벨을 부여한다.
세미콜론으로 split한 결과가 잘못된 경우(복합 구성, 누락 등)를 LLM이 교정한다.
"""

import dspy


class RefineClaimElements(dspy.Signature):
    """정규식으로 1차 분리된 청구항 구성요소를 의미 단위로 정제하고 라벨을 부여한다.

    특허 청구항의 구성요소는 발명을 구성하는 기술적 단위 요소다.
    예를 들어 타이어 특허에서:
    - "트레드부에 형성된 복수의 주홈" → 구성요소 1개
    - "상기 주홈과 교차하는 횡홈" → 구성요소 1개

    세미콜론으로 split한 결과가 제공되며, 이를 검토하여:
    1. 잘못 분리된 요소를 합치거나 재분리
       (예: "A를 포함하고, B를 포함하며" → A와 B 분리)
    2. 각 요소에 한국어 의미 라벨 부여
       (예: "주홈 구조", "횡홈 배치", "보강층 재질")

    라벨은 후속 Claim Chart 비교에서 대응 요소를 찾는 데 활용된다.
    """

    claim_text: str = dspy.InputField(desc="단일 청구항 원문")
    rough_elements: str = dspy.InputField(
        desc="정규식으로 1차 분리된 구성요소 리스트 JSON"
    )

    refined_elements: str = dspy.OutputField(
        desc='정제된 구성요소 리스트 JSON. 각 요소는 {"element_id": "e1", "text": "...", "label": "..."} 형식.'
    )
