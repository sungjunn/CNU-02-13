📋 특허 심사 파이프라인 전환 사양서
"기존 특허 심사 파이프라인을 LangGraph 기반 지능형 에이전트로 전환하라."

1. 아키텍처 및 상태 관리
상태 관리 (State Management):

schemas/ 모델들을 활용하여 Pydantic BaseModel 기반의 AgentState를 정의합니다.

모든 Tool 결과 필드는 초기값을 None으로 설정합니다.

prior_claims는 List[ClaimParseOutput] 형식으로 정의합니다.

user_feedback: str 필드를 추가하여 사용자의 수정 지시를 저장합니다.

영속성 (Persistence):

SqliteSaver를 사용하여 세션별 **체크포인트(Checkpoint)**를 구현합니다.

2. 노드 구현 및 가드레일
노드 래핑 (Node Wrapping):

tools/의 기존 로직을 6개의 독립적인 노드로 래핑합니다.

pipeline.py에 존재하던 모든 가드레일 (예: 독립항 부재 시 중단 등)을 각 노드 내부 로직으로 이식합니다.

예외 처리:

가드레일 위반 시 error_message를 상태에 기록하고 즉시 END 노드로 분기합니다.


3. 피드백 루프 및 흐름 제어
인적 검토 (Human-in-the-loop):

Tool4(전략)과 Tool5(보정안)은 Refinement 모드를 지원한다.

state에 user_feedback이 존재하면 다음 값을 LLM에 함께 전달한다

수정 루프 (Refinement Loop):

사용자 피드백이 있을 경우, 해당 내용을 AgentState.user_feedback에 저장합니다.

이후 워크플로우를 Tool 4 또는 Tool 5로 회귀시킵니다.

DSPy 연동:

되돌아간 노드는 user_feedback을 참조하여 기존 결과물을 수정합니다. DSPy 모듈 호출 시 해당 피드백 값을 프롬프트 인자로 전달합니다. Refinement 지원을 위해 Signature를 수정한다.

human_review 노드는 interrupt를 사용한다.

사용자 입력

approve redo_strategy redo_amendment exit
사용자 입력은

state["user_feedback"]
에 저장된다.

LangGraph Command(resume=...) 패턴을 사용하여 interrupt 이후 상태를 재개한다.


4. 관측성 (Observability: Langfuse + DSPy)
트레이싱 (Tracing):

Langfuse를 연동하되, 단순 노드 추적을 넘어 DSPy 내부의 LLM 호출 전체가 트레이싱되도록 langfuse.callback 또는 SDK 패치 설정을 포함합니다.

모니터링:

모든 노드 함수에 @observe() 데코레이터를 적용하여 실행 과정을 가시화합니다.

5. 환경 및 프로젝트 구조
의존성 관리:

pyproject.toml에 langgraph, langfuse, langchain-core 라이브러리를 추가합니다.

파일 구조:

agent.py: 그래프 및 워크플로우 정의

run_agent.py: 에이전트 실행기(Runner) 구현

호환성:

기존에 구현된 db/ 모듈과 완벽하게 호환되도록 데이터 인터페이스를 유지합니다.

LangGraph SqliteSaver를 사용하여 상태를 저장한다.

6. eval 시스템과의 호환성 미언급

기존 eval_runner.py, optimize.py가 LangGraph 전환 후에도 작동하는지, 개별 Tool eval은 어떻게 하는지 빠져있음.