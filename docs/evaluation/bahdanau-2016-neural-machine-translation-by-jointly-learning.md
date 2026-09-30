# 검토표: bahdanau-2016-neural-machine-translation-by-jointly-learning

- 논문: NEURAL MACHINE TRANSLATION BY JOINTLY LEARNING TO ALIGN AND TRANSLATE
- 학술지·연도: arXiv (Cornell University) 2016  (출처 openalex, DOI 10.48550/arxiv.1409.0473)
- 노트 revision: `496cf63c538948bba214371e88122d2b`  sha256 `696ba2935d85461a`
- 추출: complete, 블록 105개, 생성 경로 single, 제시 105/105
- 모델: qwen3:8b, 검증 수준 structure_checked

## 채우는 방법

주장마다 판정 한 개를 적습니다: **맞음 / 인용틀림 / 수치틀림 / 근거없음 / 무인용**

- `맞음` 수치·조건이 논문과 일치하고 인용한 문단이 그 근거를 담고 있음
- `인용틀림` 값은 맞는데 그 값이 없는 문단을 가리킴
- `수치틀림` 값이나 실험 조건이 논문과 다름
- `근거없음` 논문에 없는 내용

노트의 표현이 논문과 달라도 뜻이 같으면 `맞음`입니다. 인용된 문단이 길어 잘린 경우 `byeori-local read_paper_context`로 전문을 볼 수 있습니다.

## 1차 검사

`review --audit`을 쓰면 각 주장에 자동 1차 검사 결과가 붙습니다. `flagged`는 **먼저 보셔야 할 것**이라는 뜻이고, `supported`가 맞다는 보장은 아닙니다. 이 검사는 사람이 논문을 읽고 판정한 5개 주장에서 5/5로 일치했지만, 5개는 검사기를 검증할 만한 표본이 아닙니다.

## 핵심 수치

이 논문에서 **반드시 맞아야 하는 주장 3~5개**의 번호를 적어주세요. 이후 모델·프롬프트를 바꿀 때 이 항목들이 기준이 됩니다.

- 
- 
- 

## 2. Key Contributions

### 1. **Soft Alignment Mechanism**: The proposed model uses a soft alignment approach to dynamically select relevant source sentence parts for each target word, avoiding the need for explicit segmentation.

- 1차 검사: **supported**
- 근거로 든 문장: Each time the proposed model generates a word in a translation, it (soft-)searches for a set of positions in a source sentence where the most relevant information is concentrated.

- 판정:
- 메모:

**P0005** (paragraph, INTRODUCTION)

> In order to address this issue, we introduce an extension to the encoder-decoder model which learns to align and translate jointly. Each time the proposed model generates a word in a translation, it (soft-)searches for a set of positions in a source sentence where the most relevant information is concentrated. The model then predicts a target word based on the context vectors associated with these source positions and all the previous generated target words.

### 2. **Improved Long Sentence Handling**: The architecture outperforms traditional encoder-decoder models in translating long sentences, as demonstrated by BLEU scores and qualitative analysis.

- 1차 검사: **supported**
- 근거로 든 문장: the proposed RNNsearch outperforms the conventional RNNencdec

- 판정:
- 메모:

**P0040** (paragraph, QUANTITATIVE RESULTS)

> In Table 1, we list the translation performances measured in BLEU score. It is clear from the table that in all the cases, the proposed RNNsearch outperforms the conventional RNNencdec. More importantly, the performance of the RNNsearch is as high as that of the conventional phrase-based translation system (Moses), when only the sentences consisting of known words are considered. This is a significant achievement, considering that Moses uses a separate monolingual corpus (418M words) in addition to the parallel corpora we used to train the RNNsearch and RNNencdec.

**P0044** (paragraph, LONG SENTENCES)

> As clearly visible from Fig. 2 the proposed model (RNNsearch) is much better than the conventional model (RNNencdec) at translating long sentences. This is likely due to the fact that the RNNsearch does not require encoding a long sentence into a fixed-length vector perfectly, but only accurately encoding the parts of the input sentence that surround a particular word.

### 3. **Comparable Performance to Phrase-Based Systems**: The model achieves translation performance comparable to conventional phrase-based systems (Moses) on English-to-French tasks.

- 1차 검사: **supported**
- 근거로 든 문장: the performance of the RNNsearch is as high as that of the conventional phrase-based translation system (Moses)

- 판정:
- 메모:

**P0040** (paragraph, QUANTITATIVE RESULTS)

> In Table 1, we list the translation performances measured in BLEU score. It is clear from the table that in all the cases, the proposed RNNsearch outperforms the conventional RNNencdec. More importantly, the performance of the RNNsearch is as high as that of the conventional phrase-based translation system (Moses), when only the sentences consisting of known words are considered. This is a significant achievement, considering that Moses uses a separate monolingual corpus (418M words) in addition to the parallel corpora we used to train the RNNsearch and RNNencdec.

### 4. **Joint Training of Alignment and Translation**: The alignment model is trained jointly with the translation system, allowing gradients to propagate through soft alignments.

- 1차 검사: **supported**
- 근거로 든 문장: the alignment model directly computes a soft alignment, which allows the gradient of the cost function to be backpropagated through

- 판정:
- 메모:

**P0025** (paragraph, LEARNING TO ALIGN AND TRANSLATE)

> We parametrize the alignment model a as a feedforward neural network which is jointly trained with all the other components of the proposed system. Note that unlike in traditional machine translation, the alignment is not considered to be a latent variable. Instead, the alignment model directly computes a soft alignment, which allows the gradient of the cost function to be backpropagated through. This gradient can be used to train the alignment model as well as the whole translation model jointly.

## 3. Methodology and Architecture

### 5. **Bidirectional RNN Encoder**: The encoder uses a bidirectional RNN (BiRNN) to generate annotations for each source word, capturing both preceding and following context.

- 1차 검사: **supported**
- 근거로 든 문장: we propose to use a bidirectional RNN (BiRNN, Schuster and Paliwal, 1997)

- 판정:
- 메모:

**P0028** (paragraph, ENCODER: BIDIRECTIONAL RNN FOR ANNOTATING SEQUENCES)

> The usual RNN, described in Eq. ( 1), reads an input sequence x in order starting from the first symbol x 1 to the last one x Tx . However, in the proposed scheme, we would like the annotation of each word to summarize not only the preceding words, but also the following words. Hence, we propose to use a bidirectional RNN (BiRNN, Schuster and Paliwal, 1997), which has been successfully used recently in speech recognition (see, e.g., Graves et al., 2013).

### 6. **Attention-Based Decoder**: The decoder computes context vectors by weighting annotations using an alignment model, which scores the relevance of source words to the current target word.

- 1차 검사: **supported**
- 근거로 든 문장: where e ij = a(s i-1 , h j ) is an alignment model which scores how well the inputs around position j and the output at position i match

- 판정:
- 메모:

**P0024** (paragraph, LEARNING TO ALIGN AND TRANSLATE)

> where e ij = a(s i-1 , h j ) is an alignment model which scores how well the inputs around position j and the output at position i match. The score is based on the RNN hidden state s i-1 (just before emitting y i , Eq. ( 4)) and the j-th annotation h j of the input sentence.

### 7. **Soft Alignment Computation**: The alignment weights α_ij are derived from the RNN hidden state and annotations, enabling the model to focus on relevant source segments.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 인용틀림
- 메모: 인용한 P0022는 문맥벡터가 annotation의 가중합이라는 문장뿐임. α가 RNN 은닉상태와 annotation에서 유도된다는 정렬 모델 설명은 이어지는 문단에 있음.
- 판정자: 보조 (사람 확인 필요)

**P0022** (paragraph, LEARNING TO ALIGN AND TRANSLATE)

> The context vector c i is, then, computed as a weighted sum of these annotations h i :

### 8. **Model Variants**: Two variants (RNNencdec-30, RNNencdec-50, RNNsearch-30, RNNsearch-50) were trained with varying maximum sentence lengths.

- 1차 검사: **supported**
- 근거로 든 문장: We train each model twice: first with the sentences of length up to 30 words (RNNencdec-30, RNNsearch-30) and then with the sentences of length up to 50 word (RNNencdec-50, RNNsearch-50).

- 판정:
- 메모:

**P0035** (paragraph, MODELS)

> We train two types of models. The first one is an RNN Encoder-Decoder (RNNencdec, Cho et al., 2014a), and the other is the proposed model, to which we refer as RNNsearch. We train each model twice: first with the sentences of length up to 30 words (RNNencdec-30, RNNsearch-30) and then with the sentences of length up to 50 word (RNNencdec-50, RNNsearch-50).

## 4. Key Results and Benchmarks

### 9. **BLEU Scores**: RNNsearch models outperform RNNencdec models across all sentence lengths. For example, RNNsearch-50 achieves 26.75 BLEU score on all sentences and 34.16 on sentences without unknown words, compared to RNNencdec-50’s 17.82 and 26.71, respectively.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: RNNsearch-50 achieves 26.75 BLEU score on all sentences and 34.16 on sentences without unknown words, compared to RNNencdec-50’s 17.82 and 26.71, respectively.

- 판정: 맞음
- 메모: 인용한 P0097이 Table 1이고 RNNencdec-50 17.82|26.71, RNNsearch-50 26.75|34.16이 짝까지 정확히 있음. 1차 검사의 인용문 축자 실패.
- 판정자: 보조 (사람 확인 필요)

**P0097** (table, Body)

> Table 1 : Model | All | No UNK • RNNencdec-30 13.93 | 24.19 RNNsearch-30 21.50 | 31.44 RNNencdec-50 17.82 | 26.71 RNNsearch-50 26.75 | 34.16 RNNsearch-50 | 28.45 | 36.15 Moses | 33.30 | 35.63

### 10. **Phrase-Based Comparison**: RNNsearch-50’s performance (34.16 BLEU) is close to Moses’ 35.63 on sentences without unknown words.

- 1차 검사: **flagged** — cited elsewhere: 50 as 50, 34.16 as 34.16, 35.63 as 35.63  (모델: supported)
- 근거로 든 문장: the performance of the RNNsearch is as high as that of the conventional phrase-based translation system (Moses)

- 판정: 인용틀림
- 메모: 정성 서술('RNNsearch is as high as Moses when only sentences consisting of known words are considered')은 인용한 P0040에 있음. 그러나 34.16·35.63은 Table 1(P0097)에 있고 그 문단을 인용하지 않았음.
- 판정자: 보조 (사람 확인 필요)

**P0040** (paragraph, QUANTITATIVE RESULTS)

> In Table 1, we list the translation performances measured in BLEU score. It is clear from the table that in all the cases, the proposed RNNsearch outperforms the conventional RNNencdec. More importantly, the performance of the RNNsearch is as high as that of the conventional phrase-based translation system (Moses), when only the sentences consisting of known words are considered. This is a significant achievement, considering that Moses uses a separate monolingual corpus (418M words) in addition to the parallel corpora we used to train the RNNsearch and RNNencdec.

### 11. **Qualitative Alignment Analysis**: Soft alignments from RNNsearch match human intuition, correctly aligning phrases like [European Economic Area] to [zone économique européenne].

- 1차 검사: **supported**
- 근거로 든 문장: The RNNsearch was able to correctly align [zone] with [Area], jumping over the two words ([European] and [Economic]), and then looked one word back at a time to complete the whole phrase [zone économique européenne].

- 판정:
- 메모:

**P0043** (paragraph, ALIGNMENT)

> We can see from the alignments in Fig. 3 that the alignment of words between English and French is largely monotonic. We see strong weights along the diagonal of each matrix. However, we also observe a number of non-trivial, non-monotonic alignments. Adjectives and nouns are typically ordered differently between French and English, and we see an example in Fig. 3 (a). From this figure, we see that the model correctly translates a phrase [European Economic Area] into [zone économique européen]. The RNNsearch was able to correctly align [zone] with [Area], jumping over the two words ([European] and [Economic]), and then looked one word back at a time to complete the whole phrase [zone économique européenne]. The strength of the soft-alignment, opposed to a hard-alignment, is evident, for instance, from Fig. 3 (d). Consider the source phrase [the man] which was translated into [l' homme]. Any hard alignment will map [the] to [l'] and [man] to [homme]. This is not helpful for translation, as one must consider the word following [the] to determine whether it should be translated into [le], [la], [les] or [l']. Our soft-alignment solves this issue naturally by letting the model look at both [the] and [man], and in this example, we see that the model was able to correctly translate [the] into [l']. We observe similar behaviors in all the presented cases in Fig. 3. An additional benefit of the soft alignment is that it naturally deals with source and target phrases of different lengths, without requiring a counter-intuitive way of mapping some words to or from nowhere ([NULL]) (see, e.g., Chapters 4 and 5 of Koehn, 2010).

### 12. **Robustness to Length**: RNNsearch-50 maintains performance on sentences up to 50 words, while RNNencdec-50 shows significant degradation.

- 1차 검사: **supported**
- 근거로 든 문장: RNNsearch-50, especially, shows no performance deterioration even with sentences of length 50 or more.

- 판정:
- 메모:

**P0041** (paragraph, QUANTITATIVE RESULTS)

> The agreement on the European Economic Area was signed in August 1992 . <end> L' accord sur la zone économique européenne a été signé en août 1992 . <end> It should be noted that the marine environment is the least known of environments . <end> Il convient de noter que l' environnement marin est le moins connu de l' environnement . <end> (a) (b) Destruction of the equipment means that Syria can no longer produce new chemical weapons . <end> La destruction de l' équipement signifie que la Syrie ne peut plus produire de nouvelles armes chimiques . <end> " This will change my future with my family , " the man said . <end> " Cela va changer mon avenir avec ma famille " , a dit l' homme . <end> One of the motivations behind the proposed approach was the use of a fixed-length context vector in the basic encoder-decoder approach. We conjectured that this limitation may make the basic encoder-decoder approach to underperform with long sentences. In Fig. 2, we see that the performance of RNNencdec dramatically drops as the length of the sentences increases. On the other hand, both RNNsearch-30 and RNNsearch-50 are more robust to the length of the sentences. RNNsearch-50, especially, shows no performance deterioration even with sentences of length 50 or more. This superiority of the proposed model over the basic encoder-decoder is further confirmed by the fact that the RNNsearch-30 even outperforms RNNencdec-50 (see Table 1). tokens when only the sentences having no unknown words were evaluated (last column).

## 5. Limitations and Future Work

### 13. **Unknown Words**: The model struggles with rare or unknown words, as evidenced by lower BLEU scores on sentences containing unknown words.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 인용틀림
- 메모: 미지 단어가 있으면 성능이 낮다는 근거는 Table 1(P0097)의 All 대 No UNK 열임. 인용한 P0040은 'known words만 고려하면 Moses와 대등하다'는 서술이라 이 주장을 직접 진술하지 않음.
- 판정자: 보조 (사람 확인 필요)

**P0040** (paragraph, QUANTITATIVE RESULTS)

> In Table 1, we list the translation performances measured in BLEU score. It is clear from the table that in all the cases, the proposed RNNsearch outperforms the conventional RNNencdec. More importantly, the performance of the RNNsearch is as high as that of the conventional phrase-based translation system (Moses), when only the sentences consisting of known words are considered. This is a significant achievement, considering that Moses uses a separate monolingual corpus (418M words) in addition to the parallel corpora we used to train the RNNsearch and RNNencdec.

### 14. **Scalability**: The attention mechanism may limit applicability to tasks requiring processing of very long sequences.

- 1차 검사: **supported**
- 근거로 든 문장: However, this may limit the applicability of the proposed scheme to other tasks.

- 판정:
- 메모:

**P0060** (paragraph, LEARNING TO ALIGN)

> Our approach, on the other hand, requires computing the annotation weight of every word in the source sentence for each word in the translation. This drawback is not severe with the task of translation in which most of input and output sentences are only 15-40 words. However, this may limit the applicability of the proposed scheme to other tasks.

### 15. **Future Directions**: Improving handling of unknown words and exploring extensions to other language pairs or domains are suggested.

- 1차 검사: **supported**
- 근거로 든 문장: One of challenges left for the future is to better handle unknown, or rare words.

- 판정:
- 메모:

**P0068** (paragraph, CONCLUSION)

> One of challenges left for the future is to better handle unknown, or rare words. This will be required for the model to be more widely used and to match the performance of current state-of-the-art machine translation systems in all contexts.

