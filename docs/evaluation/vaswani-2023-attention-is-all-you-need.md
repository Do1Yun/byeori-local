# 검토표: vaswani-2023-attention-is-all-you-need

- 논문: Attention Is All You Need
- 학술지·연도:  2023  (출처 openalex, DOI 10.65215/2q58a426)
- 노트 revision: `349b48ec088f4724a3725235b6c71e9f`  sha256 `e311798e2f03a967`
- 추출: complete, 블록 85개, 생성 경로 single, 제시 85/85
- 모델: qwen3:8b, 검증 수준 structure_checked

## 채우는 방법

주장마다 판정 한 개를 적습니다: **맞음 / 인용틀림 / 수치틀림 / 근거없음**

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

### 1. **Transformer Architecture**: A novel model replacing recurrence and convolutions with self-attention, enabling parallelization and better handling of long-range dependencies.

- 1차 검사: **supported**
- 근거로 든 문장: We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.

- 판정: 
- 메모: 

**P0001** (abstract, Abstract)

> The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 Englishto-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.

### 2. **Attention Mechanisms**: Scaled dot-product attention and multi-head attention improve model performance, with the latter mitigating reduced resolution from averaging.

- 1차 검사: **supported**
- 근거로 든 문장: We call our particular attention "Scaled Dot-Product Attention

- 판정: 
- 메모: 

**P0016** (paragraph, Scaled Dot-Product Attention)

> We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension d k , and values of dimension d v . We compute the dot products of the query with all keys, divide each by √ d k , and apply a softmax function to obtain the weights on the values.

**P0021** (paragraph, Multi-Head Attention)

> Instead of performing a single attention function with d model -dimensional keys, values and queries, we found it beneficial to linearly project the queries, keys and values h times with different, learned linear projections to d k , d k and d v dimensions, respectively. On each of these projected versions of queries, keys and values we then perform the attention function in parallel, yielding d v -dimensional output values. These are concatenated and once again projected, resulting in the final values, as depicted in Figure 2.

### 3. **Positional Encoding**: Sinusoidal functions inject positional information into embeddings, allowing extrapolation to longer sequences.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 
- 메모: 

**P0038** (paragraph, Positional Encoding)

> In this work, we use sine and cosine functions of different frequencies:

### 4. **State-of-the-Art Results**: Achieved 28.4 BLEU on English-to-German and 41.8 BLEU on English-to-French, surpassing prior models and ensembles.

- 1차 검사: **flagged** — cited elsewhere: 41.8 as 41.8  (모델: supported)
- 근거로 든 문장: establishing a new state-of-the-art BLEU score of 28.4

- 판정: 
- 메모: 

**P0055** (paragraph, Machine Translation)

> On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles) by more than 2.0 BLEU, establishing a new state-of-the-art BLEU score of 28.4. The configuration of this model is listed in the bottom line of Table 3. Training took 3.5 days on 8 P100 GPUs. Even our base model surpasses all previously published models and ensembles, at a fraction of the training cost of any of the competitive models.

**P0056** (paragraph, Machine Translation)

> On the WMT 2014 English-to-French translation task, our big model achieves a BLEU score of 41.0, outperforming all of the previously published single models, at less than 1/4 the training cost of the previous state-of-the-art model. The Transformer (big) model trained for English-to-French used dropout rate P drop = 0.1, instead of 0.3.

## 3. Methodology and Architecture

### 5. **Encoder-Decoder Structure**: Stacked self-attention and feed-forward layers for both encoder and decoder.

- 1차 검사: **supported**
- 근거로 든 문장: The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder

- 판정: 
- 메모: 

**P0012** (paragraph, Model Architecture)

> Most competitive neural sequence transduction models have an encoder-decoder structure [5,2,35]. Here, the encoder maps an input sequence of symbol representations (x 1 , ..., x n ) to a sequence of continuous representations z = (z 1 , ..., z n ). Given z, the decoder then generates an output sequence (y 1 , ..., y m ) of symbols one element at a time. At each step the model is auto-regressive [10], consuming the previously generated symbols as additional input when generating the next. The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, shown in the left and right halves of Figure 1, respectively.

### 6. **Encoder Stack**: 6 identical layers with multi-head self-attention and position-wise feed-forward networks, using residual connections and layer normalization.

- 1차 검사: **supported**
- 근거로 든 문장: The encoder is composed of a stack of N = 6 identical layers.

- 판정: 
- 메모: 

**P0013** (paragraph, Encoder and Decoder Stacks)

> Encoder: The encoder is composed of a stack of N = 6 identical layers. Each layer has two sub-layers. The first is a multi-head self-attention mechanism, and the second is a simple, positionwise fully connected feed-forward network. We employ a residual connection [11] around each of the two sub-layers, followed by layer normalization [1]. That is, the output of each sub-layer is LayerNorm(x + Sublayer(x)), where Sublayer(x) is the function implemented by the sub-layer itself. To facilitate these residual connections, all sub-layers in the model, as well as the embedding layers, produce outputs of dimension d model = 512.

### 7. **Decoder Stack**: 6 identical layers with multi-head self-attention, encoder-decoder attention, and masked self-attention to preserve auto-regressive properties.

- 1차 검사: **supported**
- 근거로 든 문장: The decoder is also composed of a stack of N = 6 identical layers.

- 판정: 
- 메모: 

**P0014** (paragraph, Encoder and Decoder Stacks)

> Decoder: The decoder is also composed of a stack of N = 6 identical layers. In addition to the two sub-layers in each encoder layer, the decoder inserts a third sub-layer, which performs multi-head attention over the output of the encoder stack. Similar to the encoder, we employ residual connections around each of the sub-layers, followed by layer normalization. We also modify the self-attention sub-layer in the decoder stack to prevent positions from attending to subsequent positions. This masking, combined with fact that the output embeddings are offset by one position, ensures that the predictions for position i can depend only on the known outputs at positions less than i.

### 8. **Positional Encoding**: Sinusoidal functions with dimensions $ d_{\text{model}} $, enabling relative position learning.

- 1차 검사: **supported**
- 근거로 든 문장: positional encodings have the same dimension d model as the embeddings

- 판정: 
- 메모: 

**P0037** (paragraph, Positional Encoding)

> Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or absolute position of the tokens in the sequence. To this end, we add "positional encodings" to the input embeddings at the bottoms of the encoder and decoder stacks. The positional encodings have the same dimension d model as the embeddings, so that the two can be summed. There are many choices of positional encodings, learned and fixed [9].

### 9. **Multi-Head Attention**: 8 parallel attention heads with reduced dimensionality, maintaining computational efficiency.

- 1차 검사: **supported**
- 근거로 든 문장: In this work we employ h = 8 parallel attention layers, or heads

- 판정: 
- 메모: 

**P0025** (paragraph, Multi-Head Attention)

> In this work we employ h = 8 parallel attention layers, or heads. For each of these we use

## 4. Key Results and Benchmarks

### 10. **BLEU Scores**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 11. **English-to-German**: 28.4 (Transformer (big)) vs. 23.75 (ByteNet).

- 1차 검사: **flagged** — cited elsewhere: 23.75 as 23.75  (모델: supported)
- 근거로 든 문장: establishing a new state-of-the-art BLEU score of 28.4

- 판정: 
- 메모: 

**P0055** (paragraph, Machine Translation)

> On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles) by more than 2.0 BLEU, establishing a new state-of-the-art BLEU score of 28.4. The configuration of this model is listed in the bottom line of Table 3. Training took 3.5 days on 8 P100 GPUs. Even our base model surpasses all previously published models and ensembles, at a fraction of the training cost of any of the competitive models.

### 12. **English-to-French**: 41.8 (Transformer (big)) vs. 39.2 (Deep-Att + PosUnk).

- 1차 검사: **flagged** — cited elsewhere: 41.8 as 41.8, 39.2 as 39.2  (모델: not_in_paragraph)
- 근거로 든 문장: none

- 판정: 
- 메모: 

**P0056** (paragraph, Machine Translation)

> On the WMT 2014 English-to-French translation task, our big model achieves a BLEU score of 41.0, outperforming all of the previously published single models, at less than 1/4 the training cost of the previous state-of-the-art model. The Transformer (big) model trained for English-to-French used dropout rate P drop = 0.1, instead of 0.3.

### 13. **Training Costs**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 14. Transformer (big) trained for 3.5 days on 8 GPUs, vs. 3.5 days for ConvS2S Ensemble.

- 1차 검사: **supported**
- 근거로 든 문장: The big models were trained for 300,000 steps (3.5 days).

- 판정: 
- 메모: 

**P0050** (paragraph, Hardware and Schedule)

> We trained our models on one machine with 8 NVIDIA P100 GPUs. For our base models using the hyperparameters described throughout the paper, each training step took about 0.4 seconds. We trained the base models for a total of 100,000 steps or 12 hours. For our big models,(described on the bottom line of table 3), step time was 1.0 seconds. The big models were trained for 300,000 steps (3.5 days).

**P0078** (table, Body)

> Table 2 : Model | BLEU EN-DE EN-FR | Training Cost (FLOPs) EN-DE EN-FR ByteNet [18] | 23.75 | | Deep-Att + PosUnk [39] | | 39.2 | 1.0 • 10 20 GNMT + RL [38] | 24.6 | 39.92 | 2.3 • 10 19 1.4 • 10 20 ConvS2S [9] | 25.16 | 40.46 | 9.6 • 10 18 1.5 • 10 20 MoE [32] | 26.03 | 40.56 | 2.0 • 10 19 1.2 • 10 20 Deep-Att + PosUnk Ensemble [39] | | 40.4 | 8.0 • 10 20 GNMT + RL Ensemble [38] | 26.30 | 41.16 | 1.8 • 10 20 1.1 • 10 21 ConvS2S Ensemble [9] | 26.36 | 41.29 | 7.7 • 10 19 1.2 • 10 21 Transformer (base model) | 27.3 | 38.1 | 3.3 • 10 18 Transformer (big) | 28.4 | 41.8 | 2.3 • 10 19

### 15. **Efficiency**: Self-attention reduces sequential operations to a constant, unlike recurrent layers with $ O(n) $ complexity.

- 1차 검사: **supported**
- 근거로 든 문장: a self-attention layer connects all positions with a constant number of sequentially executed operations

- 판정: 
- 메모: 

**P0044** (paragraph, Why Self-Attention)

> As noted in Table 1, a self-attention layer connects all positions with a constant number of sequentially executed operations, whereas a recurrent layer requires O(n) sequential operations. In terms of computational complexity, self-attention layers are faster than recurrent layers when the sequence length n is smaller than the representation dimensionality d, which is most often the case with sentence representations used by state-of-the-art models in machine translations, such as word-piece [38] and byte-pair [31] representations. To improve computational performance for tasks involving very long sequences, self-attention could be restricted to considering only a neighborhood of size r in the input sequence centered around the respective output position. This would increase the maximum path length to O(n/r). We plan to investigate this approach further in future work.

## 5. Limitations and Future Work

### 16. **Long-Sequence Challenges**: Self-attention may struggle with very long sequences; restricted attention mechanisms could improve scalability.

- 1차 검사: **supported**
- 근거로 든 문장: To improve computational performance for tasks involving very long sequences, self-attention could be restricted to considering only a neighborhood of size r in the input sequence centered around the respective output position.

- 판정: 
- 메모: 

**P0044** (paragraph, Why Self-Attention)

> As noted in Table 1, a self-attention layer connects all positions with a constant number of sequentially executed operations, whereas a recurrent layer requires O(n) sequential operations. In terms of computational complexity, self-attention layers are faster than recurrent layers when the sequence length n is smaller than the representation dimensionality d, which is most often the case with sentence representations used by state-of-the-art models in machine translations, such as word-piece [38] and byte-pair [31] representations. To improve computational performance for tasks involving very long sequences, self-attention could be restricted to considering only a neighborhood of size r in the input sequence centered around the respective output position. This would increase the maximum path length to O(n/r). We plan to investigate this approach further in future work.

### 17. **Task Generalization**: While successful in translation, further exploration is needed for tasks like image or audio processing.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: We plan to apply them to other tasks. We plan to extend the Transformer to problems involving input and output modalities other than text

- 판정: 
- 메모: 

**P0069** (paragraph, Conclusion)

> We are excited about the future of attention-based models and plan to apply them to other tasks. We plan to extend the Transformer to problems involving input and output modalities other than text and to investigate local, restricted attention mechanisms to efficiently handle large inputs and outputs such as images, audio and video. Making generation less sequential is another research goals of ours.

### 18. **Parameter Efficiency**: Larger models (e.g., big Transformer) outperform smaller variants, suggesting scalability benefits.

- 1차 검사: **supported**
- 근거로 든 문장: bigger models are better

- 판정: 
- 메모: 

**P0061** (paragraph, Model Variations)

> In Table 3 rows (B), we observe that reducing the attention key size d k hurts model quality. This suggests that determining compatibility is not easy and that a more sophisticated compatibility function than dot product may be beneficial. We further observe in rows (C) and (D) that, as expected, bigger models are better, and dropout is very helpful in avoiding over-fitting. In row (E) we replace our sinusoidal positional encoding with learned positional embeddings [9], and observe nearly identical results to the base model.

