# Patent Agent

한국 특허 의견제출통지서 → Claim Chart + 보정 청구항 자동 생성 파이프라인.

특허·의견제출통지서 텍스트를 넣으면 Claim Chart Excel + 보정 청구항 초안을 자동 생성.

**Tool 흐름 (순차 실행):**

| Tool | 역할 | 방식 |
|------|------|------|
| Tool 1 | 의견제출통지서 → 거절이유·인용발명 구조화 | LLM API |
| Tool 2 | 청구항 원문 → 독립항/종속항/구성요소 분해 | LLM API |
| Tool 3 | 구성요소 ↔ 상세설명 단락 매핑 | LLM API |
| Tool 4 | 당사 청구항 vs 선행특허 1:1 비교 (Claim Chart) | LLM API |
| Tool 5 | 차이점 분석 + 거절이유별 대응 전략 수립 | LLM API |
| Tool 6 | 보정 청구항 초안 생성 (quality 낮으면 재시도) | LLM API |
| Tool 7 | 결과 JSON 저장 (차수 관리) | 파일 I/O |
| Tool 8 | Claim Chart Excel 파일 생성 | openpyxl |

→ 최종 출력: `data/results/{출원번호}/round_{n}_chart.xlsx`

## 입력 데이터 준비 방식

`data/samples/` 안의 파일들:
미리 특허에서 텍스트 추출되있다는 가정으로
- `office_action_*.txt` — 의견제출통지서 PDF에서 텍스트 직접 복붙
- `our_patent_claims.txt`, `our_patent_description.txt` — 특허 원문에서 텍스트 직접 복붙
- `prior_art_jp2007141071.txt` — 위 두 문서를 바탕으로 LLM이 생성한 선행특허 번역본

## 스택
- 클로드 SDK (agent 프레임워크 사용 x)
- LLM: claude-haiku-4-5-20251001 (factchat api )
- 데이터 검증: Pydantic v2
- 패키지 관리: uv

## 실행

```bash
# 최초 세팅
uv venv && uv sync --extra dev
cp .env.example .env  # FACTCHAT_API 입력

# 연결 테스트
uv run python llm/client.py

# 전체 파이프라인
uv run pytest tests/test_e2e.py -v -s
```

## 구조

```
schemas/   Pydantic 모델 (OfficeAction, Claim, ClaimChart, AmendedClaim)
tools/     Tool 1~8 (통지서 파싱 → Claim Chart → 보정 청구항 → Excel)
agent/     pipeline.py (순차 실행) / agent.py (재시도 판단 포함)
llm/       Factchat Gateway 래퍼 (Anthropic SDK, LLM 호출 공통 모듈)
data/      samples/ (입력 텍스트), results/ (출력 JSON/Excel)
```

