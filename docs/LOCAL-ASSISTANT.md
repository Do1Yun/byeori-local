# 로컬 업무 도우미

직접 지정한 작업 메모와 로컬 Git 기록으로 메모 정리, 커밋 요약, 파일 분류 제안,
보고서 초안을 만든다. Ollama 연결·local-only 모델 검사·추론 직렬화는 기존 로컬
런타임을 재사용하고, 논문 catalog와 업무 도우미 워크스페이스는 분리한다.
논문은 사람이 확보한다. 이 도구에는 웹 수집이나 크롤링 기능이 없다.

## 현재 사용할 수 있는 기능

| 명령 | 입력 | 결과 |
|---|---|---|
| `notes` | 명시한 UTF-8 파일 또는 폴더 | 요약, 결정 사항, 할 일, 미확정 사항 |
| `commits` | 허용한 로컬 Git 저장소와 기간 | 기본은 커밋 제목의 짧은 한국어 요약. `--diff`로 전체 메시지·patch를 읽어 상세 정리 |
| `classify` | 명시한 폴더 | 파일별 분류와 이유. 원본은 이동하거나 이름을 바꾸지 않음 |
| `report` | UTF-8 자료 및/또는 이전 작업 ID | 진행 내용, 결과, 남은 작업, 확인 필요 사항이 담긴 초안 |

CLI는 생성이 끝날 때까지 기다리고 JSON으로 작업 상태와 결과 경로를 출력한다.
MCP는 작업 ID를 먼저 반환하고 `get_task`로 상태를 조회한다.
OpenClaw 자체를 설치하는 변경은 아니며, 여기서 제공하는 MCP 도구를 지원하는
클라이언트에서 연결하거나 CLI를 직접 실행할 수 있다.

## 설치와 준비

저장소 루트에서 실행한다. 현재 가상환경에는 아래 두 실행 파일을 설치했다.
새 환경에서는 `uv sync --group dev`로 설치한다.

```sh
export BYEORI_ASSISTANT_DATA="$PWD/.byeori-assistant"
.venv/bin/byeori-assistant init --model qwen3:8b --read-root "$PWD"
.venv/bin/byeori-assistant doctor
```

이 작업에서 `.byeori-assistant`를 이미 초기화했다면 `init`은 다시 실행할 필요가 없다.
설정은 `config.json`에 저장하며 재초기화는 기존 설정을 덮어쓰지 않는다.
전역 옵션 `--workspace`는 하위 명령 **앞**에 지정하고, 환경 변수 대신 사용할 수 있다.

기본 설정은 설치된 `qwen3:8b`, context 8192, 출력 상한 2048 token이다.
짧은 업무용 입력에 맞춘 값이며, 장시간 자동 작업의 성능 보장은 아니다.
모델을 자동 다운로드하지 않으며 cloud 모델 또는 외부 Ollama endpoint를 허용하지 않는다.
`doctor`가 `model_locality: local`과 `recovery_pending: false`인지 확인한다.
Ollama 서버 자체의 cloud 비활성화 설정은 별도이며, 기존 런타임과 마찬가지로
`cloud_disable_verification: unverified`로 표시한다.

기본 읽기 범위는 워크스페이스의 `inbox/`이며 `--read-root`로 추가한 폴더만 읽는다.
현재 워크스페이스에는 사용자가 작업을 요청한 이 저장소를 읽기 범위로 추가했다.
다른 메모 폴더를 사용하려면 다음처럼 명시적으로 추가한다.

```sh
.venv/bin/byeori-assistant allow-root /절대경로/작업메모
```

실행 중인 MCP 서버에는 시작 시 읽은 설정이 적용되므로 읽기 범위를 바꾸면 재시작한다.
숨김 파일·숨김 폴더·symlink·생성 결과 폴더는 입력 탐색에서 제외한다.
보고서에 기존 결과를 쓰려면 폴더 탐색 대신 `--task`로 성공한 작업을 지정한다.

## 네 가지 작업 실행

```sh
# 직접 작성한 메모. 폴더도 지정할 수 있다.
.venv/bin/byeori-assistant notes examples/assistant/work-notes.md

# 커밋 제목과 변경 파일 통계. 전체 메시지와 patch까지 읽으려면 --diff를 추가한다.
.venv/bin/byeori-assistant commits "$PWD" --since "7 days ago" --limit 3

# 기본 분류: notes/code/data/documents/images/archives/other
.venv/bin/byeori-assistant classify examples/assistant

# 분류 항목은 직접 정할 수도 있다.
.venv/bin/byeori-assistant classify examples/assistant --category work --category research --category other

# 원자료로 보고서 초안 만들기
.venv/bin/byeori-assistant report examples/assistant/work-notes.md --title "작업 보고서"

# 메모 정리/커밋 요약 결과를 합쳐 보고서 만들기
.venv/bin/byeori-assistant report --task <메모-작업-ID> --task <커밋-작업-ID> --title "주간 보고서"

.venv/bin/byeori-assistant history --limit 10
.venv/bin/byeori-assistant status <작업-ID>
.venv/bin/byeori-assistant read <작업-ID>
```

예시 파일은 기능 확인용 데이터이며 실제 프로젝트의 완료 실적을 나타내지 않는다.
실제 메모는 `.byeori-assistant/inbox/`에 넣거나 허용한 폴더를 직접 지정한다.
Git 요약에는 커밋되지 않은 변경이 포함되지 않는다. 개수 제한으로 범위를 줄인 경우
`limit_reached`로 알리며 기간·commit ID·patch 포함 여부를 실행 기록에 남긴다.
기본 모드는 파일 통계를 snapshot에 보존하되 모델 요약은 제목만 사용한다
(`model_basis: commit_subjects`). 실제 실행에서 모델이 파일명/증감 통계만 보고
파일 내용 삭제나 인증 코드 변경을 추측해, 기본 모드에서 이 추론 경로를 제거했다.
상세 변경 설명은 `--diff`로 patch를 제공한 경우에도 사람이 확인할 초안이다.

## 결과와 실행 기록

`runs/<task_id>/`에 다음 파일을 남긴다. 워크스페이스는 Git에서 제외한다.

- `inputs.json`: 읽은 원자료의 snapshot, 파일 hash, 줄 범위 또는 commit ID.
- `candidate-<번호>.json`: 각 모델 호출의 원래 응답. 검증 실패도 보존한다.
- `result.json`, `result.md`: 검증을 통과한 분류 제안/초안과 입력 출처.
- `receipt.json`: 상태, 입력·출력 hash, 모델·토큰 정보, 실제 호출 payload hash와 batch별 출처.

하나의 입력 창에 들어가지 않으면 작은 batch로 나누어 각각 정리한 결과를 이어 붙인다.
본문을 조용히 잘라 읽거나 요약을 재압축하지 않는다. 각 호출은 직렬 실행하고,
입력 파일 200개·파일당 2 MiB·전체 텍스트 16 MiB·모델 호출 32회 상한을 넘으면
더 작은 범위를 지정하도록 실패한다. 생성 과정에서 모든 source record를 모델에
제공했다는 사실이 모든 사실을 결과에 빠짐없이 옮겼다는 뜻은 아니다.

입력 창 초과 판정에는 기존 보수적인 토큰 추정을 그대로 사용한다. 다만 업무용 JSON/Git
통계 입력은 실제 1,469 token을 3,068로 추정해 논문용 응답 검사(55%)에서 오판했다.
업무 도우미의 응답 토큰 비율 검사는 35%로 따로 설정하고 receipt에 기록한다.
원래 논문 런타임의 55% 설정은 유지한다. 이 비율 검사는 휴리스틱이며 tokenizer를
이용한 정확한 원문 읽기 증명은 아니다.

Ollama의 [구조화 출력](https://docs.ollama.com/capabilities/structured-outputs)에
작업별 JSON schema를 전달하고, 응답의 JSON 구조, 허용한 section/category, 제공한 출처 ID를 검사한다.
파일 분류는 모든 입력을 정확히 한 번씩 분류해야 성공한다.
출처 검사는 사실·수치·완료 여부의 의미적 정확성을 보장하지 않는다.
보고서에 이전 생성 결과를 사용하면 `generated_draft`로 표시하고 원래 작업까지 연결한다.
파일 분류는 텍스트 파일의 처음 일부를 참고하고, PDF·이미지·압축 파일 등은 파일명과
메타데이터로만 제안한다. 해당 파일의 본문이나 이미지 내용을 읽었다고 주장하지 않는다.

CLI 종료 코드는 성공 0, 실행/생성 실패 1, 잘못된 입력 2이다.
중간 프로세스가 종료된 작업은 상태 조회 때 `interrupted`로 표시한다.
자동 재실행하지 않으므로 동일 입력으로 새 작업을 제출한다.
Ollama 호출이 끝났는지 불명확하면 기존 공용 runtime 표식으로 후속 추론을 막는다.
서버의 이전 요청 종료를 직접 확인한 다음 해제한다.

```sh
.venv/bin/byeori-assistant recover-runtime --acknowledge-idle
```

예약 실행, 상시 감시, 메신저 연결, 파일 자동 이동은 현재 구현 범위에 포함하지 않는다.
현재 단계는 네 가지 작업을 CLI/MCP에서 직접 제출해 사용하고 실제 유용성을 확인하는 것이다.

## MCP 연결

클라이언트의 MCP 설정에 실제 절대 경로를 넣는다.

```json
{
  "mcpServers": {
    "byeori-assistant": {
      "command": "<저장소>/.venv/bin/byeori-assistant-mcp",
      "env": {
        "BYEORI_ASSISTANT_DATA": "<저장소>/.byeori-assistant"
      }
    }
  }
}
```

현재 가상환경과 워크스페이스의 절대 경로가 들어간 설정을 출력할 수도 있다.
워크스페이스에 이 설정을 `mcp.json`으로 저장해 두었다.

```sh
.venv/bin/byeori-assistant mcp-config
```

도구는 `organize_notes`, `summarize_commits`, `classify_files`, `draft_report`,
`get_task`, `list_tasks`, `read_task_result`이다.
한 서버에서 기다리는 작업은 최대 8개이며, 생성은 워크스페이스당 하나씩 실행한다.
서버가 종료되면 그 서버의 대기·실행 작업은 자동 재개하지 않는다.
클라이언트가 cloud 모델을 사용하는 경우 반환된 자료는 그 클라이언트에 전달된다.
로컬 추론 설정과 호출 클라이언트의 모델 설정은 별개다.

## 검증

```sh
.venv/bin/python -m pytest tests/test_local_assistant.py
```

회귀 테스트는 원본 보존, 텍스트 전체 batch 전달, 출처/분류 누락 거부, 읽기 범위,
snapshot 및 결과 hash, 이전 초안의 보고서 연결, 로컬 Git 범위, background 작업을 확인한다.
실제 모델 생성 확인 결과는 아래 실행 기록에 별도로 남긴다.

## 실제 실행 확인: 2026-10-01~02

Apple M4 / 16 GiB, Ollama 0.34.4, `qwen3:8b` Q4_K_M에서 네 작업의 로컬 생성과
결과 저장을 확인했다. 각 행은 작은 입력을 한 번 실행한 기록이며 성능 benchmark가 아니다.
시간은 receipt의 실행 시작~완료를 기준으로 한다.

| 작업 | 확인 입력 | 상태 | 시간 | 작업 ID |
|---|---|---|---|---|
| 메모 정리 | 예시 메모 1개 | 성공 | 15.73초 | `e9be38e1a9164c9286c972bf60195466` |
| 커밋 요약 | 실제 저장소의 최근 커밋 3개 제목 | 성공 | 6.48초 | `1fcb01d3664e4d6ba4e68df32dcded2b` |
| 파일 분류 | 예시 메모·CSV 2개 | 성공 | 8.47초 | `7bfb11cf0173459c96d2460728c1837e` |
| 보고서 초안 | 메모·커밋 요약 작업 2개 | 성공 | 27.58초 | `0e3b655f21784a43b18e92d0c1687469` |

MCP 실행 파일을 별도 stdio 프로세스로 시작해 7개 도구 목록 조회와 저장된 결과 읽기도
확인했다. 전체 테스트는 **2,459개 통과, 1개 skip**이며 신규 업무 도우미 테스트는 32개다.
실제 사용 설정은 `.byeori-assistant/config.json`, MCP 클라이언트 설정은
`.byeori-assistant/mcp.json`, 결과는 `.byeori-assistant/runs/<task_id>/result.md`에 있다.

실행 중 확인한 JSON 형식 오류, 파일 분류 누락, placeholder 이유, Git 통계로부터의
과도한 추론, 토큰 검사 오판, 이전 초안의 출처 번호 혼동을 코드/검사/prompt에 반영했다.
실패한 실행 기록도 워크스페이스에 보존했다.

**생성 성공은 정확성 인증이 아니다.** 최종 커밋 요약에서도 `eleven papers`를 옮기는
과정에 한국어·중국어 표현이 섞인 사례가 있고, 메모의 일부 내용이 요약에서 빠졌다.
보고서는 입력 초안의 표현 오류를 그대로 옮길 수 있다. 검토할 수 있는 원래 커밋 제목과
자료 경로를 결과에 함께 제공하며, 숫자·완료 여부·중요한 할 일은 사람이 확인한다.
이 기능은 검토 가능한 업무 초안을 만드는 단계까지 구현됐다.
