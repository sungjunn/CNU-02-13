"""Tool 2 래퍼 — 청구항 파서.

ClaimParserModule을 감싸서 Pydantic 입출력 검증을 수행한다."""

from pydantic import ValidationError

from schemas.tool2 import ClaimParseInput, ClaimParseOutput, ParsedClaim
from schemas.common import ClaimElement, ClaimType
from modules.tool2_module import ClaimParserModule
from tools.base import ToolBase

MAX_RETRIES = 3


class ClaimParserTool(ToolBase):
    """청구항 파서 Tool."""

    def __init__(self):
        self.module = ClaimParserModule()

    def run(self, input_data: ClaimParseInput) -> ClaimParseOutput:
        """청구항 파싱 실행.

        Args:
            input_data: ClaimParseInput

        Returns:
            ClaimParseOutput
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                prediction = self.module(claims_text=input_data.claims_text)

                # prediction의 claims를 ParsedClaim 모델로 변환
                parsed_claims = []
                for c in prediction.claims:
                    elements = [
                        ClaimElement(
                            element_id=e.get("element_id", f"e{i}"),
                            text=e.get("text", ""),
                            label=e.get("label", ""),
                        )
                        for i, e in enumerate(c.get("elements", []))
                    ]
                    parsed_claims.append(ParsedClaim(
                        claim_number=c["claim_number"],
                        claim_type=ClaimType(c["claim_type"]),
                        depends_on=c.get("depends_on"),
                        original_text=c["original_text"],
                        elements=elements,
                    ))

                return ClaimParseOutput(
                    total_claims=prediction.total_claims,
                    independent_claims=prediction.independent_claims,
                    dependent_claims=prediction.dependent_claims,
                    claims=parsed_claims,
                )

            except (ValidationError, ValueError, Exception) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    continue

        raise RuntimeError(
            f"Tool 2 실행 실패 ({MAX_RETRIES}회 재시도 후): {last_error}"
        )
