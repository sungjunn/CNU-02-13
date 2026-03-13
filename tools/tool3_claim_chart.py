"""Tool 3 래퍼 — Claim Chart 생성.

ClaimChartModule을 감싸서 Pydantic 입출력 검증을 수행한다."""

from pydantic import ValidationError

from schemas.tool3 import ClaimChartInput, ClaimChartOutput, ClaimChartEntry, ElementMatch
from schemas.common import ClaimElement, MatchLevel
from modules.tool3_module import ClaimChartModule
from tools.base import ToolBase

MAX_RETRIES = 3


class ClaimChartTool(ToolBase):
    """Claim Chart 생성 Tool."""

    def __init__(self):
        self.module = ClaimChartModule()

    def run(self, input_data: ClaimChartInput) -> ClaimChartOutput:
        """Claim Chart 생성 실행.

        Args:
            input_data: ClaimChartInput

        Returns:
            ClaimChartOutput
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                prediction = self.module(
                    our_claims=input_data.our_claims,
                    prior_claims=input_data.prior_claims,
                    our_description=input_data.our_description,
                )

                # prediction → Pydantic 모델 변환
                charts = []
                for chart_dict in prediction.charts:
                    element_matches = []
                    for em in chart_dict.get("element_matches", []):
                        our_el = em.get("our_element", {})
                        prior_el = em.get("prior_element")

                        element_matches.append(ElementMatch(
                            our_element=ClaimElement(
                                element_id=our_el.get("element_id", ""),
                                text=our_el.get("text", ""),
                                label=our_el.get("label", ""),
                            ),
                            prior_element=ClaimElement(
                                element_id=prior_el.get("element_id", ""),
                                text=prior_el.get("text", ""),
                                label=prior_el.get("label", ""),
                            ) if prior_el else None,
                            match_level=MatchLevel(em.get("match_level", "없음")),
                            reasoning=em.get("reasoning", ""),
                        ))

                    charts.append(ClaimChartEntry(
                        our_claim_number=chart_dict["our_claim_number"],
                        prior_claim_number=chart_dict["prior_claim_number"],
                        element_matches=element_matches,
                    ))

                return ClaimChartOutput(
                    charts=charts,
                    summary=prediction.summary,
                )

            except (ValidationError, ValueError, Exception) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    continue

        raise RuntimeError(
            f"Tool 3 실행 실패 ({MAX_RETRIES}회 재시도 후): {last_error}"
        )
