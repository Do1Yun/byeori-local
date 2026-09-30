# 평가 세트

노트의 주장과 그것이 인용한 원문을 짝지은 검토표입니다. 논문 한 편에 파일 하나이고, 파일 이름은 그 논문의 문서 식별자입니다.

각 주장에는 자동 1차 검사 결과가 붙어 있습니다. **`supported`가 아닌 것부터** 읽으시고, `판정:` 칸에 `맞음 / 인용틀림 / 수치틀림 / 근거없음` 중 하나를 적어주세요. 파일 위쪽 **핵심 수치** 칸에는 그 논문에서 반드시 맞아야 하는 주장 번호 3~5개를 적습니다.

1차 검사는 모델이 근거 문장을 인용하게 하고 코드가 그 인용·수치가 원문에 있는지 검증하는 방식입니다. 사람이 논문을 읽고 판정한 5개 주장에서 5/5로 일치했지만, 5개는 검사기를 검증할 표본이 아닙니다. `supported`도 표본을 뽑아 확인해주세요.

| 논문 | 연도 | 주장 | supported | 먼저 볼 것 | 내역 |
|---|---|---|---|---|---|
| [scLong: a billion-parameter foundation model for cap](bai-2026-sclong-a-billion-parameter-foundation-model.md) | Nature Communications 2026 | 28 | 16 | **12** | flagged 6, no_evidence 6 |
| [BERT: Pre-training of Deep Bidirectional Transformer](devlin-2019-bert-pre-training-of-deep-bidirectional.md) | 2019 | 18 | 9 | **9** | flagged 5, not_in_paragraph 2, no_evidence 2 |
| [Attention Is All You Need](vaswani-2023-attention-is-all-you-need.md) | 2023 | 18 | 11 | **7** | flagged 4, not_in_paragraph 1, no_evidence 2 |
| [Assessing scale and predictive diversity in models f](chen-2026-assessing-scale-and-predictive-diversity-in.md) | PLoS Computational Biology 2026 | 21 | 15 | **6** | no_evidence 6 |
| [Large-scale foundation model on single-cell transcri](hao-2024-large-scale-foundation-model-on-single.md) | Nature Methods 2024 | 20 | 14 | **6** | flagged 4, not_in_paragraph 2 |
| [HEIST: A GRAPH FOUNDATION MODEL FOR SPATIAL TRANSCRI](madhu-2025-heist-a-graph-foundation-model-for.md) | 2025 | 14 | 9 | **5** | flagged 4, no_evidence 1 |
| [NEURAL MACHINE TRANSLATION BY JOINTLY LEARNING TO AL](bahdanau-2016-neural-machine-translation-by-jointly-learning.md) | arXiv | 15 | 11 | **4** | flagged 2, not_in_paragraph 2 |
| [Novae: a graph-based foundation model for spatial tr](blampe-2025-novae-a-graph-based-foundation-model.md) | Nature Methods 2025 | 19 | 15 | **4** | flagged 4 |
| [scGPT: toward building a foundation model for single](cui-2024-scgpt-toward-building-a-foundation-model.md) | Nature Methods 2024 | 19 | 15 | **4** | flagged 4 |
| [Transfer learning enables predictions in network bio](theodoris-2023-transfer-learning-enables-predictions-in-network.md) | Nature 2023 | 18 | 14 | **4** | flagged 3, not_in_paragraph 1 |
| [scPRINT: pre-training on 50 million cells allows rob](kalfon-2025-scprint-pre-training-on-50-million.md) | Nature Communications 2025 | 18 | 17 | **1** | not_in_paragraph 1 |
| **합계** | | **208** | **146** | **62** | |

## 판정의 뜻

- `맞음` 수치·조건이 논문과 일치하고 인용한 문단이 그 근거를 담고 있음. 표현이 달라도 뜻이 같으면 맞음입니다.
- `인용틀림` 값은 논문에 있는데 그 값이 없는 문단을 가리킴
- `수치틀림` 값이나 실험 조건이 논문과 다름
- `근거없음` 논문에 없는 내용

## 다시 만들기

```text
byeori-local review <문서 식별자> --audit --out docs/evaluation/<문서 식별자>.md
```

노트를 다시 생성하면 revision이 바뀝니다. 검토표 위쪽의 `노트 revision`이 어느 노트를 판정한 것인지 말해주므로, 모델·프롬프트를 바꾼 뒤 같은 기준으로 비교할 수 있습니다.
