# byeori-local 단계 B 구현 제안서 — 작업 수명·재개·백업

작성일 2026-10-12. 검토 대상은 작업 트리(HEAD `a9228f0` + 미커밋 변경)이며, 이 문서는 **구현을 맡는 다른 모델이 저장소만 읽고 작업을 시작할 수 있을 만큼** 상세하게 쓴 명세다. 앞선 두 문서 — [검토서](LOCAL-LLM-REVIEW-2026-10-01.md)와 [수정 명세서](LOCAL-LLM-REMEDIATION-SPEC-2026-10-01.md) — 가 정한 원칙과 용어를 그대로 쓴다. 수정 명세서 20절의 단계 구분(A~E)에서 **단계 A는 끝났고, 이 문서는 단계 B를 구현 가능한 수준으로 구체화**한다.

읽는 순서: 1절(현재 상태)과 2절(결함 목록)을 먼저 읽고, 3절의 보존 계약을 지킨 채 8절의 순서대로 4절·5절을 구현한다. 6절은 실제 워크스페이스에서 사람이 수행하는 검증 절차다.

---

## 1. 현재 진행 상황 — 2026-10-12에 직접 확인한 사실

| 항목 | 확인한 값 |
| --- | --- |
| HEAD | `a9228f0` (2026-10-01 01:11 KST), `origin/main`과 동일 |
| 미커밋 변경 | 추적 파일 13개 수정(`+747 / −434`), 미추적 파일 7개(1,708줄). **11일간 버전 관리 밖**에 있다 |
| 전체 테스트 | `.venv/bin/python -m pytest -o addopts='' -q` → **2,459 passed, 1 skipped** (16초) |
| 로컬 테스트 | `test_local_integrity.py`·`test_local_runtime.py`·`test_local_remediation.py`·`test_local_assistant.py` → **170 passed** |
| 단계 A | R01~R11 전부 수정, 회귀 테스트 32개 전환. 결과는 수정 명세서 22절에 기록됨 |
| 업무 도우미 | `byeori-assistant` 4개 작업(notes/commits/classify/report), CLI+MCP 7개 도구, 테스트 32개, 실제 모델 실행 기록 15건. [LOCAL-ASSISTANT.md](LOCAL-ASSISTANT.md). 검토서의 A~E 로드맵 밖에서 추가된 갈래다 |
| 실제 워크스페이스 `.byeori-local/` | **schema 4**(코드는 5), 논문 11편, 활성 노트 11개, revision 27개, job 51개. `journal_mode=delete`. `document_aliases`·`metadata_checks` 테이블 아직 없음(열 때 생성됨). 크기: `papers/` 96 MB, `runs/` 6.3 MB, `wiki/` 216 KB, DB 384 KB |
| 실제 job 이력 | 성공 31(노트 24 + 레거시 3 + 질문 4), 실패 18, 취소 1, 중단 1 |
| 서비스 | Ollama 0.34.4(`sh.brew.ollama.plist`로 launchd 관리), GROBID 0.9.1 `/api/version` 응답 확인 |

### 1.1 실패 18건의 원인 분포 — 단계 B의 우선순위 근거

실제 DB를 읽기 전용으로 조회한 결과다(`jobs.error` 기준).

| 원인 | 건수 | 뜻 |
| --- | --- | --- |
| `Model did not finish normally; incomplete output was not published` | **7** | 출력 한도(`num_predict`) 도달. 모두 digest 또는 노트 생성 중, 모두 **처음부터 재실행**됨 |
| 구조 검증 실패(heading 순서 2, 미인용 3, 미지 문단 ID 1) | 6 | 모델 출력 문제; `revalidate`로 일부 구제 가능 |
| `GROBID extraction failed` | 3 | 같은 초에 3건 — 추출기 서버가 내려간 상태에서 배치가 큐를 소진함 |
| `Input exceeds conservative context budget` (레거시 경로) | 1 | 현재 코드에는 분할 경로가 있어 재현되지 않음 |
| `Block P0080 alone needs about 1688 tokens and a part may use 1536` | 1 | 단일 블록이 출력 예산 초과 |

**결론**: 실패의 7/18이 수십 분 진행 후 출력 한도에서 끊긴 뒤 체크포인트 없이 전체 재실행된 경우고, 3/18은 추출기 가용성 확인 없이 큐를 태운 경우다. 둘 다 단계 B(재개·worker preflight)가 직접 겨냥하는 결함이다.

---

## 2. 이번 조사에서 확인한 부족한 점

각 항목은 파일·행(2026-10-12 작업 트리 기준), 확인한 증거, 결과를 적는다. F01~F19는 4절의 구현 항목과 5절의 테스트에서 번호로 참조한다.

### 작업 수명 (worker)

| 번호 | 결함 | 위치 | 증거와 결과 |
| --- | --- | --- | --- |
| F01 | 노트 job에 `queued` 상태가 없다 | `store.py:318-322` `start()` | `INSERT ... 'running','start'`로 바로 실행 상태. 제출과 실행을 분리할 수 없어 CLI가 끝날 때까지 수 시간 전면에 묶인다 |
| F02 | 질문 worker가 daemon thread다 | `jobs.py:66` | 제출 프로세스가 끝나면 함께 사라진다. MCP 서버 종료 시 실행 중 질문은 `interrupted`(실데이터 1건). 지속 실행 보장이 아니다 |
| F03 | claim이 자기 `owner_token`에 묶여 있다 | `store.py:357-366` `claim_question`, `store.py:339-355` orphan 판정 | `owner_token IS ?` 때문에 다른 프로세스가 제출한 질문을 지속 worker가 가져갈 수 없다. orphan 판정은 **제출자 PID**(`request.pid`) 기준이라, 제출 CLI가 종료되면 worker가 처리할 질문도 `interrupted`로 바뀐다. worker 모드와 양립 불가 |
| F04 | heartbeat·attempt·fencing이 없다 | `jobs` DDL `store.py:36-40`, `set_stage`/`finish` `store.py:389-410` | 상태 변경이 `job_id`만으로 이뤄진다. 살아 있는지 알 수 없고, 수정 명세서 7.1의 `worker_id/attempt/heartbeat_at/started_at/cancel_ack_at`가 없다 |
| F05 | 취소가 part 경계에서 확인되지 않는다 | `service.py:885-980` `_write`, `store.py:476-478` | 취소는 `publish()`에서만 거부된다. 13 part 논문을 취소해도 13번 모델 호출을 모두 마친 뒤 버린다(part당 수 분) |
| F08 | HTTP timeout 600초가 설정으로 노출되지 않는다 | `llm.py:96`, `cli.py:33-37` | `build_service`가 `timeout`을 넘기지 않는다. 한 호출이 10분을 넘으면 `outcome_unknown` → endpoint 전체 `recovery_pending` → 무인 배치가 멈춘다 |
| F15 | worker 로그가 없다 | — | 장기 실행의 관측 수단이 DB의 `stage` 한 칸이다 |
| F16 | `process_all`이 배치 전체 동안 `.worker.lock`을 쥔다 | `service.py:461-479` | 의도된 직렬화지만, 그동안 `metadata`·`revalidate`·`process`가 모두 "Another worker is processing"으로 실패한다. 큐에 넣는 경로가 없다 |
| F19 | 추출기 가용성 preflight가 없다 | `service.py:281-291` | GROBID가 내려가 있으면 큐의 모든 노트 job이 같은 오류로 즉시 실패한다(실데이터 3건, 같은 초) |

### 재개 (checkpoint)

| 번호 | 결함 | 위치 | 증거와 결과 |
| --- | --- | --- | --- |
| F06 | 재개가 없다 | `service.py:493-575` `_process` | 매 실행이 새 job·새 추출·모든 part 재 digest다. `runs/<job>/digest-NN.md`·`document.json`은 남지만 아무 경로도 다시 읽지 않는다(`revalidate`가 `candidate.md`를 재사용하는 것이 유일한 예외). 1.1의 7건이 전부 처음부터 재실행됐다 |
| F07 | 출력 한도 도달이 별도 오류가 아니다 | `llm.py:252`, `service.py:924` | `done_reason != "stop"`이면 모두 같은 `ModelError`. `_write`는 문자열 `"did not finish"` 포함 여부로 분기한다. `done_reason` 값(`length`)이 receipt에 남지 않아 1.1의 분류도 오류 문구로 추정한 것이다 |

### 저장·복구 (backup / restore / reindex / migration)

| 번호 | 결함 | 위치 | 증거와 결과 |
| --- | --- | --- | --- |
| F09 | 백업·복원 명령이 없다 | `cli.py:137-184` 명령 목록 | 실제 워크스페이스(103 MB)의 보호 수단이 파일 복사 외에 없다. 수정 명세서 18.2 미구현 |
| F10 | 색인 재구축이 없다 | `store.py:480-500` `publish` 내부 | 색인 코드가 `publish` 안에 인라인이다. `integrity_problems`는 색인 불일치를 **탐지만** 한다. 복원 뒤 색인을 다시 만들 수 없다 |
| F11 | migration이 `ADD COLUMN`만 가정한다 | `store.py:130` | `statement.split()[2]`, `[-2]`로 테이블·컬럼명을 뽑는다. `CREATE TABLE`/`CREATE INDEX` 문장은 잘못 파싱된다. 단계 B의 신규 테이블 추가 전에 반드시 고쳐야 한다 |
| F12 | migration이 열 때 자동 실행되고 사전 계획·백업이 없다 | `store.py:97-118` `__init__` | 실제 워크스페이스는 schema 4다. 다음 어떤 명령이든 제자리에서 올린다. 수정 명세서 18.1의 "읽기 전에 계획 확인" 미구현 |
| F13 | `journal_mode=delete` | `store.py:160` | 지속 worker(writer) + MCP 서버(reader) + CLI(reader/writer)가 동시에 열면 `SQLITE_BUSY`를 `timeout=30`으로만 버틴다 |
| F14 | `runs/` 산출물이 DB에 추적되지 않는다 | `_refresh` `service.py:686-747`, `_revalidate` `service.py:814-880` | 어느 파일이 어느 job의 것인지 경로 규약으로만 안다. manifest가 없다. `metadata`·`revalidate` job은 `receipt.json`조차 쓰지 않아 `reconcile_receipts`가 건너뛴다 |

### 문서·버전 관리

| 번호 | 결함 | 위치 | 증거와 결과 |
| --- | --- | --- | --- |
| F17 | 존재하지 않는 CLI 안내 잔존 | `docs/evaluation/*.md:18` (논문 11편 전부) | `byeori-local read_paper_context`는 CLI가 아니라 MCP 도구다. `cli.py:86`의 생성기는 이미 고쳐졌으나 생성된 11개 파일은 그대로다 |
| F18 | 두 묶음이 한 작업 트리에 미커밋 | `git status` | 안정화(R01~R11)와 업무 도우미가 섞여 있다. 어느 한쪽만 되돌릴 수 없다 |

---

## 3. 수정 범위와 보존 계약

범위는 `src/byeori/local/`, `tests/test_local_*.py`, `docs/LOCAL-*.md`다. 원본 AWS 명령·인프라·테스트는 건드리지 않는다. 업무 도우미(`assistant*.py`)는 이번 단계의 변경 대상이 아니다(worker 통합은 단계 B 이후 별도 범위).

수정 명세서 2절의 계약 다섯 가지를 그대로 지킨다. 이 단계에서 특히 중요한 것:

1. 원본 PDF, 과거 추출, 노트 revision, `runs/` 산출물, 검토 이력은 **삭제·제자리 덮어쓰기 금지**. 체크포인트 재사용은 **참조**이며 복사·이동이 아니다.
2. 실패·취소·중단된 attempt가 활성 노트·검색 결과를 바꾸지 않는다.
3. `job.succeeded` ≠ 노트 게시 ≠ 형식 검증 ≠ 사람 검토. 새 상태(`queued`, worker 상태, 체크포인트 재사용)도 이 구분을 흐리지 않는다.
4. cloud 모델·자동 cloud fallback 금지. worker는 기존 `OllamaBackend`의 local-only preflight를 그대로 쓴다.
5. **restore는 새 디렉터리에만** 한다. 기존 워크스페이스 위에 덮어쓰는 복원 경로를 만들지 않는다.
6. 로그·receipt·manifest에 논문 본문, prompt 전문, secret을 쓰지 않는다. 경로·ID·hash·토큰 수만 쓴다.

---

## 4. 구현 명세

### 4.0 선행 작업 — 구현 전에 사람이 한다

**(a) 커밋 분리.** 성격이 다른 두 묶음을 나눈다. 순서대로 실행한다.

```sh
cd "$REPO"    # 저장소 루트의 절대 경로
# 1) 안정화 (R01~R11) + 검토 문서
git add .gitignore docs/LOCAL-DEVELOPMENT.md docs/LOCAL-LLM-REMEDIATION-SPEC-2026-10-01.md \
        docs/LOCAL-LLM-REVIEW-2026-10-01.md docs/reviews/ \
        src/byeori/local/cli.py src/byeori/local/jobs.py src/byeori/local/llm.py \
        src/byeori/local/locking.py src/byeori/local/mcp_server.py src/byeori/local/metadata.py \
        src/byeori/local/service.py src/byeori/local/store.py src/byeori/local/evidence.py \
        tests/test_local_integrity.py tests/test_local_runtime.py tests/test_local_remediation.py \
        tests/local_helpers.py
git commit -m "Fix the eleven reproduced defects of the local runtime and turn them into regression tests"
# 2) 업무 도우미
git add pyproject.toml src/byeori/local/assistant.py src/byeori/local/assistant_cli.py \
        src/byeori/local/assistant_mcp.py tests/test_local_assistant.py examples/ docs/LOCAL-ASSISTANT.md
git commit -m "Add a bounded local work assistant with its own workspace"
git push origin main
```

`pyproject.toml`의 변경은 `byeori-assistant`·`byeori-assistant-mcp` 두 스크립트 추가만이므로 2번 커밋에 속한다(`git diff pyproject.toml`로 확인했다). `docs/LOCAL-DEVELOPMENT.md`에는 업무 도우미 링크 한 줄이 섞여 있지만 분리할 가치가 없다.

**(b) 실제 워크스페이스의 수동 백업.** 4.6의 `backup` 명령은 워크스페이스를 **열면서** migration을 수행하므로, 첫 번째 백업은 아무 프로세스도 열지 않은 상태에서 파일 복사로 한다. MCP 서버·worker가 떠 있지 않은지 확인한 뒤:

```sh
cp -Rp .byeori-local ".byeori-local.pre-schema6-$(date +%Y%m%d)"
```

이 복사본은 schema 4 그대로이며 **이전 코드로 열 수 있는 유일한 복원점**이다. 지우지 않는다.

**(c) F17 정정.** 11개 평가 파일의 18행을 `cli.py:86`이 현재 쓰는 문구(`MCP read_paper_context(paper_id, paragraph_id, revision)`)로 바꾼다. 내용 변경이 아니라 안내 정정이므로 판정 fingerprint에 영향이 없다.

### 4.1 schema 6과 migration 일반화 (F11, F12, F13, F04 기반)

**`store.py`**

```python
SCHEMA_VERSION = 6
JOB_KINDS = ("note", "question", "metadata", "revalidate")
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "interrupted")  # 변경 없음
EXECUTORS = ("inline", "worker")
```

`MIGRATIONS[6]`은 다음 문장을 이 순서로 담는다. `SCHEMA` 스크립트(새 워크스페이스용)에도 같은 테이블·인덱스를 추가한다.

```sql
ALTER TABLE jobs ADD COLUMN worker_id TEXT;
ALTER TABLE jobs ADD COLUMN attempt INTEGER NOT NULL DEFAULT 1;
ALTER TABLE jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3;
ALTER TABLE jobs ADD COLUMN heartbeat_at TEXT;
ALTER TABLE jobs ADD COLUMN started_at TEXT;
ALTER TABLE jobs ADD COLUMN cancel_ack_at TEXT;
ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN executor TEXT;
ALTER TABLE jobs ADD COLUMN resumed_from TEXT;
ALTER TABLE jobs ADD COLUMN error_code TEXT;
CREATE INDEX IF NOT EXISTS jobs_claim ON jobs (status, executor, priority, created_at);
CREATE TABLE IF NOT EXISTS workers (
    worker_id TEXT PRIMARY KEY, pid INTEGER NOT NULL, process_started TEXT, hostname TEXT,
    code_version TEXT, started_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL,
    state TEXT NOT NULL, current_job_id TEXT, stopped_at TEXT);
CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, stage TEXT NOT NULL,
    key_sha256 TEXT NOT NULL, job_id TEXT NOT NULL, created_at TEXT NOT NULL,
    files TEXT NOT NULL, meta TEXT NOT NULL,
    UNIQUE (paper_id, stage, key_sha256));
CREATE INDEX IF NOT EXISTS checkpoints_paper ON checkpoints (paper_id, stage);
CREATE TABLE IF NOT EXISTS job_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, at TEXT NOT NULL,
    event TEXT NOT NULL, worker_id TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS job_events_job ON job_events (job_id, event_id);
```

`_migrate`(`store.py:120-133`)를 다음 규칙으로 일반화한다.

- 문장이 `ALTER TABLE <t> ADD COLUMN <c>`로 시작하면 지금처럼 `PRAGMA table_info`로 컬럼 존재를 확인하고 없을 때만 실행한다.
- 그 외 문장(`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`)은 그대로 실행한다. 멱등이어야 하므로 `IF NOT EXISTS`가 없는 문장은 `ValueError`로 거부한다(구현자가 실수로 넣는 것을 막는다).
- 각 버전의 문장 전체를 **하나의 트랜잭션**으로 적용하고 마지막에 `schema_version`을 올린다. 중간 실패 시 롤백되어 이전 버전으로 남는다(`with con:` 블록이 이미 그 역할을 하지만, `executescript`는 쓰지 않는다 — 암묵적 COMMIT을 일으킨다).
- 기존 행의 `executor`가 `NULL`이면 **inline으로 해석**한다(4.4). migration에서 `UPDATE`로 채우지 않는다 — 과거 기록은 그대로 둔다.

**자동 migration 제어 (F12).**

- 환경 변수 `BYEORI_LOCAL_AUTO_MIGRATE` 기본 `on`. `off`면 `LocalStore.__init__`가 schema가 낮은 워크스페이스를 열 때 `ValueError("Workspace schema is 4 and this release reads 6; run 'byeori-local migrate --plan' and back up first")`를 던지고 `error_code = "schema_migration_required"`로 CLI exit 1.
- 새 CLI 명령 `byeori-local migrate --plan`: DB를 **읽기 전용**(`?mode=ro`)으로 열어 `{ "current": 4, "target": 6, "steps": {5: [...], 6: [...]}, "backup_recommended": true }`를 출력한다. 워크스페이스를 바꾸지 않는다.
- `byeori-local migrate --apply`: 일반 열기와 같은 migration을 수행하고 `{ "from": 4, "to": 6 }`를 출력한다.
- `doctor` 출력에 `schema: {"version": 6, "code": 6}`를 추가한다.

**WAL (F13).** `LocalStore.db()`(`store.py:159-166`)에서 연결 직후 `PRAGMA journal_mode=WAL`을 한 번 실행한다(DB에 영구 저장되므로 첫 연결에서만 실제 전환). `PRAGMA synchronous=NORMAL`은 쓰지 않는다 — 기본 `FULL` 유지. WAL은 reader가 writer를 막지 않게 해 F13을 해소하고, 4.6의 `Connection.backup()`과 호환된다. `catalog.sqlite3-wal`·`-shm` 파일이 생기므로 4.6의 백업은 **이 파일을 복사하지 않고 backup API로 DB를 뜬다**.

**유지보수 잠금.** `locking.py`에 공유/배타 잠금을 추가한다.

```python
@contextmanager
def maintenance_lock(root, *, exclusive=False):
    """Readers and writers hold it shared; backup, restore and reindex hold it exclusive."""
    # .maintenance.lock 파일에 fcntl.flock(LOCK_SH 또는 LOCK_EX). Windows(msvcrt)는 공유 잠금이
    # 없으므로 둘 다 배타로 동작하며 doctor가 "maintenance_lock: exclusive_only"로 표시한다.
```

`LocalStore.db()`는 연결을 여는 동안 `maintenance_lock(root)`(공유)을 쥔다. 백업·복원·reindex는 배타로 쥐어 모든 DB 접근을 **잠깐** 멈춘다(모델 호출은 DB 연결을 쥐지 않으므로 계속 돈다). 재진입: 같은 스레드가 공유 잠금을 중첩해 쥐는 것은 허용된다(flock은 open file description별이라 자연히 그렇다). 배타 잠금을 쥔 스레드가 `self.db()`를 열면 데드락이므로, 백업·reindex 코드는 **자기 연결을 직접 `sqlite3.connect`로 연다**.

### 4.2 공통 기반 — 작업 테이블 API 확장 (F01, F03, F04, F14)

`LocalStore`에 다음을 추가·변경한다. 기존 공개 메서드의 시그니처는 유지한다.

```python
def enqueue(self, kind, *, paper_id=None, request=None, priority=0, executor="worker",
            resumed_from=None, attempt=1, max_attempts=3) -> str:
    """Insert a queued job. kind in JOB_KINDS. request is JSON-serialisable or None."""

def claim_next(self, worker_id) -> dict | None:
    """BEGIN IMMEDIATE; pick the first row of
       SELECT job_id FROM jobs WHERE status='queued' AND executor='worker'
         ORDER BY priority DESC, created_at ASC, job_id ASC LIMIT 1;
       UPDATE jobs SET status='running', stage='claimed', worker_id=?, started_at=?, heartbeat_at=?
         WHERE job_id=? AND status='queued';   -- rowcount must be 1
       INSERT job_events(..., 'claimed', worker_id, NULL)
       return self.job(job_id)"""

def heartbeat(self, job_id, worker_id, *, worker_state, at=None):
    """UPDATE jobs SET heartbeat_at=? WHERE job_id=? AND worker_id=? AND status='running';
       UPDATE workers SET heartbeat_at=?, state=?, current_job_id=? WHERE worker_id=?"""

def register_worker(self, worker_id, *, pid, process_started, hostname, code_version) -> None
def stop_worker(self, worker_id, state="stopped") -> None
def worker_status(self) -> dict:
    """The newest workers row plus: alive (pid alive AND process_started matches AND
       heartbeat age < 60 s), heartbeat_age_seconds, state, current_job_id."""

def event(self, job_id, event, *, worker_id=None, detail=None) -> None
def events(self, job_id, limit=50) -> list[dict]

def sweep_running_worker_jobs(self, worker_id, *, requeue=True) -> dict:
    """Called by a worker that has just taken .worker.lock, so no other worker is alive.
       For every row WHERE status='running' AND executor='worker':
         - mark it interrupted (error_code 'worker_interrupted', cancel_ack_at if cancel_requested)
         - if requeue and cancel_requested IS NULL and attempt < max_attempts:
               enqueue(kind, paper_id, request, priority, executor='worker',
                       resumed_from=job_id, attempt=attempt+1, max_attempts)
               event(job_id, 'requeued', detail={'as': new_job_id})
           else: error_code 'max_attempts_exhausted' when the cap stopped it
       Returns {'interrupted': [...], 'requeued': {old: new}}"""

def release_claim(self, job_id, worker_id, *, reason) -> None:
    """running → queued again, worker_id NULL, stage 'released'; event 'released'.
       Used only when the worker discovers a precondition (extractor down) before any model call."""
```

**fencing.** `set_stage`, `finish`, `publish`, `_record_terminal`에 선택 인자 `lease=None`을 추가한다. `lease`는 `{"job_id", "worker_id"}`다. `lease`가 있으면 모든 UPDATE에 `AND worker_id=?`를 붙이고, `rowcount != 1`이면 `StaleLease(RuntimeError)`(`error_code="stale_lease"`)를 던진다. `lease`가 없으면(inline 경로) 지금 동작과 같다. 하나의 job 행은 `queued→running`을 한 번만 거치고 그 worker만 쓰므로 `attempt` 컬럼은 체인 길이 정보일 뿐 fencing에 쓰지 않는다 — 재시도는 **항상 새 job 행**이다(아래 4.4). `publish()`는 트랜잭션 안의 기존 검사(`store.py:476-478`)에 `worker_id` 일치를 더한다.

**취소 확인 지점.** `request_cancel`(`store.py:370-382`)은 그대로 두고, `cancel_ack_at`은 실행 측이 취소를 **인지한 시각**으로 `finish(..., "cancelled")` 안에서 기록한다. MCP `cancel_job`과 CLI `cancel`은 이제 모든 kind에 동작한다(코드상 이미 그렇다; 문서만 바뀐다).

**inline 질문 경로(F03 호환).** `claim_question(owner_token)`의 WHERE를 `AND (executor IS NULL OR executor='inline') AND owner_token IS ?`로 바꾼다. `orphaned_questions()`는 `executor IN (NULL,'inline')`인 행만 본다. worker 행의 orphan 판정은 `sweep_running_worker_jobs`(worker 시작 시)와 `worker_status().alive`(조회 시 진단)로 대체한다. `start_question(..., executor="inline")` 기본값으로 기존 동작을 보존하고, `QuestionJobs.submit`은 `service.executor`가 `"worker"`일 때 `store.enqueue("question", request=..., priority=10, executor="worker")`만 하고 thread를 띄우지 않는다.

**receipt 보완 (F14).** `_refresh`와 `_revalidate`는 성공·실패 모두 `runs/<job_id>/receipt.json`을 `write_new`로 남긴다. 최소 필드: `job_id, kind, paper_id, outcome, stage, started_at, finished_at, error, error_code, revision_id(성공 시), written_by_job(revalidate), checkpoints: null`. `reconcile_receipts`는 `execution.json`이 없어도 `kind in ('metadata','revalidate')`면 DB에서 복원한다.

### 4.3 출력 한도·timeout·추출기 preflight·취소 지점 (F05, F07, F08, F19)

**`llm.py`**

```python
class OutputTruncated(ModelError):
    error_code = "output_truncated"          # done_reason == "length"

class AbnormalStop(ModelError):
    error_code = "abnormal_stop"             # done is not True, or any other done_reason
```

`_generate`(`llm.py:252-253`)의 한 줄 검사를 둘로 나눈다. `Generation.metadata`에 `done_reason`을 항상 기록한다. `generate(system, prompt, *, think=None, response_format=None, num_predict=None)` — `num_predict`가 주어지면 `options.num_predict`를 그 값으로 하되 `num_predict + estimated_input + RESERVE_TOKENS <= context`가 아니면 `ValueError`. `OllamaBackend.__init__`의 `timeout`을 `build_service`가 `--timeout` / `BYEORI_OLLAMA_TIMEOUT`(기본 600)으로 넘긴다. worker 문서는 1800을 권한다.

`fingerprint()` 메서드를 추가한다: `doctor()`를 한 번 호출해 `{"model", "digest", "template_sha256", "server_version", "context", "output"}`를 반환한다. 체크포인트 키(4.5)의 입력이다. `_generate`가 매 호출 `doctor()`를 부르는 현재 구조는 유지한다(local-only 검사).

**`service.py`**

- `_write`(`service.py:924`)의 `"did not finish" not in str(exc)` 분기를 `not isinstance(exc, OutputTruncated)`로 바꾼다. 분할 정책은 그대로다.
- 최종 노트 패스(single 또는 digests→note)에서 `OutputTruncated`가 나면 **한 번만** `num_predict = min(backend.output * 2, backend.context - estimated_input - RESERVE_TOKENS)`로 재시도한다. 이 값이 `backend.output`보다 크지 않으면 재시도하지 않는다. receipt의 해당 generation에 `retry_cause: "output_truncated"`, `num_predict_override`를 기록한다. 두 번째도 잘리면 실패다. 잘린 출력은 어떤 경우에도 게시하지 않는다.
- `GrobidExtractor.ready()`: `GET /api/version`(timeout 5초)이 200이면 `{"ready": True, "version": "0.9.1"}`, 아니면 `{"ready": False, "error": "..."}`. 예외를 던지지 않는다. `extract()`는 변경 없다. 2026-10-12에 이 endpoint가 `{"version":"0.9.1","revision":"0.9.1"}`를 반환함을 확인했다.
- `_stage(job_id, record, stage, lease=None)`에서 매 호출 `job = store.job(job_id)`를 읽어 `cancel_requested`가 있으면 `JobCancelled(RuntimeError)`(`error_code="cancelled"`)를 던진다. `_write`는 part마다 `_stage`를 부르므로 **part 경계마다 취소가 확인**된다. `_process`의 `except` 블록은 `JobCancelled`를 분리해 `finish(job_id, "cancelled", stage=..., error="Cancelled at a part boundary; checkpoints kept")`로 끝내고 `record["outcome"]="cancelled"`를 쓴다. 취소 뒤 어떤 산출물도 활성 노트로 가지 않는다(계약 2).

### 4.4 지속 worker (F01, F02, F03, F04, F15, F16, F19)

새 모듈 **`src/byeori/local/worker.py`**. `boto3`를 import하지 않는다(`tests/test_cloud_only.py` 계약).

```python
class Worker:
    POLL_SECONDS = 2.0
    HEARTBEAT_SECONDS = 15.0
    EXTRACTOR_WAIT_SECONDS = 30.0
    RECOVERY_WAIT_SECONDS = 30.0

    def __init__(self, service, *, log_dir=None, resume_interrupted=True,
                 once=False, max_jobs=None, clock=time.monotonic, sleep=time.sleep): ...

    def run(self) -> dict:
        """Hold .worker.lock for the whole life of this process (worker_lock, non-blocking:
        a second worker fails fast with error_code 'worker_busy'). Then:
          register_worker → sweep_running_worker_jobs(requeue=resume_interrupted) → loop."""
```

루프의 한 바퀴(의사코드; 각 분기가 `workers.state`를 갱신하고 상태가 바뀔 때만 로그 한 줄):

```text
if stop_requested:                       state=stopping → break
if backend.doctor()["recovery_pending"]: state=paused_recovery_pending; heartbeat; sleep RECOVERY_WAIT; continue
job = store.claim_next(worker_id)
if job is None:                          state=idle; if once: break; heartbeat; sleep POLL; continue
if job.kind == "note" and not extractor.ready()["ready"]:
    store.release_claim(job_id, worker_id, reason="extractor_unavailable")
    state=waiting_extractor; sleep EXTRACTOR_WAIT; continue
state=running; start heartbeat thread for job_id
try: dispatch(job)                       # 아래 표
finally: stop heartbeat thread
jobs_done += 1; if max_jobs and jobs_done >= max_jobs: break
```

| kind | 호출 | 결과 처리 |
| --- | --- | --- |
| `note` | `service._process(paper_id, job_id=job_id, lease=lease, resume=not request.get("no_resume"))` | `_process`가 스스로 `finish`/`publish`한다. `RuntimeError`는 로그만 |
| `question` | `service.ask(request.question, request.paper_id)` | `jobs.py:81-97` `_answer`의 로직을 `QuestionJobs.answer(job, lease)`로 옮겨 inline·worker가 공유한다 |
| `metadata` | `service._refresh(paper_id, job_id=job_id, lease=lease)` | 4.2의 receipt |
| `revalidate` | `service._revalidate(request.written_by, job_id=job_id, lease=lease)` | 같음 |

`_process`·`_refresh`·`_revalidate`는 `job_id=None`이면 지금처럼 `store.start()`로 running job을 만들고(inline), 주어지면 그 행을 쓴다. inline 경로는 `with worker_lock(...)`을 그대로 쥐므로 worker가 떠 있는 동안 `process`/`metadata`/`revalidate`는 `RuntimeError("A worker is running in this workspace; submit the job with --submit instead")`(`error_code="worker_running"`)로 즉시 실패한다 — F16의 대기·실패를 **안내가 있는 실패**로 바꾸는 것이고, 큐 경로는 `--submit`이다.

**`ModelTimeout` 처리.** `_process`가 `ModelTimeout`으로 실패하면 job은 `failed`(`error_code="outcome_unknown"`)로 끝나고, worker는 다음 바퀴에서 `recovery_pending`을 보고 `paused_recovery_pending`으로 들어간다. 사람이 `byeori-local recover-runtime --acknowledge-idle`을 실행하면 자동으로 재개한다. 그 job은 자동 재큐하지 않는다 — 서버가 아직 계산 중일 수 있고, 같은 요청의 즉시 재시도는 수정 명세서 7.3이 금지한다. 재시도는 사람이 `process --submit`으로 넣는다(체크포인트가 있으므로 비용은 작다).

**신호.** `SIGTERM`/`SIGINT` 첫 번째: `stop_requested=True`. 모델 호출 중이면 그 호출이 끝나기를 기다리고(`_stage`가 `stop_requested`도 확인해 `JobInterrupted`를 던진다 → job `interrupted` + `requeue` 1건 즉시 생성, 체크포인트 보존) 루프를 빠져나와 `stop_worker`를 기록한다. 두 번째 신호: `os._exit(130)`. 이때 running job은 다음 worker가 `sweep_running_worker_jobs`로 정리하고, 진행 중이던 모델 호출은 `inflight` 표식 때문에 `recovery_pending`이 된다(기존 설계).

**heartbeat thread.** 15초마다 `store.heartbeat(job_id, worker_id, worker_state="running")`. 모델 호출이 수십 분이어도 `jobs.heartbeat_at`이 전진하므로 `status`가 "살아 있음"을 보인다. thread는 daemon이며 job 종료 시 `Event`로 멈춘다.

**로그 (F15).** `<workspace>/logs/worker-<started_at UTC, 초까지>-<worker_id[:8]>.jsonl`에 한 줄 JSON `{"at","level","worker_id","job_id","event","detail"}`; 같은 내용을 stderr에 사람이 읽는 형식으로 쓴다. `detail`에는 paper_id, stage, error_code, 토큰 수, 체크포인트 ID만 쓴다. 논문·prompt·답변 본문은 **쓰지 않는다**(테스트 T15).

**설정.** `BYEORI_LOCAL_EXECUTOR` = `inline`(기본, 현재 동작) | `worker`. `build_service`가 `service.executor`로 노출한다. MCP 서버는 이 값을 시작 시 읽는다(런타임 변경 없음, 재시작 필요 — 업무 도우미 문서와 같은 규칙).

**`workers.state` 값**: `idle | running | waiting_extractor | paused_recovery_pending | stopping | stopped`.

### 4.5 체크포인트 — 재개 (F06)

새 모듈 **`src/byeori/local/checkpoint.py`**. 저장은 `store.checkpoints` 테이블과 기존 `runs/<job_id>/` 파일이다. **파일을 옮기거나 복사하지 않는다.** 재사용은 과거 job의 파일을 **참조**하는 것이다.

```python
EXTRACTION_SCHEMA = 1        # parse_tei / document.json 구조가 바뀌면 올린다

def key(stage, **inputs) -> str:
    """sha256 of json.dumps({"stage": stage, **inputs}, sort_keys=True, ensure_ascii=False)."""

class Checkpoints:
    def __init__(self, store): ...
    def lookup(self, paper_id, stage, key_sha256) -> dict | None:
        """Row whose every file still exists and hashes to the recorded sha256. On mismatch:
           event(job_id_of_checkpoint, 'checkpoint_corrupt', detail=path) and return None.
           Never deletes or rewrites the file."""
    def record(self, paper_id, stage, key_sha256, job_id, files: list[tuple[str, bytes]], meta: dict) -> str:
        """INSERT OR IGNORE (first writer wins); files = [(relative_path, content_bytes)] already
           written by write_new; stores [{"path", "sha256", "bytes"}]."""
    def for_paper(self, paper_id) -> list[dict]
```

**단계별 키와 산출물.** `fp = backend.fingerprint()`는 job 시작 시 한 번 구한다.

| stage | key 입력 | 재사용 시 읽는 파일 | 비고 |
| --- | --- | --- | --- |
| `extraction` | `pdf_sha256=paper_id, extractor="grobid", extractor_version=extractor.ready()["version"], extraction_schema=EXTRACTION_SCHEMA` | `grobid.tei.xml`, `document.json` | `blocks = document["blocks"]`를 **그대로** 쓴다(재파싱하지 않음). `record["extraction"]["path"]`가 과거 job의 경로를 가리키게 된다 |
| `digest` | `extraction_id, block_ids=[...part의 ID], model=fp.digest, template=fp.template_sha256, context, output, prompt_version=PROMPT_VERSION, system_sha256=sha(DIGEST_SYSTEM), suffix_sha256=sha(DIGEST_NOW), think=False` | `digest-NN.md` | 분할(halving)은 결정적이므로 같은 part는 같은 키다. 분할된 반쪽도 각자 키를 가진다 |
| `candidate` | `extraction_id, provided_ids(sorted), inputs_sha256=sha(모델에 준 user 본문), model=fp.digest, template, context, output, prompt_version, system_sha256=sha(NOTE_SYSTEM 또는 NOTE_FROM_DIGESTS_SYSTEM), num_predict_override` | `candidate.md` | 재사용 시 `validate_note`·`publish`는 정상 수행한다. 검증 규칙만 바뀐 경우를 다루는 `revalidate`와 겹치지만 충돌하지 않는다 |

`metadata` 조회(OpenAlex)는 체크포인트하지 않는다 — 외부 상태이고 비용이 작으며, 결과는 `metadata_checks`에 이미 기록된다.

**`_process` 변경 (`service.py:493-575`).** 시그니처 `_process(self, paper_id, *, job_id=None, lease=None, resume=True)`. 각 stage 진입 시:

```text
k = key(stage, ...)
hit = checkpoints.lookup(paper_id, stage, k) if resume else None
if hit: 파일을 읽어 그 stage의 결과로 쓰고
        record["checkpoints"]["reused"].append({"stage", "checkpoint_id", "job_id": hit.job_id, "files": [...]})
        store.event(job_id, "checkpoint_reused", detail=...)
else:   지금처럼 생성·write_new → checkpoints.record(...) → record["checkpoints"]["created"].append(...)
```

`record["resumed_from"]`에는 재사용한 체크포인트들의 `job_id` 중 가장 최근 것을 넣고, `jobs.resumed_from`은 4.2의 재큐에서 채운 값을 유지한다(둘은 뜻이 다르다: 전자는 "무엇을 읽었나", 후자는 "어느 job의 후속인가"). 재사용된 extraction의 `document.json` 경로는 `note_versions.extraction_path`에 그대로 들어가므로 `store.document()`·`context()`·`review_sheet`는 수정 없이 동작한다.

**`_revalidate` 수정.** `service.py:814-880`은 `runs/<written_by>/document.json`·`grobid.tei.xml`을 **접두어로** 찾는다. 재사용된 extraction은 다른 job 디렉터리에 있으므로 `receipt["extraction"]["path"]`와 그 옆의 `grobid.tei.xml`을 읽도록 바꾼다. receipt에 `extraction.path`가 없는 레거시 job은 지금처럼 접두어로 찾는다.

**무효화.** 키에 모델 digest·template·prompt version·추출 ID·예산이 모두 들어가므로 수정 명세서 16.3의 "원본/입력 hash, 모델 digest, prompt/schema 버전, 옵션이 모두 맞을 때만 재사용"이 자동으로 성립한다. 명시적으로 끄는 길: `process --no-resume`(request에 `no_resume: true`).

**CLI** `byeori-local checkpoints <paper_id>`: `for_paper` 결과를 `{stage, created_at, job_id, files, meta.block_ids(앞 2개·뒤 2개만)}`로 출력한다.

### 4.6 백업·복원·색인 재구축 (F09, F10, F14)

새 모듈 **`src/byeori/local/backup.py`**. 수정 명세서 18.2의 계약을 그대로 구현한다.

**manifest 형식 (`manifest.json`, format 1)**

```json
{
  "format": 1,
  "created_at": "2026-10-12T05:00:00+00:00",
  "source_root": "<워크스페이스 절대 경로>",
  "schema_version": 6,
  "code_version": {"package": "0.1.0b1", "git": "a9228f0 or null"},
  "journal_mode": "wal",
  "db": {"file": "catalog.sqlite3", "sha256": "...", "bytes": 393216, "integrity_check": "ok"},
  "files": [{"path": "papers/<sha>/original.pdf", "sha256": "...", "bytes": 1234567}, ...],
  "counts": {"papers": 11, "notes": 11, "note_versions": 27, "jobs": 51, "checkpoints": 0},
  "referenced_missing": [],
  "unreferenced": ["runs/<job>/digest-03.md", ...],
  "included_dirs": ["papers", "wiki", "runs", "quarantine", "logs"],
  "verified": true
}
```

**`create_backup(store, destination: Path, *, include_inbox=False) -> dict`**

1. `destination`은 존재하지 않거나 빈 디렉터리여야 한다. 아니면 `ValueError`(`error_code="destination_not_empty"`), 아무것도 쓰지 않는다.
2. `maintenance_lock(store.root, exclusive=True)`를 쥔다. 진행 중인 DB 연결이 닫히기를 기다리고 새 연결을 막는다. 모델 호출은 계속 돈다.
3. `src = sqlite3.connect(root/"catalog.sqlite3")`, `dst = sqlite3.connect(destination/"catalog.sqlite3")`, `src.backup(dst)`. `dst.execute("PRAGMA integrity_check")`가 `ok`가 아니면 중단(`error_code="backup_db_corrupt"`). `-wal`·`-shm` 파일은 복사하지 않는다.
4. `included_dirs`를 걸으며 각 파일을 `shutil.copyfile`(메타데이터 보존은 `copystat`)로 같은 상대 경로에 복사하되, **읽으면서 sha256을 계산**해 manifest 항목을 만든다. symlink는 따라가지 않고 `skipped_symlinks`에 기록한다.
5. DB에서 참조 집합을 만든다: `papers.pdf_path`, `note_versions.path`, `note_versions.extraction_path`, 그 옆 `grobid.tei.xml`, `checkpoints.files[*].path`. `referenced_missing = referenced − copied`(있으면 결과 `status: "incomplete"`, CLI exit 3이지만 백업은 끝까지 쓴다). `unreferenced = copied − referenced`(정보).
6. manifest를 `write_new`와 같은 방식(임시 파일 → fsync → 배타 링크)으로 쓴다.
7. 잠금을 풀고 **두 번째로** 모든 복사 파일을 다시 읽어 manifest의 sha256과 대조한다. 전부 일치하면 `verified: true`로 manifest를 다시 쓴다(이 파일만 예외적으로 교체 허용; 그 외 파일은 불변).
8. 결과 `{destination, files, bytes, counts, referenced_missing, unreferenced_count, verified, seconds}`를 돌려준다.

같은 SSD의 백업은 디스크 고장 대비가 아니다. CLI 출력에 `"same_volume_as_source": true/false`(`os.stat().st_dev` 비교)를 넣고 true면 `warning: "same volume; copy this backup to another device"`를 덧붙인다.

**`restore_backup(backup_dir: Path, destination: Path, *, allow_migration=True) -> dict`**

1. `destination`은 **존재하지 않아야** 한다(빈 디렉터리도 거부; `error_code="destination_exists"`). 원래 워크스페이스 경로를 넘기면 당연히 거부된다.
2. `manifest.json`을 읽고 `format == 1`을 확인한다. manifest의 모든 파일과 DB가 `backup_dir`에 **있고 sha256·bytes가 일치**하는지 먼저 전부 검사한다. 하나라도 어긋나면 `destination`을 만들지 않고 `error_code="restore_verification_failed"`, 어긋난 경로 목록을 반환한다.
3. `destination`을 만들고 파일과 DB를 복사한다(복사하면서 다시 hash → 일치 확인).
4. `LocalStore(destination, create=False)`로 연다. schema가 낮으면 migration(기록 `migration: {"from": 4, "to": 6}`), 높으면 기존 규칙대로 거부한다. `allow_migration=False`면 낮은 schema도 거부한다.
5. `status='running'`인 job을 모두 `interrupted`(`error_code="restored_while_running"`, error 문구에 백업 시각)로 바꾼다. `queued`는 그대로 둔다. worker 행은 모두 `state='stopped'`로 닫는다.
6. `store.reindex()`(아래).
7. `store.integrity_problems(deep=True)`가 비어야 한다.
8. 검색 smoke: 활성 노트마다 `docs.title`로 `store.search(title, 5)`를 호출해 그 노트의 `stem`이 결과에 있어야 한다. `title`은 FTS `sections.title` 컬럼에 색인되므로 반드시 맞아야 한다.
9. `destination/RESTORED.json`에 `{backup_dir, manifest.created_at, restored_at, migration, interrupted_jobs, checks: {integrity: [], search_smoke: "11/11"}}`를 쓴다.
10. 5~8 중 하나라도 실패하면 결과 `status: "restored_with_problems"`로 돌려주고 exit 1이다. 디렉터리는 지우지 않는다(사람이 본다).

**`LocalStore.reindex() -> dict`**

- `publish()`의 색인 부분(`store.py:480-500`)을 `_index_note(db, *, stem, title, markdown, relative, metadata, summary)`로 뽑아내고 `publish`와 `reindex`가 공유한다. `note_summary`·`parse_frontmatter`·`split_frontmatter`는 순수 함수이므로 `service.py:348-398`에서 `evidence.py`로 옮기고 `service.py`는 re-export한다(기존 import 경로 유지; R10의 중복 정의 검사 통과).
- `maintenance_lock(exclusive=True)` + 직접 연결 + `BEGIN IMMEDIATE`: `DELETE FROM sections`, `DELETE FROM section_map`, `DELETE FROM docs WHERE doc_type='note'`, 그리고 `notes JOIN note_versions JOIN papers`를 순회하며 파일을 읽고(`note_sha256` 대조, 불일치는 건너뛰고 problems에 기록) `_index_note`. 한 트랜잭션이다.
- 끝나면 `integrity_problems()`의 색인 항목이 비어야 한다. 반환 `{"reindexed": n, "skipped": [...], "problems": [...]}`.

**CLI**

```text
byeori-local backup <dest_dir> [--include-inbox]
byeori-local restore <backup_dir> <new_workspace_dir> [--no-migration]
byeori-local reindex
```

### 4.7 CLI·MCP 계약 변경 요약

**새 명령·옵션** (`cli.py`)

```text
전역: --timeout <초>                            BYEORI_OLLAMA_TIMEOUT, 기본 600
worker [--once] [--poll-seconds 2] [--max-jobs N] [--no-resume-interrupted] [--log-dir <dir>]
process <paper_id>|--all [--submit] [--no-resume]
ask "<질문>" [--paper <id>] [--submit]           --submit이면 job_id만 출력하고 종료
metadata <paper_id>|--all [--submit]
revalidate <job_id>|--all [--submit]
status [<job_id>] [--limit N] [--cursor C]       job 단건은 events(최근 20)와 worker 진단을 포함
checkpoints <paper_id>
backup <dest_dir> [--include-inbox]
restore <backup_dir> <new_workspace_dir> [--no-migration]
reindex
migrate --plan | --apply
```

`--submit`은 kind별로 `store.enqueue(...)`를 호출하고 `{"job_id", "status": "queued", "executor": "worker", "worker": store.worker_status()}`를 출력한다. worker가 없으면 `worker.alive=false`와 `"diagnostic": "worker_unavailable"`을 함께 출력하되 **exit 0**이다 — 제출 자체는 성공이고, 실행 여부는 `status`로 본다.

**exit code**: 기존 규칙 유지(0 정상, 1 실패/`failed`/`interrupted`, 2 인자 오류, 3 부분 실패). 추가: `worker`는 정상 종료 0, 잠금 충돌 1(`worker_busy`); `backup`은 `referenced_missing`이 있으면 3; `restore`는 검증 실패 1, 문제 있는 복원 1; `migrate --plan`은 항상 0.

**새 `error_code`**: `schema_migration_required`, `worker_busy`, `worker_running`, `stale_lease`, `output_truncated`, `abnormal_stop`, `cancelled`, `worker_interrupted`, `max_attempts_exhausted`, `extractor_unavailable`, `destination_not_empty`, `destination_exists`, `backup_db_corrupt`, `restore_verification_failed`, `restored_while_running`.

**MCP** (`mcp_server.py`)

- `worker_status() -> dict` 도구 추가.
- `get_job`은 `job | {"events": store.events(job_id, 20), "worker": store.worker_status()}`를 반환한다(기존 필드 유지).
- `ask_byeori`는 `service.executor`에 따라 inline(지금) 또는 enqueue. 반환 형식은 같고 `executor` 필드가 추가된다.
- 등록·생성 도구는 추가하지 않는다(현재 설계 유지: ingestion은 CLI).

### 4.8 무인 운영 절차 (LOCAL-DEVELOPMENT.md의 "무모니터 Mac 운영 절차" 항목)

구현이 아니라 문서다. Ollama는 이미 `~/Library/LaunchAgents/sh.brew.ollama.plist`로 관리된다. worker용 plist **예시**를 문서에 넣되 설치는 사람이 한다.

```xml
<!-- ~/Library/LaunchAgents/local.byeori.worker.plist (예시; REPO_PATH를 저장소 절대 경로로 바꾼다) -->
<plist version="1.0"><dict>
  <key>Label</key><string>local.byeori.worker</string>
  <key>ProgramArguments</key><array>
    <string>REPO_PATH/.venv/bin/byeori-local</string>
    <string>--timeout</string><string>1800</string><string>worker</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>BYEORI_LOCAL_DATA</key><string>REPO_PATH/.byeori-local</string>
    <key>BYEORI_LOCAL_MODEL</key><string>qwen3:8b</string>
    <key>BYEORI_LOCAL_EXECUTOR</key><string>worker</string>
  </dict>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>REPO_PATH/.byeori-local/logs/launchd.err</string>
</dict></plist>
```

문서에 적을 운영 규칙: GROBID(Colima)는 사람이 올린다 — worker는 `waiting_extractor`로 기다릴 뿐 컨테이너를 띄우지 않는다. `recovery_pending`은 사람이 `recover-runtime`으로 푼다. 매일 한 번 `backup`을 외장 디스크 경로로 실행하고, 그 디스크가 없으면 **디스크 고장 복구 보장 불가**라고 `doctor`가 표시한다(백업 디렉터리 경로를 `BYEORI_LOCAL_BACKUP_HINT`로 주면 존재 여부만 확인; 선택).

---

## 5. 테스트 명세

세 파일을 새로 만든다. 모든 테스트는 임시 디렉터리와 `tests/local_helpers.py`·`test_local_integrity.py`의 `Model`/`PartsModel`/`Extractor` fixture를 쓴다. 실제 Ollama·GROBID·사용자 데이터에 접근하지 않는다. 기존 170개는 그대로 통과해야 하며, 계약이 바뀐 곳(`claim_question`의 executor 필터, `"did not finish"` 문자열 분기)은 기존 테스트의 기대값을 정정한다.

### `tests/test_local_worker.py`

| 번호 | 테스트 | 설정 | 단언 |
| --- | --- | --- | --- |
| T01 | `test_queued_note_job_is_claimed_and_published_by_worker_once` | `enqueue("note", pid)`; `Worker(service, once=True).run()` | job `succeeded`, `worker_id` 설정, 활성 노트 존재, events에 `claimed`·`finished` |
| T02 | `test_second_worker_fails_fast_while_first_holds_lock` | 스레드가 `worker_lock` 보유 | 두 번째 `run()`이 `RuntimeError`(`error_code=worker_busy`) |
| T03 | `test_inline_process_refuses_while_worker_runs` | 같은 설정 | `service.process(pid)`의 메시지에 `--submit` 포함, `error_code=worker_running` |
| T04 | `test_worker_question_is_not_orphaned_when_submitter_pid_is_dead` | `executor='worker'`, `request.pid`=죽은 PID | `sweep_orphaned_questions()` 뒤에도 `queued`; worker가 답한다 |
| T05 | `test_inline_question_orphan_rule_unchanged` | 기존 `test_a_question_left_by_a_dead_process_is_not_left_queued` 그대로 | 통과 유지 |
| T06 | `test_question_is_claimed_before_an_older_note_job` | note(priority 0) 먼저, question(priority 10) 나중 enqueue; `max_jobs=1` | 질문 job만 `succeeded` |
| T07 | `test_cancel_between_parts_stops_before_the_next_model_call` | `PartsModel`; 1번째 part 생성 직후 `request_cancel` (model.generate 안의 콜백) | job `cancelled`, `cancel_ack_at` 설정, 모델 호출 수 = 1, part 1 체크포인트 존재, 활성 노트 없음 |
| T08 | `test_worker_start_requeues_a_job_left_running_with_resumed_from` | 행을 `running, worker_id='dead', executor='worker'`로 둠 | 옛 행 `interrupted`, 새 행 `queued, attempt=2, resumed_from=옛 job_id`; `once` 실행 후 새 행 `succeeded` |
| T09 | `test_requeue_stops_at_max_attempts` | `attempt=3, max_attempts=3` | 새 행 없음, `error_code=max_attempts_exhausted` |
| T10 | `test_timeout_pauses_worker_until_recovery_is_acknowledged` | backend가 `ModelTimeout`을 던지며 `blocked` 파일 생성; 두 번째 job 대기 | 첫 job `failed/outcome_unknown`; worker state `paused_recovery_pending`; 두 번째 job `queued` 유지; `recover_runtime(acknowledge=True)` 뒤 다음 바퀴에서 두 번째 job 실행 |
| T11 | `test_worker_waits_for_extractor_and_still_answers_questions` | `extractor.ready()` → False | note job `queued`(released), state `waiting_extractor`, question job은 `succeeded` |
| T12 | `test_graceful_stop_interrupts_after_the_current_part_and_requeues` | part 1 중 `stop_requested` | job `interrupted`, 후속 `queued` 행 1개, 체크포인트 보존 |
| T13 | `test_heartbeat_advances_job_and_worker_rows` | 가짜 clock/sleep | `heartbeat_at` 두 번 이상 전진 |
| T14 | `test_a_stale_lease_cannot_publish` | `publish(..., lease=다른 worker_id)` | `StaleLease`; 활성 노트 불변; job 상태 불변 |
| T15 | `test_worker_log_never_contains_paper_text` | TEI에 고유 문장 삽입 | 로그 파일 전체에 그 문장 없음; `event` 필드만 존재 |
| T16 | `test_mcp_ask_enqueues_for_worker_when_configured` | `BYEORI_LOCAL_EXECUTOR=worker` | `ask_byeori` 반환 `executor=worker`, thread 미생성, `get_job`에 `worker` 진단 |

### `tests/test_local_checkpoint.py`

| 번호 | 테스트 | 설정 | 단언 |
| --- | --- | --- | --- |
| T17 | `test_resume_after_a_crash_in_the_fourth_part_reuses_three_digests` | `PartsModel`이 4번째 호출에서 예외 → job failed; 두 번째 `process` | 모델 호출 수 = (남은 part + 노트 1); receipt `checkpoints.reused`에 extraction + digest 3개; 노트 게시 |
| T18 | `test_checkpoint_is_not_reused_when_the_model_digest_changes` | `fingerprint().digest` 변경 | 모든 part 재생성, `reused`에 extraction만 |
| T19 | `test_checkpoint_is_not_reused_when_the_prompt_version_changes` | `monkeypatch PROMPT_VERSION` | 같음 |
| T20 | `test_checkpoint_is_not_reused_when_the_extraction_changes` | 다른 TEI | extraction 포함 전부 재생성 |
| T21 | `test_a_corrupt_checkpoint_file_is_ignored_and_recorded_not_deleted` | `digest-01.md` 내용 변조 | 미스로 처리, 해당 part 재생성, `checkpoint_corrupt` event, 변조 파일 그대로 존재 |
| T22 | `test_no_resume_ignores_every_checkpoint` | `resume=False` | `reused` 비어 있음 |
| T23 | `test_output_truncation_is_its_own_error_and_halves_the_part` | `done_reason="length"` 응답 | `OutputTruncated`; part 분할(기존 `test_a_part_whose_digest_is_cut_off_is_halved_and_retried` 정정) |
| T24 | `test_a_truncated_final_note_is_retried_once_with_a_larger_output_within_context` | 첫 노트 패스 `length`, 두 번째 `stop` | 호출 2회, 두 번째 `num_predict` > `output`, `≤ context − input − 512`; receipt `retry_cause`; 세 번째 호출 없음 |
| T25 | `test_a_twice_truncated_note_is_not_published` | 둘 다 `length` | job failed `output_truncated`, 활성 노트 없음 |
| T26 | `test_a_reused_extraction_keeps_the_note_pointing_at_the_existing_document_json` | T17 뒤 | `note_versions.extraction_path`가 첫 job 경로; `store.document()`·`context()` 정상 |
| T27 | `test_revalidate_reads_the_extraction_path_from_the_receipt` | 재사용 extraction으로 실패한 candidate | `revalidate` 성공 |
| T28 | `test_checkpoints_listing_names_stage_job_and_files` | — | CLI `checkpoints <pid>` 출력 형식 |

### `tests/test_local_backup.py`

| 번호 | 테스트 | 설정 | 단언 |
| --- | --- | --- | --- |
| T29 | `test_backup_writes_a_manifest_and_verifies_every_file` | 활성 노트, 과거 revision, 실패 job, alias, metadata_check, quarantine 파일 | manifest `verified=true`, counts 일치, `referenced_missing=[]`, 모든 참조 파일 포함, `-wal` 파일 없음 |
| T30 | `test_backup_refuses_a_non_empty_destination` | 파일 하나 있는 dest | `destination_not_empty`, dest 불변 |
| T31 | `test_backup_taken_during_publishing_is_transactionally_consistent` | 스레드가 publish 반복; 동시에 backup | 복원 DB `integrity_check=ok`; `notes` 수 == 그 시점 `note_versions`의 활성 수; 반쪽 트랜잭션 없음 |
| T32 | `test_restore_into_a_new_directory_reproduces_every_citation` | T29 백업 → restore | `read(pid, revision)`·`context(pid,"P0001",revision)`이 원본과 같음; `search(title)`에 stem; `RESTORED.json` 존재 |
| T33 | `test_restore_refuses_an_existing_destination_and_a_tampered_backup` | 빈 dest 존재 / 백업 파일 1바이트 변경 | 각각 `destination_exists`, `restore_verification_failed`; 후자는 dest 미생성 |
| T34 | `test_restore_marks_running_jobs_interrupted_and_keeps_queued` | 백업 시점 running 1, queued 1 | interrupted 1(`restored_while_running`), queued 1 |
| T35 | `test_restore_migrates_an_older_backup_and_refuses_a_newer_one` | schema 5 DB 백업 / `schema_version=99` | 전자 `migration {5→6}`; 후자 거부 |
| T36 | `test_reindex_rebuilds_search_after_index_rows_are_lost` | `DELETE FROM sections` | `integrity_problems()`에 색인 문제 → `reindex()` 뒤 비어 있음; 검색 정상 |
| T37 | `test_migration_applies_create_table_statements_idempotently` | schema 5 fixture DB | 6으로 올라가고 `workers`·`checkpoints`·`job_events` 존재; 두 번 열어도 동일 |
| T38 | `test_auto_migrate_off_refuses_and_plan_reports_without_writing` | `BYEORI_LOCAL_AUTO_MIGRATE=off` | `schema_migration_required`; `migrate --plan` 출력 `{current:5,target:6}`; DB 파일 mtime 불변; `--apply` 뒤 6 |
| T39 | `test_wal_is_enabled_and_shared_lock_does_not_block_readers` | 두 연결 | `journal_mode=wal`; reader가 writer 트랜잭션 중에도 읽음 |
| T40 | `test_metadata_and_revalidate_jobs_leave_receipts` | `_refresh`·`_revalidate` 성공/실패 | `runs/<job>/receipt.json` 존재, `outcome` 일치; `reconcile_receipts`가 건너뛰지 않음 |
| T41 | `test_cli_exit_codes_for_worker_backup_restore_and_migrate` | `main([...])` 호출 | 4.7의 코드 표와 일치 |
| T42 | `test_duplicate_top_level_definitions_remain_absent` | 기존 R10 검사 | `evidence.py`로 옮긴 함수가 `service.py`에 **정의**로 남지 않음(re-export만) |

---

## 6. 실서비스 검증 절차 — 실제 워크스페이스에서 사람이 수행

구현과 5절 테스트가 끝난 뒤, 아래를 **순서대로** 한다. 각 단계의 출력(JSON)을 `docs/reviews/phase-b-verification-2026-MM-DD.md`에 붙인다. 모델 재생성은 7단계 한 편만 한다.

```sh
cd "$REPO"    # 저장소 루트의 절대 경로
export BYEORI_LOCAL_DATA="$PWD/.byeori-local" BYEORI_LOCAL_MODEL=qwen3:8b

# 1. MCP 서버·worker가 떠 있지 않은지 확인하고 4.0(b)의 수동 복사본이 있는지 확인
ls -d .byeori-local.pre-schema6-*

# 2. 계획 조회(쓰지 않음) → 4→6
.venv/bin/byeori-local migrate --plan

# 3. 적용 → doctor로 schema 6, journal_mode wal 확인
.venv/bin/byeori-local migrate --apply
.venv/bin/byeori-local doctor
.venv/bin/byeori-local check --deep          # 기대: problems []

# 4. 첫 정식 백업(같은 볼륨 경고가 나와야 함) → 외장 디스크가 있으면 거기로 한 번 더
.venv/bin/byeori-local backup "$HOME/byeori-backups/$(date +%Y%m%d)-schema6"

# 5. 새 디렉터리로 복원 → 11/11 검색 smoke, integrity [] 확인 → 복원본은 검증 후 지워도 됨
.venv/bin/byeori-local restore "$HOME/byeori-backups/<위 디렉터리>" /tmp/byeori-restore-test
BYEORI_LOCAL_DATA=/tmp/byeori-restore-test .venv/bin/byeori-local check --deep
BYEORI_LOCAL_DATA=/tmp/byeori-restore-test .venv/bin/byeori-local search "foundation model"

# 6. 색인 재구축이 현재 색인과 같은 결과를 내는지
.venv/bin/byeori-local reindex && .venv/bin/byeori-local check

# 7. 재개 실측: 1.1의 출력 한도 실패 논문 중 chunked 경로가 필요한 것 하나를 고른다
.venv/bin/byeori-local status --limit 50 | grep -B2 -A2 "did not finish"     # paper_id 확보
.venv/bin/byeori-local --timeout 1800 process <paper_id> --submit
.venv/bin/byeori-local --timeout 1800 worker --once &                        # 터미널 1
.venv/bin/byeori-local status <job_id>                                       # 터미널 2: stage가 'generate part 2/N'이 되면
kill -TERM %1                                                                # 첫 신호: part 2가 끝나면 interrupted + 재큐
.venv/bin/byeori-local checkpoints <paper_id>                                # extraction + digest 2개 기대
.venv/bin/byeori-local --timeout 1800 worker --once                          # 재개: receipt.checkpoints.reused 확인
.venv/bin/byeori-local status <new_job_id>
```

기록할 측정값: 7단계의 첫 실행 part별 소요, 재개 뒤 재사용된 체크포인트 수와 절약된 시간, 전체 노트 생성 시간, `ollama ps`의 상주 메모리, 활동 모니터의 memory pressure. **세 편 이하의 측정을 성능 보장으로 쓰지 않는다**(수정 명세서 19.2).

7단계에서 `recovery_pending`이 발생하면 그것도 결과다 — timeout 1800이 부족한 part의 크기와 소요를 기록하고, `recover-runtime --acknowledge-idle` 뒤 재큐로 재개되는지 확인한다.

---

## 7. 문서 갱신 목록

구현 뒤 다음을 갱신한다. 수정 명세서 21절의 요구와 겹치는 항목은 그쪽 문구를 따른다.

- `docs/LOCAL-DEVELOPMENT.md`: 기능별 상태 표에서 `중간 단계부터의 작업 재개`·`색인 재구축·백업·복원`·`무모니터 Mac 운영 절차`를 실제 검증 수준(`mock 검증` 또는 `실서비스 검증`)으로 바꾼다. 환경 변수 표에 `BYEORI_OLLAMA_TIMEOUT`, `BYEORI_LOCAL_EXECUTOR`, `BYEORI_LOCAL_AUTO_MIGRATE`를 추가한다. 명령 목록에 4.7을 추가한다. "질문은 워크스페이스당 하나씩 순서대로" 문단에 worker 모드의 우선순위 규칙(질문이 노트보다 먼저 claim되지만 **진행 중인 노트 job을 중단하지는 않는다**)을 적는다. 4.8의 운영 절차를 넣는다.
- `docs/LOCAL-LLM-REMEDIATION-SPEC-2026-10-01.md`: 22절 아래에 "23. 단계 B 구현 결과"를 추가하고 21절 체크리스트의 해당 항목(`강제 중단 후 checkpoint 재개와 새 디렉터리 백업 복원`)을 체크한다. 이 문서(단계 B 제안서)로 링크한다.
- `README.md`: 로컬 설치 첫 안내에 `worker`·`backup` 한 줄씩.
- `CHANGELOG.md`: 단계 A와 단계 B를 각각 항목으로.
- `docs/evaluation/` 11개 파일: 4.0(c).
- `.gitignore`: `.byeori-local.pre-schema6-*/`, `logs/`는 워크스페이스 안이라 이미 제외됨 — 확인만.

---

## 8. 구현 순서와 완료 조건

각 묶음은 그 자체로 테스트가 통과하고 커밋할 수 있는 단위다. 앞 묶음이 끝나기 전에 뒤 묶음을 시작하지 않는다.

| 순서 | 묶음 | 포함 | 완료 조건 |
| --- | --- | --- | --- |
| 0 | 선행 | 4.0 (a)(b)(c) | 커밋 2개가 `origin/main`에 있음; `.byeori-local.pre-schema6-*` 존재; 평가 파일 11개 정정 |
| 1 | 저장 기반 | 4.1 schema 6·migration 일반화·`migrate`·WAL·maintenance lock, 4.2의 테이블 API(`enqueue`/`claim_next`/`heartbeat`/`events`/fencing/receipt), 4.6의 `reindex`와 `_index_note` 분리 | T36~T42 통과; 기존 170개 통과; **동작 변화 없음**(executor 기본 inline) |
| 2 | 백업·복원 | 4.6 `backup`/`restore` | T29~T35 통과; **6절 1~6단계를 실제 워크스페이스에서 수행**해 결과 기록. 이 시점부터 실데이터에 검증된 복원점이 생긴다 |
| 3 | 작은 수정 | 4.3 `OutputTruncated`/`AbnormalStop`, `--timeout`, `ready()`, part 경계 취소 | T07, T23~T25 통과; 기존 분할 테스트 정정 |
| 4 | 재개 | 4.5 `checkpoint.py`, `_process`·`_revalidate` 변경, `checkpoints` CLI | T17~T22, T26~T28 통과 |
| 5 | worker | 4.4 `worker.py`, `--submit`, MCP executor, 로그, 신호 | T01~T06, T08~T16 통과; 6절 7단계 실측 기록 |
| 6 | 문서·운영 | 4.8, 7절 | 문서 갱신; 수정 명세서 21절 체크 |

단계 B 전체의 완료 판단(수정 명세서 20절의 "다음 단계로 넘어가는 조건"):

- [ ] 실제 강제 중단(SIGTERM) 뒤 재시작에서 앞선 part를 다시 호출하지 않고 노트가 게시됨 — 6절 7단계 기록.
- [ ] 실제 워크스페이스를 새 디렉터리에 복원해 `check --deep` 빈 결과, 검색 smoke 11/11 — 6절 5단계 기록.
- [ ] schema 4→6 migration이 실데이터에서 11편·27 revision·51 job을 보존 — 6절 3단계 `check --deep`.
- [ ] 두 묶음이 분리 커밋되고 push됨.
- [ ] 기본 8B 자원 프로필(context 32768, output 4096, timeout 1800)에서 긴 논문 1편의 worker 실행이 OOM·swap 급증 없이 끝남 — 6절 측정값.

이 다섯 개가 되면 수정 명세서 20절의 **단계 C(구조화 claim·원문 재독·v2 평가)**로 넘어간다. 단계 C는 이 문서의 범위가 아니며, 그때 기존 11편의 47개 결함을 사람이 판정하는 작업(19.1의 3)을 함께 시작한다.

---

## 9. 이 문서가 정한 결정과 대안

구현자가 바꾸지 말아야 할 결정이다. 바꾸려면 사용자와 상의한다.

| 결정 | 선택 | 버린 대안과 이유 |
| --- | --- | --- |
| 재시도 단위 | **새 job 행**(`resumed_from` 체인) | 같은 행의 `attempt` 증가는 `runs/<job_id>/`에 `write_new`로 쓴 불변 파일과 충돌하고, `reconcile_receipts`·`revalidate`·`integrity_problems`가 "job 하나 = run 디렉터리 하나 = receipt 하나"에 의존한다 |
| 체크포인트 저장 | **참조**(과거 job 디렉터리의 파일을 그대로 가리킴) | 복사는 저장 공간을 두 배로 쓰고 "불변 파일은 옮기지 않는다"는 계약을 흐린다 |
| 질문 우선 | claim 시점 우선순위만(`priority 10 > 0`). **진행 중인 노트 job은 중단하지 않음** | part 경계에서 양보하면 노트 job의 모델 상주·KV 상태가 바뀌고 체크포인트 키가 복잡해진다. 긴급하면 노트를 `cancel`하고 질문 뒤 `--submit`으로 재개(체크포인트가 비용을 흡수) |
| 중단 job 자동 재큐 | 기본 **on**, `max_attempts=3` | off면 무인 운영의 의미가 없다. 한도가 없으면 같은 실패를 무한 반복한다 |
| `outcome_unknown` 뒤 재큐 | **하지 않음**(사람이 다시 제출) | 서버가 계산 중일 수 있다. 수정 명세서 7.3 |
| executor 기본값 | **inline**(현재 동작 유지) | worker를 기본으로 하면 worker 없는 사용자의 `ask`가 영원히 `queued`다 |
| 백업 중 쓰기 | 공유/배타 flock로 DB 접근만 잠깐 멈춤 | worker 전체 정지는 수십 분짜리 모델 호출을 기다려야 한다; DB 파일 raw 복사는 WAL과 함께 비일관 |
| 색인 | FTS 재구축을 활성 노트 기준으로만 | 과거 revision까지 색인하면 검색이 물러난 노트를 답한다(R01~R02에서 바로잡은 동작) |
| 업무 도우미 | 이번 범위 밖 | worker 통합은 두 런타임의 job 모델을 맞춘 뒤 별도로 |

---

## 10. 구현 결과 — 2026-10-12

4~8절을 구현했다. 코드는 `src/byeori/local/{store,service,llm,locking,jobs,cli,mcp_server}.py`와 신규 `worker.py`·`checkpoint.py`·`backup.py`에 있다. 테스트는 신규 `tests/test_local_{worker,checkpoint,backup}.py`에 있다. 로컬 테스트는 170개에서 220개로, 전체는 2,509개 통과(1 skip)다. 2026-10-01 재현 스크립트는 모든 항목에서 수정된 동작을 보인다.

### 10.1 실제 워크스페이스에서 확인한 것 (6절 1~6단계)

| 단계 | 결과 |
| --- | --- |
| 수동 복사본 | `.byeori-local.pre-schema6-20261012` (schema 4, 원본과 `diff -r` 동일) |
| `backup` (schema 4 그대로) | 파일 204개·107 MB, 검증 통과, 참조 누락 0. 백업은 워크스페이스를 열지 않으므로 schema가 바뀌지 않음 |
| `migrate --plan` → `--apply` | 4→6, 논문 11·노트 11·revision 27·job 51 보존, `journal_mode` delete→wal |
| `doctor`, `check --deep` | 모델 local, recovery_pending 없음, GROBID 0.9.1 ready, 문제 0 (원본 PDF·TEI 모두 재해시) |
| `backup` (schema 6) → `restore` (새 디렉터리) | 0.14초·0.21초. 복원본 deep check 문제 0, 제목 검색 11/11 |
| `reindex` | 복원본에서 다시 만든 색인이 실제 색인과 docs 11행·sections 88행 모두 동일. 실제 워크스페이스에서 실행해도 문제 0 |

### 10.2 실제 모델로 확인한 중단과 재개 (6절 7단계)

복원본에서 진행했다. 실제 워크스페이스의 활성 노트는 바꾸지 않았다. 대상은 Vaswani(15쪽, 85블록)와 chen-2026(56블록)이다. `qwen3:8b`, context 16384, timeout 1800을 썼고, 이 설정에서 두 논문 모두 3개 part로 나뉜다. 시각은 job 이벤트 기록이다.

| 시각(UTC) | 사건 |
| --- | --- |
| 12:32:23 | **시험 1 (Vaswani)**: worker가 job `2fd256dc`를 claim. 추출과 메타데이터에 12초 |
| 12:32:35–12:35:34 | part 1 생성, 179초. 이 중 약 99초는 Mac이 잠든 시간 |
| 12:35:55 | part 2 생성 중 SIGTERM |
| 12:36:31 | part 2 완료(57초) 후 part 3 앞에서 멈춤. `interrupted`, 새 job `f0165dff`(attempt 2)로 재큐 |
| 12:38:31 | 새 worker가 claim. 추출과 digest 2개를 checkpoint에서 읽고 7초 만에 part 3에 도달 |
| 12:38:38–12:39:16 | part 3만 생성, 38초 |
| 12:39:16–12:41:26 | 노트 생성 129초 → **구조 검증에서 거부**. 노트가 `[P0051-P0053]`을 인용했고, 범위를 펼치면 나오는 `P0052`는 어느 digest에도 남지 않은 문단이다. R04에서 넣은 "제공한 근거만 인용" 검사가 의도대로 막은 것이며, 재개와는 무관하다(재개하지 않아도 같은 digest가 나온다) |
| 12:42:39 | **시험 2 (chen-2026, 56블록)**: job `eacb10ae` claim |
| 12:42:42–12:43:39 | part 1 생성, 57초. part 2가 시작되는 순간 SIGTERM(자동) |
| 12:45:22 | part 2 완료(103초) 후 멈춤. `d92763dc`(attempt 2)로 재큐 |
| 12:45:32 | 새 worker가 추출과 digest 2개를 읽고 1초 만에 part 3에 도달 |
| 12:45:33–12:46:17 | part 3만 생성, 44초 |
| 12:46:17–13:14:53 | 노트 생성. 모델이 실제로 계산한 시간은 118.6초, 벽시계로는 28.6분. Mac이 21:46:32 KST부터 944초, 22:03:01부터 약 11분 잠들었다(`caffeinate -i`만 쥔 상태) |
| 13:14:53 | 검증·게시 성공. 활성 노트는 중단된 job의 `document.json`을 가리키고, 블록 56/56 제시, `check --deep` 문제 0 |

두 시험 모두 재개는 명세대로 동작했다. SIGTERM은 진행 중인 호출을 끝낸 뒤 다음 part 앞에서 멈췄고, 새 job은 이전 job의 추출과 digest 2개를 다시 읽어 모델 호출을 part 1개와 노트 1개로 줄였다. 다시 묻지 않은 part 두 개는 시험 1에서 236초, 시험 2에서 160초였다. 시험 2는 게시까지 마쳐 8절의 완료 조건("실제 강제 중단 뒤 재시작에서 앞선 part를 다시 호출하지 않고 노트가 게시됨")을 충족했다. 시험 1의 게시 거부는 분할 노트가 digest에 없는 문단을 인용하는 기존 품질 문제이며 단계 C(구조화 claim)의 과제다.

**실행 중 발견한 결함 — 수정함.** 이 Mac은 `pmset` 설정이 `sleep 1`(유휴 1분 뒤 잠자기)이고 Power Nap이 켜져 있다. 사람이 없는 동안 시스템은 잠들어 있다가 짧은 DarkWake 구간에서만 계산했다. 시험 1의 part 1 도중 99초(21:33:50 KST, "Maintenance Sleep")를 잃었고, macOS의 monotonic clock은 잠든 시간을 세지 않아 job 시간이 248초가 아니라 151.5초로 기록됐다. 그래서 worker가 job 동안 `caffeinate -i`를 쥐게 했다. 그러나 시험 2에서는 그 상태로도 노트 생성 중에 944초를 잠들었다. `PreventUserIdleSystemSleep`(-i)은 이미 잠든 뒤 DarkWake로 깨어난 Mac이 다시 잠드는 것을 막지 못하기 때문이다. worker는 이제 job을 실행하는 동안 `caffeinate -i -s -w <worker pid>`를 쥔다. `-s`(`PreventSystemSleep`, AC 전원에서 유효)는 Power Nap 중 Time Machine이 쓰는 것과 같은 assertion이다. job이 없을 때는 잠들 수 있고, `--allow-sleep`으로 끌 수 있다. 로그 시간은 벽시계로 기록한다. 이 수정은 직접 확인했다. 22:30:30 KST DarkWake 직후 `caffeinate -i -s`를 5분간 쥐었더니 그동안 잠들지 않았다(이전에는 DarkWake 후 45~60초 안에 다시 잠들었다). assertion이 끝난 지 11초 뒤인 22:36:00에는 925초간 잠들었다(`pmset -g log`). 다만 긴 job 전체를 이 설정으로 돌려 본 것은 아니다.

**메모리.** 모델 적재 전 시스템 여유 메모리는 87%, swap 사용은 2,027 MB였다. 최종 노트 생성 중에는 여유 43%, swap 1,363 MB였다. `ollama ps` 기준 상주 크기는 6.6 GB(100% GPU, context 16384)다. 한 편의 관측값이며 프로필 검증으로 쓰지 않는다.

### 10.3 명세에서 바꾼 점과 이유

| 명세 | 구현 | 이유 |
| --- | --- | --- |
| 4.1 유지보수 공유/배타 flock (9절 "백업 중 쓰기") | **잠금 없이 순서로 해결**: catalog를 backup API로 먼저 복사하고 파일은 그 뒤에 복사 | 파일은 항상 그 파일을 가리키는 트랜잭션보다 먼저 쓰이고 이후 바뀌지 않는다. 따라서 snapshot이 가리키는 파일은 반드시 존재한다. 9절 결정의 목적(worker를 멈추지 않음, DB 파일 raw 복사 금지)은 그대로 지킨다. 같은 스레드에서 공유/배타 flock이 중첩되면 교착될 위험이 있어 이를 없앴다. 쓰기 중 백업을 복원하는 테스트(T31)로 확인했다 |
| 4.5 `candidate` checkpoint | **두지 않음** | 최종 노트가 생성된 뒤에는 정지 요청이 와도 검증·게시를 마친다(`interruptible=False`). 그래서 생성된 candidate가 버려지는 경로가 없다. 검증에 실패한 candidate는 `revalidate`가 맡는다. 같은 입력으로 다시 생성을 요청하는 것은 재처리의 목적과 맞지 않는다 |
| 4.5 checkpoint 사용 조건 | **추가 규칙**: 그 논문의 노트가 checkpoint보다 나중에 게시됐으면 쓰지 않음 | GROBID TEI에는 처리 시각(`when=`)이 들어가, 같은 PDF도 추출할 때마다 추출 ID가 달라진다(실제 워크스페이스: Vaswani 추출 14개의 해시가 모두 다름. 두 논문은 시각을 빼도 본문이 달랐음). 따라서 digest 재사용은 추출 재사용을 전제로 한다. 게시된 논문까지 재사용하면 "다시 처리 = 새로 추출"이라는 기존 의미가 바뀐다. 재개는 끝나지 않은 작업에만 적용한다 |
| 4.5 표 (명세에 없음) | **`digest-truncated` 표식 추가** | 실패 18건 중 7건이 출력 한도였다. 같은 part는 다시 물어도 같은 방식으로 잘리므로, 재개할 때 묻지 않고 바로 나눈다 |
| 4.1 `checkpoints` UNIQUE(paper, stage, key) | **여러 행 허용**, 최신 유효 행 사용 | 파일이 손상된 checkpoint를 지우지 않고 새로 기록할 수 있게 한다 |
| 4.5 키의 `server_version` | **키에서 제외**, 메타에 기록 | Ollama를 업그레이드할 때마다 모든 checkpoint가 무효가 되는 것을 피한다. 모델 digest와 template은 키에 남긴다 |
| 4.2 `release_claim` | **두지 않음**: 추출기가 응답하지 않으면 논문 job을 claim하지 않고 질문·메타데이터만 claim | claim과 release가 반복되며 이벤트가 30초마다 쌓이는 것을 막는다 |
| 4.3 `ExtractorUnavailable` | 연결 거부·연결 timeout에만 적용 | 읽기 timeout은 PDF 때문일 수 있으므로 일반 추출 실패로 남긴다 |
| (명세에 없음) | inline `metadata`·`revalidate` job의 `kind`가 `note`에서 `metadata`·`revalidate`로 바뀜 | worker가 kind로 실행 경로를 고르기 때문이다. 과거 행은 그대로 둔다 |
| (명세에 없음) | worker의 잠자기 방지, 벽시계 기록 | 10.2의 실측 결함 |

### 10.4 남은 일

- launchd 설치와 장기(며칠) 무인 운영은 검증하지 않았다(4.8은 문서 예시만 있음). `caffeinate -s`로 긴 job 전체를 끝까지 돌려 보지도 않았다.
- 이 Mac은 `sleep 1`이다. 무인 운영에서는 job 단위 assertion 대신 시스템 설정(`sudo pmset -c sleep 0`)을 바꾸는 방법도 있다. 이는 사용자가 정할 일이라 바꾸지 않았다.
- 백업 예약, 외장 디스크 복제와 `BYEORI_LOCAL_BACKUP_HINT`는 구현하지 않았다.
- 같은 사용자가 여러 워크스페이스를 둘 때 worker는 워크스페이스마다 하나다. endpoint 잠금이 모델 호출은 직렬화하지만 공정성 정책은 없다.
- 업무 도우미(`byeori-assistant`)의 job은 이 worker와 통합하지 않았다.
- 단계 C(구조화 claim, 원문 재독, v2 평가)와 47개 결함의 사람 판정.
