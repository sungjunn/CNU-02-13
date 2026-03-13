"""Tool 2 모듈 — 청구항 파서.

청구항 파싱: 정규식(70%) + LLM 정제(30%).

처리 흐름:
1. 정규식으로 구조 파싱 (청구항 분리, 독립/종속 판별, 구성요소 1차 분리)
2. LLM으로 복잡한 구성요소 정제 (세미콜론으로 분리 안 되는 경우만)
3. 파싱 결과 검증 (독립항 존재 여부, 종속 참조 유효성)
"""

import json
import dspy

from signatures.tool2_sig import RefineClaimElements
from utils.regex_extractors import split_claims, split_claim_elements


class ClaimParserModule(dspy.Module):
    """청구항 파싱 모듈.

    정규식으로 1차 구조 파싱 후, 복잡한 케이스만 LLM으로 정제한다.
    """

    def __init__(self):
        super().__init__()
        self.refine = dspy.Predict(RefineClaimElements)

    def forward(self, claims_text: str):
        """청구항 파싱 실행.

        Args:
            claims_text: 청구항 전문 텍스트

        Returns:
            dspy.Prediction: {
                "total_claims": int,
                "independent_claims": [...],
                "dependent_claims": {...},
                "claims": [...],
            }
        """
        # === 1단계: 정규식으로 구조 파싱 ===
        raw_claims = split_claims(claims_text)

        if not raw_claims:
            raise ValueError("청구항을 분리할 수 없습니다. 입력 텍스트를 확인하세요.")

        parsed_claims = []
        independent_claims = []
        dependent_claims = {}

        for rc in raw_claims:
            claim_number = rc["number"]

            # 독립/종속 분류
            if rc["is_dependent"]:
                dependent_claims[str(claim_number)] = rc["depends_on"]
            else:
                independent_claims.append(claim_number)

            # 구성요소 1차 분리
            rough_elements = split_claim_elements(rc["text"])

            # === 2단계: 복잡한 청구항만 LLM으로 정제 ===
            # 구성요소가 1개 이하이면서 텍스트가 긴 경우 = 분리가 잘 안 된 것
            if len(rough_elements) <= 1 and len(rc["text"]) > 100:
                try:
                    result = self.refine(
                        claim_text=rc["text"],
                        rough_elements=json.dumps(rough_elements, ensure_ascii=False),
                    )
                    refined = json.loads(result.refined_elements)
                    elements = refined
                except Exception:
                    # LLM 정제 실패 시 정규식 결과 사용
                    elements = [
                        {"element_id": f"e{i+1}", "text": e, "label": ""}
                        for i, e in enumerate(rough_elements)
                    ]
            else:
                elements = [
                    {"element_id": f"e{i+1}", "text": e, "label": ""}
                    for i, e in enumerate(rough_elements)
                ]

            parsed_claims.append({
                "claim_number": claim_number,
                "claim_type": "종속항" if rc["is_dependent"] else "독립항",
                "depends_on": rc["depends_on"],
                "original_text": rc["text"],
                "elements": elements,
            })

        # === 3단계: 파싱 결과 검증 ===
        if not independent_claims:
            raise ValueError("독립항이 하나도 없습니다. 파싱 결과를 확인하세요.")

        # 종속항 참조 유효성 검증
        all_numbers = {rc["number"] for rc in raw_claims}
        for dep_num, ref_num in dependent_claims.items():
            if ref_num not in all_numbers:
                raise ValueError(
                    f"종속항 {dep_num}이 존재하지 않는 청구항 {ref_num}을 참조합니다."
                )

        return dspy.Prediction(
            total_claims=len(raw_claims),
            independent_claims=independent_claims,
            dependent_claims=dependent_claims,
            claims=parsed_claims,
        )
