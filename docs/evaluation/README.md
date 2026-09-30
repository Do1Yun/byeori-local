# 평가 세트

논문 11편, 주장 208개. 노트가 한 주장과 그것이 인용한 원문을 짝지어 놓고, 1차 검사가 `supported`로 보지 않은 것마다 판정을 적었습니다.

**결함 47개 / 주장 208개.** 1차 검사가 `supported`로 본 148개는 판정하지 않았으므로 표본 점검이 필요합니다.

| 논문 | 연도 | 주장 | 결함 | 인용틀림 | 수치틀림 | 무인용 | 맞음 | supported |
|---|---|---|---|---|---|---|---|---|
| [scLong: a billion-parameter foundation model f](bai-2026-sclong-a-billion-parameter-foundation-model.md) | Nature Communications 2026 | 28 | **10** | 2 | 2 | 6 | 2 | 16 |
| [Assessing scale and predictive diversity in mo](chen-2026-assessing-scale-and-predictive-diversity-in.md) | PLoS Computational Biology 2026 | 21 | **6** |  |  | 6 |  | 15 |
| [BERT: Pre-training of Deep Bidirectional Trans](devlin-2019-bert-pre-training-of-deep-bidirectional.md) | 2019 | 18 | **6** | 3 | 1 | 2 | 3 | 9 |
| [Large-scale foundation model on single-cell tr](hao-2024-large-scale-foundation-model-on-single.md) | Nature Methods 2024 | 20 | **6** | 3 | 3 |  |  | 14 |
| [Attention Is All You Need](vaswani-2023-attention-is-all-you-need.md) | 2023 | 18 | **6** | 4 |  | 2 | 1 | 11 |
| [scGPT: toward building a foundation model for ](cui-2024-scgpt-toward-building-a-foundation-model.md) | Nature Methods 2024 | 19 | **4** | 4 |  |  |  | 15 |
| [NEURAL MACHINE TRANSLATION BY JOINTLY LEARNING](bahdanau-2016-neural-machine-translation-by-jointly-learning.md) | arXiv | 15 | **3** | 3 |  |  | 1 | 11 |
| [Novae: a graph-based foundation model for spat](blampe-2025-novae-a-graph-based-foundation-model.md) | Nature Methods 2025 | 19 | **2** |  | 2 |  | 2 | 15 |
| [HEIST: A GRAPH FOUNDATION MODEL FOR SPATIAL TR](madhu-2025-heist-a-graph-foundation-model-for.md) | 2025 | 14 | **2** |  | 1 | 1 | 1 | 11 |
| [Transfer learning enables predictions in netwo](theodoris-2023-transfer-learning-enables-predictions-in-network.md) | Nature 2023 | 18 | **2** | 2 |  |  | 2 | 14 |
| [scPRINT: pre-training on 50 million cells allo](kalfon-2025-scprint-pre-training-on-50-million.md) | Nature Communications 2025 | 18 | **0** |  |  |  | 1 | 17 |
| **합계** | | **208** | **47** | **21** | **9** | **17** | **13** | **148** |

## 판정의 뜻

- `맞음` 인용한 문단이 그 주장을 뒷받침함. 1차 검사가 잘못 플래그한 경우입니다.
- `인용틀림` 값은 논문에 있으나 인용한 문단에는 없음
- `수치틀림` 값·지표·실험 조건이 논문과 다르거나 논문에 없음
- `근거없음` 논문에 없는 내용
- `무인용` 주장에 문단 인용이 아예 없음

판정자는 모두 `보조 (사람 확인 필요)`입니다. 사람이 다시 볼 때는 판정자를 바꿔 적습니다.

## 읽어서 드러난 것

- 결함 47개 중 **21개가 인용 오류**입니다. 값은 논문에 있는데 다른 문단을 가리킵니다. 노트를 쓰는 모델이 논문 전체를 읽고 요약하면서 그 값이 어느 문단에서 왔는지를 잃습니다.
- **무인용 17개**는 검증 규칙의 구멍입니다. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못합니다.
- **수치틀림 9개**가 가장 까다롭습니다. 값이 논문에 있어서 기계 대조로는 통과하는데 무엇을 측정한 값인지가 틀렸습니다. 예: scFoundation 노트는 PHA-793887의 개선을 'AUC에서 0.2–0.7'이라고 적었으나 논문은 'PCC 0.07→0.73'이고, HEIST 노트는 ligand-receptor 예측의 AUC-ROC 0.995를 임상 결과 예측에 붙였습니다.
- 1차 검사가 플래그한 것 중 **13개는 거짓 경보**였습니다. 인용문 축자 대조가 엄격한 탓이 대부분이고, `SQuAD v2.0`의 `2.0`을 측정값으로 센 경우도 있습니다.

## 다시 만들기

```text
byeori-local review <문서 식별자> --audit --out docs/evaluation/<문서 식별자>.md
```

기록한 판정은 주장 문장을 키로 보존되므로 다시 만들어도 남습니다. 주장 문장이 바뀌면 그 주장은 판정하지 않은 것이 되어 빈 칸으로 돌아갑니다.
