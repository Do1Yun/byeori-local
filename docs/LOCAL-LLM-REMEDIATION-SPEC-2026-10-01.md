# byeori-local 수정·안정화 명세서

작성일: 2026-10-01. 기준 코드: `a9228f0`. 원본 비교 기준: `30a3045`.

근거 문서는 [로컬 LLM 전환 검토](LOCAL-LLM-REVIEW-2026-10-01.md), [현재 개발 안내](LOCAL-DEVELOPMENT.md), [11편 평가](evaluation/README.md)다. 이 문서는 **앞으로 구현할 요구사항과 수용 기준**이며, 아래 설계가 이미 구현되었다는 뜻은 아니다. 별도로 표시한 실행 결과만 이번 확인에서 검증했다. 명령·설정·스키마 중 `신규` 또는 `제안`으로 표시한 항목도 현재 사용할 수 있는 기능으로 간주하면 안 된다.

후속 구현: 사용자의 진행 지시를 받아 같은 날 1차 안정화를 적용했다. **본문의 현황은 작성 당시 snapshot이며, 작업 트리에 적용된 변경과 실제 사용 가능한 신규 기능은 마지막 22절에서 구분한다.** HEAD는 아직 `a9228f0`이고 이번 구현은 미커밋 상태다.

**당장 필요한 것은 모델 교체보다 작업 누락, 상태 불일치, 근거 범위, 무결성을 수정하는 일이다. M4/16GiB에서는 8B 모델의 직렬 처리와 원문을 선택적으로 읽는 질문 흐름을 우선한다. 대형 모델 동시 실행이나 검토 없는 과학적 정확도 보장을 목표로 잡지 않는다.**

## 1. 현재 진행상황과 확인 범위

### 1.1 코드·평가 상태

| 항목 | 현재 확인 결과 | 해석 |
| --- | --- | --- |
| HEAD | `a9228f0` | 앞선 검토 이후 구현 커밋 없음 |
| 작업 트리 | 검토 문서와 재현 스크립트가 미추적 파일로 존재 | 검토 이후 수정이 적용된 상태는 아님 |
| 로컬 테스트 | `test_local_integrity.py`, `test_local_runtime.py`: **106 passed** | 현재 테스트의 성공이며 아래 결함의 해소를 뜻하지 않음 |
| 전체 테스트 | 앞선 검토에서 2,395 passed, 1 skipped | 이번 명세 작성에서는 전체 테스트를 다시 실행하지 않음 |
| 결함 재현 | [재현 스크립트](reviews/local-runtime-repro-2026-10-01.py)를 다시 실행; R01~R11 동작 유지 | 모두 미해결로 계획에 포함 |
| 기존 모델 평가 | 11편, 208개 평가 항목, 보조 판정상 결함 47개 | 사람 검증을 마친 오류율이 아님; supported 148개도 확정 정답 아님 |
| 원본과의 차이 | 자동 원문 재독, Concept·Overview, 지속 worker, 재개·복원 미구현 | Evidence Note의 로컬 생성 기반까지 진행된 상태 |

이번에 실행한 검증:

```text
.venv/bin/python -m pytest tests/test_local_integrity.py tests/test_local_runtime.py -o addopts='' -q
.venv/bin/python docs/reviews/local-runtime-repro-2026-10-01.py
```

실제 논문 재생성, 새 모델 다운로드, OCR 설치, 서비스 설정 변경은 수행하지 않았다. 실제 사용자 워크스페이스의 DB도 열거나 변경하지 않았다. 현재 에이전트 환경의 `BYEORI_LOCAL_DATA`, `BYEORI_LOCAL_MODEL`, 문맥·출력 설정은 미설정이므로, 사용자의 다른 셸/MCP 설정이나 전체 논문 수를 추정하지 않는다.

### 1.2 실제 장비·서비스 상태

| 항목 | 조회로 확인한 값 | 주의점 |
| --- | --- | --- |
| 호스트 | Apple M4, `Mac16,10`, arm64, 통합 메모리 17,179,869,184 bytes = **16GiB** | 시스템·GPU·VM이 같은 물리 메모리 예산을 사용 |
| Ollama | 서버 조회 버전 **0.34.4** | 최신 문서의 기능은 이 버전에서 지원 여부를 확인해야 함 |
| 설치 모델 | `qwen3:8b`, Q4_K_M, 8.2B; 목록 표시 5.2GB | 표시 크기는 저장 용량이며 실행 메모리와 다름 |
| 모델 문맥·기능 | `ollama show`: 40,960토큰, completion/tools/thinking | 현재 설치 모델에서 vision 기능은 확인되지 않음 |
| 모델 상주 | 조회 시 `ollama ps` 목록 없음 | 현재 작업 부하의 메모리·속도를 측정한 결과가 아님 |
| Colima | default 프로필 Running, aarch64, CPU 4개, VM 6GiB | VM 할당량을 전부 실사용량으로 계산할 수는 없지만 큰 예산을 예약 |
| GROBID | `grobid/grobid:0.9.1-crf`, 컨테이너 실행 중 | VM 아키텍처만으로 이미지가 네이티브 ARM이라고 단정하지 않음 |
| OCR | 호스트 PATH에 `tesseract` 실행 파일 없음 | 컨테이너 내부·다른 경로 설치 여부는 미확인; 즉시 사용할 OCR 경로는 미검증 |
| Python 패키지 | PyMuPDF 1.28.2, httpx 0.28.1, mcp 1.30.0 | 텍스트·표 추출 대안은 기존 PyMuPDF를 활용 가능 |

개발 문서의 15쪽 110~180초, chunked 약 9분, 질문 42~70초와 커밋의 70분 이상 처리·장시간 실패는 **기존 기록**이다. 이번 조회로 같은 성능을 재검증하지 않았다. 특히 설치 파일 크기, VM 할당량, 프로세스 RSS를 단순 합산해 실제 통합 메모리 사용량으로 제시하지 않는다.

## 2. 수정 범위와 보존 계약

수정 범위는 `src/byeori/local/`, 로컬 테스트, 로컬 문서다. 원본 AWS 명령·인프라·테스트는 유지한다. 원본의 순수 검색·식별·근거 선택 로직은 재사용하되, 로컬 경로에서 AWS 클라이언트를 초기화하지 않는다. 이 경계는 [CLAUDE.md의 로컬 개발 예외](../CLAUDE.md)에 따른다.

다음은 모든 단계의 필수 계약이다.

1. 원본 PDF, 과거 추출, 노트 revision, 검토 이력은 삭제하거나 제자리 덮어쓰지 않는다.
2. 실패한 재생성이 기존 활성 노트·검색 결과를 교체하지 않는다.
3. 문헌의 사실 주장에는 모델에 실제 제공한 원문 또는 검증 가능한 근거 연결이 있어야 한다.
4. `job.succeeded`, 노트 게시, 형식 검증, 사람 검토, 의미적 정확도는 각각 구분한다.
5. cloud 모델과 자동 cloud fallback을 금지한다. 외부 메타데이터 조회는 별도 설정이다.
6. 기본 읽기·검색·점검은 원본을 변경하지 않는다. 복구·재색인은 명시적 작업으로 수행한다.
7. 현재 장비에서 검증하지 않은 모델·추출기·문맥 설정을 기본 운영 프로필로 승격하지 않는다.

## 3. 현재 환경의 가능 범위와 검색한 대안

`가능`은 설계·구현 가능한 범위, `조건부`는 실장비 검증 후 채택, `불가능`은 해당 행의 고정 조건에서 요구를 충족할 수 없다는 뜻이다. 미검증을 불가능으로 바꾸거나, 보장이 불가능하다는 이유로 보조 기능 자체를 폐기하지 않는다.

| 요구 | 판단 | 대체 방안과 채택 조건 |
| --- | --- | --- |
| 현재 8B로 노트·제한된 질문 처리 | **가능** | 기존 실행 사례 있음. 추출·추론 직렬화, 짧은 근거 묶음, 체크포인트를 우선 구현 |
| GROBID와 8B를 항상 상주시켜 장시간 운영 | **조건부; 기본값으로 부적절** | 단계별 자원 전환 또는 PyMuPDF 사용. 압력·swap·실패율을 측정한 뒤 동시 상주 여부 결정 |
| 더 작은 GROBID VM | **조건부** | CRF 단일 요청으로 4GiB VM을 실험. 공식 문서는 fulltext 처리에 4GB 이상을 권하지만 현 논문 성공·속도를 보장하지 않음. [GROBID Docker 안내](https://grobid.readthedocs.io/en/latest/Grobid-docker/) |
| Docker 없이 PDF 텍스트·텍스트 표 추출 | **가능; 품질 별도 검증** | 기존 PyMuPDF의 blocks/words 좌표와 `find_tables` 사용. 두 단 읽기 순서·복잡한 표·학술 헤더 정확도는 보장하지 않음. [PyMuPDF 텍스트·표 추출](https://pymupdf.readthedocs.io/en/latest/recipes-text.html) |
| 스캔 PDF 처리 | **조건부** | Tesseract 설치 후 페이지별 직렬 OCR. OCRmyPDF를 쓰면 jobs=1과 이미지 크기 제한 검토. OCR 오류·미처리 페이지를 공개하고 원본과 파생 PDF를 분리. [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html), [OCRmyPDF 자원 조절](https://ocrmypdf.readthedocs.io/en/latest/performance.html) |
| 14B로 일부 어려운 주장 검토 | **조건부 실험** | `qwen3:14b` Q4_K_M은 공식 표시 9.3GB. VM을 해제한 상태에서 8K 문맥부터 측정; OOM·swap·정확도 개선을 검증. 8B보다 낫다고 사전 확정하지 않음. [모델 정보](https://ollama.com/library/qwen3:14b) |
| `qwen3:32b` Q4_K_M의 모든 가중치·KV를 16GiB에 상주시켜 GPU 추론 | **불가능: 이 양자화·상주 조건** | 공식 표시 가중치만 약 20GB. 현재 8B, 조건부 14B, 또는 메모리가 큰 별도 로컬 장비를 사용. 낮은 양자화·offload·swap 실행의 존재가 이 상주 조건을 만족시키지는 않음. [모델 정보](https://ollama.com/library/qwen3:32b) |
| 여러 모델/여러 긴 요청을 동시에 안정 운영 | **현재 기본 운영으로 수용 불가** | endpoint별 추론 1개, 추출 1개. 동시성은 더 큰 장비에서 별도 평가한 경우에만 허용 |
| macOS Docker GROBID의 CUDA GPU 경로를 M4 GPU로 실행 | **불가능: 현재 공식 Docker GPU 경로** | CRF CPU 추출 또는 호스트 PyMuPDF. Linux/NVIDIA 환경 전환은 현재 장비 내 대안이 아님. [GROBID GPU 요구](https://grobid.readthedocs.io/en/latest/Grobid-docker/) |
| 모든 긴 논문·무제한 논문 집합을 한 prompt로 제공 | **불가능: 유한 문맥 조건** | 페이지·절 분할, 구조화 주장 저장, 검색과 원문 재독. 문맥 증가도 메모리를 늘리므로 전체 저장소를 넣는 방식으로 해결하지 않음. [Ollama 문맥 안내](https://docs.ollama.com/context-length) |
| 이미지 표·그래프 읽기 보조 | **조건부** | 텍스트 표/원 데이터 우선; 필요한 crop만 OCR 또는 `qwen3-vl:4b`로 시험. 공식 모델은 Q4_K_M 약 3.3GB이나 실행 메모리·논문 수치 품질은 미검증. text 모델 해제 후 단독 실행. [시각 모델 정보](https://ollama.com/library/qwen3-vl:4b) |
| 원 데이터·명시적 숫자가 없는 그래프에서 저자 보고 수치를 항상 정확히 복원 | **불가능: 정확값 보장 조건** | 보충자료·원 데이터·캡션의 보고값을 찾는다. 없으면 추정임을 표시하거나 `unavailable`로 남긴다. OCR/VLM/수동 digitization도 원래 정확값의 증명이 되지 않음 |
| 현재 8B가 원본 모델과 같은 과학적 정확도를 보장 | **보장 불가능; 동등성 미검증** | 동일 논문·동일 추출·사람 판정 비교가 필요. 현재 평가로 원본 대비 우열도 단정할 수 없음 |
| 무인 운영에서 모든 과학적 주장 100% 자동 승인 | **보장 불가능: 현재 근거·평가·모델 계약** | 코드로 확인 가능한 오류 차단, 수치·조건 검토표, 사람 승인. JSON schema나 더 큰 모델도 의미적 정확도의 증명으로 취급하지 않음 |
| 현재 HTTP 계약으로 job 한 건의 GPU 추론을 즉시 강제 중단하면서 다른 요청 보호 | **지원 불가: 현재 구현/계약** | soft cancel과 단계 경계 취소를 제공. 별도 전용 worker/backend의 취소 지원을 검증해야 즉시 중단을 약속할 수 있음 |

GROBID 문서는 이미지 크기와 런타임 메모리를 구분해야 한다. CRF 이미지가 약 500MB라는 설명을 “GROBID가 메모리 500MB만 쓴다”로 바꾸지 않는다. ARM 설명과 예제에 차이가 있으므로 현재 이미지의 architecture와 digest를 직접 확인하고, emulation 유무까지 성능 기록에 포함한다. [GROBID 공식 안내](https://grobid.readthedocs.io/en/latest/Grobid-docker/)

### 3.1 자원 프로필 제안

아래 숫자는 **실험 시작값**이며 새 성능 측정으로 확정한 값이 아니다.

| 프로필 | 모델·문맥 | 출력 상한 | 사용 조건 |
| --- | --- | --- | --- |
| `m4-16g-balanced` | 현재 `qwen3:8b`, 16,384 | digest/질문 2,048, 최종 노트 4,096 | 첫 기본 후보; 추출과 추론 자원 분리 |
| `m4-16g-low-memory` | 같은 모델, 8,192 | digest/질문 1,024~2,048 | 압력 발생 시 더 작은 근거 묶음으로 재계획; 조용히 입력 절단 금지 |
| `m4-16g-long-context` | 같은 모델, 32,768 | 4,096 | 추출 VM을 해제한 환경의 실측을 통과한 뒤 명시 선택 |
| `m4-16g-14b-experiment` | 별도 설치 14B, 8,192부터 | 2,048 | 기본 운영 제외; VM 해제·품질/메모리 비교 필요 |

현재 코드 기본값은 32,768/4,096이다. 기본값을 바꾸기 전 선택된 프로필·실제 옵션을 `doctor`와 receipt에 출력하고, 기존 명시적 CLI/MCP 설정은 존중한다. 어떤 경우에도 현재 모델의 40,960을 넘어 자동 증설하지 않는다. 전체 관리 작업의 메모리 예산을 약 12GiB 이하로 시작하고 나머지를 시스템에 남기는 정책을 시험하되, 이는 측정 전 설계 목표다. 실제 memory pressure와 swap 증가를 우선 판단한다.

Ollama 서버는 `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`을 운영 후보로 삼는다. Flash Attention 지원 여부를 확인하고 KV cache `q8_0`을 비교 실험할 수 있다. `q8_0`의 약 절반 절감은 KV cache에 관한 설명이며 전체 RAM 절반 절감이 아니다. `q4_0`은 품질 손실 검증 없이 기본화하지 않는다. [Ollama 자원 설정](https://docs.ollama.com/faq)

연속 digest 동안에는 모델을 유지하고, 추출 단계로 전환할 때는 관리 중인 요청의 종료를 확인한 뒤 unload한다. `keep_alive: 0`은 응답 후 해제를 지원한다. **GROBID 컨테이너 정지와 Colima VM 정지는 다르다.** 공유 default VM은 자동으로 정지하지 않고 `waiting_resource`로 기다리거나 PyMuPDF 경로를 선택한다. 자동 전환은 byeori 전용으로 소유권이 설정된 VM/모델에만 허용한다. [Ollama 모델 유지·해제](https://docs.ollama.com/faq)

## 4. 우선순위와 변경 대상

검토의 P1/P2를 유지하되 R07·R08과 중복 제거는 초기 안정화에 함께 포함한다.

| 작업 | 요구 | 주요 변경 파일 | 완료 판단 |
| --- | --- | --- | --- |
| S01 / R10 | 중복 제거·수정 위치 명확화 | `service.py`, 추출/검증 분리 모듈 | 동일 동작, 중복 정의 0 |
| S02 / R01 | 제한 없는 내부 순회·페이지네이션 | `store.py`, `service.py`, `cli.py`, `mcp_server.py` | 101편 이상 누락 없음 |
| S03 / R02 | 확정 메타데이터 보존 | `metadata.py`, `service.py`, `store.py` | 실패/비활성 조회가 값을 지우지 않음 |
| S04 / R03 | 작업 수명·직렬 실행 | `jobs.py`, `locking.py`, `store.py`, `llm.py` | 종료 경쟁·다중 프로세스 동시 호출 차단 |
| S05 / R04 | 호출별 제공 근거 검증 | `service.py`, `llm.py`, `audit.py` | 미제공·생략 근거의 인용 거부 |
| S06 / R05 | 파일 해시 검증 | `store.py`, `service.py`, `cli.py` | 변경 파일을 탐지하고 답변 사용 차단 |
| S07 / R06 | 추론 위치 검증 | `llm.py`, `cli.py`, 문서 | remote/cloud 표식 거부; 검증 상태 출력 |
| S08 / R07 | 실행·게시 receipt 분리 | `service.py`, `store.py` | DB 실패에 성공 receipt 없음 |
| S09 / R08 | 근거별 판정 이력 | `cli.py`, `audit.py`, `store.py` | 달라진 근거에 승인 재사용 없음 |
| S10 / R09 | 표·전체 사실 주장 평가 | `service.py`, `audit.py`, 평가 문서 | 표·인용문·요약의 주장 포함 |
| S11 / R11 | CLI 종료 코드 계약 | `cli.py` | 실패/부분 실패를 자동화가 식별 |
| S12 | 구조화 주장·원문 재독 | 근거/질문 모듈, `llm.py` | 수치의 지표·조건·원문 연결 보존 |
| S13 | 체크포인트·백업·복원 | worker/저장 모듈, CLI | 장애 후 재개·새 디렉터리 복원 검증 |
| S14 | 문서·평가 정합성 | `LOCAL-DEVELOPMENT.md`, README, 평가 | 구현/실측/미구현 구분 |
| S15 | Concept·Overview | 별도 종합 모듈 | 검토 가능한 노트 기반, revision 의존성 추적 |

## 5. R01 — 전체 작업 조회와 페이지네이션

현재 `LocalStore.papers()`의 최근 100편 제한을 `pending`, `process_all`, `refresh_all`이 함께 사용한다. `revalidate_all`의 200 job, orphan 탐색의 1,000 job 제한도 운영 대상의 상한이 되어 있다.

**변경 규칙**

- UI/MCP 목록은 `limit`(기본 50, 최대 100), `cursor`, `next_cursor`를 제공한다. 기존 `list_papers`/`list_jobs` 결과 키는 유지하고 새 필드를 추가한다.
- cursor는 정렬 키 `(created_at, paper_id 또는 job_id)`와 필터를 고정한다. 같은 시간의 자료도 중복·누락되지 않게 식별자를 tie-breaker로 사용한다.
- 내부 일괄 작업은 DB에서 미처리/재검증 조건을 직접 조회한다. 화면용 목록 API를 사용하지 않는다.
- batch 시작 시 대상 snapshot 또는 watermark를 기록한다. 실행 중 추가된 논문은 다음 batch 대상으로 명시한다. 대상 하나를 마친 뒤 다시 첫 100개만 읽는 방식은 금지한다.
- 게시 전 최신 활성 상태를 다시 확인해 다른 작업이 완료한 대상을 중복 처리하지 않는다. 상태 집계는 같은 대상 집합을 기준으로 `total/processed/failed/skipped/remaining`을 반환한다.
- orphan 복구와 전체 재검증도 cursor/직접 쿼리로 끝까지 순회한다. 페이지 크기는 메모리 조절 수단일 뿐 총 처리 한도가 아니다.

**수용 기준**: 101편 중 마지막 오래된 1편이 반드시 처리되고 pending=0이 된다. 1,001개 이상 job에서 가장 오래된 orphan을 찾는다. 같은 timestamp, 중간 삽입, 일부 실패, 재실행, 여러 페이지에 대한 중복/누락 검사를 포함한다.

## 6. R02 — 메타데이터 갱신과 문서 식별자

현재 `_refresh()`가 과거 TEI에서 시작하므로 조회 실패가 기존 year/work ID를 지운다. `OpenAlexLookup`의 HTTP 오류도 미발견으로 합쳐진다.

**필드별 병합 규칙**

1. 사람이 명시적으로 정정한 값은 외부 재조회가 바꾸지 않는다.
2. 기존 확정값을 시작점으로 삼고, 승인된 새 값으로 빈 필드를 채운다. 충돌은 `disagreements`와 후보로 기록한다.
3. `disabled`, `not_found`, `unavailable`, `rate_limited`는 확정값의 삭제 사유가 아니다. 마지막 성공 값과 확인 시간을 보존한다.
4. 값 삭제는 별도의 명시적 `clear` 요청과 이유가 있어야 한다. 빈 응답을 삭제 요청으로 해석하지 않는다.
5. `publication_year`, `preprint_year`, `version_date`를 구분한다. PDF 버전 날짜만 알면 출판 연도를 추측하지 않는다. 기존 `year`는 표시 정책에 따라 계산하고 그 출처를 기록한다.
6. 필드마다 `value/source/checked_at/authority/manual_override`를 저장한다. 노트·검색·메타데이터 revision은 같은 확정값을 사용한다.

OpenAlex key는 설정 가능하게 추가하되 secret을 로그·receipt에 기록하지 않는다. 무키 조회도 지원하고, 429는 제한된 backoff, 5xx/네트워크는 `unavailable`, 정상 빈 응답은 `not_found`로 구분한다. 마지막 성공 응답은 캐시한다. API key가 필수라거나 mailto만으로 처리량이 보장된다는 문구를 쓰지 않는다. [OpenAlex 공식 인증·제한 안내](https://help.openalex.org/api/authentication/)

PDF SHA 기반 paper ID와 게시된 revision ID는 고정한다. 이미 공개한 stem을 변경할 때는 `old_stem → paper_id` alias를 보존하고 다른 논문에 재할당하지 않는다. 현재의 `0000` 정정 사례도 alias로 연결한다. 과거 인용은 revision/extraction을 따라 계속 해석되어야 한다. 자동으로 stem을 계속 바꾸는 정책은 피한다.

메타데이터만 정정하는 revision은 모델 본문을 재생성하지 않는다. 프론트매터와 코드가 생성한 Document Information만 갱신하고 변경 이유를 남긴다. 조회 상태만 변했을 때 동일 본문 revision을 남발하지 않는다.

**수용 기준**: 확정 2021/work ID 상태에서 lookup off, 404/빈 결과, 429, 5xx를 각각 주입해 값이 유지된다. 수동 정정과 새 후보의 충돌을 보존한다. 검색 연도·표시 연도·alias·과거 revision 인용이 함께 검증된다.

## 7. R03 — 작업 소유권·취소·자원 직렬화

### 7.1 최소 수정과 지속 worker

현재의 “빈 큐를 본 worker가 종료하는 사이 submit” 경쟁을 먼저 고친다. 큐 확인·worker 종료 결정·새 submit 알림을 동일 `Condition`/잠금 아래 관리한다. idle worker를 유지하는 경우에는 명시적 shutdown을 제공한다. daemon thread는 제출 프로세스보다 오래 살지 못하므로 지속 실행 보장으로 설명하지 않는다.

후속 단계에 `byeori-local worker`를 **신규**로 추가한다. DB 큐가 요청의 소유자이고 CLI/MCP는 제출·조회한다. 기존 foreground `process`/`ask`도 같은 dispatcher를 사용한다. worker가 없으면 `queued`와 `worker_unavailable` 진단을 반환하며 성공 결과로 위장하지 않는다.

`jobs`에 `worker_id`(UUID), `attempt_id`, `heartbeat_at`, `started_at`, `cancel_ack_at`를 추가한다. 짧은 트랜잭션의 원자적 claim으로 한 worker가 소유하고, 이후 상태 변경은 worker/attempt가 모두 일치할 때만 허용한다. PID는 진단 정보이며 소유권의 증거로 사용하지 않는다.

```text
queued → running → succeeded | failed | cancelled | interrupted
running.stage = waiting_resource | extracting | digesting | writing | validating | publishing | answering
```

stale heartbeat만으로 살아 있는 worker의 작업을 재할당하지 않는다. OS 잠금과 프로세스 상태를 함께 확인하고, 이전 attempt의 지연 응답은 fencing 조건으로 게시를 차단한다. 잠금 소유 여부를 확인할 수 없으면 `recovery_pending` 진단을 남긴다. 모델 호출·파일 읽기 동안 SQLite write transaction을 유지하지 않는다.

### 7.2 모든 추론 경로에 하나의 잠금

노트 처리용 `.worker.lock`과 별개로, **동일 Ollama endpoint의 모든 byeori 호출**에 프로세스 간 잠금을 적용한다. 노트·digest·질문·검색어 번역·audit·메타 작업 중 모델 호출이 대상이다. 모델 이름별 잠금은 서로 다른 모델의 동시 상주를 막지 못하므로 endpoint 기준으로 만든다.

복수 워크스페이스도 같은 잠금을 보도록 `BYEORI_LOCAL_RUNTIME_DIR`를 **신규** 설정으로 둔다. 기본은 동일 사용자의 공용 로컬 runtime 디렉터리이고, 정규화한 endpoint 해시를 잠금 키로 쓴다. localhost/127.0.0.1/::1 alias는 같은 서버로 정규화한다. 프로세스 내부에는 추가 thread lock을 적용한다. 설정 경로가 서로 다르면 전역 직렬화가 보장되지 않음을 doctor가 알린다.

기본은 FIFO다. 긴 논문이 모든 질문을 장시간 막지 않도록 digest 경계에서 자원을 양보할 수 있지만, 최종 게시 트랜잭션 안에서는 양보하지 않는다. 질문 우선 정책을 추가하면 aging으로 오래된 논문의 기아를 방지한다. 다른 앱의 Ollama 사용까지 byeori 파일 잠금이 통제한다고 설명하지 않는다.

### 7.3 취소·타임아웃 계약

- queued 취소는 모델 호출 없이 `cancelled`, `cancel_ack_at`을 확정한다.
- running 취소는 `cancel_requested=true`, `stopped=false`를 반환한다. 호출이 돌아오거나 검증된 중단이 확인된 뒤만 `cancelled`, `stopped=true`가 된다.
- 호출 사이와 게시 직전 취소를 확인한다. 취소 이후 결과는 활성 노트/답변으로 게시하지 않고 산출물 이력만 보존한다.
- 현재 backend의 즉시 GPU 중단은 지원하지 않는다. 한 job을 취소하기 위해 공유 Ollama 서비스나 다른 앱의 모델을 강제 정지하지 않는다.
- HTTP timeout은 “서버 계산이 끝났다”는 뜻이 아니다. `outcome_unknown`을 기록하고 같은 요청을 즉시 재시도하지 않는다. `/api/ps`의 모델 상주 정보만으로 요청 종료를 판단하지 않는다.
- 종료를 확인할 방법이 없으면 endpoint를 `recovery_pending`으로 막고 관리자의 확인 또는 전용 backend 재시작 절차로 복구한다. 이 경우 자동 복구가 불완전하다는 제한을 표시한다.
- `think` 옵션 미지원이 확인된 경우에만 옵션 제거 재시도를 허용한다. 현재의 모든 `ModelError`에 대한 재시도는 폐지한다. timeout/5xx/잘린 출력은 각각 별도 오류다.

**수용 기준**: 종료 경쟁은 barrier를 둔 결정적 테스트로 재현·차단한다. 서로 다른 프로세스/워크스페이스에서 노트·질문·audit를 제출해 모델 호출의 최대 동시 수가 1인지 확인한다. PID 재사용, stale heartbeat와 살아 있는 잠금, 취소 직후 응답, timeout 후 재시도, 오래된 attempt의 게시를 검사한다.

## 8. R04 — 모델에 제공한 근거와 인용 범위

모든 모델 호출에 `EvidencePacket`을 만든다. packet은 `packet_id`, paper/revision/extraction ID, 실제 제공한 block ID와 hash, 발췌 범위, 생략 사유를 가진다. 파일에 문단이 존재한다는 사실과 모델이 그 문단을 받았다는 사실을 분리한다.

노트만 제공한 질문의 최초 허용 범위는 노트에 명시된 근거 연결이다. 새 수치나 조건을 원문 사실로 반환하려면 해당 원문 block을 추가 제공한다. `_paragraphs()`에서 추출 JSON의 모든 ID를 허용 집합으로 반환하는 동작은 제거한다. 답변·audit의 코드 검증은 해당 호출 packet만 사용한다.

chunked 생성에서는 part별 `provided_ids`, 구조화 digest별 `retained_evidence_ids`, `omitted_ids`를 저장한다. 최종 노트가 인용할 수 있는 범위는 **최종 입력의 주장/근거 레코드에 유지된 ID**다. 처음에는 제공했지만 digest에서 사라진 ID도 최종 단계에서 자유롭게 인용할 수 없다. 원문을 다시 제공하면 새 packet을 만든다.

실패 블록을 개수 10% 이하라는 이유로 자동 생략하는 정책은 바꾼다. 결과·방법·한계·표의 실패는 `coverage_incomplete`로 처리하고 재분할·재추출 또는 검토 필요 draft로 남긴다. 초록만 있어 `complete`로 분류되는 문제도 수정한다. 참조문헌 등 정책상 제외 가능한 블록은 제외 이유를 기록한다. `provided coverage=100%`를 핵심 사실 보존률 또는 의미적 완독의 증거로 쓰지 않는다.

**수용 기준**: P0001만 제공한 답변의 P0002 인용은 거부한다. P0007 digest 실패 뒤 P0007을 인용한 candidate는 게시하지 않는다. 알고 있는 ID라도 packet에 없으면 실패한다. block 개수가 적어도 핵심 결과가 생략되면 complete 게시가 불가하다.

## 9. R05 — 무결성 검증과 사용 차단

기존 `note_sha256`은 실제 노트 bytes와 대조한다. 추출에는 TEI hash와 별도로 **문단 JSON 자체의 `document_sha256`**을 저장한다. PDF → 추출 산출물 → revision → 검색 문서 → 답변 인용의 hash 연결을 확인한다.

| 검사 | 기본 동작 | 오류 시 동작 |
| --- | --- | --- |
| 노트 읽기/답변 선택 | 읽은 bytes와 revision hash 비교 | 해당 revision 사용 차단, 무결성 오류 반환 |
| 원문 문단 읽기 | JSON 파일 hash와 extraction record 확인 | 답변·audit 근거 사용 차단 |
| 기본 `check` | 활성 노트/추출 hash, 포인터·FTS·job 참조 확인 | 경로·expected/actual·문제 유형 출력 |
| **신규** `check --deep` | 모든 원본·추출·과거 revision·checkpoint·alias·receipt 순회 | 전체 보고; 파일 자동 삭제 금지 |
| **신규** `reindex` | 검증된 활성 revision에서 FTS 재구축 | tampered 자료 제외, 제외 이유 출력 |

불일치 파일은 원위치에서 덮어쓰지 않는다. 수정 후보/격리 복사본과 진단을 보존하며, 복구 전 검색에서도 손상 revision의 내용이 답변에 들어가지 않게 한다. 전체 점검 중 변경이 감지되면 일관성 있는 snapshot으로 재검사한다.

기존 문단 JSON에 hash가 없으면 `integrity_status=legacy_unverified`로 표시한다. 마이그레이션 시 현재 bytes의 hash를 기준선으로 등록할 수는 있지만, 과거 내용이 바뀌지 않았음을 검증했다고 기록하지 않는다. 중요한 기존 노트는 원본으로부터 새 추출과 검토를 수행한다.

**수용 기준**: 노트 수치를 28.4→99.9로 바꾸면 `check`와 읽기에서 탐지한다. JSON 한 글자 변경, 원본 교체, 잘못된 revision/extraction 연결, FTS에만 남은 손상 내용을 검사한다. 로컬 파일과 DB를 동시에 변조할 수 있는 관리자에 대한 위변조 불가능성은 이 hash 설계가 보장하지 않는다.

## 10. R06 — 로컬 추론 위치 검증

기본 endpoint는 literal loopback으로 제한한다. loopback이 아닌 서버는 **신규 명시 옵션**으로 허용하고 doctor/receipt에 `explicit_remote_endpoint`를 표시한다. 이는 LAN의 로컬 추론 장비도 현재 기계 밖이라는 사실을 드러내기 위한 구분이다. redirect와 endpoint 변경은 다시 검증하며, 모델 tag만으로 실행 위치를 판단하지 않는다.

`/api/tags`의 선택 모델 digest와 remote 표식을 확인하고, `/api/show`에서 capabilities·template·context metadata를 기록한다. 현재 공식 OpenAPI의 `ModelSummary`에는 `remote_model`, `remote_host`가 있다. 해당 값이 있으면 local-only 모드에서 추론 전에 거부한다. cloud 명칭의 알려진 모델도 차단하되 이름 검사만을 유일한 방어로 삼지 않는다. 최신 명세와 현재 0.34.4의 응답 차이는 fixture로 확인한다. [Ollama 공식 OpenAPI](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml)

Ollama **서버**에 `disable_ollama_cloud: true` 또는 `OLLAMA_NO_CLOUD=1`을 적용하고 재시작해야 한다. byeori 클라이언트에 변수만 지정해서 기존 서버가 바뀐다고 설명하지 않는다. doctor는 `endpoint_policy`, `model_locality`, `cloud_disable_verification=verified|unverified`를 구분한다. 확인할 수 없는 설정은 녹색 확정으로 표시하지 않는다. [Ollama cloud 비활성화](https://docs.ollama.com/faq)

신뢰하지 않는 HTTP proxy/server가 실제로 어디서 계산하는지는 클라이언트 metadata만으로 증명할 수 없다. 엄격한 완전 오프라인 사용은 관리되는 호스트 서버·cloud 비활성화·네트워크 차단까지 별도 운영 검증이 필요하다. OpenAlex off, 로컬 모델, 로컬 MCP 클라이언트도 함께 설정해야 한다. cloud MCP 클라이언트에 근거를 반환하면 그 클라이언트가 자료를 외부로 보낼 수 있다는 현재 안내를 유지한다.

**수용 기준**: mock remote 모델과 임의 cloud alias에서 chat 호출 수가 0이다. digest가 바뀌면 검증을 갱신한다. 기본 외부 URL 거부, 명시 LAN 허용 표시, redirect 검사, 오프라인 OpenAlex off, cloud disable 미확인 표시를 확인한다.

## 11. R07 — 실행 기록과 게시 확정

현재 `_process()`의 성공 receipt가 DB 게시보다 먼저 기록된다. 파일과 SQLite를 하나의 ACID transaction으로 묶었다고 설명할 수 없다. 다음 순서로 바꾼다.

1. 추출·candidate·호출별 receipt를 불변 파일로 저장한다. 실행 receipt의 성공은 `generation_completed`이며 최종 job 성공이 아니다.
2. candidate의 검증 결과와 hash를 저장한다. 새 revision 파일이 존재해도 활성 포인터를 바꾸기 전에는 미게시 산출물이다.
3. 한 SQLite transaction에서 revision 등록, 활성 포인터, FTS, job의 `succeeded`를 함께 확정한다. 취소·attempt fencing도 여기서 재확인한다.
4. commit 뒤 `publication_receipt.json`을 새로 쓴다. 실패 시에는 별도 terminal receipt를 쓰며 기존 실행 receipt를 덮어쓰지 않는다.
5. commit 직후 프로세스가 죽어 terminal receipt가 없으면 DB를 기준으로 복구한다. `reconciled_from_db=true`를 남기고 실제로 기록하지 못한 시각·토큰·호출 결과를 만들어 넣지 않는다.

게시 여부의 정본은 DB다. 이미 DB commit이 끝난 뒤 receipt 기록에 실패했다면 job을 다시 failed로 바꾸지 않고 `receipt_incomplete` 진단으로 남긴다. commit 실패 때 남은 revision 파일은 orphan 산출물로 보존한다. 기존 receipt는 역사 자료로 유지하되 DB와 모순되는 경우 `legacy_receipt_conflict`로 보고한다.

**수용 기준**: 파일 생성 전후, 검증 뒤, commit 직전, commit 직후, terminal receipt 직전에 각각 장애를 주입한다. 실패 job의 활성 노트가 생기지 않고, DB 실패에 최종 성공 receipt가 남지 않으며, DB 성공은 재시작 뒤에도 성공으로 복원된다.

## 12. R08·R09 — 검토 판정의 수명과 평가 범위

### 12.1 근거가 바뀌면 판정 무효화

판정 fingerprint는 `paper_id + canonical_claim + sorted evidence IDs + evidence content hashes + evaluation_schema_version`으로 만든다. 수치·단위·지표·조건도 canonical claim에 포함한다. normalization은 공백·표기 등 의미를 바꾸지 않는 범위로 제한한다. 번역/문장 재작성으로 이전 승인을 자동 재사용하지 않는다.

`review_records`에는 fingerprint, claim 위치, note revision, extraction, `verdict`, `reviewer_type=human|assistant`, reviewer, timestamp, reason을 저장한다. 판정은 append-only이며 이전 판정을 삭제하지 않는다. Markdown 검토표는 DB/구조화 기록을 보여주는 산출물로 만들고, 문장만으로 과거 표에서 판정을 복사하는 로직은 폐지한다.

동일 문장에 P0001→P0002를 붙이거나 근거 bytes가 변하면 새 판정은 `unreviewed`다. 메타데이터만 달라지고 주장·근거 fingerprint가 완전히 같으면 판정 재사용이 가능하다. 모델이 바뀌어도 동일 주장·동일 근거라는 조건을 만족하면 판정 이력을 연결할 수 있다. assistant의 `supported`를 human 승인으로 승격하지 않는다.

### 12.2 평가 대상 확장

줄의 첫 글자가 `|` 또는 `>`라는 이유로 제외하지 않는다. Markdown 구조를 파싱하거나 구조화 claim에서 직접 검토 항목을 만든다. parser를 추가하면 직접 의존성과 버전을 선언한다.

| 위치 | 추출 규칙 |
| --- | --- |
| One-line Summary | 문헌의 기여·수치·성능 주장은 포함 |
| Contributions/Method/Results/Limitations | 문장별 사실과 해석을 구분; 한 줄의 여러 주장을 분리 |
| 표 | 행·열 머리글, 단위, caption, footnote와 셀 값을 함께 보존 |
| 인용문 | 본문과 같은 기준으로 사실 주장 포함 |
| Related Work | 다른 논문의 사실은 해당 논문의 근거가 필요; 없으면 미검증으로 표시 |
| Glossary | 일반 용어 정의와 해당 논문의 구현·결과 설명을 구분; 후자는 근거 평가 포함 |
| Document Information | 과학 주장 평가와 분리한 메타데이터 검사 |

분리가 불확실한 복합 문장은 원래 위치와 전체 문장을 남겨 사람이 나눌 수 있게 한다. 모델로만 claim을 추출하면 누락 가능성이 있으므로 원문 구조와 추출된 항목 수·제외 이유를 함께 제공한다.

기존 208개는 `evaluation_schema=v1` 기록으로 보존하고, 확장 후 `v2`의 분모를 새로 집계한다. 표·요약이 추가된 결과를 기존 208개와 그대로 비교하지 않는다.

**수용 기준**: 기존 `999%` 표 행이 검토표에 나타난다. 같은 문장/새 인용, 같은 인용/새 근거, 메타데이터만 변경, 수치 조건 변경을 각각 검사한다. 모든 판정에 reviewer type과 evidence fingerprint가 있고 assistant/human 집계가 분리된다.

## 13. R10·R11 — 코드 구조와 CLI 계약

### 13.1 중복 정의 제거

`service.py`의 중복 함수·클래스 16개는 **실제로 적용되는 후반 정의**를 기준으로 정리한다. 먼저 두 정의의 차이를 확인하고, 무조건 앞부분을 남기지 않는다. 이 단계에서 기능 변경을 함께 넣지 않아 기존 테스트와 결과 차이를 평가할 수 있게 한다.

후속으로 추출, 근거 packet/인용, 노트 생성·검증, 질문, 검토, receipt, scheduler를 분리한다. `LocalService`는 orchestration과 저장 경계만 담당한다. 기존 테스트/import를 유지할 필요가 있으면 얇은 re-export를 두되 함수 구현을 복제하지 않는다. CI에서 같은 Python scope의 함수·클래스 이름 재정의를 탐지한다.

원본 `wiki_search.py`, `identity.py`와 근거 선택의 순수 함수는 활용할 수 있다. `evidence_packet.py`의 S3 접근이나 `infra/extract_worker.py`의 AWS 초기화까지 로컬로 import하지 않는다. 필요하면 순수 로직과 저장 adapter를 분리하고 원본 테스트로 동작 보존을 확인한다.

### 13.2 종료 코드·상태·오류

| CLI 결과 | 종료 코드 제안 | 의미 |
| --- | ---: | --- |
| 정상 완료, 정상적인 `insufficient_evidence` | 0 | 실행 성공; 과학적 정답의 보장은 아님 |
| job failed/interrupted, 서비스·무결성 오류 | 1 | 운영 실패 |
| 잘못된 인자·설정 | 2 | argparse와 일치 |
| batch 일부 실패/일부 미완료 | 3 | 성공 일부 존재, 후속 처리 필요 |
| foreground 사용자 Ctrl-C | 130 | 프로세스 중단; job의 실제 취소 완료 여부는 별도 |

`cancel` 명령의 접수 성공은 코드 0으로 반환할 수 있지만 `stopped`를 반드시 함께 제공한다. 제출 명령의 코드 0도 queued 접수를 뜻할 뿐 완료가 아니다. worker가 계속 실행 중이면 Ctrl-C가 단순 대기 종료인지 job 취소 요청인지 옵션·문서로 구분한다. 아직 실행 중인 job을 프로세스 종료만으로 cancelled라고 쓰지 않는다.

오류 응답은 `error_code`, `stage`, `retryable`, `job_id`, `message`로 통일한다. server response의 원문·API key는 오류 로그에 포함하지 않는다. job/paper 미존재는 명시적 not-found 오류이고 빈 정상 목록으로 위장하지 않는다. MCP는 실패를 구조화 결과/도구 오류로 구분한다.

**수용 기준**: 모델 오류의 ask가 1, 정상 유보가 0, 부분 실패 batch가 3이다. stdout JSON과 종료 코드가 모순되지 않는다. 16개 중복 정의가 사라지고 기존 로컬·원본 테스트가 유지된다.

## 14. 구조화 주장과 수치 귀속

형식 정규화만으로 scFoundation의 PCC→AUC, HEIST의 다른 실험 AUC 귀속 오류를 해결할 수 없다. digest와 최종 노트 사이에 구조화 claim을 도입한다. 숫자를 원문 어딘가에서 찾는 검사가 아니라 **값·지표·대상·조건의 묶음**을 보존하는 설계다.

### 14.1 중간 데이터 계약 제안

```json
{
  "schema_version": 1,
  "claim_id": "C0001",
  "kind": "reported_result",
  "statement": "원문이 보고한 결과를 조건과 함께 서술",
  "metric": "원문에 쓰인 지표명",
  "value": "원문 수치 문자열",
  "unit": "원문 단위 또는 null",
  "condition": {
    "task": "측정 과제",
    "dataset": "측정 데이터",
    "population": "대상 또는 null",
    "baseline": "비교 대상 또는 null",
    "split": "평가 분할 또는 null"
  },
  "evidence": [{
    "packet_id": "packet-...",
    "extraction_id": "extraction-...",
    "block_id": "P0042",
    "block_sha256": "sha256:...",
    "quote": "원문에 실제 존재하는 근거 문장",
    "start": 0,
    "end": 24
  }],
  "uncertainties": []
}
```

위 값은 형식 예시이며 실제 논문 결과가 아니다. `kind`는 `reported_result`, `reported_method`, `author_limitation`, `reviewer_interpretation` 등을 구분한다. 원문에 없는 condition은 null/unknown으로 남기고 모델이 채우지 않는다. 문자열 수치는 반올림·유효숫자를 보존한다. 과학적 단위와 백분율 차이, 상대 변화와 percentage point를 구분한다.

Ollama `/api/chat`의 `format`에 JSON schema를 전달하는 방식을 시험한다. schema 성공은 구조 적합성을 뜻한다. 코드가 ID, hash, quote 범위, 값의 원문 연결을 추가 검사해야 하며 의미적 타당성은 별도 검토 대상이다. 직접 validator 의존성을 추가하거나 명시적 필드 검증을 구현하고, transitive dependency에만 기대지 않는다. [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)

### 14.2 생성·검증·표시 규칙

- 한 번에 큰 JSON을 요구하지 않는다. 작은 part마다 claim을 생성·검증하고 불변 파일로 저장한다.
- quote는 해당 packet 원문에서 확인한다. 공백 normalization을 허용하면 원래 bytes/offset에 역매핑한다. 찾지 못한 quote는 가공된 증거로 게시하지 않는다.
- 수치 claim은 지표·단위·조건이 같은 근거에 연결되는지 검사한다. 단순 숫자 포함 여부는 mechanical check로만 표시한다.
- 노트의 숫자·citation은 검증된 claim record에서 코드가 렌더링한다. 최종 자유 서술 모델이 새로운 숫자를 만들거나 근거 ID를 바꾸지 못하게 한다.
- 요약·표의 사실 주장도 claim을 참조한다. 해석은 해석으로 표시하고 근거와 불확실성을 함께 남긴다.
- 관련 연구의 원문이 없으면 해당 논문의 결과를 확정 서술하지 않는다. “현재 논문이 이렇게 설명함”이라는 간접 출처와 직접 검증을 구분한다.
- JSON parse/형식 오류는 예산 내 1회 수정 후보를 만들 수 있다. 의미 검토 실패를 같은 모델의 반복 생성만으로 해결했다고 처리하지 않는다.

### 14.3 상태를 분리

`artifact_status=draft|published|superseded`, `validation_level=structure|evidence_mechanical`, `review_state=unreviewed|assistant_reviewed|human_reviewed|rejected`, `coverage_status=complete|incomplete|unknown`을 별도 필드로 둔다. `evidence_mechanical`은 과학적 정확도를 인증하는 이름이 아니다.

형식/근거 검사 통과·필수 범위 충족 자료는 unreviewed 상태로 게시할 수 있으나 검색·읽기·답변에 검토 상태를 표시한다. 핵심 근거 누락이나 알려진 수치 오류가 있는 자료는 draft/needs_review로 보존하고 기본 답변 후보에서 제외한다. 기존 노트는 자동 승인하지 않고 `legacy_unreviewed`로 연결한다. assistant 검토만 있는 11편 평가도 사람이 승인한 자료로 취급하지 않는다.

**수용 기준**: PCC와 AUC, 서로 다른 과제의 같은 숫자, 상대 개선과 절대 개선, 동일 값/다른 cohort의 fixtures를 사용한다. 원문 수치 문자열이 렌더링 중 바뀌지 않고, 범위 밖 quote/ID가 차단되며, 사실과 해석의 상태가 구분된다. 사람 평가에서 귀속 오류가 줄었는지도 따로 측정한다.

## 15. 질문 처리 — 검색·원문 재독·근거 부족 반환

원본 question agent의 모든 도구를 작은 모델에 한 번에 맡기지 않는다. 다음의 제한된 흐름부터 구현한다.

```mermaid
flowchart LR
    Q[질문 job] --> S[노트 검색]
    S --> N[관련 절과 revision 선택]
    N --> P[필요한 원문 block 읽기]
    P --> A[주장별 답변 생성]
    A --> V[제공 근거·인용·hash 검사]
    V --> R[답변 또는 근거 부족]
```

1. 최대 2회 검색한다. 최초 후보는 5개까지, 실제 읽는 노트는 관련성·문맥에 따라 최대 3개로 시작한다. 모두 설계 시작값이다.
2. 전체 노트 대신 질문 관련 Results/Method/Limitations와 근거 claim을 선택한다. 각 note revision을 처음부터 고정한다.
3. 수치·비교·실험 조건이 필요한 질문은 관련 원문을 읽는다. note에 없는 block도 추가 읽기가 가능하지만 **실제로 제공한 packet**에 등록해야 사용할 수 있다.
4. 답변은 claim별 evidence를 갖는 구조화 결과로 생성한다. E1 등의 표시 라벨은 코드가 revision/extraction/claim에 연결해 렌더링한다.
5. 각 사실 주장에 근거가 있는지 검사한다. 인용 하나가 전체 무인용 답변을 통과시키지 못하게 한다.
6. 근거 없는 사실을 삭제/유보하고, 해석·불확실성을 분리한다. 검색·원문 확인을 해도 부족하면 `insufficient_evidence`와 이유·확인한 범위를 반환한다.

새 reason은 `missing_source`, `coverage_incomplete`, `claim_unverified`, `evidence_integrity_failed`, `budget_exhausted` 등을 포함한다. 무결성·서비스 장애는 정상 유보와 운영 오류를 구분한다. 과거 형식의 `model_answer_uncited` 등은 호환 가능하게 유지하거나 명시적 버전 변경을 한다.

질문 receipt에는 검색어, 후보/선택 revision, 읽은 block과 hash, 호출별 packet, 예산, 최종 claim citation을 남긴다. 기본 논문 질문에서 note 수정/자동 종합을 수행하지 않는다. 보충자료가 필요한데 저장되어 있지 않으면 unavailable을 기록한다.

**수용 기준**: 다른 논문의 같은 지표, 정반대 결과, 노트에 없는 조건, 3편이 문맥을 초과하는 경우, 손상 노트, 원문 재독 후만 답할 수 있는 질문을 포함한다. 답변 모든 사실 claim의 근거 범위가 확인되고, 근거 부족과 운영 실패가 구분된다.

## 16. 문맥 예산·호출 기록·재개

### 16.1 예산 계산

현재 문자 가중 추정과 0.55 비율 검사는 소수 실측에 따른 휴리스틱이다. system prompt, chat template, schema, evidence, 출력 여유를 포함한 **실제 전송 입력**을 기준으로 예산을 계산한다. 한국어·숫자 표·수식·긴 ID가 많은 자료로 오차를 측정한다. `prompt_eval_count=0`/누락이면 검사를 건너뛴 정상 완독으로 처리하지 않고 `token_accounting_unverified`를 남긴다.

`context - output - reserve`를 넘으면 호출 전 packet을 줄이거나 더 작은 part로 나눈다. 블록을 무언가 잘라 보냈으면 발췌 범위와 미제공 범위를 남긴다. 잘림 의심, 비정상 stop, 빈 응답은 성공 게시를 차단한다. 출력 한도 도달도 정상적인 근거 완성으로 취급하지 않는다.

정확한 tokenizer 기반 사전 검사 대안은 `llama.cpp` server의 `/apply-template`와 `/tokenize`다. 설치 모델의 GGUF·tokenizer·chat template가 같은지 고정하고 렌더링된 입력을 계산해야 한다. 이 대안은 **미설치·미검증**이며 migration 필수 사항이 아니다. 다른 backend를 써도 16GiB 제약은 유지되며 두 추론 서버를 동시에 상주시키지 않는다. 현재 Ollama 추정만으로 입력이 한 토큰도 잘리지 않았다는 강한 보장은 할 수 없다. [llama.cpp 공식 server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

### 16.2 호출별 receipt

노트·digest·질문·번역·audit에 같은 receipt 구조를 적용한다.

| 필드 | 요구 |
| --- | --- |
| 실행 식별 | job/attempt/call ID, code commit 또는 source hash, schema version |
| 모델 | tag **및 digest**, backend/server 버전, template hash, endpoint policy |
| 설정 | context, output, temperature, think, format/schema hash, KV profile 등 확인 가능한 실제 옵션 |
| 입력 | system/user 메시지 hash, packet ID, block/claim IDs, 실제 payload hash |
| 결과 | input/output tokens와 availability, done/stop reason, elapsed, retry cause |
| 범위·검증 | coverage, omitted IDs/reasons, structural/mechanical 결과, review state |

기존 `prompt_sha256`처럼 원문 body만 hash한 값은 전체 prompt hash라는 이름으로 유지하지 않는다. 전송 payload는 불변 로컬 파일로 보존하거나 복원 가능한 message 파일+옵션으로 구성한다. receipt/log에 원문 전체와 secret을 중복 출력하지 않는다. temperature=0도 byte 단위 재현성을 보장하지 않으므로 결과 hash를 함께 저장한다.

### 16.3 체크포인트·재시도

체크포인트 경계는 원본 확인 → 추출 → 메타데이터 후보 → part별 claim/digest → 합성 candidate → 검증 → 게시다. 저장한 단계는 원본/입력 hash, 모델 digest, prompt/schema 버전, 옵션이 모두 맞을 때만 재사용한다. 불일치 산출물은 보존하되 새 attempt에서 재계산한다.

새 attempt는 이전 valid checkpoint를 참조하되 `resumed_from`을 기록한다. 재분할은 part lineage를 남기고 이미 성공한 unrelated part를 다시 생성하지 않는다. queued/running 취소 확인은 모든 경계에 있다. `revalidate`는 모델 없이 구조·근거를 검사하는 기능이며, 새로운 과학적 사실의 승인으로 확장하지 않는다.

긴 작업의 총 예산은 시간·호출 수·part 수로 제한하고 설정 가능하게 한다. 예를 들어 전체 논문 2시간, audit 10개 claim 단위는 초기 실험 정책이며 지원 성능 약속이 아니다. 예산 소진은 checkpoint와 remaining을 반환하고, 재개 시 누적 비용을 확인할 수 있게 한다. 모든 208개 주장을 무제한 직렬 재판정하는 작업을 기본 실행하지 않는다.

**수용 기준**: 네 번째 part에서 죽은 작업이 앞선 세 part를 호출하지 않고 재개된다. 모델 digest·원문·prompt 버전 변경은 해당 checkpoint를 무효화한다. token 수 누락/zero와 출력 잘림을 검사한다. timeout 재시도는 7.3의 불확정 상태 규칙을 따른다.

## 17. 추출기·OCR 대체 경로

현재 GROBID 경로를 기준으로 유지하고, `--extractor grobid|pymupdf|auto`를 **신규 제안**한다. auto는 선택 사유·실제 추출기를 기록하며 fallback이 GROBID와 같은 품질이라는 뜻이 아니다.

- PyMuPDF 경로는 페이지, bbox, reading order, block type, table cell 위치를 보존한다. 이를 기존 block 소비 API에 adapter로 제공하되 TEI/GROBID 결과라고 표시하지 않는다.
- 글자가 추출된다는 이유만으로 전문이 충분하다고 판정하지 않는다. 페이지별 텍스트 분포·이미지 비율·본문 부재·표/그림 누락을 보고한다. 표지의 도장/헤더만 텍스트인 스캔을 정상 text PDF로 분류하지 않는다.
- 구조를 판별할 수 없으면 `partial`, 필요한 페이지를 읽지 못하면 `needs_ocr`/`coverage_incomplete`다. OCR 실패를 조용히 빈 block으로 바꾸지 않는다.
- OCR은 페이지당 한 번만 수행하고 동일 TextPage를 재사용한다. 원본 PDF를 보존한 별도 파생 파일과 engine/version/language/page coverage를 기록한다.
- OCRmyPDF를 채택하면 설치 버전에서 지원하는 옵션을 확인한다. `--jobs 1`, `--optimize 0`, `--output-type pdf`, 이미지 megapixel 제한을 검토한다. 이미지 픽셀 수가 큰 페이지의 메모리 부담을 조절하되 미처리 페이지를 숨기지 않는다. [OCRmyPDF 공식 성능 안내](https://ocrmypdf.readthedocs.io/en/latest/performance.html)
- `find_tables`의 텍스트 표 결과도 header/merged cell/단위/footnote를 대조한다. 이미지 표는 OCR/VLM 후보이며 자동 수치 승인 대상이 아니다.
- vision 실험은 작은 crop 1개와 짧은 문맥부터 시작한다. 추출값의 confidence·근거 이미지 위치·사람 확인을 남기며, 그래프 원 데이터가 없으면 정확 보고값으로 바꾸지 않는다.

**수용 기준**: 정상 text, 두 단, 복잡한 텍스트 표, 헤더만 text인 스캔, 이미지 그래프 PDF를 각각 평가한다. 누락 페이지를 감지하고 원본 hash가 변하지 않는다. OCR 미설치 상태에서 필요한 의존성과 limitation이 명시되며 무한 retry/자동 다운로드가 없다.

## 18. 저장 계약·마이그레이션·백업·복원

### 18.1 추가 스키마 제안

현재 schema version은 4다. 다음 기능을 한 번에 거대한 migration으로 넣지 않고, 구현 묶음마다 5 이후의 버전을 순차 배정한다. 아래는 논리 계약이며 최종 DDL은 해당 구현에서 검토한다.

| 데이터 | 필수 정보 |
| --- | --- |
| job 소유권/이벤트 | worker/attempt, heartbeat, cancel ack, stage/event, error code |
| extraction record | PDF hash, TEI/JSON hash, engine/version, page coverage, integrity status |
| revision 상태 | artifact/review/coverage 상태, validation level, 코드 생성 이유 |
| metadata values | 필드별 값·출처·수동 정정·확인 시각·충돌 |
| document aliases | alias, paper ID, 생성 이유/시각; alias 재할당 금지 |
| call/packet record | model digest/options, prompt/schema hashes, provided evidence, immutable path |
| claim/review record | 조건 묶음·근거 hash·fingerprint·판정자·판정 이력 |

읽기 전에 migration plan과 현재/목표 버전을 확인할 수 있게 한다. 기존 PDF/revision 파일을 이동·삭제하지 않고 additive column/table을 우선한다. DB 외 파일 검사/생성은 manifest로 추적한다. migration 중 모델이나 외부 metadata를 호출하지 않는다.

새 foreign key는 실제로 활성화하고 검증하되 기존 orphan을 숨기거나 자동 삭제하지 않는다. 기존 DB에 대한 `foreign_key_check`, migration 실패 rollback, 다른 프로세스 동시 접근 차단을 시험한다. 지원보다 높은 schema는 읽기 전 명시적으로 거부한다. rollback은 신규 DB를 기존 도구로 강제 열기보다 백업을 **새 디렉터리**에 복원하는 절차로 제공한다.

### 18.2 백업·복원 계약

`byeori-local backup`, `restore`는 **신규**다. 실행 중 SQLite 파일만 복사하는 방식은 채택하지 않는다. maintenance lock으로 등록·게시·판정·상태 변경을 멈추고, SQLite `Connection.backup()`으로 일관된 DB snapshot을 만든 뒤 참조 파일과 manifest를 보존한다. 불변 파일이더라도 snapshot과 파일 목록의 연결을 검사해야 한다. [Python SQLite backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup)

백업에는 원본, 활성/과거 revision, 추출, runs/checkpoints, 검토 기록, alias, quarantine, schema/code/version, 파일별 hash가 포함된다. secret과 사용자 endpoint 자격증명은 포함하지 않는다. 모든 유지 대상 파일을 manifest로 열거하고 unreferenced 산출물도 별도 목록으로 남긴다. DB와 파일 전체가 자동으로 원자적 백업되는 것처럼 설명하지 않는다.

복원 대상은 새 디렉터리만 허용한다. 원래 워크스페이스 위에 덮어쓰지 않는다. manifest/hash 검사 → DB 무결성 → 참조 연결 → 활성 index 재구축 → 읽기/검색/과거 인용 검증을 통과해야 복원 완료다. 과거 running job은 재개 후보/interrupted로 분류하고 실제 실행 중이라고 복원하지 않는다.

같은 SSD의 복사본은 장비/디스크 고장 대비가 아니다. 외장 디스크 등 별도 저장 위치가 있으면 검증된 백업을 복제한다. 그 장치가 현재 존재한다고 가정하지 않으며, 없으면 **디스크 고장 복구 보장 불가**라고 운영 상태에 표시한다.

**수용 기준**: 활성 노트·과거 revision·원본·판정·alias가 있는 fixture를 새 디렉터리에 복원하고 동일 인용을 조회한다. 파일 하나 누락/변경, backup 중 writer, migration 중 crash, 상위 schema, 기존 대상 덮어쓰기 거부를 검사한다.

## 19. 평가·성능 수용 기준

### 19.1 검증 단계

1. **결정적 회귀 테스트**: R01~R11 재현을 기대 동작 assertion으로 옮긴다. 현재 스크립트의 JSON 출력만으로 통과를 판단하지 않는다. 경계값·경쟁·crash injection을 포함한다.
2. **실서비스 smoke**: 현재 8B/CRF에서 짧은 text, 표 중심, 긴 논문 각 1편으로 pipeline/자원/재개를 확인한다. OCR/VLM 경로는 의존성이 설치된 별도 실험에서 추가한다.
3. **고정 품질 평가**: 기존 11편의 원본·추출·prompt/model digest를 고정한다. 기존 60개 플래그 항목(47개 결함, 13개 맞음 기록)을 사람이 판정하고 supported 148개도 중요 수치와 층화 표본을 확인한다. 처음 30개 표본은 시작 정책이지 전체 정답률 증명이 아니다.
4. **확장 평가**: v2의 표·요약·인용문 항목을 추가하고 개발에 쓰지 않은 논문 5편 이상을 별도 holdout 후보로 둔다. 사람 검토 가능량에 맞춰 표본 수를 확정한다.
5. **모델/원본 비교**: 같은 corpus/추출/평가 규칙으로만 비교한다. 원본 cloud 모델 실행은 비용·외부 전송이 있는 별도 작업이며 이번 local-only 수정의 필수 단계로 실행하지 않는다. 비교 자료가 없으면 원본 동등성은 미검증으로 유지한다.

### 19.2 출시를 막는 조건

| 영역 | 필수 수용 기준 |
| --- | --- |
| 상태·데이터 | R01~R11 새 회귀 검증 통과; 누락, 확정값 소실, 실패 게시, 판정 오재사용 없음 |
| 근거 | 반환된 factual claim의 제공 범위/ID/hash 검사 100% 통과; 중요한 미제공 원문으로 성공하지 않음 |
| 수치 | 기존 확정 오류를 golden case로 고정; 잘못된 지표·대상 귀속이 재생성/답변에 재현되면 일반 답변 사용 제외 |
| 평가 표시 | assistant/human, 미검토, 제외 항목, v1/v2 분모 분리; supported를 정답률로 표현하지 않음 |
| 자원 | 선택 프로필의 긴 논문 포함 실서비스 run에서 OOM 없음; swap 지속 증가/압력 발생 시 기본 프로필 보류 |
| 복구 | 단계 중단 후 재개, commit/receipt 복구, 새 디렉터리 restore 성공 |
| 호환 | 로컬 테스트와 변경 영향에 맞는 원본 테스트 통과; 원본 AWS 경로의 회귀 없음 |

`근거 검사 100%`는 코드로 확인할 수 있는 조건의 기준이다. 의미적 정확도 100% 기준과 혼동하지 않는다. semantic 평가의 분모는 사람이 확인한 claim만 사용하고, 미판정·누락·거짓 경보를 별도 집계한다. 기존 47개는 보조 판정이므로 사람 확정 전 전부를 “정답 오류” golden label로 고정하지 않는다.

속도는 처리시간 median/p95, 호출·재시도·실패 수, 출력 tokens, 초기 load/추론 시간, 관측 memory pressure/swap을 기록한다. 소수 3편 smoke의 p95를 안정적 서비스 SLA로 제시하지 않는다. 전후 비교는 동일 자료·동일 백그라운드 부하로 하고, 품질을 낮춰 빨라진 결과를 성능 개선으로만 보고하지 않는다.

## 20. 구현 순서와 종료 조건

| 단계 | 구현 묶음 | 다음 단계로 넘어가는 조건 |
| --- | --- | --- |
| A. 상태·근거 안정화 | S01~S11, 최소 공용 추론 잠금, 호출별 근거 범위, 해시, receipt | 재현 결함 회귀 통과; 기존 활성 자료 보존; local-only 검사 |
| B. 장기 작업 운영 | 지속 worker, checkpoint, 예산, 자원 전환, backup/restore | 실제 강제 중단/재시작·복원 성공; 기본 8B 자원 프로필 검증 |
| C. 품질 개선 | 작은 구조화 claim, 코드 렌더링, 제한된 원문 재독, v2 평가 | 기존 수치 오류 검토·차단, 사람 평가와 미검토 상태 표시 |
| D. 추출 대안 실험 | PyMuPDF/OCR/선택 VLM, 조건부 14B·KV cache 비교 | 각각의 품질·메모리 실측을 통과한 경로만 지원 목록 추가 |
| E. 지식 누적 | category, glossary 후보, Concept, Overview, backlinks/catalog | 검토 가능한 member note와 revision 의존성 추적 |

완전한 데이터 계약을 기다리며 A를 지연하지 않는다. 예를 들어 범위 인용·해시 검증은 자유 서술 candidate에도 즉시 적용하고 구조화 claim은 C에서 확장한다. schema 변경은 기능 묶음과 함께 작게 적용한다. 시간 견적은 실제 수정량·성능 측정 뒤 산정하며 이 문서에서 근거 없는 완료 일정을 약속하지 않는다.

Concept는 처음에 소수(예: 5편)의 glossary/claim 기반으로 만들고 `member_revision_ids`를 기록한다. 원본의 후보 추출 기준은 재사용하되 로컬 경로·alias에 맞춰 검증한다. member 노트가 바뀌면 종합 문서를 `stale`로 표시한다. Overview는 주제별 작은 근거 묶음을 통합하고 출처를 유지한다. 여러 번의 요약으로 모든 원문의 사실이 보존된다고 주장하지 않는다. 소규모 구현은 현재 장비에서 가능하지만 대규모 생성 시간·품질은 아직 미검증이다.

## 21. 문서 정정 요구와 최종 구현 체크리스트

`LOCAL-DEVELOPMENT.md`와 패키지/README 안내는 아래 내용을 실제 구현 후 갱신한다.

- “모델 이해 품질은 아직 평가 대상 아님”을 현재 보조 평가 진행 상태와 미검토 한계로 정정한다.
- GROBID 이미지 저장 크기와 실행 메모리, 공유 VM과 전용 VM, 실제 architecture를 구분한다.
- OpenAlex가 모든 값을 확정/덮어쓴다는 설명을 필드 보완·충돌·수동 정정·실패 보존 규칙으로 바꾼다. mailto와 key/제한 안내를 맞춘다.
- 현재 검토표의 `byeori-local read_paper_context` 안내는 존재하지 않는 CLI 명령이다. MCP의 `read_paper_context(paper_id, paragraph_id, revision)`로 안내하거나 별도 CLI를 구현한 뒤 실제 명령으로 정정한다.
- 파일 기록과 DB 게시의 원자성 범위, receipt의 정본, 작업 취소의 접수/완료를 정확히 설명한다.
- 질문 하나씩 실행한다는 설명에 적용 범위·공용 endpoint 잠금·다른 앱의 부하 한계를 명시한다.
- 모델 tag만으로 로컬 실행을 확정하지 않고 cloud 비활성화/검증 상태를 안내한다.
- 완전 오프라인 사용과 OpenAlex 사용, cloud MCP 클라이언트에 자료 반환을 구분한다.
- 신규 worker/backup/restore/프로필은 실제 수용 검증 후 설치·운영 안내에 추가한다.

개발 완료 여부는 아래 항목으로 판단한다. 이번 문서 작성 시점에는 **미완료**다.

- [ ] R01~R11 모두 기대 동작을 검사하는 회귀 테스트로 전환하고 수정.
- [ ] 노트·질문·audit·번역의 추론 직렬화와 작업 소유권 검증.
- [ ] 제공 근거 ID와 실제 파일 hash를 반환·게시 전에 검증.
- [ ] 실패/취소/불확정 timeout에서 기존 활성 데이터 보존.
- [ ] 호출별 model digest·prompt/packet·예산·terminal 결과 추적.
- [ ] 판정 fingerprint와 사람/보조 판정 구분, 표 포함 v2 평가.
- [ ] 강제 중단 후 checkpoint 재개와 새 디렉터리 백업 복원.
- [ ] 현재 8B 프로필의 실서비스 메모리·품질 검증.
- [ ] 조건부 대안의 검증 결과와 불가능/미지원 조건을 운영 문서에 유지.

이 범위를 충족하면 “원문과 근거를 보존하며 제한된 연구 질문을 처리하는 로컬 byeori”로 진행할 수 있다. 원본 전체 기능·대규모 종합·무인 과학 검증·대형 모델 성능까지 완료되었다는 뜻은 아니다.

## 22. 1차 안정화 구현 결과 — 2026-10-01

단계 A의 **R01~R11 핵심 재현 결함**을 수정했다. 상세 요구사항 전체, 단계 B~E, 실제 논문 재생성과 사람 품질 평가는 완료하지 않았다. 저장소의 변경 파일만 수정했으며 실제 사용자 데이터·서버 설정·모델 설치는 변경하지 않았다.

| 번호 | 구현과 확인 결과 | 남은 범위 |
| --- | --- | --- |
| R01 | 내부 cursor 순회로 101편 모두 게시. pending 누락 없음. 1,002개 job에서 오래된 orphan 탐색. 동일 timestamp와 조회 중 새 등록 검사 | 큰 실제 corpus의 처리량·장기 운영 실측 |
| R02 | 기존 확정값 기반 병합, off/빈 결과/429/503에도 연도·work ID 유지. lookup 상태 DB 기록, 선택 API key, 짧은 429 1회 재시도, retired stem alias 보존 | 수동 정정/명시적 clear, 세 종류 날짜, 완전한 필드별 authority와 캐시 정책 |
| R03 | submit/종료의 동일 잠금, manager별 owner UUID, 프로세스 birth time 확인, workspace 질문 직렬화, endpoint 공용 추론 잠금. 미완료 요청 표식·timeout quarantine과 명시적 복구 | 지속 worker, heartbeat/attempt fencing, dispatcher·waiting_resource·공정성 정책 |
| R04 | 답변 인용을 실제 제공한 노트의 문단으로 제한. 인용 없는 문장 유보. digest의 미제공 ID 및 최종 digest에서 사라진 ID 차단. 실패 블록 자동 생략 게시 폐지 | 정식 EvidencePacket/claim schema, 자동 원문 재독, 페이지별 추출 coverage |
| R05 | 노트와 새 추출 JSON hash 대조. 손상 자료 읽기·답변·검색 차단. 게시 직전 추출 hash 재확인. deep에서 PDF·TEI도 검사 | 기존 hash 없는 JSON의 역사 검증, 모든 checkpoint/alias의 심층 검사, reindex |
| R06 | loopback 기본 제한, 명시 외부 endpoint 옵션, tag/show remote·cloud 표식 검사, 요청 전 locality 확인. 실제 qwen3:8b metadata 조회 성공 | 서버 cloud 비활성화 상태는 unverified; 엄격한 오프라인 운영 검증 |
| R07 | execution과 terminal receipt 분리. 게시 실패는 failed receipt. commit 후 receipt 실패가 성공을 뒤집지 않음. 누락 terminal 결과의 DB 기반 복구 | 메타데이터·재검증 등 모든 작업의 통합 receipt schema/이벤트 추적 |
| R08 | 주장·논문·인용·근거 hash fingerprint로 판정 재사용 제한. 근거 변경 시 판정 제거. 기존 검토표를 별도 history에 보존 | 통합 review_records 저장·사람 승인 정책·변경 UI |
| R09 | 표 행과 header, 인용문, 요약, Related Work, Glossary도 평가 v2에 포함. 999% 표 누락 재현 해소 | 복합 주장 분리는 휴리스틱; 완전한 claim extraction·v2 사람 평가 |
| R10 | 동일 중복 정의 16개 제거. 근거/검토 helper를 evidence.py로 분리. 중복 재발 검사 추가 | 추출·노트·질문 등 나머지 모듈 분리 |
| R11 | ask 실패 1, 인자 오류 2, 부분 batch 실패 3, 정상 유보 0. 구조화 CLI 오류, 미존재 job 오류 | 모든 오류의 상세 stage/attempt contract, 지속 worker의 interrupt 정책 |

추가로 불변 파일 생성의 `exists → os.replace` 경쟁을 exclusive hard link 생성으로 바꿨다. 같은 이름을 동시에 쓰면 한 writer만 성공하며 기존 파일을 덮어쓰지 않는다. 해당 파일시스템은 hard link를 지원해야 한다.

### 확인한 검증 결과

- 전체 테스트: **2,427 passed, 1 skipped**. 실행 명령 `.venv/bin/python -m pytest -o addopts='' -q --tb=short`.
- 로컬 테스트: 기존 106개에서 **138개**로 확장. 32개 회귀 case 추가; 바뀐 계약을 기대하는 기존 테스트도 정정했다.
- [재현 스크립트](reviews/local-runtime-repro-2026-10-01.py): 101/101 게시, 확정값 유지, job/receipt 모두 failed, 파일 변경 탐지·읽기 차단, 생략 근거 게시 거부, 종료 경쟁 뒤 job 완료, 두 질문 동시 실행 없음, 달라진 근거에 판정 승계 없음, 표 평가 포함, CLI 실패 코드 1, cloud mock chat 호출 0, 중복 정의 없음.
- 별도 프로세스 두 개가 동일 endpoint 잠금을 공유하는 것을 테스트했다. 이는 byeori 외부 앱까지 직렬화한다는 뜻은 아니다.
- 실제 Ollama 0.34.4에서 qwen3:8b의 local metadata, model digest, template hash, capabilities, recovery 상태를 조회했다. **실제 논문 생성·답변 품질과 새 자원 프로필은 재측정하지 않았다.**

### 실제 사용할 수 있는 인터페이스

```text
byeori-local list --limit 50 [--cursor <next_cursor>]
byeori-local status --limit 20 [--cursor <next_cursor>]
byeori-local check --deep
byeori-local reconcile-receipts
byeori-local recover-runtime --acknowledge-idle
```

recover-runtime은 이전 서버 요청이 종료됐음을 직접 확인한 뒤 사용하는 명령이다. 즉시 GPU 취소 명령이 아니다. 남은 요청 표식은 복구 이력으로 옮겨 보존한다. MCP에는 `list_papers_page`, `list_jobs_page`를 추가했고 기존 list 반환 도구는 유지했다. CLI list/목록 status는 cursor envelope를 반환한다.

신규 설정은 `BYEORI_LOCAL_RUNTIME_DIR`, 선택적인 `BYEORI_OPENALEX_API_KEY`, 명시 외부 서버용 `--allow-remote-ollama`다. 기존 데이터는 schema 5로 additive migration한다. 과거 JSON hash가 없는 노트는 legacy_unverified로 읽으며 과거 무변조를 인증하지 않는다.

다음 구현 묶음은 **단계 B의 지속 worker·checkpoint·백업/복원**, 이후 **단계 C의 구조화 주장과 원문 재독**이다. 기존 11편의 수치·귀속 오류가 이번 안정화로 자동 수정되었다고 간주하면 안 된다.
