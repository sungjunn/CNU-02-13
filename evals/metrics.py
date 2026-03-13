"""Tool별 평가 함수 (DSPy metric 호환).

모든 metric 함수는 (example, prediction, trace=None) -> float 형식.
DSPy optimizer가 직접 사용할 수 있다.

Tool 1~3: 확정적 비교 (정확도)
Tool 4~5: LLM-as-Judge 체크리스트

=== LLM-as-Judge 설정 ===
JUDGE_MODEL 환경변수로 Judge 모델을 지정한다 (기본: openai/gpt-4o-mini).
파이프라인 LLM과 다른 모델을 사용하여 self-preference bias를 방지한다.
OPENAI_API_KEY 또는 ANTHROPIC_API_KEY가 필요하다.
미설정 시 문자열 포함 여부로 폴백한다.
"""

import os
import dspy
from dotenv import load_dotenv

load_dotenv()

# Judge LM 전역 캐시 — 매 호출마다 새로 생성하지 않음
_JUDGE_LM: dspy.LM | None = None


def _get_judge_lm() -> dspy.LM | None:
    """Judge LM을 한 번만 생성하여 캐시로 반환.

    JUDGE_MODEL 환경변수로 모델 지정 (기본: openai/gpt-4o-mini).
    API key 없으면 None 반환 → 폴백 사용.

    지원 프리픽스: openai/ anthropic/ openrouter/ factchat/
    """
    global _JUDGE_LM
    if _JUDGE_LM is not None:
        return _JUDGE_LM

    model = os.getenv("JUDGE_MODEL", "openai/gpt-4o-mini")

    try:
        if model.startswith("factchat/"):
            model_name = model[len("factchat/"):]
            api_key = os.getenv("FACTCHAT_API_KEY", "")
            if not api_key:
                return None
            base_url = os.getenv("FACTCHAT_BASE_URL",
                                 "https://factchat-cloud.mindlogic.ai/v1/gateway")
            _JUDGE_LM = dspy.LM(f"openai/{model_name}",
                                api_key=api_key, api_base=base_url)
        elif model.startswith("openrouter/"):
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not api_key:
                return None
            _JUDGE_LM = dspy.LM(model, api_key=api_key)
        elif "anthropic" in model:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                return None
            _JUDGE_LM = dspy.LM(model, api_key=api_key)
        else:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return None
            _JUDGE_LM = dspy.LM(model, api_key=api_key)

        return _JUDGE_LM
    except Exception:
        return None


# =============================================================================
# Tool 1 — 통지서 분석 평가 (확정적)
# =============================================================================

def tool1_metric(example, prediction, trace=None) -> float:
    """Tool 1 평가: 정확도 기반.

    비교 항목 (각 25%):
    1. 거절 법조항 일치율 (리스트 비교)
    2. 선행특허 번호 일치율 (리스트 비교)
    3. 해당 청구항 번호 일치율 (리스트 비교)
    4. 거절 유형 일치 (단일값 비교)

    최종 점수 = 4개 항목의 평균 (0.0 ~ 1.0)
    """
    scores = []

    # 1. 거절 법조항
    expected_articles = set(getattr(example, "_expected_articles", []))
    predicted_articles = set(getattr(prediction, "rejection_articles", []))
    if expected_articles:
        scores.append(_set_similarity(expected_articles, predicted_articles))
    else:
        scores.append(1.0)

    # 2. 선행특허 번호
    expected_numbers = set(getattr(example, "_expected_numbers", []))
    predicted_numbers = set(getattr(prediction, "prior_art_numbers", []))
    if expected_numbers:
        scores.append(_set_similarity(expected_numbers, predicted_numbers))
    else:
        scores.append(1.0)

    # 3. 청구항 번호
    expected_claims = set(getattr(example, "_expected_claim_numbers", []))
    predicted_claims = set(getattr(prediction, "rejected_claim_numbers", []))
    if expected_claims:
        scores.append(_set_similarity(expected_claims, predicted_claims))
    else:
        scores.append(1.0)

    # 4. 거절 유형
    expected_type = getattr(example, "_expected_type", None)
    predicted_type = getattr(prediction, "rejection_type", None)
    if expected_type:
        scores.append(1.0 if expected_type == predicted_type else 0.0)
    else:
        scores.append(1.0)

    return sum(scores) / len(scores)


# =============================================================================
# Tool 2 — 청구항 파싱 평가 (확정적)
# =============================================================================

def tool2_metric(example, prediction, trace=None) -> float:
    """Tool 2 평가: 파싱 정확도.

    비교 항목 (가중치):
    1. 청구항 총 개수 일치 (20%)
    2. 독립항 분류 정확도 (30%)
    3. 종속 관계 정확도 (30%)
    4. 구성요소 분리 개수 ±1 허용 (20%)

    최종 점수 = 가중 평균 (0.0 ~ 1.0)
    """
    weights = [0.2, 0.3, 0.3, 0.2]
    scores = []

    # 1. 총 개수
    expected_total = getattr(example, "_expected_total", 0)
    predicted_total = getattr(prediction, "total_claims", 0)
    scores.append(1.0 if expected_total == predicted_total else 0.0)

    # 2. 독립항 분류
    expected_indep = set(getattr(example, "_expected_independent", []))
    predicted_indep = set(getattr(prediction, "independent_claims", []))
    if expected_indep:
        scores.append(_set_similarity(expected_indep, predicted_indep))
    else:
        scores.append(1.0)

    # 3. 종속 관계
    expected_deps = getattr(example, "_expected_deps", {})
    predicted_deps = getattr(prediction, "dependent_claims", {})
    if expected_deps:
        match_count = sum(
            1 for k, v in expected_deps.items()
            if str(k) in predicted_deps and predicted_deps[str(k)] == v
        )
        scores.append(match_count / len(expected_deps))
    else:
        scores.append(1.0)

    # 4. 구성요소 개수 (±1 허용)
    expected_el_count = getattr(example, "_expected_element_count", None)
    if expected_el_count is not None:
        claims = getattr(prediction, "claims", [])
        if claims:
            actual_count = len(claims[0].get("elements", []))
            scores.append(1.0 if abs(actual_count - expected_el_count) <= 1 else 0.0)
        else:
            scores.append(0.0)
    else:
        scores.append(1.0)

    return sum(w * s for w, s in zip(weights, scores))


# =============================================================================
# Tool 3 — Claim Chart 매칭 평가 (확정적)
# =============================================================================

def tool3_metric(example, prediction, trace=None) -> float:
    """Tool 3 평가: Claim Chart 매칭 정확도.

    구성요소별 매칭 수준(동일/유사/없음)이 expected와 일치하는 비율.
    최종 점수 = 일치 요소 / 전체 요소 (0.0 ~ 1.0)
    """
    expected_matchings = getattr(example, "_expected_matchings", [])
    predicted_charts = getattr(prediction, "charts", [])

    if not expected_matchings:
        return 1.0

    total = 0
    correct = 0

    for exp in expected_matchings:
        exp_our_claim = exp.get("our_claim")
        exp_prior_claim = exp.get("prior_claim")

        # 대응하는 predicted chart 찾기
        pred_chart = None
        for pc in predicted_charts:
            if (pc.get("our_claim_number") == exp_our_claim and
                    pc.get("prior_claim_number") == exp_prior_claim):
                pred_chart = pc
                break

        if pred_chart is None:
            total += len(exp.get("element_matches", []))
            continue

        for exp_em in exp.get("element_matches", []):
            total += 1
            exp_level = exp_em.get("match_level", "")
            # 대응 요소 찾기
            for pred_em in pred_chart.get("element_matches", []):
                pred_our = pred_em.get("our_element", {})
                if pred_our.get("text", "") == exp_em.get("our_element", ""):
                    if pred_em.get("match_level", "") == exp_level:
                        correct += 1
                    break

    return correct / total if total > 0 else 1.0


# =============================================================================
# Tool 4 — 전략 평가 (LLM-as-Judge)
# =============================================================================

def tool4_metric(example, prediction, trace=None) -> float:
    """Tool 4 평가: 체크리스트 기반 (LLM-as-Judge).

    expected의 must_include 항목 각각에 대해
    LLM-as-Judge가 prediction에 포함되어 있는지 yes/no 판정.

    최종 점수 = 충족 항목 / 전체 항목 (0.0 ~ 1.0)

    === LLM-as-Judge bias 완화 규칙 ===
    1. Judge 모델은 파이프라인 LLM과 다른 모델 사용
    2. yes/no만 답하게 설계 (verbosity bias 방지)
    3. 여유가 있으면 2회 반복하여 일관성 확인
    """
    must_include = getattr(example, "_must_include", [])
    if not must_include:
        return 1.0

    # prediction 텍스트 합치기
    strategy_text = getattr(prediction, "strategy", "")
    rebuttal_text = str(getattr(prediction, "rebuttal_points", ""))
    full_text = f"{strategy_text}\n{rebuttal_text}"

    score = _judge_checklist(full_text, must_include)
    return score


# =============================================================================
# Tool 5 — 보정안 평가 (체크리스트 + 근거)
# =============================================================================

def tool5_metric(example, prediction, trace=None) -> float:
    """Tool 5 평가: 체크리스트 + 근거 확인.

    1. must_include 체크리스트 충족률 (40%)
    2. must_not_include 체크 — 포함되면 감점 (20%)
    3. 상세설명 근거 존재 비율 (20%)
    4. diff가 비어있지 않은지 (20%)

    최종 점수 = 4개 항목의 가중 평균
    """
    weights = [0.4, 0.2, 0.2, 0.2]
    scores = []

    # prediction 텍스트 합치기
    amended = getattr(prediction, "amended_claim", "")
    added = str(getattr(prediction, "added_elements", ""))
    full_text = f"{amended}\n{added}"

    # 1. must_include 충족률
    must_include = getattr(example, "_must_include", [])
    if must_include:
        scores.append(_judge_checklist(full_text, must_include))
    else:
        scores.append(1.0)

    # 2. must_not_include 체크
    must_not_include = getattr(example, "_must_not_include", [])
    if must_not_include:
        violations = _judge_checklist(full_text, must_not_include)
        scores.append(1.0 - violations)  # 포함되면 감점
    else:
        scores.append(1.0)

    # 3. 상세설명 근거 존재 비율
    basis = getattr(prediction, "description_basis", [])
    if basis:
        scores.append(1.0)  # 근거가 있으면 만점
    else:
        scores.append(0.0)

    # 4. diff 비어있지 않은지
    diff_text = getattr(prediction, "diff_text", "")
    scores.append(1.0 if diff_text.strip() else 0.0)

    return sum(w * s for w, s in zip(weights, scores))


# =============================================================================
# 헬퍼 함수
# =============================================================================

def _set_similarity(expected: set, predicted: set) -> float:
    """두 집합의 유사도 (Jaccard 기반).

    교집합 / 합집합. 둘 다 비어있으면 1.0.
    """
    if not expected and not predicted:
        return 1.0
    intersection = expected & predicted
    union = expected | predicted
    return len(intersection) / len(union)


def _judge_checklist(text: str, checklist: list[str]) -> float:
    """LLM-as-Judge로 체크리스트 평가.

    각 항목에 대해 텍스트에 포함되어 있는지 판정.
    Judge LM이 설정되지 않았거나 호출 실패 시 문자열 포함 여부로 폴백.

    === Bias 완화 규칙 ===
    - JUDGE_MODEL로 파이프라인 LLM과 다른 모델 사용 (self-preference bias 방지)
    - yes/no만 답하게 설계 (verbosity bias 방지)

    Returns:
        충족 비율 (0.0 ~ 1.0)
    """
    if not checklist:
        return 1.0

    judge_lm = _get_judge_lm()
    fulfilled = 0

    for item in checklist:
        if judge_lm is None:
            # Judge LM 미설정 → 문자열 포함 여부로 폴백
            if item in text:
                fulfilled += 1
            continue

        try:
            judge_prompt = (
                f"다음 텍스트에 '{item}'과 의미적으로 동일한 내용이 포함되어 있는가?\n"
                f"텍스트: {text[:3000]}\n"
                f"답변: yes 또는 no만 답하시오."
            )
            # 전역 LM을 덮어쓰지 않도록 with dspy.context 사용
            with dspy.context(lm=judge_lm):
                response = judge_lm(judge_prompt)

            answer = str(response).strip().lower()
            if "yes" in answer:
                fulfilled += 1

        except Exception:
            # 호출 실패 시 문자열 포함 여부로 폴백
            if item in text:
                fulfilled += 1

    return fulfilled / len(checklist)
