"""Tool 1 DSPy Signature — 통지서 거절이유 요약.

정규식으로 이미 추출된 메타데이터(법조항, 특허번호, 청구항 번호)와 함께
의견제출통지서 원문을 받아, 심사관의 거절 논리를 요약한다.

⚠️ 이 Signature는 LLM이 처리할 부분만 정의한다.
   법조항 추출, 특허번호 추출 등 확정적 데이터는 정규식(utils/regex_extractors.py)이 담당.
"""

import dspy


class AnalyzeNotice(dspy.Signature):
    """의견제출통지서의 거절이유를 분석하여 심사관의 논리를 요약한다.

    특허 심사에서 의견제출통지서는 심사관이 특허 출원을 거절하는 이유를 설명하는 공식 문서다.
    이 Signature는 통지서의 핵심 논리를 파악하여 대응 전략 수립에 필요한 정보를 추출한다.

    정규식으로 이미 추출된 메타데이터(법조항, 특허번호, 청구항 번호)가
    함께 제공된다. 이 메타데이터를 참고하여 거절이유를 요약하라.

    거절 유형별 주의사항:
    - 신규성 거절(제29조 제1항): 심사관이 동일한 선행기술이 있다고 주장. 어떤 구성이 동일하다고 보는지 파악.
    - 진보성 거절(제29조 제2항): 심사관이 선행기술의 조합으로 용이하게 발명할 수 있다고 주장.
      어떤 선행기술을 어떻게 조합하는지, 조합의 동기가 무엇인지 파악.
    - 기재불비(제42조): 상세설명 또는 청구항의 기재가 불충분하다는 주장.
    """

    notice_text: str = dspy.InputField(desc="의견제출통지서 원문 텍스트")
    extracted_metadata: str = dspy.InputField(
        desc="정규식으로 추출된 법조항, 특허번호, 청구항 번호 JSON"
    )

    examiner_reasoning: str = dspy.OutputField(
        desc="심사관의 거절 논리 요약 (3~5문장). 거절의 핵심 근거와 논리 흐름을 포함."
    )
    rejection_analysis: str = dspy.OutputField(
        desc="거절 유형별 상세 분석 JSON. 각 거절이유에 대해 {type, legal_basis, target_claims, prior_arts, reasoning} 형식."
    )
