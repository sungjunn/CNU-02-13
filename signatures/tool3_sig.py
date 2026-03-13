"""Tool 3 DSPy Signature — 배치 구성요소 매칭 판정.

당사 청구항 구성요소 리스트와 선행특허 청구항 구성요소 리스트를 통째로 비교하여
전체 매칭 리스트를 한 번에 생성한다 (O(1) 호출).
"""

import dspy


class BatchJudgeClaimChart(dspy.Signature):
    """당사 청구항 구성요소들과 선행특허 구성요소들을 통째로 비교하여
    각 구성요소별 최적의 매칭 수준(동일/유사/없음)을 판정한다.

    판정 기준 (특허 실무 기준):
    - 동일: 실질적으로 같은 기술 내용. 표현이 다르더라도 기술적 의미가 동일하면 "동일" 판정.
    - 유사: 관련은 있으나 기술적 차이가 존재 (상위/하위 개념, 수량 차이 등).
    - 없음: 선행특허에 해당 구성이 전혀 개시되지 않음.

    출력 형식 (반드시 JSON 리스트 형식으로 작성):
    [
      {
        "our_element_id": "EL_01",
        "prior_element_id": "PA_EL_01", (없으면 null)
        "match_level": "동일", (동일/유사/없음 중 하나)
        "reasoning": "판정 근거..."
      },
      ...
    ]
    """

    our_elements: str = dspy.InputField(desc="당사 청구항 구성요소 리스트 (ID: 텍스트)")
    prior_elements: str = dspy.InputField(desc="선행특허 청구항 구성요소 리스트 (ID: 텍스트)")
    our_description_context: str = dspy.InputField(
        desc="당사 상세설명 중 관련 단락 (용어 의미 파악용)"
    )

    matches_json: str = dspy.OutputField(
        desc="구성요소별 매칭 결과 리스트 (JSON 형식)"
    )
