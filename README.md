###
아직 완성x 밑의 설명만으로 안될수있으니 코드직접 보고 수정 및 실행

# Patent Agent — 특허 심사대응 AI Agent

의견제출통지서를 입력하면 Tool 1→6을 순서대로 실행하여 보정안까지 자동 생성.
Human-in-the-loop으로 Claim Chart / 전략 / 보정안 검토 단계에서 사람이 개입 가능.

```
Tool 1(통지서 분석) → Tool 2(청구항 파싱) → Tool 3(Claim Chart)
→ [검토] → Tool 4(전략) → [검토] → Tool 5(보정안) → [검토] → Tool 6(차수 관리)
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| 패키지 관리 | uv |
| 오케스트레이션 | LangGraph (StateGraph + 체크포인트) |
| 프롬프트 프레임워크 | DSPy (Signature / Module / MIPROv2 최적화) |
| LLM API | Claude / OpenAI / OpenRouter / Factchat |
| 관측성 | Langfuse + OpenInference DSPy instrumentation |
| 데이터 저장 | SQLite (특허 DB) + SQLite (LangGraph 체크포인트 분리) |
| 데이터 검증 | Pydantic v2 |

## 설치

```bash
# uv 설치 (없으면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync
```

## 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 편집
```

지원 모델 프리픽스:

| 프리픽스 | 필요 키 |
|----------|---------|
| `anthropic/claude-...` | `ANTHROPIC_API_KEY` |
| `openai/gpt-...` | `OPENAI_API_KEY` |
| `openrouter/...` | `OPENROUTER_API_KEY` |
| `factchat/...` | `FACTCHAT_API_KEY` |

Langfuse 관측성(선택):
`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` 설정 시 자동 활성화.

## 실행

```bash
# 1. 케이스 데이터 로드 (data/case_01/input/ → DB)
uv run python -m db.loader --case case_01

# 2. Agent 실행 (Human-in-the-loop)
uv run python run_agent.py --case case_01

# 이전 세션 이어서 실행 (체크포인트 복구)
uv run python run_agent.py --case case_01 --thread-id <이전_thread_id>

# 파이프라인 직접 실행 (검토 단계 없이)
uv run python pipeline.py --case case_01
uv run python pipeline.py --case case_01 --start-from tool3
```

## 평가 및 프롬프트 최적화

```bash
# Tool별 평가
uv run python -m evals.eval_runner --tool tool1 --case case_01
uv run python -m evals.eval_runner --all --case case_01

# DSPy MIPROv2 자동 프롬프트 최적화
uv run python -m evals.optimize --tool tool1
uv run python -m evals.optimize --tool tool3 --auto heavy
```

상세 가이드: [EVAL_AND_OPTIMIZE.md](EVAL_AND_OPTIMIZE.md)
빠른 시작: [QUICKSTART.md](QUICKSTART.md)

## 디렉토리 구조

```
patent_agent/
├── agent.py               # LangGraph StateGraph (Human-in-the-loop 포함)
├── run_agent.py           # CLI 진입점 — 스트림 실행, 검토 루프
├── pipeline.py            # 검토 단계 없이 직접 실행하는 파이프라인
│
├── schemas/               # Pydantic 모델 — 모든 Tool의 입출력 계약서
│   ├── common.py          # 공통 타입 (ClaimElement, MatchLevel, RejectionType 등)
│   ├── tool1.py ~ tool6.py
│   ├── db_models.py       # SQLite 테이블 스키마
│   └── agent_state.py     # LangGraph AgentState TypedDict
│
├── db/                    # SQLite 데이터베이스
│   ├── database.py        # PatentDB CRUD
│   ├── loader.py          # 파일 → DB 일괄 로드 (txt 전용)
│   ├── patent_agent.db    # 특허 문서 DB (gitignore)
│   └── checkpoints.db     # LangGraph 체크포인트 DB (gitignore)
│
├── signatures/            # DSPy Signature — LLM 입출력 구조 정의
│   └── tool1~5_sig.py
│
├── modules/               # DSPy Module — 정규식 + LLM + 후처리 조합
│   ├── tool1~5_module.py
│   └── tool6_version_manager.py   # 100% 코드 (DSPy 미사용)
│
├── tools/                 # Tool 래퍼 — Module + Pydantic 검증
│   ├── base.py
│   └── tool1~6_*.py
│
├── utils/                 # 공통 유틸리티
│   ├── regex_extractors.py
│   └── diff_utils.py
│
├── evals/                 # 평가 시스템
│   ├── metrics.py         # Tool별 평가 함수 (DSPy metric 호환)
│   ├── datasets.py        # 검증셋 로드
│   ├── eval_runner.py     # eval 실행
│   └── optimize.py        # DSPy MIPROv2 최적화
│
├── data/                  # 케이스별 원본 파일 + 정답 JSON
│   └── case_01/
│       ├── input/         # notice.txt, our_claims.txt, our_description.txt
│       │                  # prior_art_N_claims.txt, prior_art_N_description.txt
│       └── expected/      # tool1_expected.json, tool2_expected.json, ...
│
├── optimized_modules/     # DSPy 최적화 결과 (git 포함, 팀 공유)
└── pyproject.toml
```

## 아키텍처

### LangGraph 그래프 흐름

```
START → tool1 → tool2 → tool3 → review_chart ─── approve ──→ tool4 → review_strategy ─── approve ──→ tool5 → review_amendment → tool6 → END
                                      │                             │                              │
                                   redo                      redo_strategy                  redo_amendment / redo_strategy
                                      └───────────────────────────→┘                              └──────────────────────────→
```

- `review_*` 노드: `interrupt()`로 사람 입력 대기
- redo 선택 시 추가 지시 텍스트를 LLM 프롬프트에 반영하여 재실행

### Signature / Schema / Module 계층

| 계층 | 역할 |
|------|------|
| `schemas/` | Tool 전체 입출력 (정규식 + LLM + 후처리 포함) |
| `signatures/` | LLM에게 맡기는 부분만 정의 |
| `modules/` | 정규식 → LLM → 후처리 조립 |

### 정규식 + LLM 역할 분담

```
Tool 1: 정규식 40% (법조항, 번호 추출)  + LLM 60% (요약)
Tool 2: 정규식 70% (구조 파싱)          + LLM 30% (구성요소 정제)
Tool 3: 코드  60% (조합 생성)           + LLM 40% (매칭 판정)
Tool 4: 코드  20% (전처리)              + LLM 80% (논증 생성)
Tool 5: LLM   70% (보정안 생성)         + 코드 30% (검증)
Tool 6: 코드 100% (DSPy 미사용)
```

## 모델 변경

`.env`의 `DEFAULT_MODEL`만 바꾸면 전체 파이프라인 LLM이 바뀜:

```
DEFAULT_MODEL=anthropic/claude-sonnet-4-6
# DEFAULT_MODEL=openai/gpt-4o
# DEFAULT_MODEL=openrouter/anthropic/claude-sonnet-4-5
# DEFAULT_MODEL=factchat/claude-sonnet-4-6
```

## DSPy 프롬프트 확인

```python
import dspy
dspy.inspect_history(n=3)
```

## 케이스 파일 구조

```
data/case_01/input/
├── notice.txt                   # 의견제출통지서
├── our_claims.txt               # 당사 청구항
├── our_description.txt          # 당사 상세설명
├── prior_art_1_claims.txt       # 선행특허 1 청구항
└── prior_art_1_description.txt  # 선행특허 1 상세설명
```

- 파일 형식: **txt 전용** (PDF 직접 로드 미지원)
- 선행특허 여러 건: `prior_art_2_*`, `prior_art_3_*` 형식으로 추가
