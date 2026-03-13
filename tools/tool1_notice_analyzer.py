"""Tool 1 래퍼 — 통지서 분석.

NoticeAnalyzerModule을 감싸서 Pydantic 입출력 검증을 수행한다.
변환 실패 시 최대 3회 재시도."""

from pydantic import ValidationError

from schemas.tool1 import NoticeAnalysisInput, NoticeAnalysisOutput, RejectionDetail
from schemas.common import RejectionType
from modules.tool1_module import NoticeAnalyzerModule
from tools.base import ToolBase

import json

MAX_RETRIES = 3


class NoticeAnalyzerTool(ToolBase):
    """통지서 분석 Tool."""

    def __init__(self):
        self.module = NoticeAnalyzerModule()

    def run(self, input_data: NoticeAnalysisInput) -> NoticeAnalysisOutput:
        """통지서 분석 실행.

        Args:
            input_data: NoticeAnalysisInput

        Returns:
            NoticeAnalysisOutput
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                prediction = self.module(notice_text=input_data.notice_text)

                # LLM의 rejection_analysis JSON 파싱 → RejectionDetail 리스트
                rejection_details = []
                try:
                    analysis_raw = json.loads(prediction.rejection_analysis)
                    if isinstance(analysis_raw, list):
                        for item in analysis_raw:
                            rejection_details.append(RejectionDetail(
                                rejection_type=RejectionType(item.get("type", "기타")),
                                legal_basis=item.get("legal_basis", ""),
                                target_claims=item.get("target_claims", []),
                                prior_art_ids=item.get("prior_arts", []),
                                summary=item.get("reasoning", ""),
                            ))
                except (json.JSONDecodeError, KeyError):
                    pass

                return NoticeAnalysisOutput(
                    rejection_articles=prediction.rejection_articles,
                    prior_art_numbers=prediction.prior_art_numbers,
                    rejected_claim_numbers=prediction.rejected_claim_numbers,
                    rejection_type=RejectionType(prediction.rejection_type),
                    examiner_reasoning=prediction.examiner_reasoning,
                    rejection_details=rejection_details,
                )

            except (ValidationError, Exception) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    continue

        raise RuntimeError(
            f"Tool 1 실행 실패 ({MAX_RETRIES}회 재시도 후): {last_error}"
        )
