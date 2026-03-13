"""Tool 6 래퍼 — 차수 관리.

100% 코드 기반. VersionManager를 Tool 인터페이스로 감싼다."""

from schemas.tool6 import VersionRecord, VersionHistory
from modules.tool6_version_manager import VersionManager
from tools.base import ToolBase


class VersionManagerTool(ToolBase):
    """차수 관리 Tool."""

    def __init__(self, base_dir: str = "data/versions"):
        self.manager = VersionManager(base_dir)

    def run(self, input_data=None):
        """Tool 인터페이스 호환용. 직접 메서드를 호출하는 것을 권장."""
        raise NotImplementedError(
            "VersionManagerTool은 save_version(), load_version() 등 "
            "개별 메서드를 직접 호출하세요."
        )

    def save_version(
        self,
        case_id: str,
        rejection_summary: str,
        strategy_summary: str,
        original_claim: str,
        amended_claim: str,
        diff_text: str,
        notes: str = "",
    ) -> VersionRecord:
        """새 차수 저장."""
        record = self.manager.save_version(
            case_id=case_id,
            rejection_summary=rejection_summary,
            strategy_summary=strategy_summary,
            original_claim=original_claim,
            amended_claim=amended_claim,
            diff_text=diff_text,
            notes=notes,
        )
        return VersionRecord(**record)

    def load_version(self, case_id: str, version: int) -> VersionRecord | None:
        """특정 차수 로드."""
        record = self.manager.load_version(case_id, version)
        if record is None:
            return None
        return VersionRecord(**record)

    def get_history(self, case_id: str) -> VersionHistory:
        """차수 이력 조회."""
        summary = self.manager.get_history_summary(case_id)
        versions = self.manager.load_all_versions(case_id)
        return VersionHistory(
            case_id=case_id,
            versions=[VersionRecord(**v) for v in versions],
            latest_version=summary["latest_version"],
            diff_between_versions=summary.get("diff_from_prev", ""),
        )
