"""eval 데이터셋 로드.

DB에서 해당 Tool의 검증셋을 읽어 DSPy Example 리스트로 변환한다.

=== 핵심: expected JSON → dspy.Example 변환 매핑 ===

expected JSON의 필드명과 DSPy Signature의 필드명이 다를 수 있다.
각 Tool별로 아래 매핑 규칙을 적용하여 변환한다.

- Tool 1: 정규식 출력 필드 → _expected_* 접두사
- Tool 2: 파싱 결과 필드 → _expected_* 접두사
- Tool 3: 매칭 결과 → _expected_matchings
- Tool 4: 체크리스트 → _must_include
- Tool 5: 체크리스트 → _must_include, _must_not_include
"""

import json
from pathlib import Path

import dspy

from db.database import PatentDB


def _load_result(case_id: str, tool_name: str) -> dict:
    """data/results/{case_id}/{tool_name}.json 로드. 없으면 {}."""
    path = Path("data") / "results" / case_id / f"{tool_name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_eval_dataset(
    tool_name: str,
    db_path: str = "db/patent_agent.db",
) -> list[dspy.Example]:
    """DB에서 해당 Tool의 검증셋을 읽어 DSPy Example 리스트로 변환.

    Args:
        tool_name: "tool1", "tool2", ... "tool5"
        db_path: SQLite DB 파일 경로

    Returns:
        list[dspy.Example] — DSPy optimizer/evaluator에 바로 넘길 수 있는 형식
    """
    db = PatentDB(db_path)
    try:
        eval_records = db.get_evals_for_tool(tool_name)
    finally:
        db.close()

    examples = []
    for record in eval_records:
        expected = json.loads(record.expected_json)

        # Tool별 변환 매핑
        converter = _TOOL_CONVERTERS.get(tool_name)
        if converter:
            example = converter(expected, record.case_id, db_path)
            examples.append(example)

    return examples


def _convert_tool1(expected: dict, case_id: str, db_path: str) -> dspy.Example:
    """Tool 1 검증셋 변환.

    expected JSON 필드 → dspy.Example 필드:
    - "rejection_articles" → _expected_articles (정규식 검증용)
    - "prior_art_numbers" → _expected_numbers (정규식 검증용)
    - "rejected_claim_numbers" → _expected_claim_numbers (정규식 검증용)
    - "rejection_type" → _expected_type (자동 분류 검증용)
    """
    # 입력 데이터 로드 (DB에서 통지서 텍스트)
    db = PatentDB(db_path)
    try:
        case = db.get_case(case_id)
        if case:
            action = db.get_office_action(case.action_id)
            notice_text = action.notice_text if action else ""
        else:
            notice_text = ""
    finally:
        db.close()

    return dspy.Example(
        notice_text=notice_text,
        extracted_metadata="{}",
        _expected_articles=expected.get("rejection_articles", []),
        _expected_numbers=expected.get("prior_art_numbers", []),
        _expected_claim_numbers=expected.get("rejected_claim_numbers", []),
        _expected_type=expected.get("rejection_type", ""),
    ).with_inputs("notice_text", "extracted_metadata")


def _convert_tool2(expected: dict, case_id: str, db_path: str) -> dspy.Example:
    """Tool 2 검증셋 변환."""
    db = PatentDB(db_path)
    try:
        case = db.get_case(case_id)
        claims_text = ""
        if case:
            patent = db.get_patent(case.our_patent_id)
            if patent:
                claims_text = patent.claims_text
    finally:
        db.close()

    return dspy.Example(
        claims_text=claims_text,
        _expected_total=expected.get("total_claims", 0),
        _expected_independent=expected.get("independent_claims", []),
        _expected_deps=expected.get("dependent_claims", {}),
        _expected_element_count=len(expected.get("claim_1_elements", [])),
    ).with_inputs("claims_text")


def _convert_tool3(expected: dict, case_id: str, db_path: str) -> dspy.Example:
    """Tool 3 검증셋 변환.

    입력: Tool 2 중간 결과(독립항) + DB 상세설명
    """
    t2 = _load_result(case_id, "tool2")
    our_claims = [
        c for c in t2.get("our", {}).get("claims", [])
        if c.get("claim_type") == "독립항"
    ]
    prior_claims = [
        c
        for pd in t2.get("prior", [])
        for c in pd.get("claims", [])
        if c.get("claim_type") == "독립항"
    ]

    our_description = ""
    db = PatentDB(db_path)
    try:
        case = db.get_case(case_id)
        if case:
            patent = db.get_patent(case.our_patent_id)
            if patent:
                our_description = patent.description_text
    finally:
        db.close()

    return dspy.Example(
        our_claims=our_claims,
        prior_claims=prior_claims,
        our_description=our_description,
        _expected_matchings=expected.get("matchings", []),
    ).with_inputs("our_claims", "prior_claims", "our_description")


def _convert_tool4(expected: dict, case_id: str, db_path: str) -> dspy.Example:
    """Tool 4 검증셋 변환.

    입력: Tool 1/3 중간 결과
    """
    t1 = _load_result(case_id, "tool1")
    t3 = _load_result(case_id, "tool3")

    unmatched = []
    disputed = []
    for chart in t3.get("charts", []):
        for em in chart.get("element_matches", []):
            if em.get("match_level") == "없음":
                unmatched.append(em.get("our_element", {}))
            elif em.get("match_level") == "유사":
                disputed.append(em.get("our_element", {}))

    return dspy.Example(
        claim_chart_summary=t3.get("summary", ""),
        rejection_type=t1.get("rejection_type", "기타"),
        examiner_reasoning=t1.get("examiner_reasoning", ""),
        unmatched_elements=unmatched,
        disputed_elements=disputed,
        _must_include=expected.get("must_include", []),
    ).with_inputs(
        "claim_chart_summary", "rejection_type", "examiner_reasoning",
        "unmatched_elements", "disputed_elements",
    )


def _convert_tool5(expected: dict, case_id: str, db_path: str) -> dspy.Example:
    """Tool 5 검증셋 변환.

    입력: Tool 2/4 중간 결과 + DB 상세설명
    """
    t2 = _load_result(case_id, "tool2")
    t4 = _load_result(case_id, "tool4")

    original_claim = ""
    for c in t2.get("our", {}).get("claims", []):
        if c.get("claim_type") == "독립항":
            original_claim = c.get("original_text", "")
            break

    description_text = ""
    db = PatentDB(db_path)
    try:
        case = db.get_case(case_id)
        if case:
            patent = db.get_patent(case.our_patent_id)
            if patent:
                description_text = patent.description_text
    finally:
        db.close()

    return dspy.Example(
        original_claim=original_claim,
        strategy=t4.get("strategy", ""),
        description_text=description_text,
        _must_include=expected.get("must_include", []),
        _must_not_include=expected.get("must_not_include", []),
    ).with_inputs("original_claim", "strategy", "description_text")


# Tool별 변환 함수 매핑
_TOOL_CONVERTERS = {
    "tool1": _convert_tool1,
    "tool2": _convert_tool2,
    "tool3": _convert_tool3,
    "tool4": _convert_tool4,
    "tool5": _convert_tool5,
}
