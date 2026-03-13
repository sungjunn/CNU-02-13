"""Tool 5 DSPy Signature — 보정안 생성.

대응 전략에 따라 보정된 독립항 초안을 생성한다.
보정 시 반드시 상세설명에 근거가 있는 표현만 사용해야 한다.
"""

import dspy


class GenerateAmendment(dspy.Signature):
    """대응 전략에 따라 보정된 독립항 초안을 생성한다.

    === 보정 원칙 (한국 특허법 기준) ===
    1. 신규사항 추가 금지: 보정은 최초 출원 명세서에 기재된 범위 내에서만 가능.
       상세설명에 근거가 있는 표현만 사용해야 한다.
    2. 청구범위 감축: 보정은 일반적으로 청구범위를 좁히는 방향.
       구성요소를 추가하거나 기존 구성을 한정하는 방식.
    3. 선행특허 차별화: 보정 후 청구항이 선행특허와 명확히 구별되어야 한다.

    === 보정 방식 ===
    - 종속항의 한정사항을 독립항에 통합 (가장 일반적)
    - 상세설명의 구체적 실시예를 구성요소로 추가
    - 수치 한정 추가 (상세설명에 근거 있는 경우)
    - 기능적 표현을 구조적 표현으로 변경

    원본 청구항에서 변경된 부분을 명확히 표시하라.
    """

    original_claim: str = dspy.InputField(desc="원본 독립항 전문")
    strategy: str = dspy.InputField(desc="대응 전략 텍스트 (Tool 4 출력)")
    description_text: str = dspy.InputField(desc="당사 상세설명 전문 (보정 근거 확인용)")

    amended_claim: str = dspy.OutputField(desc="보정된 청구항 전문")
    added_elements: str = dspy.OutputField(
        desc='추가된 구성요소 리스트 JSON. 각 항목은 {"element_id": "...", "text": "...", "label": "..."} 형식.'
    )
    description_basis: str = dspy.OutputField(
        desc='보정 근거가 되는 상세설명 단락 리스트 JSON. 각 항목은 {"paragraph": "...", "relevance": "..."} 형식.'
    )
