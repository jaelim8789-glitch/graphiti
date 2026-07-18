# Graphiti 개발 자동화 & MCP 워크플로우

이 Fork는 AI 에이전트(Claude/Cline/Kiro)가 Graphiti를 개발할 때 쓰는 MCP 자동화와
개발 편의 타깃을 제공한다.

## 1. MCP 서버 구성 (`.mcp.json`)

| 서버 | 용도 |
|------|------|
| `graphiti` | 로컬 Graphiti MCP 서버 (`http://127.0.0.1:8001/mcp/`) |
| `qdrant` | 벡터 검색/메모리 (로컬 venv 바이너리) |
| `git` | 저장소 작업 자동화 |
| `filesystem` | 워크스페이스 파일 접근 |
| `context7` | 라이브러리 문서 조회 |
| `playwright` | e2e/UI 검증 자동화 |
| `sequential-thinking` | 복잡한 설계 단계 추론 |
| `fetch` | 이슈/문서 웹 조회 (`mcp-server-fetch`) |
| `docker` | Neo4j 컨테이너 기동/관리 |

> 로컬 전용 서버(graphiti/qdrant/git)는 현재 Windows 경로에 하드코딩되어 있다.
> 타 OS로 이식 시 해당 바이너리 경로를 환경에 맞게 조정.

## 2. Make 타깃

```bash
make dev-setup     # 의존성 설치 + Neo4j 컨테이너 기동
make mcp-up        # Neo4j + Graphiti MCP 서버 시작
make mcp-down      # 개발 스택 중지
make mcp-status    # 컨테이너/포트 상태 확인
make mcp-dev       # MCP 서버 포그라운드 실행 (--reload, 디버깅)
make check         # format + lint + test
```

## 3. 개발 흐름 (에이전트 기준)

1. `make mcp-up` 으로 Neo4j + Graphiti MCP 서버 기동
2. 에이전트가 `.mcp.json` 서버로 코드 탐색/수정/테스트
3. `make check` 로 포맷·린트·단위테스트 검증
4. 변경 후 upstream 동기화는 `make` 없이 `docs/FORK_MAINTENANCE.md` 절차 따름

## 4. CI (Fork 전용)

- `.github/workflows/sync-upstream.yml`: upstream 수동 동기화
- upstream 기본 CI(lint/typecheck/test)는 그대로 상속
