"""파일 → DB 일괄 로드 스크립트.

data/case_XX/input/ 폴더의 텍스트 파일들을 읽어서 DB에 삽입한다.

사용법:
    uv run python -m db.loader --case case_01

파일명 규칙:
    - notice.txt                              → OfficeAction
    - our_claims.txt + our_description.txt    → PatentDocument (doc_type="our_patent")
    - prior_art_1_claims.txt + prior_art_1_description.txt → PatentDocument (doc_type="prior_art")
    - expected/tool1_expected.json            → EvalDataset (tool_name="tool1")
"""

import argparse
import json
import re
from pathlib import Path

from db.database import PatentDB
from schemas.db_models import PatentDocument, OfficeAction, CaseRecord, EvalDataset


def _read_text(path: Path) -> str:
    """텍스트 파일 읽기 (UTF-8). 없으면 빈 문자열."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _find_prior_art_files(input_dir: Path) -> list[dict]:
    """선행특허 txt 파일 탐색.

    패턴: prior_art_N_claims.txt + prior_art_N_description.txt

    반환: [{"id": "prior_art_1", "claims_text": "...", "description_text": "..."}, ...]
    """
    found_ids: set[str] = set()
    results = []

    pattern = re.compile(r"prior_art_(\d+)_claims\.txt")
    for f in sorted(input_dir.iterdir()):
        m = pattern.match(f.name)
        if m:
            num = m.group(1)
            art_id = f"prior_art_{num}"
            if art_id in found_ids:
                continue
            found_ids.add(art_id)

            claims_text = _read_text(input_dir / f"prior_art_{num}_claims.txt")
            desc_text = _read_text(input_dir / f"prior_art_{num}_description.txt")
            results.append({
                "id": art_id,
                "claims_text": claims_text,
                "description_text": desc_text,
            })

    return sorted(results, key=lambda x: x["id"])


def load_case(case_name: str, db_path: str = "db/patent_agent.db"):
    """케이스 데이터를 DB에 일괄 로드.

    Args:
        case_name: 케이스 폴더 이름 (예: "case_01")
        db_path: SQLite DB 파일 경로
    """
    data_dir = Path("data") / case_name
    input_dir = data_dir / "input"
    expected_dir = data_dir / "expected"

    if not input_dir.exists():
        print(f"[오류] 입력 폴더를 찾을 수 없습니다: {input_dir}")
        return

    db = PatentDB(db_path)

    try:
        # === 1. 당사 특허 로드 ===
        our_patent_id = f"{case_name}_our_patent"
        our_claims = _read_text(input_dir / "our_claims.txt")
        our_description = _read_text(input_dir / "our_description.txt")

        if our_claims:
            db.insert_patent(PatentDocument(
                doc_id=our_patent_id,
                doc_type="our_patent",
                title=f"{case_name} 당사 특허",
                claims_text=our_claims,
                description_text=our_description,
            ))
            print(f"[로드] 당사 특허: {our_patent_id}")
        else:
            print(f"[경고] 당사 특허 파일 없음 (our_claims.txt)")

        # === 2. 선행특허 로드 ===
        prior_art_ids = []
        for pa in _find_prior_art_files(input_dir):
            pa_doc_id = f"{case_name}_{pa['id']}"
            prior_art_ids.append(pa_doc_id)
            db.insert_patent(PatentDocument(
                doc_id=pa_doc_id,
                doc_type="prior_art",
                title=f"{case_name} {pa['id']}",
                claims_text=pa["claims_text"],
                description_text=pa["description_text"],
            ))
            print(f"[로드] 선행특허: {pa_doc_id}")

        # === 3. 통지서 로드 ===
        action_id = f"{case_name}_action"
        notice_text = _read_text(input_dir / "notice.txt")
        if notice_text:
            db.insert_office_action(OfficeAction(
                action_id=action_id,
                our_patent_id=our_patent_id,
                notice_text=notice_text,
                prior_art_ids=prior_art_ids,
            ))
            print(f"[로드] 통지서: {action_id}")
        else:
            print(f"[경고] 통지서 파일 없음 (notice.txt)")

        # === 4. 케이스 생성 ===
        db.create_case(CaseRecord(
            case_id=case_name,
            action_id=action_id,
            our_patent_id=our_patent_id,
        ))
        print(f"[로드] 케이스 생성: {case_name}")

        # === 5. 검증셋 로드 ===
        if expected_dir.exists():
            for f in sorted(expected_dir.glob("tool*.json")):
                match = re.match(r"(tool\d+)_", f.name)
                if match:
                    tool_name = match.group(1)
                    eval_type = "checklist" if "checklist" in f.name else "exact_match"
                    db.insert_eval(EvalDataset(
                        eval_id=f"{case_name}_{tool_name}",
                        case_id=case_name,
                        tool_name=tool_name,
                        expected_json=f.read_text(encoding="utf-8"),
                        eval_type=eval_type,
                    ))
                    print(f"[로드] 검증셋: {tool_name} ({eval_type})")

        print(f"\n=== {case_name} 로드 완료 ===")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="케이스 데이터를 DB에 로드")
    parser.add_argument("--case", required=True, help="케이스 폴더 이름 (예: case_01)")
    parser.add_argument("--db-path", default="db/patent_agent.db", help="DB 파일 경로")
    args = parser.parse_args()

    load_case(args.case, args.db_path)
