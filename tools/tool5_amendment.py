"""Tool 5 래퍼 — 보정안 생성.

AmendmentModule을 감싸서 Pydantic 입출력 검증을 수행한다."""

from pydantic import ValidationError

from schemas.tool5 import AmendmentInput, AmendmentOutput, DescriptionBasis
from schemas.common import ClaimElement
from modules.tool5_module import AmendmentModule
from tools.base import ToolBase

MAX_RETRIES = 3


class AmendmentTool(ToolBase):
    """보정안 생성 Tool."""

    def __init__(self):
        self.module = AmendmentModule()

    def run(self, input_data: AmendmentInput) -> AmendmentOutput:
        """보정안 생성 실행.

        Args:
            input_data: AmendmentInput

        Returns:
            AmendmentOutput
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                prediction = self.module(
                    original_claim=input_data.original_claim,
                    strategy=input_data.strategy,
                    description_text=input_data.description_text,
                )

                # 추가된 구성요소 변환
                added_elements = []
                for el in prediction.added_elements:
                    if isinstance(el, dict):
                        added_elements.append(ClaimElement(
                            element_id=el.get("element_id", ""),
                            text=el.get("text", ""),
                            label=el.get("label", ""),
                        ))

                # 상세설명 근거 변환
                description_basis = []
                for db_item in prediction.description_basis:
                    if isinstance(db_item, dict):
                        description_basis.append(DescriptionBasis(
                            paragraph=db_item.get("paragraph", ""),
                            relevance=db_item.get("relevance", ""),
                        ))

                return AmendmentOutput(
                    amended_claim=prediction.amended_claim,
                    added_elements=added_elements,
                    description_basis=description_basis,
                    diff_text=prediction.diff_text,
                    warnings=prediction.warnings,
                )

            except (ValidationError, ValueError, Exception) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    continue

        raise RuntimeError(
            f"Tool 5 실행 실패 ({MAX_RETRIES}회 재시도 후): {last_error}"
        )
