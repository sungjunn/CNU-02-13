"""Tool 3 모듈 — Claim Chart 생성기 (배치 처리 최적화 버전).

기존 O(N) 호출 방식에서 청구항 쌍당 1회 호출(O(1))로 개선하여 실행 속도를 비약적으로 향상시킴.
"""

import json
import re

import dspy

from signatures.tool3_sig import BatchJudgeClaimChart


class ClaimChartModule(dspy.Module):
    """Claim Chart 생성 모듈 (배치 처리).

    당사 청구항과 선행특허 청구항의 모든 구성요소를 한 번에 LLM에 전달하여
    전체 매칭 리스트를 생성한다.
    """

    def __init__(self):
        super().__init__()
        self.judge = dspy.Predict(BatchJudgeClaimChart)

    def _format_elements(self, elements: list[dict]) -> str:
        """구성요소 리스트를 ID: 텍스트 형태의 문자열로 포맷팅."""
        return "\n".join([
            f"- {el.get('element_id', 'ID없음')}: {el.get('text', '')}"
            for el in elements
        ])

    def _extract_json(self, text: str) -> list[dict]:
        """문자열에서 JSON 리스트를 추출하고 파싱."""
        # ```json ... ``` 블록 추출 시도
        json_match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 전체 텍스트에서 [ ] 블록 추출 시도
        list_match = re.search(r"(\[.*\])", text, re.DOTALL)
        if list_match:
            try:
                return json.loads(list_match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"JSON 결과 추출 실패: {text[:200]}...")

    def forward(self, our_claims: list, prior_claims: list, our_description: str):
        """Claim Chart 생성 실행.

        Args:
            our_claims: 당사 파싱된 청구항 리스트
            prior_claims: 선행특허 파싱된 청구항 리스트
            our_description: 당사 상세설명 텍스트

        Returns:
            dspy.Prediction: {"charts": [...], "summary": "..."}
        """
        charts = []
        desc_context = our_description[:3000]  # 컨텍스트 길이 확장

        for our_claim in our_claims:
            for prior_claim in prior_claims:
                our_elements = our_claim.get("elements", [])
                prior_elements = prior_claim.get("elements", [])

                if not our_elements:
                    continue

                # 1. 입력 포맷팅
                our_elements_text = self._format_elements(our_elements)
                prior_elements_text = self._format_elements(prior_elements)

                # 2. 배치 LLM 호출 (청구항 쌍당 1회)
                result = self.judge(
                    our_elements=our_elements_text,
                    prior_elements=prior_elements_text,
                    our_description_context=desc_context,
                )

                # 3. JSON 파싱
                try:
                    matches_data = self._extract_json(result.matches_json)
                except Exception as e:
                    # 실패 시 빈 매칭 결과 생성 (또는 재시도 로직 추가 가능)
                    print(f"[경고] JSON 파싱 실패: {e}")
                    matches_data = []

                # 4. 기존 포맷으로 변환
                element_matches = []
                # LLM 결과 맵핑 (ID 기준)
                prior_map = {el["element_id"]: el for el in prior_elements}
                match_results = {m["our_element_id"]: m for m in matches_data}

                for our_el in our_elements:
                    res = match_results.get(our_el["element_id"], {})
                    prior_el_id = res.get("prior_element_id")
                    
                    element_matches.append({
                        "our_element": our_el,
                        "prior_element": prior_map.get(prior_el_id) if prior_el_id else None,
                        "match_level": res.get("match_level", "없음"),
                        "reasoning": res.get("reasoning", "배치 판정 결과 누락"),
                    })

                charts.append({
                    "our_claim_number": our_claim.get("claim_number"),
                    "prior_claim_number": prior_claim.get("claim_number"),
                    "element_matches": element_matches,
                })

        # === 5단계: 결과 검증 및 요약 생성 (기존 로직 유지) ===
        if not charts:
            raise ValueError("Claim Chart 결과가 비어있습니다.")

        total_elements = sum(len(c["element_matches"]) for c in charts)
        identical_count = sum(
            1 for c in charts for em in c["element_matches"]
            if em["match_level"] == "동일"
        )
        similar_count = sum(
            1 for c in charts for em in c["element_matches"]
            if em["match_level"] == "유사"
        )
        absent_count = sum(
            1 for c in charts for em in c["element_matches"]
            if em["match_level"] == "없음"
        )

        summary = (
            f"전체 {total_elements}개 구성요소 비교: "
            f"동일 {identical_count}개, 유사 {similar_count}개, 없음 {absent_count}개."
        )

        return dspy.Prediction(charts=charts, summary=summary)
