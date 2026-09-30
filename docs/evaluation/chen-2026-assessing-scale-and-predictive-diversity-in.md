# 검토표: chen-2026-assessing-scale-and-predictive-diversity-in

- 논문: Assessing scale and predictive diversity in models for single-cell transcriptomics based on Geneformer
- 학술지·연도: PLoS Computational Biology 2026  (출처 openalex, DOI 10.1371/journal.pcbi.1013701)
- 노트 revision: `77c1ee1a307a4cdca262ee68e43184f6`  sha256 `e5982d998e736c02`
- 추출: complete, 블록 56개, 생성 경로 single, 제시 56/56
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

### 1. **Structural Alignment**: GF CAB mitigates repetitive gene predictions and biases toward high-frequency genes by aligning with the rank-ordered structure of single-cell transcriptomic data.

- 1차 검사: **supported**
- 근거로 든 문장: GF CAB provides a framework for developing more efficient and biologically informative models for single-cell analysis

- 판정:
- 메모:

**P0001** (abstract, Abstract)

> Single-cell transcriptomic data provide critical insights into cellular states and disease mechanisms, and foundation models have recently emerged as powerful tools for learning gene-gene relationships from these data. However, current approaches often overlook key challenges, including the mismatch between model design and the rank-ordered structure of gene expression profiles, as well as the unclear benefits of large-scale pretraining for biological applications. Here, we present GF CAB , a modified modeling framework designed to better capture the structural properties of ranked single-cell transcriptomic data. GF CAB incorporates a cumulative assignment mechanism to suppress repeated gene predictions and a similarity-based regularization strategy to promote diversity in model outputs. Across multiple evaluation settings, including pretraining behavior, biologically relevant classification tasks, and cross-dataset analyzes, GF CAB consistently reduces redundancy and enhances the recovery of low-frequency genes with known functional and disease relevance while maintaining or improving predictive accuracy. In downstream applications, including classification and zero-shot batch effect correction, the model achieves competitive or improved performance compared to existing approaches. We further show that indiscriminately increasing the pretraining data scale does not uniformly improve performance. Instead, models trained on substantially smaller datasets can match or exceed the performance of larger models and often demonstrate improved generalization across datasets. Together, these findings highlight the importance of aligning model design with the intrinsic structure of biological data and suggest that architectural innovation can reduce reliance on large-scale training data. GF CAB provides a framework for developing more efficient and biologically informative models for single-cell analysis, with potential applications in disease characterization and precision biology.

### 2. **Data Scaling Evaluation**: Demonstrates diminishing returns from increasing pretraining data scale, showing smaller datasets (1M) can match or exceed 30M-scale models in performance and generalization.

- 1차 검사: **supported**
- 근거로 든 문장: models trained on 1M profiles consistently matched or outperformed their 30M counterparts

- 판정:
- 메모:

**P0001** (abstract, Abstract)

> Single-cell transcriptomic data provide critical insights into cellular states and disease mechanisms, and foundation models have recently emerged as powerful tools for learning gene-gene relationships from these data. However, current approaches often overlook key challenges, including the mismatch between model design and the rank-ordered structure of gene expression profiles, as well as the unclear benefits of large-scale pretraining for biological applications. Here, we present GF CAB , a modified modeling framework designed to better capture the structural properties of ranked single-cell transcriptomic data. GF CAB incorporates a cumulative assignment mechanism to suppress repeated gene predictions and a similarity-based regularization strategy to promote diversity in model outputs. Across multiple evaluation settings, including pretraining behavior, biologically relevant classification tasks, and cross-dataset analyzes, GF CAB consistently reduces redundancy and enhances the recovery of low-frequency genes with known functional and disease relevance while maintaining or improving predictive accuracy. In downstream applications, including classification and zero-shot batch effect correction, the model achieves competitive or improved performance compared to existing approaches. We further show that indiscriminately increasing the pretraining data scale does not uniformly improve performance. Instead, models trained on substantially smaller datasets can match or exceed the performance of larger models and often demonstrate improved generalization across datasets. Together, these findings highlight the importance of aligning model design with the intrinsic structure of biological data and suggest that architectural innovation can reduce reliance on large-scale training data. GF CAB provides a framework for developing more efficient and biologically informative models for single-cell analysis, with potential applications in disease characterization and precision biology.

**P0011** (paragraph, GF CAB improves masked gene prediction fidelity and reveals diminishing returns from data scaling)

> We next investigated the relationship between data scale and predictive performance. Tracking masked gene prediction accuracy across training steps revealed that performance gains are largely concentrated in the early phase of training, with most improvements achieved within the first ∼30% of total steps, followed by clear diminishing returns (Fig 2E, S1 Fig). Across both architectures, models trained on 1M profiles consistently matched or outperformed their 30M counterparts, indicating that increased data scale does not necessarily yield improved predictive capacity under fixed model capacity. Extending this analysis across a broader range of dataset sizes (10K-30M cells) further confirmed a saturating scaling behavior, with performance gains plateauing beyond the ∼1M regime (Fig 2F, S2 Fig). To further assess architectural scaling, we fixed the pretraining dataset at 30M profiles and systematically increased model capacity ( S3 Fig). Performance improvements were primarily observed in lower-capacity, underparameterized regimes, suggesting that gains diminish once the model approaches saturation relative to the data scale. These results highlight the importance of coordinated scaling between model capacity and data size, rather than independent expansion of either factor. Notably, GF CAB consistently outperformed baseline models across all data and model scales, underscoring the importance of architectural alignment over brute-force scaling. However, we acknowledge the risk that our subsampling strategy may benefit our smaller datasets in their diversity representation compared to curating datasets simply from a more limited number of sources.

### 3. **Architectural Innovation**: Introduces the CAB module, combining cumulative assignment suppression and similarity-based regularization to enhance predictive diversity and biological relevance.

- 1차 검사: **supported**
- 근거로 든 문장: Central to this design is a cumulative assignment and balancing (CAB) module, implemented as a post-prediction processor.

- 판정:
- 메모:

**P0003** (paragraph, Introduction)

> To address these underexplored limitations, we introduce GF CAB , a modified GF architecture designed to better align model behavior with the rank-ordered structure of single-cell transcriptomic data. Central to this design is a cumulative assignment and balancing (CAB) module, implemented as a post-prediction processor. The CAB module incorporates a probability cumulative-assignment mechanism to propagate positional constraints across predictions, ensuring consistency with the non-redundant nature of gene rankings within each cell. In parallel, a similarity-based regularization term penalizes redundant or overly similar probability distributions across gene positions, thereby promoting diversity in predicted gene identities. Together, these components explicitly encode structural priors of the data into the prediction process, mitigating the mismatch introduced by conventional masked language modeling objectives. To further investigate the role of data scale in conjunction with architectural design, we additionally construct a reduced pretraining corpus (Genecorpus-1M) by uniformly subsampling one million profiles from the original Genecorpus-30M, enabling controlled comparisons across different data regimes (Fig 1A).

**P0005** (paragraph, Results)

> GF CAB is a model architecture aligned with rank-ordered single-cell transcriptomic profiles GF CAB is designed to address two key limitations of the original Geneformer (GF) architecture: repetitive gene predictions across masked positions within a single ranked cell profile and a systematic bias toward highly frequent, ubiquitously expressed genes at the expense of rarer but biologically informative signals. These issues arise from the mismatch between the masked language modeling objective and the non-redundant, rank-ordered structure of single-cell transcriptomic data. To mitigate this mismatch, GF CAB operates on the post-BERT probability distributions and introduces a cumulative assignment and balancing (CAB) module to enforce cross-position constraints and promote distributional diversity (Fig 1C; Methods).

## 3. Methodology and Architecture

### 4. **Cumulative Assignment and Balancing (CAB) Module**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 5. Propagates positional constraints across predictions using a blocking vector to suppress repeated gene assignments.

- 1차 검사: **supported**
- 근거로 든 문장: To reduce repetition across masked positions, we introduce a cumulative-assignment mechanism that explicitly propagates information across positions.

- 판정:
- 메모:

**P0005** (paragraph, Results)

> GF CAB is a model architecture aligned with rank-ordered single-cell transcriptomic profiles GF CAB is designed to address two key limitations of the original Geneformer (GF) architecture: repetitive gene predictions across masked positions within a single ranked cell profile and a systematic bias toward highly frequent, ubiquitously expressed genes at the expense of rarer but biologically informative signals. These issues arise from the mismatch between the masked language modeling objective and the non-redundant, rank-ordered structure of single-cell transcriptomic data. To mitigate this mismatch, GF CAB operates on the post-BERT probability distributions and introduces a cumulative assignment and balancing (CAB) module to enforce cross-position constraints and promote distributional diversity (Fig 1C; Methods).

**P0006** (paragraph, Results)

> Formally, for a cell profile with multiple masked positions, the BERT backbone produces a probability matrix over the gene vocabulary for each position, where each column represents a predicted distribution across all candidate genes. To reduce repetition across masked positions, we introduce a cumulative-assignment mechanism that explicitly propagates information across positions. Specifically, a blocking vector encoding observed (unmasked) genes is incorporated to suppress candidates that are already present within the same cell profile. The resulting probability distributions are then sequentially adjusted so that genes assigned high confidence at earlier positions are progressively down-weighted in subsequent predictions. This cumulative suppression, conceptually analogous to a Noisy-OR formulation [24], ensures that high-probability assignments are not repeatedly selected across positions, thereby enforcing non-redundant predictions within each cell.

### 6. Adjusts probability distributions to downweight high-confidence predictions in subsequent masked positions, mimicking a Noisy-OR formulation.

- 1차 검사: **supported**
- 근거로 든 문장: This cumulative suppression, conceptually analogous to a Noisy-OR formulation [24], ensures that high-probability assignments are not repeatedly selected across positions

- 판정:
- 메모:

**P0006** (paragraph, Results)

> Formally, for a cell profile with multiple masked positions, the BERT backbone produces a probability matrix over the gene vocabulary for each position, where each column represents a predicted distribution across all candidate genes. To reduce repetition across masked positions, we introduce a cumulative-assignment mechanism that explicitly propagates information across positions. Specifically, a blocking vector encoding observed (unmasked) genes is incorporated to suppress candidates that are already present within the same cell profile. The resulting probability distributions are then sequentially adjusted so that genes assigned high confidence at earlier positions are progressively down-weighted in subsequent predictions. This cumulative suppression, conceptually analogous to a Noisy-OR formulation [24], ensures that high-probability assignments are not repeatedly selected across positions, thereby enforcing non-redundant predictions within each cell.

### 7. **Similarity-Based Regularization**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 8. Penalizes redundant probability distributions across masked positions using pairwise dot-product similarity, encouraging exploration of low-frequency genes.

- 1차 검사: **supported**
- 근거로 든 문장: penalizes overly similar probability distributions across masked positions

- 판정:
- 메모:

**P0007** (paragraph, Results)

> In parallel, to enhance predictive diversity, we incorporate a similarity-based regularization term that penalizes overly similar probability distributions across masked positions. Concretely, the similarity between positional predictions is quantified using pairwise dot-product similarity, and the aggregated similarity across positions is minimized during training. This constraint discourages the model from concentrating probability mass on a limited subset of highly frequent genes. Instead, it encourages a broader exploration of candidate genes across positions. The final training objective combines the standard masked language modeling loss with this diversity regularization, balancing predictive accuracy and distributional diversity.

**P0010** (paragraph, GF CAB improves masked gene prediction fidelity and reveals diminishing returns from data scaling)

> Notably, models trained on smaller datasets exhibited systematically higher diversity, characterized by reduced repetition and increased coverage of distinct genes (Fig 2B, 2C). This observation suggests that increasing pretraining data alone does not resolve the tendency of rank-based models to overproduce frequent genes and may instead reinforce such biases. One plausible explanation is that large-scale pretraining encourages the model to learn highly consistent and dominant gene-gene relationships, leading to sharper and more concentrated probability distributions over a limited set of high-frequency genes. In contrast, models trained on smaller datasets are exposed to fewer and less constrained co-expression patterns, resulting in smoother predictive distributions with higher entropy. This, in turn, promotes greater exploratory diversity during masked prediction, allowing lower-frequency genes to be more readily recovered. Such behavior is consistent with our empirical observations of increased uniqueness and reduced repetition in smaller-scale genes. (B) Pretrained models are evaluated across multiple downstream tasks, including gene dosage sensitivity classification, cell type classification, tissue type classification, disease type classification, and zero-shot batch integration. (C) Illustration of the GF CAB architecture, highlighting the cumulative-assignment suppression and similarity-based regularization components introduced during pretraining to reduce repetition and enhance predictive diversity. All icons and graphical elements in this figure were created by the authors or generated using Python scripts. https://doi.org/10.1371/journal.pcbi.1013701.g001 models. To contextualize these findings, we additionally report relative training times (Fig 2D), highlighting the trade-off between computational cost and marginal performance gains.

### 9. **Pretraining Corpus**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 10. Reduced Genecorpus-1M (1M profiles) and Genecorpus-30M (30M profiles) for controlled comparisons.

- 1차 검사: **supported**
- 근거로 든 문장: construct a reduced pretraining corpus (Genecorpus-1M) by uniformly subsampling one million profiles from the original Genecorpus-30M

- 판정:
- 메모:

**P0003** (paragraph, Introduction)

> To address these underexplored limitations, we introduce GF CAB , a modified GF architecture designed to better align model behavior with the rank-ordered structure of single-cell transcriptomic data. Central to this design is a cumulative assignment and balancing (CAB) module, implemented as a post-prediction processor. The CAB module incorporates a probability cumulative-assignment mechanism to propagate positional constraints across predictions, ensuring consistency with the non-redundant nature of gene rankings within each cell. In parallel, a similarity-based regularization term penalizes redundant or overly similar probability distributions across gene positions, thereby promoting diversity in predicted gene identities. Together, these components explicitly encode structural priors of the data into the prediction process, mitigating the mismatch introduced by conventional masked language modeling objectives. To further investigate the role of data scale in conjunction with architectural design, we additionally construct a reduced pretraining corpus (Genecorpus-1M) by uniformly subsampling one million profiles from the original Genecorpus-30M, enabling controlled comparisons across different data regimes (Fig 1A).

## 4. Key Results and Benchmarks

### 11. **Masked Gene Prediction**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 12. GF CAB reduced repetition and increased uniqueness compared to GF, achieving higher accuracy across 1M and 30M datasets.

- 1차 검사: **supported**
- 근거로 든 문장: GF CAB consistently achieved higher prediction accuracy, reduced repetition, and increased uniqueness across both data scales.

- 판정:
- 메모:

**P0009** (paragraph, GF CAB improves masked gene prediction fidelity and reveals diminishing returns from data scaling)

> We first evaluated whether GF CAB improves alignment with rank-ordered single-cell transcriptomic profiles. To systematically characterize predictive behavior, we quantified masked gene prediction accuracy, repetition ratio, and uniqueness (Methods), capturing model fidelity, redundancy across masked positions, and the diversity of predicted genes, respectively. We benchmarked both GF and GF CAB , pretrained on 1M and 30M profiles, on an independent test set of 50,000 ranked cells (Fig 2A-2C, S1 Table). GF CAB consistently achieved higher prediction accuracy, reduced repetition, and increased uniqueness across both data scales. These results indicate that improved architectural alignment with the rank-ordered structure directly translates into enhanced predictive performance and more biologically consistent outputs.

**P0010** (paragraph, GF CAB improves masked gene prediction fidelity and reveals diminishing returns from data scaling)

> Notably, models trained on smaller datasets exhibited systematically higher diversity, characterized by reduced repetition and increased coverage of distinct genes (Fig 2B, 2C). This observation suggests that increasing pretraining data alone does not resolve the tendency of rank-based models to overproduce frequent genes and may instead reinforce such biases. One plausible explanation is that large-scale pretraining encourages the model to learn highly consistent and dominant gene-gene relationships, leading to sharper and more concentrated probability distributions over a limited set of high-frequency genes. In contrast, models trained on smaller datasets are exposed to fewer and less constrained co-expression patterns, resulting in smoother predictive distributions with higher entropy. This, in turn, promotes greater exploratory diversity during masked prediction, allowing lower-frequency genes to be more readily recovered. Such behavior is consistent with our empirical observations of increased uniqueness and reduced repetition in smaller-scale genes. (B) Pretrained models are evaluated across multiple downstream tasks, including gene dosage sensitivity classification, cell type classification, tissue type classification, disease type classification, and zero-shot batch integration. (C) Illustration of the GF CAB architecture, highlighting the cumulative-assignment suppression and similarity-based regularization components introduced during pretraining to reduce repetition and enhance predictive diversity. All icons and graphical elements in this figure were created by the authors or generated using Python scripts. https://doi.org/10.1371/journal.pcbi.1013701.g001 models. To contextualize these findings, we additionally report relative training times (Fig 2D), highlighting the trade-off between computational cost and marginal performance gains.

### 13. Smaller datasets (1M) showed higher diversity, with GF CAB outperforming GF in low-prevalence gene recovery.

- 1차 검사: **supported**
- 근거로 든 문장: GF CAB showed increased recovery of low-prevalence genes compared to GF

- 판정:
- 메모:

**P0013** (paragraph, GF CAB improves masked gene prediction fidelity and reveals diminishing returns from data scaling)

> Finally, we assessed the biological relevance of enhanced diversity by examining predictions across gene frequency strata. GF CAB showed increased recovery of low-prevalence genes compared to GF (Fig 2H, 2I, S5 Fig), including lineage-associated transcription factors (ASCL1, OLIG2, KLK6) [25][26][27], tissue-specific markers (BGLAP, GATA4) [28,29], and disease-relevant signaling and remodeling mediators (FGFR3, MMP9) [30,31]. These findings suggest that improved diversity translates into greater sensitivity to biologically meaningful but underrepresented signals.

### 14. **Downstream Tasks**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 15. Outperformed GF and classical baselines (e.g., SVM, random forest) in gene dosage sensitivity, cell type classification, and zero-shot batch effect correction.

- 1차 검사: **supported**
- 근거로 든 문장: GF CAB outperformed GF across both pretraining scales

- 판정:
- 메모:

**P0015** (paragraph, GF CAB improves downstream task performance and preserves generalization under reduced data scaling)

> To evaluate whether improvements in pretraining behavior translate into downstream utility, we assessed GF CAB across a diverse set of biologically relevant classification tasks and zero-shot batch effect correction benchmarks. Specifically, we considered three classification tasks, including gene dosage sensitivity prediction, cardiomyocyte disease-state classification, and tissue-specific cell type classification, and four zero-shot batch integration datasets, including Immune 330K [32], Pancreas 16K [33], PBMC 12K [12,34], and scCello out-of-distribution (OOD) cell type 487K [35] (Fig 3A). We benchmarked GF CAB against the original Geneformer (GF) across both 1M and 30M pretraining regimes, alongside representative classical baselines including logistic regression [36], random forest [37], and support vector machine [38], as well as established reference methods including HVGs-based representations and scVI [12] for batch integration.

**P0016** (paragraph, GF CAB improves downstream task performance and preserves generalization under reduced data scaling)

> Across classification tasks, GF CAB demonstrated competitive or improved predictive performance relative to GF (Fig 3B-3D, S2- S5 Table). For in-distribution tasks derived directly from the pretraining corpus, including gene dosage sensitivity and spleen cell type classification, GF CAB showed slightly reduced performance compared to GF at the 30M scale but consistently outperformed GF under the 1M setting. This behavior can be attributed to the regularization introduced by the CAB module, which suppresses redundant predictions and reduces overly concentrated probability distributions across masked positions. While these mechanisms can improve predictive diversity and robustness, they may also reduce the extent to which the model exploits task-specific predictive signals in settings where the original GF model already performs strongly. Thus, the slight advantage of GF-30M in these in-distribution tasks may reflect differences in the trade-off between predictive diversity and task-specific optimization. In contrast, for the out-of-distribution cardiomyocyte disease classification task, where we predict disease states (non-failing, hypertrophic, and dilated) from independently processed datasets, GF CAB outperformed GF across both pretraining scales (Fig 3D). This reversal highlights the effect of regularization in mitigating overfitting to pretraining-specific patterns and improving generalization under distribution shift. These observations are consistent with a classical biasvariance trade-off, whereby increased regularization reduces overfitting at the expense of peak in-distribution performance while enhancing robustness to unseen data. Notably, GF CAB pretrained on 1M data consistently matched or exceeded the performance of GF pretrained on 30M data, indicating that architectural improvements can offset, and in some cases surpass, gains from large-scale pretraining.

### 16. Pretrained on 1M data matched or exceeded 30M-scale models in classification accuracy and generalization.

- 1차 검사: **supported**
- 근거로 든 문장: GF CAB pretrained on 1M data consistently matched or exceeded the performance of GF pretrained on 30M data

- 판정:
- 메모:

**P0016** (paragraph, GF CAB improves downstream task performance and preserves generalization under reduced data scaling)

> Across classification tasks, GF CAB demonstrated competitive or improved predictive performance relative to GF (Fig 3B-3D, S2- S5 Table). For in-distribution tasks derived directly from the pretraining corpus, including gene dosage sensitivity and spleen cell type classification, GF CAB showed slightly reduced performance compared to GF at the 30M scale but consistently outperformed GF under the 1M setting. This behavior can be attributed to the regularization introduced by the CAB module, which suppresses redundant predictions and reduces overly concentrated probability distributions across masked positions. While these mechanisms can improve predictive diversity and robustness, they may also reduce the extent to which the model exploits task-specific predictive signals in settings where the original GF model already performs strongly. Thus, the slight advantage of GF-30M in these in-distribution tasks may reflect differences in the trade-off between predictive diversity and task-specific optimization. In contrast, for the out-of-distribution cardiomyocyte disease classification task, where we predict disease states (non-failing, hypertrophic, and dilated) from independently processed datasets, GF CAB outperformed GF across both pretraining scales (Fig 3D). This reversal highlights the effect of regularization in mitigating overfitting to pretraining-specific patterns and improving generalization under distribution shift. These observations are consistent with a classical biasvariance trade-off, whereby increased regularization reduces overfitting at the expense of peak in-distribution performance while enhancing robustness to unseen data. Notably, GF CAB pretrained on 1M data consistently matched or exceeded the performance of GF pretrained on 30M data, indicating that architectural improvements can offset, and in some cases surpass, gains from large-scale pretraining.

**P0020** (paragraph, GF CAB improves downstream task performance and preserves generalization under reduced data scaling)

> Collectively, these results demonstrate that GF CAB translates improved pretraining behavior into enhanced downstream performance, achieving competitive classification accuracy while consistently improving generalization in zero-shot settings. Importantly, these gains are maintained, and in some cases amplified, under reduced data scaling, highlighting that principled architectural alignment can preserve and even enhance the generalization capacity of single-cell foundation models without reliance on large-scale pretraining.

### 17. **Generalization**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 18. Improved cross-dataset performance, including Drop-seq and DroNc-seq modalities, with stronger zero-shot batch integration under reduced data scaling.

- 1차 검사: **supported**
- 근거로 든 문장: Models were fine-tuned on single-cell data and evaluated in a zero-shot manner across modalities

- 판정:
- 메모:

**P0019** (paragraph, GF CAB improves downstream task performance and preserves generalization under reduced data scaling)

> Finally, to assess generalization under cross-platform distribution shifts, we evaluated models on cardiomyocyte datasets spanning Drop-seq (single-cell) and DroNc-seq (single-nucleus) modalities [41]. Models were fine-tuned on single-cell data and evaluated in a zero-shot manner across modalities (Fig 3F). GF CAB exhibited improved integration performance following fine-tuning, consistent with prior observations [19], further supporting its ability to generalize across technical and biological shifts.

**P0020** (paragraph, GF CAB improves downstream task performance and preserves generalization under reduced data scaling)

> Collectively, these results demonstrate that GF CAB translates improved pretraining behavior into enhanced downstream performance, achieving competitive classification accuracy while consistently improving generalization in zero-shot settings. Importantly, these gains are maintained, and in some cases amplified, under reduced data scaling, highlighting that principled architectural alignment can preserve and even enhance the generalization capacity of single-cell foundation models without reliance on large-scale pretraining.

## 5. Limitations and Future Work

### 19. **Zero-Shot Integration Gaps**: GF CAB still lags behind non-ranking-based models (e.g., scCello) in zero-shot batch integration, highlighting intrinsic limitations of rank-based representations.

- 1차 검사: **supported**
- 근거로 든 문장: GF CAB consistently improved over GF within the naive ranking-based family, but did not fully close the performance gap with non-ranking-based approaches.

- 판정:
- 메모:

**P0026** (paragraph, Component-wise contributions of GF CAB and benchmarking against foundation models)

> We next extended this comparison to zero-shot batch integration (Fig 4C). Consistent with prior studies [35,39,40,43], ranking-based foundation models, including GF and GF CAB , remain less competitive than dedicated integration methods such as HVG-based representations and scVI. Among foundation models, scFoundation and SCimilarity, both characterized by relatively simpler architectures, exhibited stronger generalization, while scCello outperformed GF by incorporating cell ontology information to guide representation learning. In this context, GF CAB consistently improved over GF within the naive ranking-based family, but did not fully close the performance gap with non-ranking-based approaches. This suggests that while architectural refinement can alleviate some limitations, intrinsic constraints of rank-based representations remain a key factor in zero-shot generalization.

### 20. **Data Scaling Trade-offs**: While smaller datasets reduce computational costs, further exploration of hybrid scaling strategies (model + data) is needed to balance performance and efficiency.

- 1차 검사: **supported**
- 근거로 든 문장: models pretrained on substantially smaller datasets can match or exceed the performance of models trained on datasets up to 30-fold larger

- 판정:
- 메모:

**P0029** (paragraph, Discussion)

> A second key contribution of this work is the systematic evaluation of data scaling in single-cell foundation models. Contrary to the prevailing assumption that larger pretraining datasets uniformly improve performance, we show that gains in both predictive behavior and downstream tasks exhibit clear diminishing returns, with the majority of improvements occurring early in training. Notably, under an improved architecture such as GF CAB , models pretrained on substantially smaller datasets can match or exceed the performance of models trained on datasets up to 30-fold larger. Furthermore, smaller-scale models consistently exhibit stronger generalization in zero-shot settings, suggesting that excessive scaling may reinforce dataset-specific biases at the expense of transferability.

### 21. **Architectural Refinement**: Future work should focus on integrating domain-specific constraints and improving cross-dataset generalization through joint model-architecture and representation strategies.

- 1차 검사: **supported**
- 근거로 든 문장: Future progress will likely depend on jointly advancing model architectures and representation strategies

- 판정:
- 메모:

**P0030** (paragraph, Discussion)

> Collectively, this study addresses two underexplored challenges in the development of single-cell foundation models: the mismatch between model architectures and rank-ordered transcriptomic representations, and the limited understanding of data scaling effects in this domain. Our results motivate a shift in design principles, emphasizing that scaling alone is insufficient without architectures that respect the intrinsic structure of biological data. While rank-based representations provide a powerful framework for capturing gene expression patterns, they also impose inherent constraints, particularly in settings requiring robust cross-dataset generalization. Future progress will likely depend on jointly advancing model architectures and representation strategies to better reconcile predictive accuracy, diversity, and generalization in single-cell learning systems.

