"""Tool 1 모듈 — 통지서 분석기.

통지서 분석: 정규식 추출(40%) + LLM 요약(60%).

처리 흐름:
1. 정규식으로 확정적 데이터 추출 (법조항, 특허번호, 청구항 번호)
2. LLM에게 추출 메타데이터 + 원문을 넘겨서 요약 생성
3. 정규식 결과 + LLM 결과를 합쳐서 최종 출력 구성
"""

import json
import dspy

from signatures.tool1_sig import AnalyzeNotice
from utils.regex_extractors import (
    extract_rejection_articles,
    extract_patent_numbers,
    extract_claim_numbers,
    classify_rejection_type,
)


class NoticeAnalyzerModule(dspy.Module):
    """통지서 분석 모듈.

    정규식으로 확정적 데이터(법조항, 번호 등)를 추출하고,
    LLM으로 심사관의 거절 논리를 요약한다.
    """

    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(AnalyzeNotice)

    def forward(self, notice_text: str):
        """통지서 분석 실행.

        Args:
            notice_text: 의견제출통지서 원문 텍스트

        Returns:
            dict: {
                "rejection_articles": [...],
                "prior_art_numbers": [...],
                "rejected_claim_numbers": [...],
                "rejection_type": "...",
                "examiner_reasoning": "...",
                "rejection_analysis": "...",
            }
        """
        # === 1단계: 정규식으로 확정적 데이터 추출 ===
        rejection_articles = extract_rejection_articles(notice_text)
        prior_art_numbers = extract_patent_numbers(notice_text)
        rejected_claim_numbers = extract_claim_numbers(notice_text)
        rejection_type = classify_rejection_type(rejection_articles)

        # 메타데이터 JSON 구성
        metadata = {
            "rejection_articles": rejection_articles,
            "prior_art_numbers": prior_art_numbers,
            "rejected_claim_numbers": rejected_claim_numbers,
            "rejection_type": rejection_type,
        }

        # === 2단계: LLM에게 추출 메타데이터 + 원문을 넘겨서 요약 ===
        result = self.analyze(
            notice_text=notice_text,
            extracted_metadata=json.dumps(metadata, ensure_ascii=False),
        )

        # === 3단계: 정규식 결과 + LLM 결과를 합쳐서 최종 출력 ===
        return dspy.Prediction(
            rejection_articles=rejection_articles,
            prior_art_numbers=prior_art_numbers,
            rejected_claim_numbers=rejected_claim_numbers,
            rejection_type=rejection_type,
            examiner_reasoning=result.examiner_reasoning,
            rejection_analysis=result.rejection_analysis,
        )
