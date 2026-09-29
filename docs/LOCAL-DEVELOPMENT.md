# Local LLM 개발 버전

기존 `byeori` AWS 명령과 별도로 `byeori-local` / `byeori-local-mcp`를 추가했습니다.
이 버전은 단일 논문 처리 흐름을 검증하는 개발용 런타임입니다. AWS 배포·자격증명이 필요하지 않으며 기존 S3 데이터를 자동으로 내려받거나 변경하지 않습니다.

## 기능별 상태

`구현`은 코드가 존재한다는 뜻이고, `mock 검증`은 고정 응답·transport mock 테스트까지, `실서비스 검증`은 실제 GROBID·실제 Ollama 모델로 확인했다는 뜻입니다. 모델의 논문 이해 품질은 어느 항목에서도 아직 평가 대상이 아닙니다.

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
| 인용 답변과 근거 부족 시 유보 | 실서비스 검증 |
| 작업 receipt(단계·추출기 버전·prompt digest·설정) | 실서비스 검증 |
| 워크스페이스 무결성 점검(`check`) | 실서비스 검증 |
| MCP stdio 도구(읽기·검색·질문) | mock 검증 (실제 클라이언트 연결은 미검증) |
| 긴 논문의 section 분할 생성과 coverage 추적 | 미구현 |
| 토큰 기반 입력 예산 | 미구현 (보수적 byte 예산만) |
| 비동기 질문 job 제출·조회·취소 | 미구현 (동기 실행) |
| 중간 단계부터의 작업 재개 | 미구현 |
| Concept·Overview 생성, AWS 저장소 연결 | 미구현 |
| catalog 페이지네이션·색인 재구축·백업·복원 | 미구현 |
| schema migration | 미구현 (이전 스키마 워크스페이스는 거부하고 파일은 보존) |
| 무모니터 Mac 운영 절차 | 미구현 |
| 실제 논문 다수에 대한 품질·성능 평가 | 미검증 |

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
Ollama는 macOS 호스트에서 실행하는 구성을 우선합니다. GROBID는 [공식 설치 안내](https://grobid.readthedocs.io/en/latest/Grobid-docker/)에 따라 준비합니다. 경량 CRF 이미지(`grobid/grobid:<버전>-crf`, 약 0.5 GB)는 16 GB 장비에서 모델과 함께 운영할 수 있고, 딥러닝 모델을 포함한 full 이미지(약 10 GB)는 메모리를 더 요구합니다.

| 환경 변수 | 기본값 |
|---|---|
| `BYEORI_LOCAL_DATA` | 없음: 명시적으로 설정해야 함 |
| `BYEORI_LOCAL_MODEL` | 없음: 명시적으로 설정해야 함 |
| `BYEORI_OLLAMA_URL` | `http://127.0.0.1:11434` |
| `BYEORI_GROBID_URL` | `http://127.0.0.1:8070` |
| `BYEORI_CONTEXT` | `32768` |
| `BYEORI_OUTPUT_TOKENS` | `4096` |

워크스페이스는 반드시 `BYEORI_LOCAL_DATA` 또는 `--data-dir`로 지정하며, 없는 디렉터리는 `init`에서만 만듭니다. 현재 작업 폴더에 조용히 워크스페이스를 만들지 않습니다: MCP 클라이언트가 임의의 폴더에서 서버를 실행해도 빈 저장소를 새로 열지 않습니다.

모델은 `ollama list`에 있는 **로컬 모델**을 선택합니다. context는 모델·장비가 지원하는 범위 내에서 설정합니다. `doctor`는 Ollama 접근, 모델 설치, 워크스페이스 무결성을 확인하며 GROBID·추출 품질까지 보장하지 않습니다. 외부 서버 URL을 지정하면 해당 서버로 원문이 전달됩니다. HTTP 클라이언트는 시스템 프록시를 사용하지 않습니다.

## 첫 논문 처리

```text
byeori-local add "paper.pdf" --title "Paper title"
byeori-local process <반환된-paper_id>
byeori-local search "cohort samples"
byeori-local read <paper_id> [--revision <revision_id>]
byeori-local revisions <paper_id>
byeori-local ask "이 논문의 핵심 방법은?" --paper <paper_id>
byeori-local status [<job_id>]
byeori-local check
```

전역 옵션(`--data-dir`, `--model`, `--context`)은 하위 명령 앞에 둡니다. PDF는 SHA-256으로 중복 확인하며 원본을 보존합니다. DOI가 없어도 등록할 수 있습니다. `process`는 GROBID 추출과 Ollama 호출을 동기 실행하므로 수 분 걸릴 수 있습니다.

작업별 TEI·문단 JSON·모델 후보·실행 기록은 `runs/<job_id>/`에 남습니다. `receipt.json`은 성공·실패 모두 남으며 도달한 단계, GROBID가 스스로 기록한 버전, prompt digest, 설정을 담습니다. 게시된 노트는 `wiki/sources/<paper_id>/<revision_id>.md`에 버전별로 보존하고, `note_versions`가 각 revision의 sha256과 그 노트가 읽은 추출을 기록합니다. catalog는 논문당 하나의 활성 노트를 가리키며 검색도 그 revision만 사용합니다.

노트 파일·검색 색인·활성 포인터·작업 성공은 한 트랜잭션에서 확정됩니다. 따라서 실패로 기록된 작업의 노트가 검색에 노출되는 상태는 생기지 않고, 재생성이 실패하면 이전 노트가 계속 검색에 사용됩니다. 파일은 임시 이름에 쓰고 fsync 후 이름을 바꾸므로 절반만 쓰인 산출물을 읽는 일이 없습니다. 등록이 중간에 끊겨 원본이 일부만 남은 경우 그 파일을 `quarantine/`으로 옮기고 다시 등록합니다: 삭제하지 않습니다.

출력 잘림, 잘못된 section 이름·순서, 존재하지 않는 문단 citation은 게시하지 않습니다. 반면 heading의 줄 끝 공백과 heading 레벨(`###`)은 애플리케이션이 정규화합니다. 프론트매터와 `## 1. Document Information`을 애플리케이션이 쓰는 것과 같은 이유이며, 실제 모델이 흔히 만드는 형식 편차 때문에 내용이 올바른 노트를 버리지 않습니다. section 이름과 순서는 계약이므로 그대로 검사합니다.

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

도구: `list_papers`, `search_wiki`, `read_evidence_note`, `list_note_revisions`, `read_paper_context`, `ask_byeori`, `get_job`.
등록·생성은 CLI에서 실행합니다. `ask_byeori`는 서버의 Ollama를 호출합니다. 클라이언트 자체가 클라우드 모델이면 반환된 자료는 그 모델의 문맥으로 전달될 수 있습니다.

`read_evidence_note`는 `next_start`로 다음 범위를 읽고, 반환된 `revision_id`를 다시 넘기면 같은 버전을 계속 읽습니다. 문단 citation `[P0001]`은 `read_paper_context(paper_id, paragraph_id, revision)`로 그 revision이 읽은 추출에 연결합니다. `ask_byeori`는 `answer_status`가 `answered` 또는 `insufficient_evidence`이며, 근거가 없거나 모델 답변의 근거 라벨을 확인할 수 없으면 오류가 아니라 유보를 반환하고 답변 본문을 돌려주지 않습니다. 인용에는 `note_revision_id`, `note_sha256`, `extraction_id`, `extraction_status`가 함께 옵니다.

## 측정값

Apple M4 / 10 core / RAM 16 GB / macOS 15.7.4, GROBID 0.9.1-crf(colima 4 cpu · 6 GB VM), qwen3:8b Q4_K_M에서 15쪽 논문 1편:

| 항목 | 값 |
|---|---|
| GROBID 추출 | 약 10초, TEI 89 KB, 블록 85개 |
| 노트 생성 | 1분 50초 ~ 3분 (입력 8,567 token, 출력 1,764 token) |
| 질문 1건(한국어 → 영어 검색어 번역 포함) | 약 70초 |
| 모델 상주 메모리 | context 40960에서 8.3 GB (100% GPU) |

모델 1개와 GROBID VM을 동시에 올리면 16 GB 중 약 14 GB를 점유합니다. 더 큰 모델을 쓰려면 GROBID를 필요할 때만 실행하는 운용이 필요합니다. 한 편의 측정값이며 논문 유형별 분포는 아닙니다.

## 현재 범위와 제한

- 구조·citation ID 존재만 기계적으로 확인합니다(`validation_level: structure_checked`). 근거가 claim을 의미적으로 뒷받침하는지는 검사하지 않습니다. 실제 실행에서 노트가 어떤 수치를 실제로는 그 문단에 없는 문단 ID로 인용한 사례를 확인했습니다. 수치를 쓰려면 `read_paper_context`로 원문을 확인해야 합니다.
- 표는 행당 한 줄, 셀은 `|`로 분리합니다. 다만 GROBID가 병합 셀(colspan)을 표현하지 못해 여러 열 머리글이 한 셀에 합쳐지는 경우가 있고, 그때 값이 어느 열에 속하는지는 원문 확인이 필요합니다.
- GROBID 추출 결과만 읽습니다. OCR·이미지 이해·표 셀 검증·보충자료는 자동 처리하지 않습니다. 초록이 없으면 추출 상태를 `partial`로 기록하고 게시는 막지 않습니다.
- 긴 입력은 보수적인 UTF-8 byte 예산을 넘으면 거부합니다. 이 예산은 실제 tokenizer 측정이 아니며 과대 추정합니다: 관측된 한 편에서 prompt 33 KB가 실제로는 8,567 token이었습니다. 아직 section별 분할 생성과 coverage 추적은 없습니다.
- 질문은 노트 기반이며 자동 원문 재독·위키 편집은 하지 않습니다. MCP로 원문 문단을 직접 확인할 수 있습니다.
- Concept·Overview 생성, AWS 저장소 연결, 자동 작업 큐, 백업 자동화는 후속 구현입니다.
- MCP는 stdio이고 질문은 동기 실행입니다. 클라이언트 timeout을 충분히 설정해야 합니다.
- 실제 논문 다수에 대한 품질·속도 평가는 별도 진행해야 합니다.

## 테스트

```text
uv sync --group dev
.venv/bin/python -m pytest tests/test_local_integrity.py tests/test_local_runtime.py tests/test_wiki_search.py tests/test_cloud_only.py
```

`test_local_integrity.py`는 실제 GROBID 출력과 실제 모델 노트에서 재현한 결함을 사용자에게 보이는 불변 조건으로 고정합니다. 개발 기록에는 mock 테스트 통과와 실제 모델 검증을 구분해 기록합니다. 원본 AWS 테스트는 그대로 유지합니다.
