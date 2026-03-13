# Eval 데이터셋 구축 & 프롬프트 최적화 가이드

## 전체 흐름

```
① expected JSON 작성
    ↓
② DB에 삽입 (PatentDB.insert_eval)
    ↓
③ eval_runner로 현재 Module 점수 확인
    ↓
④ optimize.py로 MIPROv2 최적화 실행
    ↓
⑤ optimized_modules/{tool}/ 저장
    ↓
⑥ pipeline/run_agent 실행 시 자동 로드
```

---

## 1. Eval 데이터셋이란

`eval_datasets` 테이블에 저장된 **입력 케이스 + 기대 출력 쌍**입니다.

```
eval_datasets 테이블
├── eval_id      (고유 ID)
├── case_id      (case_records.case_id FK)
├── tool_name    ("tool1" ~ "tool5")
├── expected_json (Tool 기대 출력 JSON)
└── eval_type    ("validation" | "test")
```

`case_id`를 통해 입력 데이터는 `patent_documents` / `office_actions`에서 읽어오고,
`expected_json`이 정답 레이블 역할을 합니다.

---

## 2. Tool별 expected JSON 형식

### Tool 1 — 통지서 분석

```json
{
  "rejection_articles": ["제29조 제1항"],
  "prior_art_numbers": ["10-2021-0123456", "10-2019-0098765"],
  "rejected_claim_numbers": ["1", "3", "5"],
  "rejection_type": "신규성",
  "examiner_reasoning": "청구항 1의 A 구성요소는 선행특허 1의 B에 대응하며..."
}
```

**작성 팁:**
- `rejection_articles`는 통지서 원문에서 법조항 번호를 그대로 복사
- `rejection_type`은 `"신규성"` / `"진보성"` / `"기타"` 세 가지만 허용
- `examiner_reasoning`은 심사관 논리 핵심 1~2문장으로 요약 (LLM-as-Judge로 평가)

---

### Tool 2 — 청구항 파싱

```json
{
  "total_claims": 10,
  "independent_claims": [1, 5, 9],
  "dependent_claims": {
    "2": 1,
    "3": 1,
    "4": 2,
    "6": 5
  },
  "claim_1_elements": [
    "트레드부에 형성된 홈 패턴",
    "사이드월부를 구성하는 고무층",
    "비드부에 삽입된 와이어"
  ]
}
```

**작성 팁:**
- `dependent_claims`는 `{"종속항번호": 상위항번호}` 형식
- `claim_1_elements`는 독립항 1항의 구성요소 리스트 (세미콜론 기준)
- 구성요소 분리 개수는 ±1 허용 기준으로 평가되므로 엄격하지 않아도 됨

---

### Tool 3 — Claim Chart 매칭

```json
{
  "matchings": [
    {
      "our_claim": 1,
      "prior_claim": 1,
      "element_matches": [
        {
          "our_element": "트레드부에 형성된 홈 패턴",
          "match_level": "동일"
        },
        {
          "our_element": "사이드월부를 구성하는 고무층",
          "match_level": "유사"
        },
        {
          "our_element": "비드부에 삽입된 와이어",
          "match_level": "없음"
        }
      ]
    }
  ]
}
```

**작성 팁:**
- `match_level`은 `"동일"` / `"유사"` / `"없음"` 세 가지만 허용
- `our_element` 텍스트는 Tool 2 결과의 element 텍스트와 **정확히 일치**해야 점수 계산 가능
- 케이스당 1~2쌍 (our_claim × prior_claim) 이면 충분

---

### Tool 4 — 전략 생성

```json
{
  "must_include": [
    "비드부 와이어는 선행특허에 개시되지 않은 고유 구성요소",
    "사이드월 고무층의 두께 차이는 기술적으로 유의미한 차이",
    "출원인의 발명은 선행특허와 결합해도 자명하지 않음"
  ]
}
```

**작성 팁:**
- LLM-as-Judge가 `must_include` 각 항목이 전략 텍스트에 **의미적으로** 포함되는지 판단
- 항목은 구체적이고 독립적으로 — "전략이 좋다" 같은 모호한 항목은 피할 것
- 3~5개 항목이 적정 (너무 많으면 평가 불안정)

---

### Tool 5 — 보정안 생성

```json
{
  "must_include": [
    "비드부에 삽입된 와이어의 직경 범위 한정",
    "상세설명 단락 [0042]의 수치 범위를 청구항에 반영"
  ],
  "must_not_include": [
    "선행특허에 개시된 홈 패턴 형상 그대로 사용",
    "출원일 이후 공개된 기술 언급"
  ]
}
```

**작성 팁:**
- `must_not_include`는 보정 시 절대 포함하면 안 되는 내용 (신규사항 추가, 청구범위 확장 등)
- `must_include`는 상세설명에 근거가 있는 구체적인 한정 사항
- Tool 5는 법적 유효성이 중요하므로 특허 전문가 검토 후 작성 권장

---

## 3. DB에 eval 데이터 삽입

직접 Python 스크립트로 삽입합니다.

```python
# scripts/insert_eval.py 등 별도 스크립트 작성
import json
from db.database import PatentDB
from schemas.db_models import EvalDataset

db = PatentDB("db/patent_agent.db")

# Tool 1 eval 데이터 삽입
db.insert_eval(EvalDataset(
    eval_id="eval_case01_tool1_v1",
    case_id="case_01",           # case_records에 이미 있어야 함
    tool_name="tool1",
    expected_json=json.dumps({
        "rejection_articles": ["제29조 제1항"],
        "prior_art_numbers": ["10-2021-0123456"],
        "rejected_claim_numbers": ["1"],
        "rejection_type": "신규성",
        "examiner_reasoning": "청구항 1의 A 구성요소는 선행특허 1에 개시됨",
    }, ensure_ascii=False),
    eval_type="validation",
))

db.close()
```

**eval_id 규칙:** `eval_{case_id}_{tool_name}_{버전}` 으로 관리하면 추적이 쉽습니다.

---

## 4. 데이터셋 구축 팁

### 최소 권장 수량

| Tool | 최소 | 권장 | 이유 |
|------|------|------|------|
| Tool 1 | 5건 | 15건+ | 거절 유형별 균형 (신규성/진보성/기타) |
| Tool 2 | 5건 | 10건+ | 청구항 수 다양성 (3항/10항/20항) |
| Tool 3 | 5건 | 10건+ | 매칭 수준 분포 (동일/유사/없음 혼합) |
| Tool 4 | 5건 | 10건+ | 전략 유형별 |
| Tool 5 | 5건 | 10건+ | 보정 강도별 (경미/중간/대폭) |

### 케이스 선택 기준

```
좋은 케이스:                          피해야 할 케이스:
✓ 실제 특허 심사 사례                 ✗ 너무 단순한 (청구항 1개짜리)
✓ 거절 유형이 명확한 케이스           ✗ 결과가 애매한 케이스
✓ 선행특허가 1~3개 있는 케이스       ✗ 선행특허 5개 이상 (평가 복잡도 폭증)
✓ 다양한 기술 분야 혼합              ✗ 동일 기술 분야만 (편향)
```

### 데이터 품질 확인

작성 후 아래를 수동으로 검증:
- `rejection_type`이 통지서 원문과 실제로 일치하는가
- `match_level` 판단이 특허 전문가 기준에 맞는가
- `must_include` 항목이 상세설명에 실제 근거가 있는가

---

## 5. Eval 실행 (현재 점수 확인)

```bash
# 특정 Tool 평가
uv run python -m evals.eval_runner --tool tool1

# 전체 Tool 평가
uv run python -m evals.eval_runner --all

# 특정 케이스만 평가
uv run python -m evals.eval_runner --tool tool1 --case case_01
```

결과는 `evals/results/tool1_20260312_143022.json`에 저장됩니다.

```json
{
  "tool": "tool1",
  "overall_score": 0.7250,
  "num_examples": 8,
  "scores": [1.0, 0.75, 0.5, 0.75, ...],
  "failures": [
    {"index": 2, "score": 0.5, ...}
  ]
}
```

---

## 6. 코드 연결 구조

```
eval 데이터 흐름:

DB.eval_datasets
    ↓ load_eval_dataset("tool1")
evals/datasets.py → _convert_tool1()
    ↓
dspy.Example(
    notice_text="...",          ← DB에서 로드
    extracted_metadata="{}",
    _expected_articles=[...],   ← expected_json에서
    _expected_type="신규성",
).with_inputs("notice_text", "extracted_metadata")
    ↓
eval_runner.py
    input_fields = dict(example.inputs())   # notice_text, extracted_metadata
    prediction = module(**input_fields)      # Module 실행
    score = tool1_metric(example, prediction)
    ↓
evals/metrics.py → tool1_metric()
    _set_similarity(expected_articles, predicted_articles)
    ...
    return 0.0 ~ 1.0
```

**Tool 3~5 주의:** `data/results/{case_id}/` 폴더의 중간 결과 파일이 있어야 입력 데이터를 로드합니다.
평가 전에 `pipeline.py` 또는 `run_agent.py`를 먼저 실행해 중간 결과를 생성하세요.

```bash
# 먼저 파이프라인 실행 (중간 결과 생성)
uv run python pipeline.py --case case_01

# 그 후 Tool 3~5 평가 가능
uv run python -m evals.eval_runner --tool tool3
```

---

## 7. MIPROv2 최적화 실행

```bash
# 기본 (medium 강도)
uv run python -m evals.optimize --tool tool1

# light — LLM 호출 최소 (빠름, 개선 제한적)
uv run python -m evals.optimize --tool tool1 --auto light

# heavy — LLM 호출 최대 (느림, 최대 개선)
uv run python -m evals.optimize --tool tool1 --auto heavy
```

### 강도별 LLM 호출 횟수 (대략)

| auto | 호출 횟수 | 소요 시간 | 적합한 상황 |
|------|----------|----------|------------|
| light | 10~30회 | 5~15분 | 빠른 실험, 데이터 적을 때 |
| medium | 30~100회 | 15~60분 | 일반적인 사용 |
| heavy | 100~300회 | 1~3시간 | 최종 배포 전 |

### 최적화 후 결과

```
optimized_modules/
└── tool1/
    └── (DSPy가 저장하는 파일들)
        ├── 최적화된 instruction (프롬프트)
        └── 선택된 few-shot 예시
```

다음 `pipeline.py` / `run_agent.py` 실행 시 `load_optimized_module("tool1")`이
자동으로 이 폴더를 감지해서 로드합니다.

### 최적화 전후 비교 예시

```
최적화 전 점수: 0.6250
최적화 후 점수: 0.8500
개선: 0.6250 → 0.8500 (+0.2250)
```

---

## 8. 버전 관리

최적화 결과는 git으로 관리 권장:

```bash
git add optimized_modules/tool1/
git commit -m "tool1 프롬프트 최적화 v2 - 법조항 추출 0.63→0.85"
```

되돌릴 때:
```bash
git checkout HEAD~1 -- optimized_modules/tool1/
```

---

## 9. 권장 작업 순서 (처음 시작할 때)

```
1. case_01 데이터 로드
   python -m db.loader --input data/case_01/

2. pipeline 실행 (중간 결과 생성)
   python pipeline.py --case case_01

3. Tool 1부터 eval 데이터 작성 → DB 삽입

4. 점수 확인
   python -m evals.eval_runner --tool tool1

5. 점수가 낮으면 데이터 추가 수집

6. 데이터 10건+ 확보 후 최적화
   python -m evals.optimize --tool tool1 --auto light

7. 점수 개선 확인 후 git commit

8. 나머지 Tool 반복
```
