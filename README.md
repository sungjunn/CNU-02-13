# Patent Agent — 특허 심사대응 AI Agent

타이어 관련 특허의 심사대응을 AI로 자동화하는 시스템.
의견제출통지서를 입력하면 파이프라인이 아래 순서로 Tool을 실행한다:

```
Tool 1(통지서 분석) → Tool 2(청구항 파싱) → Tool 3(Claim Chart) → Tool 4(전략) → Tool 5(보정안) → Tool 6(차수 관리)
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| 패키지 관리 | uv |
| 프롬프트 프레임워크 | DSPy (프롬프트를 코드로 구조화, 자동 최적화) |
| LLM API | Claude, GPT (DSPy LM 설정으로 전환) |
| 코드 보조 | 정규식(re), difflib, pdfplumber |
| 데이터 저장 | SQLite |
| 데이터 검증 | Pydantic v2 |

## 설치 및 실행

```bash
# uv 설치 (없으면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 초기화 & 의존성 설치
uv sync

# 환경변수 설정
cp .env.example .env
# .env 파일에서 ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 입력

# 데이터 로드
uv run python -m db.loader --case case_01

# 파이프라인 실행
uv run python pipeline.py --case case_01

# 특정 Tool부터 재실행
uv run python pipeline.py --case case_01 --start-from tool3

# 인터랙티브 모드 (Tool 3, 5 완료 후 확인)
uv run python pipeline.py --case case_01 --interactive
```

## 평가 (Eval)

```bash
# 특정 Tool 평가
uv run python -m evals.eval_runner --tool tool1 --case case_01

# 모든 Tool 평가
uv run python -m evals.eval_runner --all --case case_01

# DSPy 프롬프트 자동 최적화
uv run python -m evals.optimize --tool tool1
uv run python -m evals.optimize --tool tool3 --auto heavy
```

## 디렉토리 구조

```
patent-agent/
├── schemas/           # Pydantic 모델 (모든 Tool의 입출력 계약서)
│   ├── common.py      # 공통 타입 (ClaimElement, MatchLevel 등)
│   ├── tool1~6.py     # 각 Tool 입출력 스키마
│   └── db_models.py   # SQLite 테이블 스키마
│
├── db/                # SQLite 데이터베이스
│   ├── database.py    # CRUD 구현
│   └── loader.py      # 파일 → DB 일괄 로드
│
├── signatures/        # DSPy Signature (LLM 입출력 구조)
│   └── tool1~5_sig.py
│
├── modules/           # DSPy Module (정규식 + LLM + 후처리 조합)
│   ├── tool1~5_module.py
│   └── tool6_version_manager.py  # 100% 코드
│
├── tools/             # Tool 실행 래퍼 (Module + Pydantic 검증)
│   ├── base.py        # ToolBase 추상 클래스
│   └── tool1~6_*.py
│
├── utils/             # 공통 유틸리티
│   ├── regex_extractors.py   # 정규식 추출
│   ├── diff_utils.py         # difflib 비교
│   └── pdf_extractor.py      # PDF 추출
│
├── evals/             # 평가 시스템
│   ├── metrics.py     # Tool별 평가 함수 (DSPy metric 호환)
│   ├── datasets.py    # 검증셋 로드
│   ├── eval_runner.py # eval 실행
│   └── optimize.py    # DSPy MIPROv2 최적화
│
├── data/              # 원본 파일 + 결과
│   └── case_01/
│       ├── input/     # 통지서, 청구항 등
│       └── expected/  # 정답 JSON (검증셋)
│
├── optimized_modules/ # DSPy 최적화 결과 (git 추적)
├── pipeline.py        # 메인 파이프라인
└── pyproject.toml     # uv 프로젝트 설정
```

## 아키텍처 핵심 개념

### Signature vs Schema vs Module

| 계층 | 역할 | 예시 |
|------|------|------|
| `schemas/` | Tool **전체**의 입출력 (정규식 + LLM + 후처리 포함) | `NoticeAnalysisOutput` |
| `signatures/` | **LLM에게 맡기는 부분만** 정의 | `AnalyzeNotice` |
| `modules/` | 이 둘을 **연결** (정규식 → LLM → 조립) | `NoticeAnalyzerModule` |

### 정규식 + LLM 역할 분담

```
Tool 1: 정규식 40% (법조항, 번호 추출) + LLM 60% (요약)
Tool 2: 정규식 70% (구조 파싱) + LLM 30% (구성요소 정제)
Tool 3: 코드 60% (조합 생성) + LLM 40% (매칭 판정)
Tool 4: 코드 20% (전처리) + LLM 80% (논증 생성)
Tool 5: LLM 70% (보정안 생성) + 코드 30% (검증)
Tool 6: 코드 100% (DSPy 안 씀)
```

## 검증셋 작성

`data/case_XX/expected/` 폴더에 정답 JSON을 작성한다.
상세 가이드: [expected/README.md](data/case_01/expected/README.md)

## 프롬프트 확인

DSPy가 자동 생성한 프롬프트를 확인하려면:

```python
import dspy
dspy.inspect_history(n=3)
```

## 모델 변경

`pipeline.py` 상단의 LM 설정 한 줄만 바꾸면 전체 파이프라인의 LLM이 바뀐다:

```python
# Claude 사용
lm = dspy.LM("anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))

# GPT 사용
lm = dspy.LM("openai/gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
```

또는 `.env`의 `DEFAULT_MODEL` 환경변수로 설정 가능.
