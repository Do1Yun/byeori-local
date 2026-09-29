# Local LLM 개발 버전

기존 `byeori` AWS 명령과 별도로 `byeori-local` / `byeori-local-mcp`를 추가했습니다.
이 버전은 단일 논문 처리 흐름을 검증하는 개발용 런타임입니다. AWS 배포·자격증명이 필요하지 않으며 기존 S3 데이터를 자동으로 내려받거나 변경하지 않습니다.

## 설치

Python 3.12 이상과 Ollama, GROBID 서버가 필요합니다. 이 저장소는 모델·Docker·GROBID를 자동 설치하지 않습니다.

Windows PowerShell, 저장소 루트에서:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$env:BYEORI_LOCAL_MODEL = "설치한-Ollama-모델명"
$env:BYEORI_LOCAL_DATA = "C:\Users\Kim Sunghyun\Documents\GitHub\byeori-local\.byeori-local"
.\.venv\Scripts\byeori-local.exe doctor
```

macOS/Linux에서는 `python3 -m venv .venv` 후 `.venv/bin/python -m pip install -e .`를 사용합니다.
Ollama는 macOS 호스트에서 실행하는 구성을 우선합니다. GROBID는 [공식 설치 안내](https://grobid.readthedocs.io/en/latest/Grobid-docker/)에 따라 준비합니다.

| 환경 변수 | 기본값 |
|---|---|
| `BYEORI_LOCAL_DATA` | 현재 작업 폴더의 `.byeori-local` |
| `BYEORI_LOCAL_MODEL` | 없음: 명시적으로 설정해야 함 |
| `BYEORI_OLLAMA_URL` | `http://127.0.0.1:11434` |
| `BYEORI_GROBID_URL` | `http://127.0.0.1:8070` |
| `BYEORI_CONTEXT` | `32768` |
| `BYEORI_OUTPUT_TOKENS` | `4096` |

모델은 `ollama list`에 있는 **로컬 모델**을 선택합니다. context는 모델·장비가 지원하는 범위 내에서 설정합니다. `doctor`는 Ollama 접근과 모델 설치 여부를 확인하며 GROBID·추출 품질까지 보장하지 않습니다. 외부 서버 URL을 지정하면 해당 서버로 원문이 전달됩니다. HTTP 클라이언트는 시스템 프록시를 사용하지 않습니다.

## 첫 논문 처리

아래 명령의 `byeori-local`은 Windows에서 `.\.venv\Scripts\byeori-local.exe`로 실행할 수 있습니다.

```text
byeori-local add "paper.pdf" --title "Paper title"
byeori-local process <반환된-paper_id>
byeori-local search "cohort samples"
byeori-local read <paper_id>
byeori-local ask "이 논문의 핵심 방법은?" --paper <paper_id>
byeori-local status
```

전역 옵션(`--data-dir`, `--model`, `--context`)은 하위 명령 앞에 둡니다. PDF는 SHA-256으로 중복 확인하며 원본을 보존합니다. DOI가 없어도 등록할 수 있습니다. `process`는 GROBID 추출과 Ollama 호출을 동기 실행하므로 수 분 걸릴 수 있습니다.

작업별 TEI·문단 JSON·모델 후보·실행 기록은 `runs/<job_id>/`에 남습니다. 성공한 노트는 `wiki/sources/<paper_id>/<job_id>.md`에 버전별로 저장합니다. catalog는 논문당 하나의 활성 노트만 가리키며 검색에서도 그 버전만 사용합니다. 이전 버전은 보존합니다.

출력 잘림, 잘못된 section, 존재하지 않는 문단 citation은 게시하지 않습니다. 재생성이 실패하면 기존 정상 노트와 검색 결과를 유지합니다. 작업 중 프로세스가 종료되면 다음 `process`가 이전 작업을 `interrupted`로 표시하고 새 작업을 시작합니다. 현재 중간 단계부터 재개하지는 않습니다. 워크스페이스당 처리 worker는 OS 파일 잠금으로 하나만 허용합니다.

## MCP 연결

클라이언트의 MCP 설정에 아래 형태를 추가합니다. 실제 모델명과 경로를 사용하세요.

```json
{
  "mcpServers": {
    "byeori-local": {
      "command": "C:\\Users\\Kim Sunghyun\\Documents\\GitHub\\byeori-local\\.venv\\Scripts\\byeori-local-mcp.exe",
      "env": {
        "BYEORI_LOCAL_DATA": "C:\\Users\\Kim Sunghyun\\Documents\\GitHub\\byeori-local\\.byeori-local",
        "BYEORI_LOCAL_MODEL": "설치한-Ollama-모델명"
      }
    }
  }
}
```

도구: `list_papers`, `search_wiki`, `read_evidence_note`, `read_paper_context`, `ask_byeori`, `get_job`.
등록·생성은 CLI에서 실행합니다. `ask_byeori`는 서버의 Ollama를 호출합니다. 클라이언트 자체가 클라우드 모델이면 반환된 자료는 그 모델의 문맥으로 전달될 수 있습니다.

`read_evidence_note`는 `next_start`로 다음 범위를 읽습니다. 문단 citation `[P0001]`은 `read_paper_context(paper_id, paragraph_id)`로 원문 추출에 연결합니다. 답변은 `[E1]`과 별도의 버전 고정된 note 경로를 반환합니다.

## 현재 범위와 제한

- 구조·citation ID 존재만 기계적으로 확인합니다. 근거가 claim을 의미적으로 뒷받침하는지는 사람이 검토해야 합니다.
- GROBID 추출 결과만 읽습니다. OCR·이미지 이해·표 셀 검증·보충자료는 자동 처리하지 않습니다.
- 긴 입력은 보수적인 UTF-8 byte 예산을 넘으면 거부합니다. 아직 section별 분할 생성은 없습니다. byte 예산은 실제 tokenizer 측정이 아닙니다.
- 질문은 노트 기반이며 자동 원문 재독·위키 편집은 하지 않습니다. MCP로 원문 문단을 직접 확인할 수 있습니다.
- Concept·Overview 생성, AWS 저장소 연결, 자동 작업 큐, 백업 자동화는 후속 구현입니다.
- MCP는 stdio이고 질문은 동기 실행입니다. 클라이언트 timeout을 충분히 설정해야 합니다.
- 모델 다운로드와 실제 논문을 통한 품질·속도 평가는 별도 진행해야 합니다.

## 테스트

```text
python -m pip install --group dev
python -m pytest tests/test_local_runtime.py tests/test_wiki_search.py tests/test_cloud_only.py
```

개발 기록에는 mock 테스트 통과와 실제 모델 검증을 구분해 기록합니다. 원본 AWS 테스트는 그대로 유지합니다.
