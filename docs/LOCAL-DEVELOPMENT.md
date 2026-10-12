# Local LLM 개발 버전

기존 `byeori` AWS 명령과 별도로 `byeori-local` / `byeori-local-mcp`를 추가했습니다.
이 버전은 단일 논문 처리 흐름을 검증하는 개발용 런타임입니다. AWS 배포·자격증명이 필요하지 않으며 기존 S3 데이터를 자동으로 내려받거나 변경하지 않습니다.

2026-10-01에 [검토 문서](LOCAL-LLM-REVIEW-2026-10-01.md)의 R01~R11에 대한 1차 안정화를 구현했습니다. [수정 명세서](LOCAL-LLM-REMEDIATION-SPEC-2026-10-01.md)의 마지막 절에 구현 범위와 남은 항목을 기록합니다. schema는 5이며 기존 4의 노트·원본을 보존하는 컬럼/테이블 추가 방식으로 갱신합니다. 실제 사용자 워크스페이스를 이 작업에서 갱신하지는 않았습니다.

작업 메모 정리·로컬 커밋 요약·파일 분류 제안·보고서 초안은 별도
[`byeori-assistant` 워크스페이스](LOCAL-ASSISTANT.md)에서 실행할 수 있습니다.

## 기능별 상태

`구현`은 코드가 존재한다는 뜻이고, `mock 검증`은 고정 응답·transport mock 테스트까지, `실서비스 검증`은 실제 GROBID·실제 Ollama 모델로 확인했다는 뜻입니다. 논문 이해 품질은 11편의 보조 판정으로 평가 중이며 사람 검증을 마친 정확도가 아닙니다. 이번 안정화의 실제 서비스 확인은 Ollama 모델·버전 조회까지이며 논문 재생성은 수행하지 않았습니다.

| 기능 | 상태 |
|---|---|
| PDF 등록·SHA-256 중복 확인·원본 보존 | 실서비스 검증 |
| 중단된 등록의 격리(quarantine)와 재등록 | mock 검증 |
| GROBID 전문 추출, 초록·표·그림 블록 분리 | 실서비스 검증 |
| 추출 상태(`complete`/`partial`/`needs_ocr`/`failed`) 기록 | 실서비스 검증 (`complete`, `partial`만 관측) |
| 표 셀 분리(행당 한 줄, `|` 구분) | 실서비스 검증 |
| 로컬 모델 노트 생성과 구조·인용 ID 검사 | 실서비스 검증 |
| 노트 revision 보존과 revision 고정 조회 | mock 검증 |
| 노트·검색·활성 포인터·작업 성공의 단일 트랜잭션 확정 | mock 검증 |
| FTS5/BM25 검색 | 실서비스 검증 |
| 인용 답변, 문단 단위 인용 검증, 근거 부족 시 유보 | 실서비스 검증 (노트 3편 대상) |
| 작업 receipt(단계·추출기 버전·prompt digest·설정) | 실서비스 검증 |
| 워크스페이스 무결성 점검(`check`) | 실서비스 검증 |
| 노트·추출 JSON hash 대조, 손상 근거의 읽기·검색 차단, `check --deep` | mock 검증 |
| MCP stdio 도구(읽기·검색·질문) | 실서비스 검증 (실제 stdio 서버 구동·조회·취소) |
| 질문 job 제출·조회·취소와 질문 이력 기록 | 실서비스 검증 |
| worker 종료 경쟁·복수 manager 방지, endpoint별 프로세스 간 추론 직렬화 | mock 검증 |
| cloud/remote 모델 차단과 loopback endpoint 기본 제한 | mock 검증; 실제 설치 모델 preflight 조회 확인 |
| 창에 안 들어가는 논문의 부분 분할 생성과 coverage 기록 | 실서비스 검증 |
| 토큰 예산 추정과 입력 잘림 감지 | 실서비스 검증 (실측 2지점 기준) |
| 필요한 원문 재독(생성 중 자동) | 미구현 |
| 중간 단계부터의 작업 재개 | 미구현 |
| TEI 헤더 메타데이터 추출(제목·저자·연도·DOI·학술지) | 실서비스 검증 |
| OpenAlex로 연도·학술지·work ID 확정과 PDF 대조 승인 | 실서비스 검증 |
| 노트를 다시 쓰지 않는 메타데이터 정정 | mock 검증 |
| 기존 위키와 같은 문서 식별자·프론트매터·색인 컬럼 | mock 검증 (upstream 검증기·concept 추출기 직접 호출) |
| Concept·Overview 생성, AWS 저장소 연결 | 미구현 |
| catalog/job cursor 페이지네이션·제한 없는 내부 batch 순회 | mock 검증 |
| 색인 재구축·백업·복원 | 미구현 |
| 게시 후 terminal receipt와 DB 기반 누락 receipt 복구 | mock 검증 |
| schema migration | 실서비스 검증 (노트 3개가 있는 워크스페이스를 제자리에서 2→3으로 올림) |
| 무모니터 Mac 운영 절차 | 미구현 |
| 주장↔인용 검토표 생성(`review`) | 실서비스 검증 |
| 실제 논문 다수에 대한 품질·성능 평가 | 진행 중 (`docs/evaluation/`) |

## 설치

Python 3.12 이상과 Ollama, GROBID 서버가 필요합니다. 이 저장소는 모델·Docker·GROBID를 자동 설치하지 않습니다.

macOS/Linux에서 저장소 루트에서:

```text
uv sync --group dev          # 또는 python3.12 -m venv .venv && .venv/bin/python -m pip install -e .
export BYEORI_LOCAL_DATA="$HOME/byeori-workspace"
export BYEORI_LOCAL_MODEL="설치한-Ollama-모델명"
.venv/bin/byeori-local init
.venv/bin/byeori-local doctor
```

Windows PowerShell에서는 `py -3.12 -m venv .venv` 후 `.\.venv\Scripts\python.exe -m pip install -e .`를 사용하고, 명령은 `.\.venv\Scripts\byeori-local.exe`로 실행합니다.
Ollama는 macOS 호스트에서 실행하는 구성을 우선합니다. GROBID는 [공식 설치 안내](https://grobid.readthedocs.io/en/latest/Grobid-docker/)에 따라 경량 CRF 이미지를 우선합니다. 이미지 다운로드 크기와 실행 메모리는 다릅니다. 16GiB 장비에서 모델과 VM의 동시 상주는 실제 memory pressure·swap을 측정한 뒤 판단합니다. 컨테이너를 정지해도 VM이 해제되지는 않으며, 공유 Colima 프로필을 자동 정지하지 않습니다.

| 환경 변수 | 기본값 |
|---|---|
| `BYEORI_LOCAL_DATA` | 없음: 명시적으로 설정해야 함 |
| `BYEORI_LOCAL_MODEL` | 없음: 명시적으로 설정해야 함 |
| `BYEORI_OLLAMA_URL` | `http://127.0.0.1:11434` |
| `BYEORI_GROBID_URL` | `http://127.0.0.1:8070` |
| `BYEORI_CONTEXT` | `32768` |
| `BYEORI_OUTPUT_TOKENS` | `4096` |
| `BYEORI_LOCAL_RUNTIME_DIR` | 사용자별 임시 디렉터리 아래 공용 추론 잠금 폴더 |
| `BYEORI_OPENALEX_API_KEY` | 없음: 선택적 Bearer 인증; 로그에 기록하지 않음 |

워크스페이스는 반드시 `BYEORI_LOCAL_DATA` 또는 `--data-dir`로 지정하며, 없는 디렉터리는 `init`에서만 만듭니다. 현재 작업 폴더에 조용히 워크스페이스를 만들지 않습니다: MCP 클라이언트가 임의의 폴더에서 서버를 실행해도 빈 저장소를 새로 열지 않습니다.

모델은 `ollama list`에 있는 **로컬 모델**을 선택합니다. context는 모델·장비가 지원하는 범위 내에서 설정합니다. `doctor`는 Ollama 접근, 설치 모델의 digest/remote 표식, 서버 버전, endpoint 정책, 워크스페이스 무결성을 확인하며 GROBID·추출 품질까지 보장하지 않습니다. 알려진 remote/cloud 모델은 추론 전에 거부합니다. 외부 URL은 `--allow-remote-ollama`로 명시적으로 허용해야 하며 해당 서버로 원문이 전달됩니다. HTTP 클라이언트는 시스템 프록시를 사용하지 않습니다.

Ollama 서버의 cloud 기능 비활성화 여부는 클라이언트가 확정하지 못하므로 `cloud_disable_verification: unverified`로 표시합니다. 엄격한 local-only 운영은 **서버**에 `OLLAMA_NO_CLOUD=1` 또는 `disable_ollama_cloud`를 적용하고 재시작해야 합니다. 클라이언트 변수만으로 실행 중 서버가 바뀌지는 않습니다. [Ollama 공식 안내](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features)

## 첫 논문 처리

```text
byeori-local add "paper.pdf" --title "Paper title"
byeori-local process <반환된-paper_id>
byeori-local search "cohort samples"
byeori-local read <paper_id> [--revision <revision_id>]
byeori-local revisions <paper_id>
byeori-local ask "이 논문의 핵심 방법은?" --paper <paper_id>
byeori-local cancel <job_id>
byeori-local status [<job_id>]
byeori-local check
byeori-local check --deep
byeori-local list --limit 50
byeori-local status --limit 20
byeori-local reconcile-receipts
byeori-local revalidate --all
byeori-local metadata --all
byeori-local review <문서 식별자> --out docs/evaluation/<이름>.md
```

전역 옵션(`--data-dir`, `--model`, `--context`)은 하위 명령 앞에 둡니다. PDF는 SHA-256으로 중복 확인하며 원본을 보존합니다. DOI가 없어도 등록할 수 있습니다. `process`는 GROBID 추출과 Ollama 호출을 동기 실행하므로 수 분 걸릴 수 있습니다.

논문은 저장 키(PDF의 SHA-256)와 **문서 식별자**를 따로 가집니다. 문서 식별자는 기존 byeori와 같은 `{첫 저자}-{연도}-{제목 단어}` 형식(예: `zhou-2021-de-novo-variants-in-autism-cohorts`)이며, 추출한 TEI 헤더에서 만듭니다. 검색 결과의 `doc_id`와 노트 경로가 이 식별자이고, `byeori.identity.split_stem`이 그대로 읽습니다. 같은 식별자가 이미 있으면 뒤에 번호를 붙입니다. 한 논문의 식별자는 첫 게시 때 정해지고 노트를 다시 써도 바뀌지 않습니다.

추출한 메타데이터는 **OpenAlex에 대조해 확정합니다.** 경량 CRF GROBID는 실제 저널 PDF의 헤더에서 출판일을 자주 못 뽑습니다(이 저장소의 Nature Communications 논문 두 편 모두 `<date/>`가 비어 있었습니다). 연도가 없으면 그 노트를 연구의 흐름 속에 놓을 수 없으므로, PDF에 인쇄된 DOI로 먼저 조회하고 없으면 제목으로 검색합니다.

받아온 기록은 기존 AWS 경로와 **같은 판정기**(`byeori.identity.judge`)를 통과해야 채택합니다: 제목이 PDF 헤더나 본문 첫 부분과 일치하고 1저자가 어긋나지 않아야 합니다. 승인된 기록은 빈 연도·학술지·DOI·work ID를 보완합니다. PDF와 충돌하면 `openalex_year`·`openalex_journal`·`metadata_disagreement`를 남기며 확정값을 덮어쓰지 않습니다. 재조회가 disabled·not_found·unavailable·rate_limited여도 기존 확정값을 보존합니다. 조회 상태는 `metadata_checks`에 기록하며 실패가 노트 게시를 막지는 않습니다. 필드 보완 출처는 `metadata_provenance`로 기록합니다.

`BYEORI_METADATA_LOOKUP=off`로 끌 수 있습니다. `BYEORI_OPENALEX_MAILTO`는 호출자 식별용이며 처리량 보장이 아닙니다. 선택적인 `BYEORI_OPENALEX_API_KEY`를 지원하고, 429는 짧은 Retry-After일 때 한 번만 재시도한 뒤 rate_limited로 기록합니다.

`byeori-local metadata --all`은 이미 게시된 논문의 연도·학술지·work ID를 **모델을 호출하지 않고** 확정합니다. 노트 본문은 모델의 작업물이므로 그대로 복사하고 프론트매터만 다시 쓰며, 게시된 노트는 제자리에서 고치지 않으므로 `revision_reason: "metadata-resolved"`를 단 새 revision이 됩니다. 연도를 나중에 알게 되면 `0000`이던 문서 식별자도 한 번 정정하고, 물러난 식별자는 색인에서 지웁니다. 이전 revision의 인용은 계속 그 문단을 가리킵니다.

프론트매터의 `text_extractor`·`text_extractor_version`이 어느 추출기가 읽었는지 밝힙니다.

물러난 식별자는 `document_aliases`로 같은 논문에 연결하고 다른 논문에 재할당하지 않습니다. `process --all`·`metadata --all`·`revalidate --all`·orphan 탐색은 화면 목록의 개수 제한을 사용하지 않습니다. `list`와 job 목록 `status`는 `next_cursor`를 반환하며 다음 조회에 `--cursor <값>`을 지정합니다. 조회 시작 뒤 추가된 자료는 새 조회에서 보입니다.

노트의 Glossary는 `- **용어**: 정의` 형식이어야 하며, byeori의 concept 추출기가 읽을 수 있는 항목이 3개 미만이면 게시하지 않습니다. 이 형식이 아니면 그 노트는 concept 페이지에 아무것도 기여하지 못합니다.

작업별 TEI·문단 JSON·모델 후보·실행 기록은 `runs/<job_id>/`에 남습니다. `receipt.json`은 성공·실패 모두 남으며 도달한 단계, GROBID가 스스로 기록한 버전, prompt digest, 설정을 담습니다. 게시된 노트는 `wiki/sources/<문서 식별자>/<revision_id>.md`에 버전별로 보존하고, `note_versions`가 각 revision의 sha256과 그 노트가 읽은 추출을 기록합니다. catalog는 논문당 하나의 활성 노트를 가리키며 검색도 그 revision만 사용합니다.

노트 revision 등록·검색 색인·활성 포인터·작업 성공은 하나의 SQLite 트랜잭션에서 확정됩니다. 파일은 그 전에 별도로 기록되므로 실패한 게시의 orphan 파일이 남을 수 있습니다. 실패가 이전 활성 노트를 교체하지는 않습니다. 파일은 임시 이름에 쓰고 fsync 후 hard link로 최종 이름을 독점 생성하여 동시 writer도 기존 산출물을 덮어쓰지 않습니다. 파일시스템은 hard link를 지원해야 합니다. 등록이 중간에 끊겨 일부만 남은 파일은 `quarantine/`에 보존하고 다시 등록합니다.

`execution.json`은 게시 전 생성 완료 기록이고, `receipt.json`은 DB 확정 후 terminal 결과입니다. commit 뒤 receipt 쓰기가 실패해도 성공 job을 failed로 바꾸지 않습니다. `reconcile-receipts`는 누락 결과를 DB에서 복원하며 기존 모순 receipt는 덮어쓰지 않고 conflicts로 보고합니다.

노트는 읽을 때 저장 hash와 대조하고, 새 revision의 문단 JSON도 별도 hash로 검증합니다. 손상 revision은 답변·검색에 사용하지 않습니다. 기존 schema 4의 JSON hash가 없는 자료는 `legacy_unverified`이며, 이후 현재 bytes에 기준선을 기록한 사실이 과거 무변조의 증명은 아닙니다. `check --deep`은 원본 PDF와 TEI도 검사합니다.

출력 잘림, 잘못된 section 이름·순서, 존재하지 않는 문단 citation은 게시하지 않습니다. 반면 표기 편차는 애플리케이션이 정규화합니다: heading의 줄 끝 공백과 레벨(`###`), 그리고 문단 인용의 다섯 가지 형태 — `[P0042]`, `(P0042)`, `[P0011, P0017]`, `[P0040-P0043]`, 그 혼합. 13블록을 넘는 범위나 역순 범위는 인용으로 인정하지 않습니다.

검증만 실패한 작업은 `byeori-local revalidate <job_id>`로 **모델을 다시 호출하지 않고** 게시할 수 있습니다. 노트 본문은 그 작업이 이미 쓴 것이고 `runs/<job_id>/candidate.md`에 남아 있으므로, 검사 규칙이 나중에 그 표기를 읽게 되면 한 시간짜리 생성을 다시 하지 않습니다. 게시된 노트는 `written_by_job`으로 어느 작업이 썼는지 밝힙니다. 프론트매터와 `## 1. Document Information`을 애플리케이션이 쓰는 것과 같은 이유이며, 실제 모델이 흔히 만드는 형식 편차 때문에 내용이 올바른 노트를 버리지 않습니다. section 이름과 순서는 계약이므로 그대로 검사합니다.

작업 중 프로세스가 종료되면 다음 `process`가 이전 작업을 `interrupted`로 표시하고 새 작업을 시작합니다. 현재 중간 단계부터 재개하지는 않습니다. 워크스페이스당 처리 worker는 OS 파일 잠금으로 하나만 허용합니다.

이전 스키마(노트에 revision이 없던 버전)로 만든 워크스페이스에 이미 게시된 노트가 있으면 열기를 거부합니다. 파일은 모두 보존되며, 이 릴리스로 만든 워크스페이스에서 `process`를 다시 실행하면 각 노트가 revision을 갖습니다.

## MCP 연결

클라이언트의 MCP 설정에 아래 형태를 추가합니다. 실제 모델명과 경로를 사용하세요.

```json
{
  "mcpServers": {
    "byeori-local": {
      "command": "<저장소>/.venv/bin/byeori-local-mcp",
      "env": {
        "BYEORI_LOCAL_DATA": "<워크스페이스 경로>",
        "BYEORI_LOCAL_MODEL": "설치한-Ollama-모델명"
      }
    }
  }
}
```

도구: `list_papers`, `list_papers_page`, `search_wiki`, `read_evidence_note`, `list_note_revisions`, `read_paper_context`, `ask_byeori`, `get_job`, `list_jobs`, `list_jobs_page`, `cancel_job`.

기존 `list_papers`·`list_jobs`의 list 반환 형식은 유지합니다. 전체 자료는 `list_papers_page`·`list_jobs_page`의 `next_cursor`로 순회합니다. 같은 Ollama endpoint를 사용하는 노트·digest·질문·번역·audit는 공용 OS 잠금과 thread 잠금으로 직렬 실행합니다. 복수 워크스페이스/앱의 `BYEORI_LOCAL_RUNTIME_DIR`는 같아야 하며, doctor가 실제 잠금 경로를 출력합니다. 이 잠금은 byeori를 거치지 않는 다른 앱의 호출을 통제하지 못합니다.

timeout이나 프로세스 강제 종료 뒤에는 서버가 계산 중일 수 있습니다. 추론 전에 남긴 호출 표식 또는 timeout 표식이 있으면 다음 호출을 `recovery_pending`으로 차단합니다. 서버의 이전 요청 종료를 직접 확인한 다음 `byeori-local recover-runtime --acknowledge-idle`로 해제합니다. `ollama ps`의 모델 상주 정보만으로 요청 종료를 확정하지 않습니다. think 옵션 제거 재시도는 모델이 해당 옵션 미지원임을 명시적으로 응답한 경우에만 수행합니다.
등록·생성은 CLI에서 실행합니다. `ask_byeori`는 서버의 Ollama를 호출합니다. 클라이언트 자체가 클라우드 모델이면 반환된 자료는 그 모델의 문맥으로 전달될 수 있습니다.

`ask_byeori`는 **질문을 job으로 제출하고 job ID를 즉시 반환합니다**(측정 0.00초). 로컬 모델은 분 단위로 답하므로 도구 호출을 열어두지 않습니다. `get_job`으로 상태를 조회하고, 답이 나오면 `result`에 담깁니다. 질문이 도는 동안에도 서버는 다른 도구에 응답합니다(생성 중 `search_wiki` 0.00초로 확인). 질문은 워크스페이스당 하나씩 순서대로 실행합니다: 같은 장비에서 두 번째 모델 호출은 첫 번째와 메모리를 다툽니다.

`cancel_job`은 **접수(`cancel_requested`)와 실제 중단(`stopped`)을 구분해 반환합니다.** 이미 모델 호출 안에 들어간 job은 그 호출이 돌아온 뒤 멈추며, 모델이 낸 답은 폐기하고 `status: cancelled`로 기록합니다. 질문을 제출한 프로세스가 답을 받기 전에 종료되면, 다음에 워크스페이스를 여는 쪽이 그 job을 `interrupted`로 기록합니다: 아무도 쓰지 않을 답을 기다리는 중이라고 보고하지 않습니다.

CLI의 `ask`는 이 프로세스가 직접 실행하므로 답이 나올 때까지 기다립니다. 기다리지 않는 제출은 호출보다 오래 사는 MCP 서버의 기능입니다. 두 경로 모두 질문 내용과 범위를 job에 기록합니다.

`read_evidence_note`는 `next_start`로 다음 범위를 읽고, 반환된 `revision_id`를 다시 넘기면 같은 버전을 계속 읽습니다. 문단 citation `[P0001]`은 `read_paper_context(paper_id, paragraph_id, revision)`로 그 revision이 읽은 추출에 연결합니다. `ask_byeori`는 `answer_status`가 `answered` 또는 `insufficient_evidence`이며, 오류가 아니라 유보를 반환하고 그때는 답변 본문을 돌려주지 않습니다. `reason`은 `no_search_hit`(검색 근거 없음 — 모델을 호출하지 않습니다), `model_answer_uncited`(근거 라벨 확인 불가), `model_citation_unresolvable`(그 노트에 없는 문단을 인용)입니다.

답변은 `[E1]` 또는 문단까지 지목하는 `[E1-P0042]`, `[E1-P0042, P0043]` 형식으로 인용합니다. 문단 ID는 **해당 호출에 제공한 노트가 인용하는 문단**으로 제한하고 실제 추출에도 존재하는지 확인합니다. 인용 없는 문장이 함께 나오면 답변을 유보합니다. 문장 분리는 휴리스틱이며 복합 주장의 의미적 타당성을 인증하지 않습니다. 인용에는 `note_revision_id`, `note_sha256`, `extraction_id`, `extraction_status`와 함께 `block_ids`가 옵니다. `read_paper_context(paper_id, block_id, revision)`으로 원문까지 이어집니다.

## 측정값

Apple M4 / 10 core / RAM 16 GB / macOS 15.7.4, GROBID 0.9.1-crf(colima 4 cpu · 6 GB VM), qwen3:8b Q4_K_M에서 15쪽 논문 1편:

| 항목 | 값 |
|---|---|
| GROBID 추출 | 약 10초, TEI 89 KB, 블록 85개 |
| 노트 생성(한 패스) | 1분 50초 ~ 3분 (입력 8,567 token, 출력 1,764 token) |
| 같은 논문을 context 16384에서 부분 분할 | 4개 부분, 9분 11초, 85/85 블록 제시, digest가 인용한 블록 61개 |
| 질문 1건(한국어, 논문 지정) | 42초 ~ 70초 |
| 질문 1건(한국어, 노트 3편 근거) | 1분 40초 |
| 모델 상주 메모리 | context 40960에서 8.3 GB (100% GPU) |

위 값은 기존 한 편의 실행 기록이며 이번 안정화에서 재측정하지 않았습니다. 모델 상주 8.3 GB와 VM 할당 6 GB를 단순 합산한 값은 실제 전체 메모리 실사용량의 측정이 아닙니다. 더 큰 모델은 추출 VM 해제와 memory pressure·swap 실측을 전제로 별도 시험합니다.

## 현재 범위와 제한

- 노트가 논문을 옳게 옮겼는지는 **사람이 읽어야** 압니다. `review` 명령이 주장마다 그것이 인용한 문단의 원문을 나란히 놓은 검토표를 만들고, 판정은 비워 둡니다. 판정을 계산하지 않는 이유는 실측입니다: 이 저장소에서 문자열 대조로 확인했을 때 옳은 주장 두 개를 조작으로 오판했습니다 — 논문은 "an additional 22 pathways"라고 쓰고 노트는 "22 unique pathways"라고 썼기 때문입니다. 원본 byeori의 `benchmark.py`도 같은 입장입니다("Quality is left to the reader").
- 구조·호출에 제공한 citation ID·파일 hash를 기계적으로 확인합니다(`validation_level: structure_checked`). 근거가 claim을 의미적으로 뒷받침하는지는 검사하지 않습니다. 실제 실행에서 노트가 어떤 수치를 실제로는 그 문단에 없는 문단 ID로 인용한 사례를 확인했습니다. 수치를 쓰려면 `read_paper_context`로 원문을 확인해야 합니다.
- 표는 행당 한 줄, 셀은 `|`로 분리합니다. 다만 GROBID가 병합 셀(colspan)을 표현하지 못해 여러 열 머리글이 한 셀에 합쳐지는 경우가 있고, 그때 값이 어느 열에 속하는지는 원문 확인이 필요합니다.
- GROBID 추출 결과만 읽습니다. OCR·이미지 이해·표 셀 검증·보충자료는 자동 처리하지 않습니다. 초록이 없으면 추출 상태를 `partial`로 기록하고 게시는 막지 않습니다.
- 입력 예산은 토큰 추정으로 판단합니다. Ollama는 tokenizer를 노출하지 않으므로 문자 종류별 가중치로 추정하며, 실측 두 지점(산문 4.04자/토큰, 숫자 표 2.15자/토큰)에서 각각 1.41배·1.20배로 항상 높게 나옵니다. 낮게 추정하면 논문이 조용히 잘리기 때문입니다.
- 창에 들어가지 않는 논문은 부분으로 나눠 각 부분의 digest를 만들고, 그 digest들로 노트를 씁니다. 부분 크기는 읽기 예산과 **써낼 수 있는 양** 양쪽으로 제한합니다: 표는 행마다 한 줄이 나와 입력당 출력 1.8배, 산문은 0.8배로 측정됐습니다. digest로 쓴 노트는 프론트매터의 `generation_path: chunked`로 구분됩니다.
- 분할로 쓴 노트는 원문을 한 번에 읽고 쓴 노트보다 귀속 오류 위험이 큽니다. 실제 실행에서 분할 노트가 base 모델의 FLOPs(3.3×10^18)를 big 모델의 값으로 적은 사례를 확인했습니다. 수치를 쓰려면 `read_paper_context`로 해당 문단을 확인해야 하며, 프론트매터의 `generation_path`로 어느 경로로 쓴 노트인지 구분할 수 있습니다.
- digest 실패 블록은 자동 생략하여 게시하지 않습니다. candidate/실패 기록을 보존합니다. 최종 노트의 인용은 digest에 유지된 ID로 한정합니다. digest 전체가 노트 한 패스에 들어가지 않으면 필요한 context를 알려주고 **거부합니다**. digest를 다시 합치는 라운드는 넣지 않았습니다: 실측에서 2개 합치기가 입력당 출력 1.76배, 4개가 1.22배로 압축이 아니라 팽창이었고, 수렴하는 라운드가 없습니다. 논문 자체의 digest는 약 0.54로 압축됩니다.
- 질문은 노트 기반이며 자동 원문 재독·위키 편집은 하지 않습니다. MCP로 원문 문단을 직접 확인할 수 있습니다.
- Concept·Overview 생성, AWS 저장소 연결, 자동 작업 큐, 백업 자동화는 후속 구현입니다.
- MCP는 stdio입니다. 질문은 job이므로 클라이언트 timeout 문제는 없지만, 서버 프로세스가 죽으면 그 안에서 돌던 질문은 사라지고 `interrupted`로 기록됩니다.
- 이전 스키마 워크스페이스는 제자리에서 올립니다(컬럼 추가). 올릴 수 없는 변경이 나오면 파일을 보존한 채 거부하고, 이 릴리스로 만든 워크스페이스에서 다시 게시하도록 안내합니다.
- 기존 11편 품질 평가는 보조 판정입니다. 안정화 후 재생성·사람 평가와 새로운 성능 측정은 별도로 진행해야 합니다.

## 테스트

```text
uv sync --group dev
.venv/bin/python -m pytest tests/test_local_integrity.py tests/test_local_runtime.py tests/test_local_remediation.py tests/test_wiki_search.py tests/test_cloud_only.py
```

`test_local_integrity.py`는 실제 GROBID 출력과 실제 모델 노트에서 재현한 결함을 사용자에게 보이는 불변 조건으로 고정합니다. 개발 기록에는 mock 테스트 통과와 실제 모델 검증을 구분해 기록합니다. 원본 AWS 테스트는 그대로 유지합니다.

검토표는 표 행·인용문·요약·Related Work·Glossary도 포함하는 `evaluation_schema=2`로 생성합니다. 과거 v1의 208개 평가 항목과 분모가 다릅니다. 판정은 주장+근거 fingerprint가 같을 때만 재사용하며, 출력 파일을 다시 쓸 때 원래 검토표를 `.review-history/`에 보존합니다. fingerprint가 없는 과거 판정은 자동 승계하지 않습니다. 과학적 주장 분리와 의미 판정은 여전히 사람 확인이 필요합니다.

CLI는 완료/정상 근거 부족 0, 실패 1, 잘못된 인자 2, 일부 실패 batch 3을 반환합니다. `cancel`의 코드 0은 취소 접수 성공이며 `stopped`로 실제 완료를 확인해야 합니다.
