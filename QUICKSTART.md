# Quick Start

## 사전 준비

```bash
# 의존성 설치
uv sync

# 환경변수 설정
cp .env.example .env
# .env 열어서 ANTHROPIC_API_KEY 입력
```

---

## 케이스 폴더 구조 만들기

```
data/
└── case_01/
    ├── input/
    │   ├── notice.txt              ← 의견제출통지서 (또는 notice.pdf)
    │   ├── our_claims.txt          ← 당사 청구범위 (또는 our_patent.pdf 통합)
    │   ├── our_description.txt     ← 당사 상세설명
    │   ├── prior_art_1_claims.txt  ← 선행특허 1 청구범위
    │   └── prior_art_1_description.txt
    └── expected/                   ← (선택) eval 정답 레이블
        ├── tool1_expected.json
        └── tool2_expected.json
```

**PDF도 지원합니다:**
- `our_patent.pdf` — 청구범위+상세설명 통합 PDF (섹션 자동 분리)
- `prior_art_1.pdf` — 선행특허 통합 PDF
- `notice.pdf` — 통지서 PDF

---

## 실행

### 1단계 — DB에 데이터 로드

```bash
uv run python -m db.loader --case case_01
```

### 2단계 — 에이전트 실행 (LangGraph, Human-in-the-loop)

```bash
uv run python run_agent.py --case case_01
```

실행하면 Tool1 → 2 → 3이 순서대로 돌고, Claim Chart 검토 단계에서 멈춥니다:

```
✓ tool1 완료
✓ tool2 완료
✓ tool3 완료
──────────────────────────────────────────────────────────────
[Claim Chart 요약]
청구항 1의 구성요소 3개 중 1개 동일, 1개 유사, 1개 없음
──────────────────────────────────────────────────────────────
옵션: approve / exit
선택 > approve

✓ tool4 완료
──────────────────────────────────────────────────────────────
[전략]
비드부 와이어 구조는 선행특허에 개시되지 않은 고유 구성요소...
──────────────────────────────────────────────────────────────
옵션: approve / redo_strategy / exit
선택 > redo_strategy
수정 지시 입력 (없으면 Enter) > 진보성 관점에서 더 강하게 주장해줘

✓ tool4 완료   ← 피드백 반영 재실행
선택 > approve

✓ tool5 완료
선택 > approve

✓ tool6 완료
```

**검토 옵션 정리:**

| 단계 | 옵션 |
|------|------|
| Claim Chart 검토 | `approve` / `exit` |
| 전략 검토 | `approve` / `redo_strategy` / `exit` |
| 보정안 검토 | `approve` / `redo_amendment` / `redo_strategy` / `exit` |

`redo` 선택 후 수정 지시를 텍스트로 입력하면 LLM이 해당 지시를 반영해서 재생성합니다.

### 2단계 (대안) — 파이프라인 직접 실행 (자동, Human-in-the-loop 없음)

```bash
uv run python pipeline.py --case case_01

# 중간부터 재실행 (이전 결과 파일 재사용, LLM 비용 절약)
uv run python pipeline.py --case case_01 --start-from tool3

# 각 단계 완료 후 Enter로 확인하며 진행
uv run python pipeline.py --case case_01 --interactive
```

---

## 결과 확인

```
data/results/case_01/
├── tool1.json   ← 거절 유형, 법조항, 선행특허 번호
├── tool2.json   ← 청구항 파싱 결과
├── tool3.json   ← Claim Chart
├── tool4.json   ← 대응 전략
└── tool5.json   ← 보정안 + diff
```

---

## 추가 기능

### 트레이싱 (Langfuse)

`.env`에 Langfuse 키 입력 시 LLM 호출 전체가 자동 추적됩니다.

```
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
```

키 없으면 트레이싱 없이 그냥 실행됩니다.

### 프롬프트 최적화 (MIPROv2)

`data/case_01/expected/`에 정답 JSON을 넣고 DB 로드 후:

```bash
# 점수 확인
uv run python -m evals.eval_runner --tool tool1

# 최적화 실행
uv run python -m evals.optimize --tool tool1 --auto light
```

최적화 결과는 `optimized_modules/tool1/`에 저장되고, 다음 실행부터 자동 적용됩니다.
자세한 내용은 [EVAL_AND_OPTIMIZE.md](EVAL_AND_OPTIMIZE.md) 참고.

### 모델 변경

`.env`의 `DEFAULT_MODEL`만 바꾸면 모든 Tool이 해당 모델로 전환됩니다.

```
DEFAULT_MODEL=anthropic/claude-opus-4-6
DEFAULT_MODEL=openai/gpt-4o
```

---

## 파일 구조 한눈에 보기

```
patent_agent/
├── run_agent.py          ← 에이전트 실행 (LangGraph + Human-in-the-loop)
├── pipeline.py           ← 파이프라인 직접 실행 (자동)
├── agent.py              ← LangGraph 그래프 정의
│
├── tools/                ← Tool 래퍼 (Pydantic 입출력, 재시도)
├── modules/              ← DSPy Module (정규식 + LLM + 후처리)
├── signatures/           ← DSPy Signature (LLM 입출력 계약)
├── schemas/              ← Pydantic 모델 (전체 입출력 계약)
│
├── db/
│   ├── loader.py         ← 파일 → DB 로드
│   └── database.py       ← SQLite CRUD
│
├── evals/
│   ├── eval_runner.py    ← 점수 평가
│   ├── optimize.py       ← MIPROv2 최적화
│   ├── metrics.py        ← Tool별 metric 함수
│   └── datasets.py       ← DB → dspy.Example 변환
│
├── data/
│   ├── case_01/input/    ← 입력 파일
│   └── results/          ← Tool 실행 결과 JSON
│
├── optimized_modules/    ← 최적화된 프롬프트 (자동 로드)
└── db/
    ├── patent_agent.db   ← 특허 데이터
    └── checkpoints.db    ← LangGraph 체크포인트
```
