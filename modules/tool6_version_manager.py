"""Tool 6 — 차수 관리 로직 (100% 코드 기반, DSPy 미사용).

차수별 심사대응 결과를 JSON 파일로 저장/로드하고 diff를 생성한다.
"""

import difflib
import json
from datetime import datetime
from pathlib import Path


class VersionManager:
    """차수 관리 — JSON 파일 기반 저장/로드."""

    def __init__(self, base_dir: str = "data/versions"):
        self.base_dir = Path(base_dir)

    def _case_dir(self, case_id: str) -> Path:
        d = self.base_dir / case_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _version_path(self, case_id: str, version: int) -> Path:
        return self._case_dir(case_id) / f"v{version:03d}.json"

    def _next_version(self, case_id: str) -> int:
        existing = sorted(self._case_dir(case_id).glob("v*.json"))
        if not existing:
            return 1
        last = existing[-1].stem  # "v001"
        return int(last[1:]) + 1

    def save_version(
        self,
        case_id: str,
        rejection_summary: str,
        strategy_summary: str,
        original_claim: str,
        amended_claim: str,
        diff_text: str = "",
        notes: str = "",
    ) -> dict:
        """새 차수를 저장하고 레코드 dict를 반환."""
        version = self._next_version(case_id)

        # diff_text가 비어 있으면 자동 생성
        if not diff_text:
            diff_text = "\n".join(
                difflib.unified_diff(
                    original_claim.splitlines(),
                    amended_claim.splitlines(),
                    fromfile="original",
                    tofile="amended",
                    lineterm="",
                )
            )

        record = {
            "version": version,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "case_id": case_id,
            "rejection_summary": rejection_summary,
            "strategy_summary": strategy_summary,
            "original_claim": original_claim,
            "amended_claim": amended_claim,
            "diff_text": diff_text,
            "notes": notes,
        }
        path = self._version_path(case_id, version)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def load_version(self, case_id: str, version: int) -> dict | None:
        """특정 차수 로드. 없으면 None."""
        path = self._version_path(case_id, version)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_all_versions(self, case_id: str) -> list[dict]:
        """모든 차수를 오름차순으로 로드."""
        result = []
        for p in sorted(self._case_dir(case_id).glob("v*.json")):
            result.append(json.loads(p.read_text(encoding="utf-8")))
        return result

    def get_history_summary(self, case_id: str) -> dict:
        """최신 차수 번호 + 직전 차수와의 diff 요약 반환."""
        versions = self.load_all_versions(case_id)
        if not versions:
            return {"latest_version": 0, "diff_from_prev": ""}

        latest = versions[-1]
        diff_from_prev = ""
        if len(versions) >= 2:
            prev = versions[-2]
            diff_from_prev = "\n".join(
                difflib.unified_diff(
                    prev["amended_claim"].splitlines(),
                    latest["amended_claim"].splitlines(),
                    fromfile=f"v{prev['version']:03d}",
                    tofile=f"v{latest['version']:03d}",
                    lineterm="",
                )
            )

        return {
            "latest_version": latest["version"],
            "diff_from_prev": diff_from_prev,
        }
