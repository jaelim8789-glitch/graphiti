# Graphiti Fork — 장기 유지보수 가이드

이 문서는 `jaelim8789-glitch/graphiti` Fork를 upstream(`getzep/graphiti`)과 지속적으로
동기화하고, Fork 고유 커밋(예: `.mcp.json`)을 잃지 않고 관리하는 방법을 정리한다.

## 1. Remote 구성 (현재 상태)

```
fork      https://github.com/jaelim8789-glitch/graphiti.git   (본인 Fork, push 대상)
upstream  https://github.com/getzep/graphiti.git              (원본, read-only)
```

로컬에 이 구성이 없다면:

```bash
git remote add upstream https://github.com/getzep/graphiti.git
git remote rename origin fork   # 기존 origin이 upstream이었던 경우
```

## 2. 브랜치 전략

- `main` (Fork): upstream 추적 + Fork 고유 커밋 병합. 직접 장기 기능 개발은 금지.
- 기능/수정 작업은 항상 토픽 브랜치에서 수행 후 `main`으로 merge.
- Fork 고유 설정(`.mcp.json` 등)은 별도 커밋으로 격리 → rebase/merge 충돌 최소화.

## 3. 수동 Sync 절차 (로컬)

```bash
# 1. upstream 최신 가져오기
git fetch upstream

# 2. Fork main을 upstream/main 기준으로 rebase
git checkout main
git rebase upstream/main

# 3. 충돌 해결 후 (필요 시)
git status
git add <resolved files>
git rebase --continue

# 4. Fork에 강제 푸시 (히스토리 재작성)
git push fork main --force-with-lease
```

> `--force-with-lease`는 다른 곳에서 push된 커밋을 실수로 덮어쓰는 것을 방지한다.
> 협업자가 있다면 반드시 사전 공지 후 진행.

## 4. GitHub Actions 수동 Sync (권장)

`.github/workflows/sync-upstream.yml` 워크플로우를 추가했다.
`Actions` 탭 → `Sync Upstream` → **Run workflow** 버튼으로 수동 실행한다.

- `upstream` remote에서 `main`을 fetch 후 Fork `main`에 merge.
- `GITHUB_TOKEN`으로 push하므로 별도 PAT 불필요.
- 자동 스케줄은 의도적 누락(통제된 동기화를 위해 수동 트리거만 허용).

## 5. Fork 고유 커밋 보존

upstream 동기화 시 `.mcp.json` 등 Fork 전용 파일은 일반적으로 충돌하지 않는다.
충돌 발생 시 ours 전략을 피하고 수동 병합한다.

## 6. 주기적 점검 체크리스트

- [ ] `git fetch upstream && git log HEAD..upstream/main --oneline` 로 신규 커밋 확인
- [ ] 분기 1회 이상 Sync 실행
- [ ] Dependabot / Security 알림 모니터링
- [ ] Fork 고유 커밋이 main에 유지되는지 확인
