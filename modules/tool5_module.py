"""Tool 5 모듈 — 보정안 생성기.

보정안 생성: LLM 생성(70%) + 코드 검증(30%).

처리 흐름:
1. LLM이 보정안 초안 생성
2. 코드로 후처리 검증 (diff 생성, 빈 문자열 체크, 원본 동일 체크)
3. 상세설명 근거 확인 (보정 내용이 상세설명에 있는지 문자열 검색)
"""

import json
import dspy

from signatures.tool5_sig import GenerateAmendment
from utils.diff_utils import generate_diff, get_changed_parts


class AmendmentModule(dspy.Module):
    """보정안 생성 모듈.

    전략에 따라 보정된 독립항 초안을 생성하고,
    코드로 품질 검증과 근거 확인을 수행한다.
    """

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GenerateAmendment)

    def forward(self, original_claim: str, strategy: str, description_text: str):
        """보정안 생성 실행.

        Args:
            original_claim: 원본 독립항 전문
            strategy: 대응 전략 텍스트
            description_text: 당사 상세설명 전문

        Returns:
            dspy.Prediction: {
                "amended_claim": "...",
                "added_elements": [...],
                "description_basis": [...],
                "diff_text": "...",
                "warnings": [...],
            }
        """
        # === 1단계: LLM이 보정안 초안 생성 ===
        result = self.generate(
            original_claim=original_claim,
            strategy=strategy,
            description_text=description_text,
        )

        amended_claim = result.amended_claim
        warnings = []

        # === 2단계: 코드 기반 후처리 검증 ===

        # 보정안이 빈 문자열이면 에러
        if not amended_claim or not amended_claim.strip():
            raise ValueError("보정안이 비어있습니다. LLM 출력을 확인하세요.")

        # 원본과 완전 동일하면 경고
        if amended_claim.strip() == original_claim.strip():
            warnings.append("⚠️ 보정안이 원본과 동일합니다. 보정이 수행되지 않았습니다.")

        # diff 생성
        diff_text = generate_diff(original_claim, amended_claim)

        # LLM 출력 파싱
        try:
            added_elements = json.loads(result.added_elements)
        except (json.JSONDecodeError, AttributeError):
            added_elements = []

        try:
            description_basis = json.loads(result.description_basis)
        except (json.JSONDecodeError, AttributeError):
            description_basis = []

        # === 3단계: 상세설명 근거 확인 ===
        changed = get_changed_parts(original_claim, amended_claim)
        for added_text in changed.get("added", []):
            # 추가된 텍스트 중 핵심 키워드가 상세설명에 있는지 확인
            # 짧은 토큰(조사, 접속사 등)은 제외하고 의미 있는 단어만 검색
            keywords = [w for w in added_text.split() if len(w) > 2]
            for kw in keywords:
                if kw not in description_text:
                    warnings.append(
                        f"⚠️ 추가된 표현 '{kw}'이 상세설명에서 발견되지 않습니다. "
                        f"신규사항 추가 가능성을 확인하세요."
                    )
                    break  # 키워드당 하나만 경고

        return dspy.Prediction(
            amended_claim=amended_claim,
            added_elements=added_elements,
            description_basis=description_basis,
            diff_text=diff_text,
            warnings=warnings,
        )
