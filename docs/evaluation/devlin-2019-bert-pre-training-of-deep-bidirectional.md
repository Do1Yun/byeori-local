# 검토표: devlin-2019-bert-pre-training-of-deep-bidirectional

- 논문: BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding
- 학술지·연도:  2019  (출처 extraction, DOI -)
- 노트 revision: `b28573663df9416fa802350ff8b29136`  sha256 `acdf1a3424996347`
- 추출: complete, 블록 131개, 생성 경로 single, 제시 131/131
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

### 1. **Bidirectional Pre-training**: BERT introduces masked language modeling (MLM) to enable deep bidirectional representations, unlike unidirectional models (Peters et al., 2018a; Radford et al., 2018).

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 2. **State-of-the-Art Performance**: Achieves 80.5% GLUE score (7.7% absolute improvement), 86.7% MultiNLI accuracy (4.6% improvement), 93.2 SQuAD v1.1 F1 (1.5 point improvement), and 83.1 SQuAD v2.0 F1 (5.1 point improvement).

- 1차 검사: **supported**
- 근거로 든 문장: obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement) and SQuAD v2.0 Test F1 to 83.1 (5.1 point absolute improvement)

- 판정: 
- 메모: 

**P0002** (abstract, Abstract)

> BERT is conceptually simple and empirically powerful. It obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement) and SQuAD v2.0 Test F1 to 83.1 (5.1 point absolute improvement).

### 3. **Reduced Task-Specific Architectures**: BERT’s fine-tuning approach minimizes the need for task-specific modifications, achieving SOTA on sentence-level and token-level tasks.

- 1차 검사: **supported**
- 근거로 든 문장: BERT is the first finetuning based representation model that achieves state-of-the-art performance on a large suite of sentence-level and token-level tasks, outperforming many task-specific architectures.

- 판정: 
- 메모: 

**P0008** (paragraph, Introduction)

> • We show that pre-trained representations reduce the need for many heavily-engineered taskspecific architectures. BERT is the first finetuning based representation model that achieves state-of-the-art performance on a large suite of sentence-level and token-level tasks, outperforming many task-specific architectures.

### 4. **Unified Architecture**: BERT’s pre-trained and fine-tuned architectures are minimal, enabling adaptability across diverse tasks.

- 1차 검사: **supported**
- 근거로 든 문장: A distinctive feature of BERT is its unified architecture across different tasks.

- 판정: 
- 메모: 

**P0022** (paragraph, BERT)

> A distinctive feature of BERT is its unified architecture across different tasks. There is mini-mal difference between the pre-trained architecture and the final downstream architecture.

## 3. Methodology and Architecture

### 5. **Model Architecture**: BERT uses a multi-layer bidirectional Transformer encoder (Vaswani et al., 2017), with BERT BASE (12 layers, 768 hidden units, 12 heads, 110M params) and BERT LARGE (24 layers, 1024 hidden units, 16 heads, 340M params).

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: We primarily report results on two model sizes: BERT BASE (L=12, H=768, A=12, Total Parameters=110M) and BERT LARGE (L=24, H=1024, A=16, Total Parameters=340M).

- 판정: 
- 메모: 

**P0023** (paragraph, BERT)

> Model Architecture BERT's model architecture is a multi-layer bidirectional Transformer encoder based on the original implementation described in Vaswani et al. (2017) and released in the tensor2tensor library.foot_0 Because the use of Transformers has become common and our implementation is almost identical to the original, we will omit an exhaustive background description of the model architecture and refer readers to Vaswani et al. (2017) as well as excellent guides such as "The Annotated Transformer." 2In this work, we denote the number of layers (i.e., Transformer blocks) as L, the hidden size as H, and the number of self-attention heads as A. 3We primarily report results on two model sizes: BERT BASE (L=12, H=768, A=12, Total Param-eters=110M) and BERT LARGE (L=24, H=1024, A=16, Total Parameters=340M).

### 6. **Input Representation**: Combines token embeddings (WordPiece), segment embeddings (for sentence pairs), and position embeddings. Special tokens [CLS] (classification) and [SEP] (sentence separation) are used.

- 1차 검사: **supported**
- 근거로 든 문장: our input representation is able to unambiguously represent both a single sentence and a pair of sentences

- 판정: 
- 메모: 

**P0024** (paragraph, BERT)

> BERT BASE was chosen to have the same model size as OpenAI GPT for comparison purposes. Critically, however, the BERT Transformer uses bidirectional self-attention, while the GPT Transformer uses constrained self-attention where every token can only attend to context to its left. 4 Input/Output Representations To make BERT handle a variety of down-stream tasks, our input representation is able to unambiguously represent both a single sentence and a pair of sentences (e.g., Question, Answer ) in one token sequence. Throughout this work, a "sentence" can be an arbitrary span of contiguous text, rather than an actual linguistic sentence. A "sequence" refers to the input token sequence to BERT, which may be a single sentence or two sentences packed together.

### 7. **Pre-training Tasks**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 8. **Masked Language Model (MLM)**: 15% of tokens are masked, and the model predicts them using bidirectional context.

- 1차 검사: **supported**
- 근거로 든 문장: In all of our experiments, we mask 15% of all WordPiece tokens in each sequence at random.

- 판정: 
- 메모: 

**P0030** (paragraph, Pre-training BERT)

> In order to train a deep bidirectional representation, we simply mask some percentage of the input tokens at random, and then predict those masked tokens. We refer to this procedure as a "masked LM" (MLM), although it is often referred to as a Cloze task in the literature (Taylor, 1953). In this case, the final hidden vectors corresponding to the mask tokens are fed into an output softmax over the vocabulary, as in a standard LM. In all of our experiments, we mask 15% of all WordPiece tokens in each sequence at random. In contrast to denoising auto-encoders (Vincent et al., 2008), we only predict the masked words rather than reconstructing the entire input.

### 9. **Next Sentence Prediction (NSP)**: Predicts if a sentence B follows sentence A, with 50% IsNext/NotNext labels.

- 1차 검사: **supported**
- 근거로 든 문장: 50% of the time B is the actual next sentence that follows A (labeled as IsNext), and 50% of the time it is a random sentence from the corpus (labeled as NotNext)

- 판정: 
- 메모: 

**P0032** (paragraph, Pre-training BERT)

> Task #2: Next Sentence Prediction (NSP) Many important downstream tasks such as Question Answering (QA) and Natural Language Inference (NLI) are based on understanding the relationship between two sentences, which is not directly captured by language modeling. In order to train a model that understands sentence relationships, we pre-train for a binarized next sentence prediction task that can be trivially generated from any monolingual corpus. Specifically, when choosing the sentences A and B for each pretraining example, 50% of the time B is the actual next sentence that follows A (labeled as IsNext), and 50% of the time it is a random sentence from the corpus (labeled as NotNext). As we show in Figure 1, C is used for next sentence prediction (NSP). 5 Despite its simplicity, we demonstrate in Section 5.1 that pre-training towards this task is very beneficial to both QA and NLI. 6 5 The final model achieves 97%-98% accuracy on NSP. 6 The vector C is not a meaningful sentence representation without fine-tuning, since it was trained with NSP.

### 10. **Fine-tuning**: Adds task-specific output layers (e.g., classification for [CLS] or token-level outputs for QA) and fine-tunes all parameters.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: For each task, we simply plug in the task-specific inputs and outputs into BERT and fine-tune all the parameters end-to-end.

- 판정: 
- 메모: 

**P0038** (paragraph, Fine-tuning BERT)

> For each task, we simply plug in the taskspecific inputs and outputs into BERT and finetune all the parameters end-to-end. At the input, sentence A and sentence B from pre-training are analogous to (1) sentence pairs in paraphrasing, (2) hypothesis-premise pairs in entailment, (3) question-passage pairs in question answering, and (4) a degenerate text-∅ pair in text classification or sequence tagging. At the output, the token representations are fed into an output layer for tokenlevel tasks, such as sequence tagging or question answering, and the [CLS] representation is fed into an output layer for classification, such as entailment or sentiment analysis.

## 4. Key Results and Benchmarks

### 11. **GLUE Benchmark**: BERT BASE improves average accuracy by 4.5% over prior SOTA, reaching 84.4% on MNLI and 92.7% on SST-2. BERT LARGE achieves 86.7% MNLI accuracy and 94.9% SST-2 accuracy.

- 1차 검사: **flagged** — cited elsewhere: 84.4 as 84.4, 92.7 as 92.7, 86.7 as 86.7, 94.9 as 94.9  (모델: supported)
- 근거로 든 문장: obtaining 4.5% and 7.0% respective average accuracy improvement over the prior state of the art

- 판정: 
- 메모: 

**P0042** (paragraph, GLUE)

> To fine-tune on GLUE, we represent the input sequence (for single sentence or sentence pairs) as described in Section 3, and use the final hidden vector C ∈ R H corresponding to the first input token ([CLS]) as the aggregate representation. The only new parameters introduced during fine-tuning are classification layer weights W ∈ R K×H , where K is the number of labels. We compute a standard classification loss with C and W , i.e., log(softmax(CW T )). We use a batch size of 32 and fine-tune for 3 epochs over the data for all GLUE tasks. For each task, we selected the best fine-tuning learning rate (among 5e-5, 4e-5, 3e-5, and 2e-5) on the Dev set. Additionally, for BERT LARGE we found that finetuning was sometimes unstable on small datasets, so we ran several random restarts and selected the best model on the Dev set. With random restarts, we use the same pre-trained checkpoint but perform different fine-tuning data shuffling and classifier layer initialization. 9 Results are presented in Table 1. Both BERT BASE and BERT LARGE outperform all systems on all tasks by a substantial margin, obtaining 4.5% and 7.0% respective average accuracy improvement over the prior state of the art. Note that BERT BASE and OpenAI GPT are nearly identical in terms of model architecture apart from the attention masking. For the largest and most widely reported GLUE task, MNLI, BERT obtains a 4.6% absolute accuracy improvement. On the official GLUE leaderboard 10 , BERT LARGE obtains a score of 80.5, compared to OpenAI GPT, which obtains 72.8 as of the date of writing.

### 12. **SQuAD v1.1**: BERT LARGE achieves 93.2 F1, outperforming prior systems by +1.5 F1 in ensembling and +1.3 F1 as a single model.

- 1차 검사: **flagged** — cited elsewhere: 1.1 as 1.1, 93.2 as 93.2  (모델: supported)
- 근거로 든 문장: Our best performing system outperforms the top leaderboard system by +1.5 F1 in ensembling and +1.3 F1 as a single system.

- 판정: 
- 메모: 

**P0047** (paragraph, SQuAD v1.1)

> As shown in Figure 1, in the question answering task, we represent the input question and passage as a single packed sequence, with the question using the A embedding and the passage using the B embedding. We only introduce a start vector S ∈ R H and an end vector E ∈ R H during fine-tuning. The probability of word i being the start of the answer span is computed as a dot product between T i and S followed by a softmax over all of the words in the paragraph: P i = e S•T i j e S•T j . The analogous formula is used for the end of the answer span. The score of a candidate span from position i to position j is defined as S•T i + E•T j , and the maximum scoring span where j ≥ i is used as a prediction. The training objective is the sum of the log-likelihoods of the correct start and end positions. We fine-tune for 3 epochs with a learning rate of 5e-5 and a batch size of 32.

**P0049** (paragraph, SQuAD v1.1)

> Our best performing system outperforms the top leaderboard system by +1.5 F1 in ensembling and +1.3 F1 as a single system. Table 3: SQuAD 2.0 results. We exclude entries that use BERT as one of their components.

### 13. **SQuAD v2.0**: BERT LARGE improves F1 by 5.1 points over prior SOTA.

- 1차 검사: **flagged** — cited elsewhere: 2.0 as 2.0  (모델: supported)
- 근거로 든 문장: We observe a +5.1 F1 improvement over the previous best system.

- 판정: 
- 메모: 

**P0053** (paragraph, SQuAD v2.0)

> The results compared to prior leaderboard entries and top published work (Sun et al., 2018;Wang et al., 2018b) are shown in Table 3, excluding systems that use BERT as one of their components. We observe a +5.1 F1 improvement over the previous best system.

### 14. **SWAG**: BERT LARGE outperforms OpenAI GPT by 8.3% and the authors’ baseline ESIM+ELMo by 27.1%.

- 1차 검사: **supported**
- 근거로 든 문장: BERT LARGE outperforms the authors' baseline ESIM+ELMo system by +27.1% and OpenAI GPT by 8.3%

- 판정: 
- 메모: 

**P0056** (paragraph, SWAG)

> We fine-tune the model for 3 epochs with a learning rate of 2e-5 and a batch size of 16. Results are presented in Table 4. BERT LARGE outperforms the authors' baseline ESIM+ELMo system by +27.1% and OpenAI GPT by 8.3%.

### 15. **Model Size Impact**: Larger models (BERT LARGE) show consistent accuracy gains across tasks, even with small training data.

- 1차 검사: **supported**
- 근거로 든 문장: larger models lead to a strict accuracy improvement across all four datasets

- 판정: 
- 메모: 

**P0067** (paragraph, Effect of Model Size)

> Results on selected GLUE tasks are shown in Table 6. In this table, we report the average Dev Set accuracy from 5 random restarts of fine-tuning. We can see that larger models lead to a strict accuracy improvement across all four datasets, even for MRPC which only has 3,600 labeled training examples, and is substantially different from the pre-training tasks. It is also perhaps surprising that we are able to achieve such significant improvements on top of models which are already quite large relative to the existing literature. For example, the largest Transformer explored in Vaswani et al. (2017) is (L=6, H=1024, A=16) with 100M parameters for the encoder, and the largest Transformer we have found in the literature is (L=64, H=512, A=2) with 235M parameters (Al-Rfou et al., 2018). By contrast, BERT BASE contains 110M parameters and BERT LARGE contains 340M parameters.

## 5. Limitations and Future Work

### 16. **Pre-training/Fine-tuning Mismatch**: The [MASK] token is absent during fine-tuning, potentially limiting context integration.

- 1차 검사: **supported**
- 근거로 든 문장: the [MASK] token does not appear during fine-tuning

- 판정: 
- 메모: 

**P0031** (paragraph, Pre-training BERT)

> Although this allows us to obtain a bidirectional pre-trained model, a downside is that we are creating a mismatch between pre-training and fine-tuning, since the [MASK] token does not appear during fine-tuning. To mitigate this, we do not always replace "masked" words with the actual [MASK] token. The training data generator chooses 15% of the token positions at random for prediction. If the i-th token is chosen, we replace the i-th token with (1) the [MASK] token 80% of the time (2) a random token 10% of the time (3) the unchanged i-th token 10% of the time. Then, T i will be used to predict the original token with cross entropy loss. We compare variations of this procedure in Appendix C.2.

### 17. **Training Instability**: BERT LARGE may require random restarts for small datasets.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 
- 메모: 

**P0039** (paragraph, Fine-tuning BERT)

> Compared to pre-training, fine-tuning is relatively inexpensive. All of the results in the paper can be replicated in at most 1 hour on a single Cloud TPU, or a few hours on a GPU, starting from the exact same pre-trained model. 7 We describe the task-specific details in the corresponding subsections of Section 4. More details can be found in Appendix A.5.

### 18. **Future Work**: Addressing the [MASK] token mismatch, exploring more diverse pre-training tasks, and improving efficiency for low-resource tasks.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 
- 메모: 

**P0075** (paragraph, Conclusion)

> Recent empirical improvements due to transfer learning with language models have demonstrated that rich, unsupervised pre-training is an integral part of many language understanding systems. In particular, these results enable even low-resource tasks to benefit from deep unidirectional architectures. Our major contribution is further generalizing these findings to deep bidirectional architectures, allowing the same pre-trained model to successfully tackle a broad set of NLP tasks. to converge. In Section C.1 we demonstrate that MLM does converge marginally slower than a leftto-right model (which predicts every token), but the empirical improvements of the MLM model far outweigh the increased training cost.

