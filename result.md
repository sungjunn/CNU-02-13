(base) (patent_agent) PS C:\Users\2343\Desktop\a_test\patent_agent> uv run python run_agent.py --case case_01
[LM] 모델: openrouter/google/gemma-3-27b-it
[Langfuse] API 키 미설정 — 트레이싱 비활성화

============================================================
  특허 심사대응 에이전트 — 케이스: case_01
============================================================

Deserializing unregistered type schemas.common.RejectionType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'RejectionType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Authentication error: Langfuse client initialized without public_key. Client will be disabled. Provide a public_key parameter or set LANGFUSE_PUBLIC_KEY environment variable.
  [기본 모듈] tool1: 최적화 결과 없음
  [기본 모듈] tool2: 최적화 결과 없음
  [기본 모듈] tool3: 최적화 결과 없음
  [기본 모듈] tool4: 최적화 결과 없음
  [기본 모듈] tool5: 최적화 결과 없음
  → 저장: data\results\case_01\tool1.json
  거절 유형: 진보성 | 법조항: ['제29조 제2항']
  ✓ tool1 완료
Authentication error: Langfuse client initialized without public_key. Client will be disabled. Provide a public_key parameter or set LANGFUSE_PUBLIC_KEY environment variable.
  → 저장: data\results\case_01\tool2.json
  당사 청구항: 3개 (독립항: [1, 1, 4])
  ✓ tool2 완료
Authentication error: Langfuse client initialized without public_key. Client will be disabled. Provide a public_key parameter or set LANGFUSE_PUBLIC_KEY environment variable.
  → 저장: data\results\case_01\tool3.json
  전체 20개 구성요소 비교: 동일 2개, 유사 15개, 없음 3개.
  ✓ tool3 완료
Deserializing unregistered type schemas.common.RejectionType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'RejectionType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.ClaimType from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'ClaimType')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]
Deserializing unregistered type schemas.common.MatchLevel from checkpoint. This will be blocked in a future version. Add to allowed_msgpack_modules to silence: [('schemas.common', 'MatchLevel')]

────────────────────────────────────────────────────────────
[Claim Chart 요약]
전체 20개 구성요소 비교: 동일 2개, 유사 15개, 없음 3개.
────────────────────────────────────────────────────────────
옵션: approve / exit
선택 >