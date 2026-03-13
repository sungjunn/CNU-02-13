"""Tool 베이스 클래스.

모든 Tool의 공통 인터페이스를 정의한다.
Pydantic 입출력 검증 + 중간 결과 저장 + DB 연동을 담당."""

import json
import os
from abc import ABC, abstractmethod
from pydantic import BaseModel


class ToolBase(ABC):
    """모든 Tool의 베이스 클래스.

    규칙:
    - 입력과 출력은 반드시 Pydantic BaseModel
    - run()은 단일 진입점
    - DSPy Module을 내부적으로 호출
    - 중간 결과를 JSON + DB에 저장
    """

    @abstractmethod
    def run(self, input_data: BaseModel) -> BaseModel:
        """Tool 실행.

        Args:
            input_data: Pydantic 입력 모델

        Returns:
            Pydantic 출력 모델
        """
        pass

    def save_result(self, result: BaseModel, path: str):
        """결과를 JSON 파일로 저장 (디버깅용).

        Args:
            result: Pydantic 출력 모델
            path: 저장 경로 (예: "data/results/case_01/tool1.json")
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                result.model_dump() if hasattr(result, "model_dump") else result,
                f,
                ensure_ascii=False,
                indent=2,
            )

    def save_to_db(self, case_id: str, result: BaseModel):
        """결과를 DB에 저장.

        TODO: 구현 예정 — Tool별 결과 테이블 설계 후 연결
        """
        pass
