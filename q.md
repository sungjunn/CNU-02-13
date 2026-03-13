# 특허 심사대응 AI Agent — 코딩 에이전트용 프로젝트 구축 프롬프트 v2

아래 지시에 따라 Python 프로젝트의 기본 골격을 만들어줘.
프롬프트 작성자와 검증셋 작성자(코드를 모르는 팀원)가 바로 작업할 수 있는 환경을 구축하는 게 목표야.

---

## 1. 프로젝트 개요

타이어 관련 특허의 심사대응을 AI로 자동화하는 시스템이야.
사용자가 의견제출통지서를 입력하면, 파이프라인이 아래 순서로 Tool을 실행해:

```
Tool 1(통지서 분석) → Tool 2(청구항 파싱) → Tool 3(Claim Chart 생성) → Tool 4(차이점 분석 + 전략) → Tool 5(보정안 생성) → Tool 6(차수 관리)
```

### 기술 스택
- **패키지 관리:** uv (pip 대체, 빠른 의존성 관리)
- **프롬프트 프레임워크:** DSPy (프롬프트를 코드로 구조화, 자동 최적화)
- **LLM API:** Claude, GPT 등 (DSPy의 LM 설정으로 전환 가능)
- **코드 보조:** 정규식(re), difflib, pdfplumber
- **데이터 저장:** SQLite (특허 문서 ~100건 저장, 검색, 메타데이터 관리)
- **임베딩/벡터DB:** 사용 안 함. 데이터 규모가 작아서(선행특허 1~3건, 청구항 10~20개) LLM 컨텍스트에 전부 들어감.
- SA-1(Data Agent)은 이미 데이터를 가져온 상태라고 가정.

---

## 2. 디렉토리 구조

```
patent-agent/
├── schemas/                  # Pydantic 모델 (모든 Tool의 입출력 계약서)
│   ├── __init__.py
│   ├── common.py             # 공통 타입 (ClaimElement, MatchLevel 등)
│   ├── tool1.py ~ tool6.py   # 각 Tool 입출력 스키마
│   └── db_models.py          # SQLite 테이블 스키마
│
├── db/                       # 데이터베이스
│   ├── __init__.py
│   ├── database.py           # SQLite 연결, 초기화, CRUD
│   ├── loader.py             # 파일 → DB 일괄 로드 스크립트
│   └── patent_agent.db       # SQLite DB 파일 (gitignore)
│
├── signatures/               # DSPy Signature 정의 (입출력 구조)
│   ├── __init__.py
│   ├── tool1_sig.py          # Tool 1용 Signature
│   ├── tool2_sig.py          # Tool 2용 Signature
│   ├── tool3_sig.py
│   ├── tool4_sig.py
│   └── tool5_sig.py
│
├── modules/                  # DSPy Module 정의 (파이프라인 구조)
│   ├── __init__.py
│   ├── tool1_module.py       # Tool 1 모듈 (정규식 전처리 + DSPy LLM 호출)
│   ├── tool2_module.py
│   ├── tool3_module.py
│   ├── tool4_module.py
│   ├── tool5_module.py
│   └── tool6_version_manager.py  # 100% 코드, DSPy 안 씀
│
├── tools/                    # Tool 실행 래퍼 (모듈 + 전후처리 조합)
│   ├── __init__.py
│   ├── base.py               # ToolBase 추상 클래스
│   ├── tool1_notice_analyzer.py
│   ├── tool2_claim_parser.py
│   ├── tool3_claim_chart.py
│   ├── tool4_strategy.py
│   ├── tool5_amendment.py
│   └── tool6_version_manager.py
│
├── utils/                    # 공통 유틸리티
│   ├── __init__.py
│   ├── regex_extractors.py   # 정규식 추출 함수 모음
│   ├── diff_utils.py         # difflib 기반 비교 유틸
│   └── pdf_extractor.py      # PDF 텍스트/도면 분리 추출
│
├── evals/                    # 평가 시스템
│   ├── __init__.py
│   ├── datasets.py           # eval 데이터셋 로드 (DB에서 읽어옴)
│   ├── metrics.py            # Tool별 평가 함수 (DSPy metric 호환)
│   ├── eval_runner.py        # eval 실행 + 결과 저장
│   ├── optimize.py           # DSPy MIPROv2 최적화 실행 스크립트
│   └── results/              # eval 결과 JSON 저장
│
├── data/                     # 원본 파일 (DB 로드 전 스테이징)
│   └── case_01/
│       ├── input/            # 통지서, 청구항, 상세설명, 선행특허 파일
│       └── expected/         # 정답 JSON (검증셋 작성자가 여기만 작성)
│
├── tests/                    # 단위테스트 (확정적 로직만)
│   ├── test_regex.py
│   ├── test_tool6.py
│   └── test_db.py
│
├── optimized_modules/        # DSPy 최적화 결과 저장 (gitignore 하지 않음, 팀 공유)
│   └── tool1/                # Tool별 최적화된 Module
│
├── pipeline.py               # 메인 파이프라인 (Tool 1→6 체이닝)
├── pyproject.toml            # uv 프로젝트 설정 + 의존성
├── .gitignore
└── README.md
```

---

## 3. uv 프로젝트 설정

pip 대신 uv를 사용해. pyproject.toml로 의존성을 관리해.

### pyproject.toml

```toml
[project]
name = "patent-agent"
version = "0.1.0"
description = "특허 심사대응 AI Agent"
requires-python = ">=3.10"
dependencies = [
    "dspy>=2.6",
    "pydantic>=2.0",
    "anthropic>=0.40.0",
    "openai>=1.0",
    "pdfplumber>=0.11",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.8",
]
```

### 설치 및 실행 방법 (README에 포함)

```bash
# uv 설치 (없으면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 초기화 & 의존성 설치
uv sync

# 실행
uv run python pipeline.py --case case_01
uv run python -m evals.eval_runner --case case_01 --tool tool1
uv run python -m evals.optimize --tool tool1
uv run pytest tests/
```

---

## 4. SQLite 데이터베이스

특허 문서 약 100건을 저장·조회하는 간단한 DB.
벡터DB가 아님. 메타데이터 저장과 조회, 케이스 관리 용도.

### schemas/db_models.py

```python
"""DB 테이블에 대응하는 Pydantic 모델.
SQLite 테이블 생성과 데이터 검증에 모두 사용."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PatentDocument(BaseModel):
    """특허 문서 (당사 특허 또는 선행특허)"""
    doc_id: str                        # 고유 ID (예: "KR10-1234567")
    doc_type: str                      # "our_patent" | "prior_art"
    title: str
    claims_text: str                   # 청구항 전문
    description_text: str              # 상세설명 전문
    filing_date: Optional[str] = None
    created_at: str = ""               # DB 저장 시 자동 생성

class OfficeAction(BaseModel):
    """의견제출통지서"""
    action_id: str                     # 고유 ID
    our_patent_id: str                 # 대상 당사 특허 doc_id (FK)
    notice_text: str                   # 통지서 전문
    prior_art_ids: list[str]           # 인용된 선행특허 doc_id 리스트
    received_date: Optional[str] = None

class CaseRecord(BaseModel):
    """심사대응 케이스 (통지서 1건 = 케이스 1건)"""
    case_id: str
    action_id: str                     # 의견제출통지서 ID (FK)
    our_patent_id: str                 # 당사 특허 ID (FK)
    status: str = "in_progress"        # in_progress | completed
    created_at: str = ""

class EvalDataset(BaseModel):
    """검증셋 레코드"""
    eval_id: str
    case_id: str                       # 어떤 케이스의 검증셋인지
    tool_name: str                     # "tool1", "tool2", ...
    expected_json: str                 # 정답 JSON (문자열로 저장)
    eval_type: str                     # "exact_match" | "checklist"
```

### db/database.py

아래 기능을 구현해:

```python
class PatentDB:
    """SQLite 기반 특허 데이터 관리"""
    
    def __init__(self, db_path="db/patent_agent.db"):
        # SQLite 연결, 테이블 자동 생성 (없으면)
    
    # === 문서 CRUD ===
    def insert_patent(self, doc: PatentDocument): ...
    def get_patent(self, doc_id: str) -> PatentDocument: ...
    def list_patents(self, doc_type: str = None) -> list[PatentDocument]: ...
    
    # === 통지서 CRUD ===
    def insert_office_action(self, action: OfficeAction): ...
    def get_office_action(self, action_id: str) -> OfficeAction: ...
    
    # === 케이스 관리 ===
    def create_case(self, case: CaseRecord): ...
    def get_case(self, case_id: str) -> CaseRecord: ...
    def list_cases(self) -> list[CaseRecord]: ...
    
    # === 검증셋 ===
    def insert_eval(self, eval_data: EvalDataset): ...
    def get_evals_for_tool(self, tool_name: str) -> list[EvalDataset]: ...
    def get_evals_for_case(self, case_id: str) -> list[EvalDataset]: ...
```

### db/loader.py

`data/case_XX/input/` 폴더의 파일들을 읽어서 DB에 일괄 로드하는 스크립트.

```bash
# 사용법
uv run python -m db.loader --case case_01

# 동작:
# 1. data/case_01/input/ 에서 txt, pdf 파일 읽기
# 2. PatentDocument, OfficeAction 객체 생성
# 3. DB에 insert
# 4. CaseRecord 생성
# 5. data/case_01/expected/ 의 JSON들을 EvalDataset으로 DB에 저장
```

파일명 규칙:
- `notice.txt` → OfficeAction
- `our_claims.txt` + `our_description.txt` → PatentDocument (doc_type="our_patent")
- `prior_art_1_claims.txt` + `prior_art_1_description.txt` → PatentDocument (doc_type="prior_art")
- `tool1_expected.json` → EvalDataset (tool_name="tool1")

---

## 5. DSPy Signature 정의

각 Tool에서 LLM이 처리하는 부분을 DSPy Signature로 정의해.
Signature는 "이 입력을 받으면 이 출력을 내라"는 구조만 정의하는 거야.
실제 프롬프트 문장은 DSPy가 자동 생성하거나 optimizer가 최적화함.

> **⚠️ Signature와 schemas의 관계:**
> - `schemas/`의 Pydantic 모델은 **Tool 전체의 입출력** (정규식 결과 + LLM 결과 + 후처리 결과 포함)
> - `signatures/`의 DSPy Signature는 **LLM에게 맡기는 부분만** 정의
> - 예: Tool 1의 경우, `schemas/tool1.py`의 `NoticeAnalysisOutput`에는 `rejection_articles`(정규식이 채움) + `examiner_reasoning`(LLM이 채움)이 모두 있지만, `signatures/tool1_sig.py`에는 `examiner_reasoning`만 OutputField로 존재
> - **Module(modules/)이 이 둘을 연결함:** Signature의 LLM 출력을 받아서 정규식 결과와 합쳐 schemas의 Pydantic 모델로 조립

### signatures/tool1_sig.py — 통지서 거절이유 요약

```python
import dspy

class AnalyzeNotice(dspy.Signature):
    """의견제출통지서의 거절이유를 분석하여 심사관의 논리를 요약한다.
    
    정규식으로 이미 추출된 메타데이터(법조항, 특허번호, 청구항 번호)가 
    함께 제공된다. 이 메타데이터를 참고하여 거절이유를 요약하라."""
    
    notice_text: str = dspy.InputField(desc="의견제출통지서 원문 텍스트")
    extracted_metadata: str = dspy.InputField(desc="정규식으로 추출된 법조항, 특허번호, 청구항 번호 JSON")
    
    examiner_reasoning: str = dspy.OutputField(desc="심사관의 거절 논리 요약 (3~5문장)")
    rejection_analysis: str = dspy.OutputField(desc="거절 유형별 상세 분석 JSON")
```

### signatures/tool2_sig.py — 청구항 구성요소 정제

```python
import dspy

class RefineClaimElements(dspy.Signature):
    """정규식으로 1차 분리된 청구항 구성요소를 의미 단위로 정제하고 라벨을 부여한다.
    
    세미콜론으로 split한 결과가 제공되며, 이를 검토하여:
    1. 잘못 분리된 요소를 합치거나 재분리
    2. 각 요소에 한국어 의미 라벨 부여"""
    
    claim_text: str = dspy.InputField(desc="단일 청구항 원문")
    rough_elements: str = dspy.InputField(desc="정규식으로 1차 분리된 구성요소 리스트 JSON")
    
    refined_elements: str = dspy.OutputField(desc="정제된 구성요소 리스트 JSON (element_id, text, label 포함)")
```

### signatures/tool3_sig.py — 구성요소 매칭 판정

```python
import dspy

class JudgeElementMatch(dspy.Signature):
    """당사 청구항 구성요소 하나와 선행특허 구성요소 하나를 비교하여 
    매칭 수준을 판정한다.
    
    판정 기준:
    - 동일: 실질적으로 같은 기술 내용
    - 유사: 관련은 있으나 차이가 존재
    - 없음: 대응하는 요소가 없음"""
    
    our_element: str = dspy.InputField(desc="당사 청구항 구성요소 텍스트")
    prior_element: str = dspy.InputField(desc="선행특허 청구항 구성요소 텍스트")
    our_description_context: str = dspy.InputField(desc="당사 상세설명 중 관련 단락")
    
    match_level: str = dspy.OutputField(desc="매칭 수준: 동일/유사/없음")
    reasoning: str = dspy.OutputField(desc="판정 근거 (2~3문장)")
```

### signatures/tool4_sig.py — 전략 생성

```python
import dspy

class GenerateStrategy(dspy.Signature):
    """Claim Chart 분석 결과와 거절이유를 바탕으로 심사대응 전략을 생성한다.
    
    거절 유형에 따라 다른 논증 방향을 사용:
    - 신규성 거절: 미매칭 구성요소를 강조하여 선행특허와의 차이 주장
    - 진보성 거절: 구성요소 조합의 기술적 효과 차이 강조"""
    
    claim_chart_summary: str = dspy.InputField(desc="Claim Chart 요약 (매칭/미매칭 구성요소)")
    rejection_type: str = dspy.InputField(desc="거절 유형: 신규성 또는 진보성")
    examiner_reasoning: str = dspy.InputField(desc="심사관 거절 논리 요약")
    unmatched_elements: str = dspy.InputField(desc="매칭 '없음'인 구성요소 리스트")
    disputed_elements: str = dspy.InputField(desc="매칭 '유사'인 구성요소 리스트")
    
    differences: str = dspy.OutputField(desc="차이점 분석 JSON (요소별 차이 설명 + 기술적 효과)")
    strategy: str = dspy.OutputField(desc="대응 전략 텍스트")
    rebuttal_points: str = dspy.OutputField(desc="반박 포인트 리스트 JSON")
```

### signatures/tool5_sig.py — 보정안 생성

```python
import dspy

class GenerateAmendment(dspy.Signature):
    """대응 전략에 따라 보정된 독립항 초안을 생성한다.
    
    보정 시 반드시 상세설명에 근거가 있는 표현만 사용해야 한다.
    원본 청구항에서 변경된 부분을 명확히 표시하라."""
    
    original_claim: str = dspy.InputField(desc="원본 독립항 전문")
    strategy: str = dspy.InputField(desc="대응 전략 텍스트")
    description_text: str = dspy.InputField(desc="당사 상세설명 전문 (근거 확인용)")
    
    amended_claim: str = dspy.OutputField(desc="보정된 청구항 전문")
    added_elements: str = dspy.OutputField(desc="추가된 구성요소 리스트 JSON")
    description_basis: str = dspy.OutputField(desc="보정 근거가 되는 상세설명 단락 리스트 JSON")
```

---

## 6. DSPy Module 정의

각 Tool의 실제 처리 로직. 정규식 전처리 + DSPy LLM 호출 + 코드 후처리를 조합.

### modules/tool1_module.py — 통지서 분석기

```python
import dspy
import re
import json

class NoticeAnalyzerModule(dspy.Module):
    """통지서 분석: 정규식 추출(40%) + LLM 요약(60%)"""
    
    def __init__(self):
        self.analyze = dspy.ChainOfThought(AnalyzeNotice)
    
    def forward(self, notice_text: str):
        # === 1단계: 정규식으로 확정적 데이터 추출 ===
        # (utils/regex_extractors.py의 함수 호출)
        # - 거절 법조항 추출: "제29조 제1항", "제29조 제2항" 등
        # - 선행특허 번호 추출: "KR10-XXXXXXX", "US-XXXXXXX" 등  
        # - 해당 청구항 번호 추출: "제1항", "제3항" 등
        # - 거절 유형 판별: 법조항으로 신규성/진보성 자동 분류
        
        # === 2단계: LLM에게는 추출 메타데이터 + 원문을 넘겨서 요약만 시킴 ===
        # result = self.analyze(
        #     notice_text=notice_text,
        #     extracted_metadata=json.dumps(metadata, ensure_ascii=False)
        # )
        
        # === 3단계: 정규식 결과 + LLM 결과를 합쳐서 최종 출력 구성 ===
        
        raise NotImplementedError("TODO: 구현 필요")
```

### modules/tool2_module.py — 청구항 파서

```python
class ClaimParserModule(dspy.Module):
    """청구항 파싱: 정규식(70%) + LLM 정제(30%)"""
    
    def __init__(self):
        self.refine = dspy.Predict(RefineClaimElements)
    
    def forward(self, claims_text: str):
        # === 1단계: 정규식으로 구조 파싱 (코드 100%) ===
        # - 청구항 번호 분리: "제1항", "제2항" 또는 "1.", "2." 패턴으로 split
        # - 독립항/종속항 분류: "제N항에 있어서" 패턴 있으면 종속항
        # - 종속 관계 트리 구성: 종속항이 인용하는 청구항 번호 파싱
        # - 구성요소 1차 분리: "comprising:" 이후 세미콜론(;)으로 split
        
        # === 2단계: LLM으로 구성요소 정제 (복잡한 경우만) ===
        # 세미콜론으로 안 잘리는 복잡한 청구항만 LLM에 넘김
        # result = self.refine(
        #     claim_text=claim.original_text,
        #     rough_elements=json.dumps(rough_elements)
        # )
        
        # === 3단계: 파싱 결과 검증 (코드) ===
        # - 독립항이 0개면 에러
        # - 종속항이 존재하지 않는 청구항을 참조하면 에러
        
        raise NotImplementedError("TODO: 구현 필요")
```

### modules/tool3_module.py — Claim Chart 생성기

```python
class ClaimChartModule(dspy.Module):
    """Claim Chart: 조합 생성(코드 60%) + 매칭 판정(LLM 40%)
    
    핵심: 당사 독립항 1개 vs 선행특허 독립항 1개씩 개별 호출.
    한 번에 모든 비교를 시키지 않음."""
    
    def __init__(self):
        self.judge = dspy.Predict(JudgeElementMatch)
    
    def forward(self, our_claims, prior_claims, our_description):
        # === 1단계: 비교 조합 생성 (코드) ===
        # 당사 독립항 N개 × 선행특허 독립항 M개 = N×M 쌍
        # 각 쌍 내에서 구성요소끼리 비교
        
        # === 2단계: LLM 매칭 판정 (구성요소 쌍별 개별 호출) ===
        # for each (our_element, prior_element) pair:
        #     result = self.judge(
        #         our_element=our_el.text,
        #         prior_element=prior_el.text,
        #         our_description_context=relevant_paragraph
        #     )
        
        # === 3단계: 결과 검증 (코드) ===
        # - 모든 매칭이 "동일"이면 경고 (비정상)
        # - 매칭 결과가 비어있으면 에러
        
        raise NotImplementedError("TODO: 구현 필요")
```

### modules/tool4_module.py — 전략 생성기

```python
class StrategyModule(dspy.Module):
    """차이점 분석 + 전략: 규칙 분기(코드 20%) + 논증 생성(LLM 80%)"""
    
    def __init__(self):
        self.generate = dspy.ChainOfThought(GenerateStrategy)
    
    def forward(self, claim_chart, rejection_type, examiner_reasoning):
        # === 1단계: 코드로 전처리 ===
        # - Claim Chart에서 매칭 "없음" 요소 자동 추출 → 차별점 후보
        # - 매칭 "유사" 요소 자동 추출 → 논쟁 가능 지점
        
        # === 2단계: 거절 유형에 따라 LLM 호출 ===
        # if rejection_type == "신규성":
        #     # 미매칭 구성요소 강조 방향
        # elif rejection_type == "진보성":
        #     # 기술적 효과 차이 강조 방향
        
        # result = self.generate(
        #     claim_chart_summary=summary,
        #     rejection_type=rejection_type,
        #     examiner_reasoning=examiner_reasoning,
        #     unmatched_elements=json.dumps(unmatched),
        #     disputed_elements=json.dumps(disputed)
        # )
        
        raise NotImplementedError("TODO: 구현 필요")
```

### modules/tool5_module.py — 보정안 생성기

```python
class AmendmentModule(dspy.Module):
    """보정안 생성: LLM 생성(70%) + 코드 검증(30%)"""
    
    def __init__(self):
        self.generate = dspy.ChainOfThought(GenerateAmendment)
    
    def forward(self, original_claim, strategy, description_text):
        # === 1단계: LLM이 보정안 초안 생성 ===
        # result = self.generate(
        #     original_claim=original_claim,
        #     strategy=strategy,
        #     description_text=description_text
        # )
        
        # === 2단계: 코드 기반 후처리 검증 ===
        # - difflib로 원본 vs 보정본 diff 생성 (변경사항 하이라이트)
        # - 보정안이 빈 문자열이면 에러
        # - 원본과 완전 동일하면 경고 (보정이 안 된 것)
        
        # === 3단계: 상세설명 근거 확인 ===
        # 보정에서 추가된 표현이 상세설명에 존재하는지 문자열 검색
        # 근거 없는 내용이 추가됐으면 warnings에 추가
        
        raise NotImplementedError("TODO: 구현 필요")
```

### modules/tool6_version_manager.py — 차수 관리자

이건 100% 코드. DSPy 안 씀. 완전 구현해줘:
- JSON 파일로 차수별 결과 저장/로드
- difflib로 차수 간 청구항 diff 생성
- 메타데이터(타임스탬프, 거절이유 요약, 전략 요약) 관리

---

## 7. Tools 래퍼 계층

DSPy Module을 감싸서 통일된 인터페이스를 제공하는 계층.
Pydantic 입출력 검증 + 중간 결과 저장 + DB 연동을 담당.

### tools/base.py

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class ToolBase(ABC):
    """모든 Tool의 베이스 클래스.
    
    규칙:
    - 입력과 출력은 반드시 Pydantic BaseModel
    - run()은 단일 진입점
    - DSPy Module을 내부적으로 호출
    - 중간 결과를 JSON + DB에 저장"""
    
    @abstractmethod
    def run(self, input_data: BaseModel) -> BaseModel:
        pass
    
    def save_result(self, result: BaseModel, path: str):
        """결과를 JSON 파일로 저장 (디버깅용)"""
        pass
    
    def save_to_db(self, case_id: str, result: BaseModel):
        """결과를 DB에 저장"""
        pass
```

각 Tool 파일(tool1~tool5)은:
1. ToolBase를 상속
2. run() 안에서 해당 DSPy Module을 호출
3. Module 출력을 Pydantic 스키마로 변환
4. 변환 실패 시 최대 3회 재시도

---

## 8. Eval 시스템 — DSPy Metric 호환

### evals/metrics.py — Tool별 평가 함수

DSPy optimizer가 사용할 수 있도록 `(example, prediction, trace=None) -> float` 형식으로 구현.

```python
def tool1_metric(example, prediction, trace=None) -> float:
    """Tool 1 평가: 정확도 기반 (확정적)
    
    비교 항목:
    - 거절 법조항 일치율 (리스트 비교)
    - 선행특허 번호 일치율 (리스트 비교)
    - 해당 청구항 번호 일치율 (리스트 비교)
    - 거절 유형 일치 (단일값 비교)
    
    최종 점수 = 4개 항목의 평균 (0.0 ~ 1.0)"""
    pass

def tool2_metric(example, prediction, trace=None) -> float:
    """Tool 2 평가: 파싱 정확도
    
    비교 항목:
    - 청구항 총 개수 일치
    - 독립항/종속항 분류 정확도
    - 종속 관계 정확도
    - 구성요소 분리 개수 (±1 허용)
    
    최종 점수 = 가중 평균 (0.0 ~ 1.0)"""
    pass

def tool3_metric(example, prediction, trace=None) -> float:
    """Tool 3 평가: Claim Chart 매칭 정확도
    
    구성요소별 매칭 수준(동일/유사/없음)이 
    expected와 일치하는 비율
    
    최종 점수 = 일치 요소 / 전체 요소 (0.0 ~ 1.0)"""
    pass

def tool4_metric(example, prediction, trace=None) -> float:
    """Tool 4 평가: 체크리스트 기반 (LLM-as-Judge)
    
    expected의 must_include 항목 각각에 대해
    LLM-as-Judge가 prediction에 포함되어 있는지 yes/no 판정
    
    최종 점수 = 충족 항목 / 전체 항목 (0.0 ~ 1.0)
    
    === LLM-as-Judge bias 완화 규칙 ===
    1. Judge 모델은 파이프라인 LLM과 다른 모델 사용
       (예: 파이프라인이 Claude면 Judge는 GPT, 또는 반대)
       → self-preference bias 방지
    2. Judge 프롬프트는 yes/no만 답하게 설계. 설명 요구하지 않음
       → verbosity bias 방지
    3. Judge 프롬프트 형식:
       "다음 텍스트에 '{체크리스트_항목}'과 의미적으로 동일한 내용이 포함되어 있는가?
        텍스트: {prediction_text}
        답변: yes 또는 no만 답하시오."
    4. 여유가 있으면 같은 판정을 2회 반복하여 일관성 확인
    """
    pass

def tool5_metric(example, prediction, trace=None) -> float:
    """Tool 5 평가: 체크리스트 + 근거 확인
    
    1. 체크리스트 충족률 (tool4와 동일 방식, 동일 bias 완화 규칙 적용)
    2. must_not_include 체크: 포함되면 감점
    3. 상세설명 근거 존재 비율 (보정 내용이 상세설명에 있는지)
    4. diff가 비어있지 않은지 (실제로 보정이 됐는지)
    
    최종 점수 = 4개 항목의 가중 평균
    
    === LLM-as-Judge 설정 ===
    tool4_metric과 동일한 bias 완화 규칙 적용.
    must_not_include 판정도 같은 Judge 모델/프롬프트 패턴 사용."""
    pass
```

### evals/datasets.py — 데이터셋 로드

```python
def load_eval_dataset(tool_name: str, db_path: str = "db/patent_agent.db"):
    """DB에서 해당 Tool의 검증셋을 읽어 DSPy Example 리스트로 변환.
    
    Returns:
        list[dspy.Example] — DSPy optimizer/evaluator에 바로 넘길 수 있는 형식
    """
    pass

# === 핵심: expected JSON → dspy.Example 변환 매핑 ===
#
# expected JSON의 필드명과 DSPy Signature의 필드명이 다를 수 있음.
# 각 Tool별로 아래 매핑 규칙을 적용하여 변환해야 함.
#
# Tool 1:
#   expected JSON 필드        → dspy.Example 필드 (Signature OutputField 기준)
#   "rejection_type"          → (metric에서 직접 비교, Signature 밖 필드)
#   "rejection_articles"      → (metric에서 직접 비교, 정규식 출력이라 Signature 밖)
#   "prior_art_numbers"       → (metric에서 직접 비교, 정규식 출력이라 Signature 밖)
#   "rejected_claim_numbers"  → (metric에서 직접 비교, 정규식 출력이라 Signature 밖)
#   ※ Tool 1의 Signature 출력은 examiner_reasoning, rejection_analysis인데,
#     이건 체크리스트가 아니면 검증이 어려우므로 eval은 정규식 출력 필드 위주로 평가.
#     LLM이 생성하는 요약의 품질은 별도 체크리스트로 평가.
#
# Tool 2:
#   "total_claims"            → metric에서 비교
#   "independent_claims"      → metric에서 비교
#   "dependent_claims"        → metric에서 비교 (종속 관계 dict)
#   "claim_1_elements"        → metric에서 비교 (구성요소 리스트)
#
# Tool 3:
#   "matchings"               → metric에서 구성요소별 match_level 비교
#     각 matching의 "match_level" ↔ Signature의 match_level 출력
#
# Tool 4:
#   "must_include"            → LLM-as-Judge에 체크리스트로 전달
#   ※ Signature 출력(strategy, rebuttal_points)을 텍스트로 합쳐서 Judge에 넘김
#
# Tool 5:
#   "must_include"            → LLM-as-Judge 체크리스트
#   "must_not_include"        → LLM-as-Judge 네거티브 체크리스트
#   ※ Signature 출력(amended_claim, added_elements)을 합쳐서 Judge에 넘김
#
# dspy.Example 생성 시 with_inputs()로 입력 필드를 명시해야 함:
#   example = dspy.Example(
#       notice_text="...",                    # 입력
#       extracted_metadata="...",             # 입력
#       examiner_reasoning="...",             # 기대 출력 (있으면)
#       _expected_articles=["제29조 제2항"],  # 정규식 검증용 (앞에 _를 붙여 구분)
#       _expected_numbers=["KR10-1234567"],
#   ).with_inputs("notice_text", "extracted_metadata")
```

### evals/eval_runner.py — 평가 실행

```python
# 사용법:
# uv run python -m evals.eval_runner --tool tool1 --case case_01
# uv run python -m evals.eval_runner --all --case case_01

# 동작:
# 1. DB에서 해당 case의 입력 데이터 + 검증셋 로드
# 2. 현재 Module로 Tool 실행
# 3. metric 함수로 점수 계산
# 4. 결과를 evals/results/ 에 JSON으로 저장:
#    {
#      "tool": "tool1",
#      "case": "case_01",
#      "timestamp": "2026-03-10T14:30:22",
#      "model": "claude-sonnet-4-20250514",
#      "overall_score": 0.85,
#      "breakdown": {
#        "rejection_articles": 1.0,
#        "prior_art_numbers": 0.67,
#        "rejected_claims": 1.0,
#        "rejection_type": 1.0
#      },
#      "failures": [
#        {"field": "prior_art_numbers", "expected": [...], "actual": [...]}
#      ]
#    }
```

### evals/optimize.py — DSPy 자동 프롬프트 최적화

```python
# 사용법:
# uv run python -m evals.optimize --tool tool1
# uv run python -m evals.optimize --tool tool3 --optimizer miprov2

# 동작:
# 1. DB에서 해당 Tool의 전체 검증셋 로드
# 2. DSPy MIPROv2 optimizer 실행
#    - 초기 Module의 프롬프트를 LLM이 여러 변형 생성
#    - 각 변형을 검증셋으로 평가
#    - 점수 높은 프롬프트 선택
# 3. 최적화된 Module을 파일로 저장

import dspy

def optimize_tool(tool_name: str):
    # 검증셋 로드
    trainset = load_eval_dataset(tool_name)
    
    # 해당 Tool의 Module과 metric 가져오기
    module = get_module(tool_name)
    metric = get_metric(tool_name)
    
    # DSPy optimizer 실행
    optimizer = dspy.MIPROv2(metric=metric, auto="medium")
    optimized = optimizer.compile(module, trainset=trainset)
    
    # 최적화 결과 저장
    optimized.save(f"optimized_modules/{tool_name}/")
    
    # 최적화 전후 점수 비교 로그
    # before_score = evaluate(module, trainset, metric)
    # after_score = evaluate(optimized, trainset, metric)

# 주의사항:
# - 검증셋이 최소 10건은 있어야 의미 있는 최적화 가능
# - LLM 호출이 수십~수백 번 발생 → 비용 주의
# - auto="light" (적은 호출), "medium", "heavy" (많은 호출) 선택 가능
# - 최적화 결과는 optimized_modules/ 에 저장되어 재사용 가능
```

---

## 9. Pipeline — 메인 실행

### pipeline.py

Tool 1 → 2 → 3 → 4 → 5 → 6 순서로 실행하는 메인 스크립트.

```python
# 사용법:
# uv run python pipeline.py --case case_01
# uv run python pipeline.py --case case_01 --start-from tool3
# uv run python pipeline.py --case case_01 --interactive

# 동작:
# 1. DB에서 케이스 정보 + 입력 데이터 로드
# 2. Tool 1 → 2 → 3 → 4 → 5 → 6 순서로 실행
# 3. 각 Tool 실행 후:
#    a. Pydantic 스키마 검증 (형식)
#    b. 코드 기반 가드레일 검증 (내용)
#    c. 중간 결과를 JSON 파일 + DB에 저장
# 4. --start-from: 이전 Tool 결과를 DB/파일에서 로드하여 지정 Tool부터 재실행
# 5. --interactive: Tool 3, Tool 5 완료 후 사용자 확인 대기

# 가드레일 검증 규칙:
# - Tool 2 출력: 독립항 0개 → 중단
# - Tool 2 출력: 종속항이 존재하지 않는 청구항 참조 → 중단
# - Tool 3 출력: 모든 매칭이 "동일" → 경고
# - Tool 5 출력: 보정안이 빈 문자열 → 중단
# - Tool 5 출력: 원본과 완전 동일 → 경고
```

### DSPy LM 설정 (pipeline.py 상단)

```python
import dspy

# .env에서 API 키 로드
# Claude 사용 시:
lm = dspy.LM("anthropic/claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))
dspy.configure(lm=lm)

# 모델 변경 시 이 한 줄만 바꾸면 전체 파이프라인의 LLM이 바뀜
# lm = dspy.LM("openai/gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
```

---

## 10. utils/ 상세

### utils/regex_extractors.py

```python
"""정규식 기반 추출 함수 모음.
한국어/영어 특허 문서 패턴 모두 지원."""

def extract_rejection_articles(text: str) -> list[str]:
    """거절 법조항 추출.
    패턴: "제29조 제1항", "제29조 제2항", "제36조" 등
    영문: "Article 29(1)", "35 U.S.C. 103" 등"""
    pass

def extract_patent_numbers(text: str) -> list[str]:
    """특허번호 추출.
    패턴: "KR10-1234567", "KR 10-2020-0123456", 
    "US 11,234,567", "US2020/0123456" 등"""
    pass

def extract_claim_numbers(text: str) -> list[int]:
    """청구항 번호 추출.
    패턴: "제1항", "제3항", "제5항" 또는 "claims 1, 3, 5" 등"""
    pass

def classify_rejection_type(articles: list[str]) -> str:
    """법조항으로 거절 유형 판별.
    제29조 제1항 → 신규성
    제29조 제2항 → 진보성"""
    pass

def split_claims(text: str) -> list[dict]:
    """청구항 텍스트를 개별 청구항으로 분리.
    반환: [{"number": 1, "text": "...", "is_dependent": False, "depends_on": None}, ...]"""
    pass

def split_claim_elements(claim_text: str) -> list[str]:
    """단일 청구항을 구성요소로 1차 분리.
    comprising: 이후 세미콜론(;)으로 split."""
    pass

def classify_claim_type(claim_text: str) -> tuple[str, int | None]:
    """독립항/종속항 판별.
    "제N항에 있어서" 또는 "according to claim N" 패턴 감지.
    반환: ("독립항", None) 또는 ("종속항", 참조_청구항_번호)"""
    pass
```

### utils/diff_utils.py

```python
"""difflib 기반 텍스트 비교 유틸."""
import difflib

def generate_diff(original: str, modified: str) -> str:
    """원본과 수정본의 차이를 unified diff 형식으로 반환"""
    pass

def generate_diff_html(original: str, modified: str) -> str:
    """원본과 수정본의 차이를 HTML 하이라이트 형식으로 반환"""
    pass

def get_changed_parts(original: str, modified: str) -> dict:
    """추가된 부분, 삭제된 부분, 변경된 부분을 분리하여 반환"""
    pass
```

### utils/pdf_extractor.py

```python
"""PDF에서 텍스트와 도면을 분리 추출.
SA-1 역할을 대신하는 테스트 데이터 준비용."""

def extract_text(pdf_path: str) -> str:
    """PDF에서 텍스트 추출. pdfplumber 사용."""
    pass

def extract_images(pdf_path: str, output_dir: str) -> list[str]:
    """PDF에서 도면 페이지를 이미지로 저장.
    텍스트가 적은 페이지 = 도면 페이지로 분류."""
    pass

def split_patent_sections(text: str) -> dict:
    """특허 텍스트를 섹션별로 분리.
    반환: {"claims": "...", "description": "...", "drawings_desc": "..."}
    섹션 헤더: "청구범위", "상세한 설명", "도면의 간단한 설명" 등"""
    pass
```

---

## 11. data/case_01/expected/ 가이드

expected 폴더에 README.md를 만들어서 각 JSON 파일의 형식을 예시와 함께 설명해줘.
코드를 모르는 팀원이 이 README만 보고 JSON을 작성할 수 있어야 해.

### 파일 목록 및 형식

**tool1_expected.json** — 정답이 명확한 필드:
```json
{
  "rejection_articles": ["제29조 제2항"],
  "prior_art_numbers": ["KR10-1234567", "KR10-2345678"],
  "rejected_claim_numbers": [1, 3, 5],
  "rejection_type": "진보성"
}
```

**tool2_expected.json** — 청구항 파싱 정답:
```json
{
  "total_claims": 10,
  "independent_claims": [1, 6],
  "dependent_claims": {
    "2": 1, "3": 1, "4": 1, "5": 2,
    "7": 6, "8": 6, "9": 7, "10": 6
  },
  "claim_1_elements": [
    {"element_id": "e1", "text": "a tread portion having a groove pattern"},
    {"element_id": "e2", "text": "a sidewall portion"}
  ]
}
```

**tool3_expected.json** — Claim Chart 정답 (회사 자료 기반):
```json
{
  "matchings": [
    {
      "our_claim": 1,
      "prior_claim": 1,
      "element_matches": [
        {
          "our_element": "a tread portion having a groove pattern",
          "prior_element": "a tread with grooves",
          "match_level": "유사"
        }
      ]
    }
  ]
}
```

**tool4_checklist.json** — 전략 평가용 체크리스트:
```json
{
  "must_include": [
    "보강층 구조의 차이 언급",
    "홈 패턴의 기술적 효과 논증",
    "선행특허에 없는 구성요소 지적",
    "진보성 관점에서의 논증"
  ]
}
```

**tool5_checklist.json** — 보정안 평가용 체크리스트:
```json
{
  "must_include": [
    "보강층 관련 구성요소 추가 또는 구체화",
    "상세설명에 근거가 있는 표현 사용"
  ],
  "must_not_include": [
    "상세설명에 없는 새로운 기술 용어",
    "원본 청구항의 핵심 구성요소 삭제"
  ]
}
```

---

## 12. 단위테스트

tests/ 에는 확정적 로직만 테스트. LLM 출력은 테스트하지 않음 (그건 eval 영역).

### tests/test_regex.py
- `extract_rejection_articles`: 다양한 법조항 패턴 테스트
- `extract_patent_numbers`: 한국, 미국, 유럽 특허번호 패턴
- `split_claims`: 실제 청구항 텍스트로 분리 테스트
- `classify_claim_type`: 독립항/종속항 판별 테스트

### tests/test_tool6.py
- 저장/로드 라운드트립
- diff 생성 정확성
- 차수 증가 로직

### tests/test_db.py
- CRUD 정상 동작
- 존재하지 않는 ID 조회 시 처리
- 케이스 생성 및 조회

---

## 13. .env.example

```
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
DEFAULT_MODEL=anthropic/claude-sonnet-4-20250514
DB_PATH=db/patent_agent.db
```

---

## 14. .gitignore

```
# 환경 설정
.env
.venv/

# DB 파일 (각자 로컬에서 loader.py로 생성)
db/patent_agent.db

# Python
__pycache__/
*.pyc
.pytest_cache/

# uv
.python-version

# IDE
.vscode/
.idea/

# OS
.DS_Store

# ❌ optimized_modules/ 는 gitignore 하지 않음!
# 최적화 결과를 팀원과 공유해야 하므로 반드시 커밋.
```

---

## 15. 구현 우선순위

반드시 이 순서로 만들어줘:

1. `pyproject.toml` + `.env.example` (uv 환경 설정)
2. `schemas/` 전체 (common.py, tool1~6.py, db_models.py)
3. `db/database.py` + `db/loader.py` (SQLite 설정)
4. `utils/` 전체 (regex_extractors.py, diff_utils.py, pdf_extractor.py)
5. `signatures/` 전체 (DSPy Signature 정의)
6. `modules/` 전체 (뼈대 + tool6 완전 구현)
7. `tools/base.py` + 각 Tool 래퍼 (뼈대)
8. `evals/metrics.py` + `evals/datasets.py`
9. `evals/eval_runner.py` + `evals/optimize.py`
10. `pipeline.py`
11. `data/case_01/expected/README.md` (검증셋 작성 가이드)
12. `tests/` 전체
13. `README.md`

---

## 15. 주의사항

- **Python 3.10+**, 패키지 관리는 **uv만 사용** (pip 쓰지 마)
- 모든 파일에 **한국어 주석** 충분히. 코드 모르는 팀원도 읽을 수 있게.
- DSPy Signature의 docstring이 프롬프트에 반영되므로 **도메인 지식을 docstring에 상세히** 써줘.
- Pydantic v2 문법 사용.
- DB는 SQLite 단일 파일. ORM 쓰지 말고 직접 SQL 작성. 간단하게.
- eval 결과 JSON에는 반드시 타임스탬프, 모델명, 각 항목별 점수, 실패 항목 상세를 포함해.
- DSPy `inspect_history`로 자동 생성된 프롬프트를 확인할 수 있다는 걸 README에 안내해.
- `optimized_modules/` 폴더를 gitignore에 넣지 마. 최적화 결과를 팀원과 공유해야 함.