"""메인 파이프라인 — Tool 1 → 2 → 3 → 4 → 5 → 6 순서로 실행.

사용법:
    uv run python pipeline.py --case case_01
    uv run python pipeline.py --case case_01 --start-from tool3
    uv run python pipeline.py --case case_01 --interactive

동작:
1. DB에서 케이스 정보 + 입력 데이터 로드
2. Tool 1 → 2 → 3 → 4 → 5 → 6 순서로 실행
3. 각 Tool 실행 후: Pydantic 검증 + 가드레일 + 중간 결과 저장
4. --start-from: 이전 Tool 결과를 파일에서 로드하여 지정 Tool부터 재실행
5. --interactive: Tool 3, Tool 5 완료 후 사용자 확인 대기
"""

import argparse
import json
import os
import sys
from pathlib import Path

import dspy
from dotenv import load_dotenv

from db.database import PatentDB
from schemas.common import MatchLevel


def setup_lm():
    """DSPy LM 설정.

    .env에서 API 키 로드 후 LM 설정.
    DEFAULT_MODEL 환경변수로 모델 변경 가능.

    지원 프리픽스:
        anthropic/...   → ANTHROPIC_API_KEY
        openai/...      → OPENAI_API_KEY
        openrouter/...  → OPENROUTER_API_KEY
        factchat/...    → FACTCHAT_API_KEY + FACTCHAT_BASE_URL
                          (OpenAI 호환 엔드포인트, 프리픽스는 모델명에서 제거)
    """
    load_dotenv()

    model = os.getenv("DEFAULT_MODEL", "anthropic/claude-sonnet-4-20250514")

    if model.startswith("factchat/"):
        model_name = model[len("factchat/"):]
        api_key = os.getenv("FACTCHAT_API_KEY")
        base_url = os.getenv("FACTCHAT_BASE_URL",
                             "https://factchat-cloud.mindlogic.ai/v1/gateway")
        lm = dspy.LM(f"openai/{model_name}", api_key=api_key, api_base=base_url)
    elif model.startswith("openrouter/"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        lm = dspy.LM(model, api_key=api_key)
    elif "anthropic" in model:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        lm = dspy.LM(model, api_key=api_key)
    elif "openai" in model:
        api_key = os.getenv("OPENAI_API_KEY")
        lm = dspy.LM(model, api_key=api_key)
    else:
        lm = dspy.LM(model)

    dspy.configure(lm=lm)
    print(f"[LM] 모델: {model}")


def load_optimized_module(tool_name: str):
    """최적화된 Module이 있으면 로드, 없으면 기본 Module 반환.

    optimized_modules/{tool_name}/ 폴더에 저장된 DSPy 최적화 결과를 사용한다.
    최적화 결과가 없으면 기본 Module을 그대로 사용한다.

    Args:
        tool_name: "tool1" ~ "tool5"

    Returns:
        DSPy Module (최적화본 또는 기본)
    """
    import importlib

    # 기본 Module 매핑
    _module_map = {
        "tool1": ("modules.tool1_module", "NoticeAnalyzerModule"),
        "tool2": ("modules.tool2_module", "ClaimParserModule"),
        "tool3": ("modules.tool3_module", "ClaimChartModule"),
        "tool4": ("modules.tool4_module", "StrategyModule"),
        "tool5": ("modules.tool5_module", "AmendmentModule"),
    }

    mod_path, cls_name = _module_map[tool_name]
    module_cls = getattr(importlib.import_module(mod_path), cls_name)
    base_module = module_cls()

    # 최적화 결과 경로 확인
    optimized_dir = Path("optimized_modules") / tool_name
    if optimized_dir.exists() and any(optimized_dir.iterdir()):
        try:
            base_module.load(str(optimized_dir))
            print(f"  [최적화 로드] {tool_name}: {optimized_dir}")
        except Exception as e:
            print(f"  [경고] {tool_name} 최적화 모듈 로드 실패, 기본 모듈 사용: {e}")
    else:
        print(f"  [기본 모듈] {tool_name}: 최적화 결과 없음")

    return base_module


def load_case_data(case_id: str, db_path: str = "db/patent_agent.db") -> dict:
    """DB에서 케이스 데이터 로드.

    Returns:
        {
            "notice_text": "...",
            "our_claims_text": "...",
            "our_description_text": "...",
            "prior_art_claims": [{"doc_id": "...", "claims_text": "..."}],
        }
    """
    db = PatentDB(db_path)
    try:
        case = db.get_case(case_id)
        if case is None:
            raise ValueError(f"케이스 '{case_id}'를 찾을 수 없습니다. 먼저 db.loader로 데이터를 로드하세요.")

        action = db.get_office_action(case.action_id)
        our_patent = db.get_patent(case.our_patent_id)

        # 선행특허 로드
        prior_arts = []
        if action:
            for pa_id in action.prior_art_ids:
                pa = db.get_patent(pa_id)
                if pa:
                    prior_arts.append({
                        "doc_id": pa.doc_id,
                        "claims_text": pa.claims_text,
                        "description_text": pa.description_text,
                    })

        return {
            "notice_text": action.notice_text if action else "",
            "our_claims_text": our_patent.claims_text if our_patent else "",
            "our_description_text": our_patent.description_text if our_patent else "",
            "prior_art_claims": prior_arts,
        }
    finally:
        db.close()


def save_intermediate(case_id: str, tool_name: str, result: dict):
    """중간 결과를 JSON으로 저장."""
    result_dir = Path("data") / "results" / case_id
    result_dir.mkdir(parents=True, exist_ok=True)
    path = result_dir / f"{tool_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  → 저장: {path}")


def load_intermediate(case_id: str, tool_name: str) -> dict | None:
    """이전 중간 결과를 로드."""
    path = Path("data") / "results" / case_id / f"{tool_name}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def run_pipeline(case_id: str, start_from: str = "tool1", interactive: bool = False):
    """파이프라인 실행.

    Args:
        case_id: 케이스 ID (예: "case_01")
        start_from: 시작 Tool ("tool1" ~ "tool6")
        interactive: True면 Tool 3, 5 완료 후 사용자 확인 대기
    """
    print(f"\n{'='*60}")
    print(f"  특허 심사대응 파이프라인 — 케이스: {case_id}")
    print(f"{'='*60}\n")

    # 데이터 로드
    data = load_case_data(case_id)

    # Tool import
    from tools.tool1_notice_analyzer import NoticeAnalyzerTool
    from tools.tool2_claim_parser import ClaimParserTool
    from tools.tool3_claim_chart import ClaimChartTool
    from tools.tool4_strategy import StrategyTool
    from tools.tool5_amendment import AmendmentTool
    from tools.tool6_version_manager import VersionManagerTool
    from schemas.tool1 import NoticeAnalysisInput
    from schemas.tool2 import ClaimParseInput
    from schemas.tool3 import ClaimChartInput
    from schemas.tool4 import StrategyInput
    from schemas.tool5 import AmendmentInput

    # 최적화 모듈 적용 — 각 Tool의 내부 module을 교체
    print("\n[모듈 로드]")
    tool1 = NoticeAnalyzerTool(); tool1.module = load_optimized_module("tool1")
    tool2 = ClaimParserTool();    tool2.module = load_optimized_module("tool2")
    tool3 = ClaimChartTool();     tool3.module = load_optimized_module("tool3")
    tool4 = StrategyTool();       tool4.module = load_optimized_module("tool4")
    tool5 = AmendmentTool();      tool5.module = load_optimized_module("tool5")

    tool_order = ["tool1", "tool2", "tool3", "tool4", "tool5", "tool6"]
    start_idx = tool_order.index(start_from) if start_from in tool_order else 0

    # 이전 결과 로드 (start_from 사용 시)
    results = {}
    if start_idx > 0:
        for prev_tool in tool_order[:start_idx]:
            prev_result = load_intermediate(case_id, prev_tool)
            if prev_result:
                results[prev_tool] = prev_result
                print(f"[로드] {prev_tool} 이전 결과")
            else:
                print(f"[경고] {prev_tool} 이전 결과 없음")

    # === Tool 1: 통지서 분석 ===
    if start_idx <= 0:
        print("\n--- Tool 1: 통지서 분석 ---")
        result1 = tool1.run(NoticeAnalysisInput(
            notice_text=data["notice_text"],
            case_id=case_id,
        ))
        results["tool1"] = result1.model_dump()
        save_intermediate(case_id, "tool1", results["tool1"])
        print(f"  거절 유형: {result1.rejection_type.value}")
        print(f"  법조항: {result1.rejection_articles}")
        print(f"  선행특허: {result1.prior_art_numbers}")

    # === Tool 2: 청구항 파싱 ===
    if start_idx <= 1:
        print("\n--- Tool 2: 청구항 파싱 ---")
        # 당사 청구항 파싱
        result2_our = tool2.run(ClaimParseInput(claims_text=data["our_claims_text"]))
        results["tool2_our"] = result2_our.model_dump()

        # 가드레일: 독립항 0개 → 중단
        if not result2_our.independent_claims:
            print("  ❌ 독립항이 없습니다. 파이프라인 중단.")
            return results

        # 선행특허 청구항 파싱
        prior_parsed = []
        for pa in data["prior_art_claims"]:
            result2_prior = tool2.run(ClaimParseInput(claims_text=pa["claims_text"]))
            prior_parsed.append(result2_prior.model_dump())

        results["tool2_prior"] = prior_parsed
        save_intermediate(case_id, "tool2", {
            "our": results["tool2_our"],
            "prior": results["tool2_prior"],
        })
        print(f"  당사 청구항: {result2_our.total_claims}개 (독립항: {result2_our.independent_claims})")

    # === Tool 3: Claim Chart 생성 ===
    if start_idx <= 2:
        print("\n--- Tool 3: Claim Chart 생성 ---")
        # 당사 독립항만 추출
        our_data = results.get("tool2_our", {})
        our_independent = [
            c for c in our_data.get("claims", [])
            if c.get("claim_type") == "독립항"
        ]

        # 선행특허 독립항
        prior_data_list = results.get("tool2_prior", [])
        prior_independent = []
        for pd in prior_data_list:
            for c in pd.get("claims", []):
                if c.get("claim_type") == "독립항":
                    prior_independent.append(c)

        result3 = tool3.run(ClaimChartInput(
            our_claims=our_independent,
            prior_claims=prior_independent,
            our_description=data["our_description_text"],
        ))
        results["tool3"] = result3.model_dump()
        save_intermediate(case_id, "tool3", results["tool3"])

        # 가드레일: 모든 매칭이 "동일" → 경고
        all_identical = all(
            em.match_level == MatchLevel.IDENTICAL
            for chart in result3.charts
            for em in chart.element_matches
        )
        if all_identical:
            print("  ⚠️ 경고: 모든 매칭이 '동일'입니다. 결과를 재검토하세요.")

        print(f"  {result3.summary}")

        if interactive:
            input("\n  [확인] Claim Chart를 검토하고 Enter를 누르세요...")

    # === Tool 4: 전략 생성 ===
    if start_idx <= 3:
        print("\n--- Tool 4: 전략 생성 ---")
        t1 = results.get("tool1", {})
        t3 = results.get("tool3", {})

        # 미매칭/유사 요소 추출
        unmatched = []
        disputed = []
        for chart in t3.get("charts", []):
            for em in chart.get("element_matches", []):
                if em.get("match_level") == "없음":
                    unmatched.append(em.get("our_element", {}))
                elif em.get("match_level") == "유사":
                    disputed.append(em.get("our_element", {}))

        result4 = tool4.run(StrategyInput(
            claim_chart_summary=t3.get("summary", ""),
            rejection_type=t1.get("rejection_type", "기타"),
            examiner_reasoning=t1.get("examiner_reasoning", ""),
            unmatched_elements=unmatched,
            disputed_elements=disputed,
        ))
        results["tool4"] = result4.model_dump()
        save_intermediate(case_id, "tool4", results["tool4"])
        print(f"  반박 포인트: {len(result4.rebuttal_points)}개")

    # === Tool 5: 보정안 생성 ===
    if start_idx <= 4:
        print("\n--- Tool 5: 보정안 생성 ---")
        # 당사 제1항 (독립항) 원문
        our_claims = results.get("tool2_our", {}).get("claims", [])
        original_claim = ""
        for c in our_claims:
            if c.get("claim_type") == "독립항":
                original_claim = c.get("original_text", "")
                break

        t4 = results.get("tool4", {})

        result5 = tool5.run(AmendmentInput(
            original_claim=original_claim,
            strategy=t4.get("strategy", ""),
            description_text=data["our_description_text"],
        ))
        results["tool5"] = result5.model_dump()
        save_intermediate(case_id, "tool5", results["tool5"])

        # 가드레일: 보정안 빈 문자열 → 중단
        if not result5.amended_claim.strip():
            print("  ❌ 보정안이 비어있습니다. 파이프라인 중단.")
            return results

        # 가드레일: 원본과 동일 → 경고
        if result5.amended_claim.strip() == original_claim.strip():
            print("  ⚠️ 경고: 보정안이 원본과 동일합니다.")

        if result5.warnings:
            for w in result5.warnings:
                print(f"  {w}")

        if interactive:
            input("\n  [확인] 보정안을 검토하고 Enter를 누르세요...")

    # === Tool 6: 차수 관리 ===
    if start_idx <= 5:
        print("\n--- Tool 6: 차수 저장 ---")
        from tools.tool6_version_manager import VersionManagerTool
        tool6 = VersionManagerTool()

        t1 = results.get("tool1", {})
        t4 = results.get("tool4", {})
        t5 = results.get("tool5", {})
        our_claims = results.get("tool2_our", {}).get("claims", [])

        version = tool6.save_version(
            case_id=case_id,
            rejection_summary=t1.get("examiner_reasoning", ""),
            strategy_summary=t4.get("strategy", "")[:500],
            original_claim=our_claims[0].get("original_text", "") if our_claims else "",
            amended_claim=t5.get("amended_claim", ""),
            diff_text=t5.get("diff_text", ""),
        )
        print(f"  차수 {version.version} 저장 완료 ({version.timestamp})")

    print(f"\n{'='*60}")
    print("  파이프라인 완료!")
    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="특허 심사대응 파이프라인")
    parser.add_argument("--case", required=True, help="케이스 ID (예: case_01)")
    parser.add_argument("--start-from", default="tool1",
                        choices=["tool1", "tool2", "tool3", "tool4", "tool5", "tool6"],
                        help="시작 Tool (이전 결과 로드)")
    parser.add_argument("--interactive", action="store_true",
                        help="Tool 3, 5 완료 후 사용자 확인 대기")
    parser.add_argument("--db-path", default="db/patent_agent.db")
    args = parser.parse_args()

    setup_lm()
    run_pipeline(args.case, args.start_from, args.interactive)


if __name__ == "__main__":
    main()
