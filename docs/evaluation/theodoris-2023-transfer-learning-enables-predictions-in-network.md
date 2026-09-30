# 검토표: theodoris-2023-transfer-learning-enables-predictions-in-network

- 논문: Transfer learning enables predictions in network biology
- 학술지·연도: Nature 2023  (출처 openalex, DOI 10.1038/s41586-023-06139-9)
- 노트 revision: `81cd0a4a62534ffda7ff4d78a9b7d543`  sha256 `83d738f40520a070`
- 추출: complete, 블록 65개, 생성 경로 single, 제시 65/65
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

### 1. **Context-Aware Attention Mechanism**: Geneformer uses self-attention to encode gene network hierarchy and context-specific interactions, enabling predictions in diverse biological contexts.

- 1차 검사: **supported**
- 근거로 든 문장: The advent of the self-attention mechanism 1,2 has further transformed the deep learning field by generating context-aware models that are able to pay attention to large input spaces and learn which elements are most important to focus on in each context, boosting predictions in a wide realm of applications 2,8 .

- 판정:
- 메모:

**P0003** (abstract, Abstract)

> Recently, the concept of transfer learning has revolutionized fields such as natural language understanding 1,2 and computer vision 3 by leveraging deep learning models pretrained on large-scale general datasets that can then be fine-tuned towards a vast array of downstream tasks with limited task-specific data that would be insufficient to yield meaningful predictions when used in isolation. Unlike modelling approaches that necessitate retraining a new model from scratch for each task 6,7 , this approach democratizes the fundamental knowledge learned during the large-scale pretraining phase to a multitude of downstream applications distinct from the pretraining learning objective, transferring knowledge to new tasks (Fig. 1a and Extended Data Fig. 1a,b). The advent of the self-attention mechanism 1,2 has further transformed the deep learning field by generating context-aware models that are able to pay attention to large input spaces and learn which elements are most important to focus on in each context, boosting predictions in a wide realm of applications 2,8 . Gene regulatory network architectures are highly context-dependent, and attention-based models, known as transformers, may be exceptionally suited to context-specific modelling of network dynamics.

### 2. **Large-Scale Pretraining Corpus**: Pretrained on Genecorpus-30M, comprising 29.9 million human single-cell transcriptomes, to capture broad network dynamics.

- 1차 검사: **supported**
- 근거로 든 문장: comprising 29.9 million human single-cell transcriptomes

- 판정:
- 메모:

**P0004** (abstract, Abstract)

> Here, we developed a context-aware, attention-based deep learning model, Geneformer, pretrained on large-scale transcriptomic data to enable predictions in settings with limited data. We assembled a largescale pretraining corpus, Genecorpus-30M, comprising 29.9 million human single-cell transcriptomes from a broad range of tissues from publicly available data. We then pretrained Geneformer on this corpus using a self-supervised masked learning objective to gain a fundamental

### 3. **Dosage Sensitivity Prediction**: Achieved 91% AUC in distinguishing dosage-sensitive vs. insensitive transcription factors using 10,000 cells, outperforming alternative methods.

- 1차 검사: **supported**
- 근거로 든 문장: The fine-tuned Geneformer significantly boosted the ability to predict dosage sensitivity compared to alternative methods (area under the receiver operating characteristic curve (AUC) 0.91)

- 판정:
- 메모:

**P0012** (paragraph, Gene dosage sensitivity predictions)

> We next tested whether Geneformer could boost predictions with limited data in a diverse set of downstream fine-tuning applications (Supplementary Table 2). A major challenge of interpreting copy number variants (CNVs) in genetic diagnosis is determining which genes are sensitive to changes in their dosage. Although conservation and allele frequency are commonly used to predict dosage sensitivity, these features do not vary across cell states and do not capture transcriptional dynamics that may inform contextual dosage sensitivity indicating which specific tissues would be affected by changes in the dosage of the gene. Using gene sets previously reported [19][20][21] to be dosage-sensitive versus dosage-insensitive, we fine-tuned Geneformer using only 10,000 random single-cell transcriptomes to distinguish dosage-sensitive versus dosage-insensitive transcription factors. The fine-tuned Geneformer significantly boosted the ability to predict dosage sensitivity compared to alternative methods (area under the receiver operating characteristic curve (AUC) 0.91) (Fig. 2a and Extended Data Fig. 7a). Notably, pretraining with larger and more diverse corpuses consistently improved the predictive power in the downstream task despite using the same amount of limited task-specific data for fine-tuning (Fig. 2b).

### 4. **Therapeutic Target Discovery**: Identified TEAD4 and GSN/PLN as candidate targets for cardiomyopathy, validated experimentally via CRISPR-mediated knockout.

- 1차 검사: **supported**
- 근거로 든 문장: CRISPR-mediated knockout of both Geneformer-predicted targets GSN and PLN in the TTN +/-cells significantly improved the contractile stress

- 판정:
- 메모:

**P0015** (paragraph, Gene dosage sensitivity predictions)

> Overall, genes whose deletion was predicted to have the most deleterious effect on cardiomyocytes were significantly enriched for human phenotypes including cardiomyopathy and abnormal myocardial morphology (Supplementary Tables 3 and 4). Among the top 25 deleted genes with the most significant effect were transcription factors known to regulate myocardial development (for example, FOXM1; refs. 25,26) and entirely new dosage-sensitive gene candidates such as TEAD4 (Supplementary Table 3). Experimental validation demonstrated

**P0031** (paragraph, In silico treatment analysis)

> We then performed experimental validation to determine whether inhibition of Geneformer-predicted therapeutic candidates for dilated cardiomyopathy could improve cardiomyocyte function in an experimental model of the disease. Titin (TTN) truncating mutations are the leading cause of dilated cardiomyopathy in humans and are found in about 20% of affected patients 36 . iPSC-derived cardiac microtissues harbouring a truncating variant (TTN +/-) in the A-band are known to exhibit reduced contractile stress compared to isogenic TTN +/+ controls 36 . Strikingly, CRISPR-mediated knockout of both Geneformer-predicted targets GSN and PLN in the TTN +/-cells significantly improved the contractile stress of the TTN +/-cardiac microtissues, validating these genes as promising candidate therapeutic targets for this disease (Fig. 6f,g and Extended Data Fig. 10e). These findings provide experimental validation in support of the utility of Geneformer as a tool for discovery of candidate therapeutic targets in human disease.

### 5. **Cross-Task Generalization**: Demonstrated robustness in predicting chromatin dynamics, transcription factor regulatory ranges, and network centrality across diverse tasks.

- 1차 검사: **supported**
- 근거로 든 문장: Geneformer significantly boosted the ability to predict bivalently marked genes compared to alternative methods (AUC 0.93 and 0.88; bivalent versus unmethylated or H3K4me3-only, respectively)

- 판정:
- 메모:

**P0019** (paragraph, Chromatin dynamics predictions)

> Bivalent chromatin structure is known to mark key developmental genes in embryonic stem cells (ESCs), maintaining their promoters poised for activation 28 . Bivalent domains consist of large regions of H3K27me3 harbouring smaller regions of H3K4me3. We fine-tuned Geneformer to distinguish bivalently marked genes from those whose promoters were unmethylated or marked solely by H3K4me3 using transcriptomes from about 15,000 ESCs 29 . The labelled gene set used for this fine-tuning included only genes found in 56 conserved regions of the genome, as previously reported 28 . Geneformer significantly boosted the ability to predict bivalently marked genes compared to alternative methods (AUC 0.93 and 0.88; bivalent versus unmethylated or H3K4me3-only, respectively) (Fig. 3a,b and Extended Data Fig. 7d,e). Furthermore, predictions were generalizable to the remainder of the genome that was excluded from fine-tuning (Fig. 3c and Extended Data Fig. 8a-c). Thus, by fine-tuning Geneformer using solely transcriptional data with only 56 labelled loci in about 15,000 ESCs, the model could predict the results of more recent studies 30 that included genome-wide profiling of bivalent domains.

**P0020** (paragraph, Chromatin dynamics predictions)

> Determining the genomic distances over which transcription factor binding influences downstream expression is valuable for interpreting regulatory variants and inferring target genes from transcription factor genome occupancy data. Others previously systematically integrated thousands of transcription factor-binding and histone-modification profiles assayed by chromatin immunoprecipitation sequencing (ChIP-seq) with thousands of gene expression profiles to identify two classes of transcription factor with distinct ranges of regulatory influence 31 . We fine-tuned Geneformer to distinguish these long-versus short-range transcription factors using only single-cell transcriptomes from about 34,000 cells undergoing iPSC to cardiomyocyte differentiation 11 with no associated ChIP-seq or genomic distance data. Again, Geneformer significantly boosted the ability to predict the regulatory range of transcription factors compared to alternative methods, whose predictions were near random (Fig. 3d and Extended Data Fig. 8d). Thus, fine-tuning the pretrained Geneformer model was able to improve predictions even for this higher-order transcription factor property of regulatory range, a particularly challenging characteristic to infer from transcriptional data alone.

## 3. Methodology and Architecture

### 6. **Rank Value Encoding**: Genes are ranked by normalized expression across Genecorpus-30M, prioritizing context-specific regulators while deprioritizing housekeeping genes.

- 1차 검사: **supported**
- 근거로 든 문장: genes are ranked by their expression in that cell normalized by their expression across the entire Genecorpus-30M

- 판정:
- 메모:

**P0007** (paragraph, Geneformer architecture and pretraining)

> The transcriptome of each single cell is then presented to the model as a rank value encoding where genes are ranked by their expression in that cell normalized by their expression across the entire Genecorpus-30M (Fig. 1c). Although the rank-based representation has limitations including not fully taking advantage of the precise gene expression measurements provided in transcript counts, the rank value encoding provides a non-parametric representation of the transcriptome of each single cell and takes advantage of the many observations of the expression of each gene across Genecorpus-30M to prioritize genes that distinguish cell state. Specifically, this method will deprioritize ubiquitously highly expressed housekeeping genes by normalizing them to a lower rank. Conversely, genes such as transcription factors that may be expressed at low levels when they are expressed but have a high power to distinguish cell state will move to a higher rank within the encoding (Extended Data Fig. 1c). Furthermore, this rank-based approach may be more robust against technical artefacts that may systematically bias the absolute transcript counts value whereas the overall relative ranking of genes within each cell remains more stable.

### 7. **Transformer Encoder**: Six self-attention layers with 256 embedding dimensions, trained via masked language modeling to learn gene relationships without labels.

- 1차 검사: **flagged** — cited elsewhere: 256 as 256  (모델: supported)
- 근거로 든 문장: During pretraining, 15% of the genes within each transcriptome were masked

- 판정: 인용틀림
- 메모: six encoder units·masked learning·15%는 P0008에 있으나 256 embedding dimensions는 없음. 그 값은 P0047('the 256 embedding dimensions for each gene')에 있음.
- 판정자: 보조 (사람 확인 필요)

**P0008** (paragraph, Geneformer architecture and pretraining)

> The rank value encoding of the transcriptome of each single cell then proceeds through six transformer encoder units 1,2 , each composed of a self-attention layer and feed forward neural network layer (Fig. 1c). Pretraining was accomplished using a masked learning objective, which has been shown in other informational fields 1,2 to improve generalizability of the foundational knowledge learned during pretraining for a wide range of downstream fine-tuning objectives. During pretraining, 15% of the genes within each transcriptome were masked, and the model was trained to predict which gene should be within each masked position in that specific cell state using the context of the remaining unmasked genes (Extended Data Fig. 1d-f). A principal strength of this approach is that it is entirely self-supervised and can be accomplished on completely unlabelled data, which allows the inclusion of large amounts of training data without being restricted to samples with accompanying labels. We implemented recent advances in distributed graphical processing unit (GPU) training 9,10 to allow efficient pretraining on the large-scale dataset.

### 8. **Pretraining Objective**: 15% of genes masked per transcriptome, with the model predicting masked genes using context from unmasked genes.

- 1차 검사: **supported**
- 근거로 든 문장: During pretraining, 15% of the genes within each transcriptome were masked

- 판정:
- 메모:

**P0008** (paragraph, Geneformer architecture and pretraining)

> The rank value encoding of the transcriptome of each single cell then proceeds through six transformer encoder units 1,2 , each composed of a self-attention layer and feed forward neural network layer (Fig. 1c). Pretraining was accomplished using a masked learning objective, which has been shown in other informational fields 1,2 to improve generalizability of the foundational knowledge learned during pretraining for a wide range of downstream fine-tuning objectives. During pretraining, 15% of the genes within each transcriptome were masked, and the model was trained to predict which gene should be within each masked position in that specific cell state using the context of the remaining unmasked genes (Extended Data Fig. 1d-f). A principal strength of this approach is that it is entirely self-supervised and can be accomplished on completely unlabelled data, which allows the inclusion of large amounts of training data without being restricted to samples with accompanying labels. We implemented recent advances in distributed graphical processing unit (GPU) training 9,10 to allow efficient pretraining on the large-scale dataset.

### 9. **Fine-Tuning**: Applied to downstream tasks (e.g., cell-type annotation, dosage sensitivity) using minimal task-specific data, achieving 90% accuracy in cardiomyocyte classification.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: achieving 90% accuracy in cardiomyocyte classification

- 판정: 맞음
- 메모: P0029에 'overall out-of-sample accuracy of 90%' 그대로 있음. 1차 검사가 인용문을 축자로 옮기지 못해 플래그된 거짓 경보.
- 판정자: 보조 (사람 확인 필요)

**P0029** (paragraph, In silico treatment analysis)

> We next tested whether our in silico perturbation strategy could be applied to model human disease and reveal candidate therapeutic targets (Fig. 6a). First, we fine-tuned Geneformer to distinguish cardiomyocytes 35 from non-failing hearts (n = 9) or hearts affected by hypertrophic (n = 11) or dilated (n = 9) cardiomyopathy with an overall out-of-sample accuracy of 90% (Fig. 6b and Extended Data Fig. 10a). We then determined the genes whose in silico deletion or activation in cardiomyocytes from non-failing hearts significantly shifted the fine-tuned Geneformer cell embeddings towards the hypertrophic or dilated cardiomyopathy states (Fig. 6c,d, Extended Data Fig. 10b,c and Supplementary Tables 567891011). Overall, the model identified 447 genes whose loss was predicted to shift cardiomyocytes towards the hypertrophic cardiomyopathy state, which were enriched for pathways including Titin binding 36 and sarcomere organization 37 known to impact hypertrophic cardiomyopathy pathogenesis. The model identified 478 genes whose loss was predicted to shift cardiomyocytes towards dilated cardiomyopathy, which were enriched for pathways involved in muscle contraction 38 and mitochondrial 39 function.

## 4. Key Results and Benchmarks

### 10. **Dosage Sensitivity**: Geneformer outperformed XGBoost and logistic regression, achieving 91% AUC for high-confidence neurodevelopmental disease genes.

- 1차 검사: **supported**
- 근거로 든 문장: The fine-tuned Geneformer model correctly predicted the high-confidence genes to be dosage sensitive in the specific context of fetal cerebral cells with 96% concordance with the original study.

- 판정:
- 메모:

**P0012** (paragraph, Gene dosage sensitivity predictions)

> We next tested whether Geneformer could boost predictions with limited data in a diverse set of downstream fine-tuning applications (Supplementary Table 2). A major challenge of interpreting copy number variants (CNVs) in genetic diagnosis is determining which genes are sensitive to changes in their dosage. Although conservation and allele frequency are commonly used to predict dosage sensitivity, these features do not vary across cell states and do not capture transcriptional dynamics that may inform contextual dosage sensitivity indicating which specific tissues would be affected by changes in the dosage of the gene. Using gene sets previously reported [19][20][21] to be dosage-sensitive versus dosage-insensitive, we fine-tuned Geneformer using only 10,000 random single-cell transcriptomes to distinguish dosage-sensitive versus dosage-insensitive transcription factors. The fine-tuned Geneformer significantly boosted the ability to predict dosage sensitivity compared to alternative methods (area under the receiver operating characteristic curve (AUC) 0.91) (Fig. 2a and Extended Data Fig. 7a). Notably, pretraining with larger and more diverse corpuses consistently improved the predictive power in the downstream task despite using the same amount of limited task-specific data for fine-tuning (Fig. 2b).

**P0013** (paragraph, Gene dosage sensitivity predictions)

> We then asked whether, without any further training, the fine-tuned model could predict the dosage sensitivity of a recently reported set Nature | Vol 618 | 15 June 2023 | 619 of disease genes (Fig. 2c). Collins et al. analysed CNVs from 753,994 individuals to define genes whose deletion was associated with primarily neurodevelopmental disease with either high or moderate confidence 22 . The fine-tuned Geneformer model correctly predicted the high-confidence genes to be dosage sensitive in the specific context of fetal cerebral cells with 96% concordance with the original study. The moderate-confidence genes reported by the authors were a much more permissive set (0.15-0.85 score versus high-confidence score cutoff greater than 0.85). The fine-tuned Geneformer predicted moderate-confidence genes to be dosage sensitive in fetal cerebral cells with 84% concordance with the original study. Interestingly, although the high-confidence genes, which may have a stronger effect, were predicted by Geneformer to be dosage sensitive at similar rates in fetal cerebral (96%) and other cells (95%), the predicted dosage sensitivity of the moderate-confidence genes seemed to be more context specific. The moderate-confidence genes were predicted to be dosage sensitive at a higher rate in fetal cerebral cells compared to neurons across any adult or developmental timepoint, consistent with the association of these genes with predominantly neurodevelopmental phenotypes in which adult neurons may be less relevant. They were predicted to be dosage sensitive at an even lower rate in random cells from any tissue, highlighting the context awareness of Geneformer.

### 11. **Chromatin Dynamics**: Predicted bivalent chromatin marks with 93% AUC, surpassing alternatives in distinguishing bivalent vs. unmethylated genes.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: Geneformer significantly boosted the ability to predict bivalently marked genes compared to alternative methods (AUC 0.93 and 0.48; bivalent versus unmethylated or H3K4me3-only, respectively)

- 판정: 맞음
- 메모: P0019에 'AUC 0.93 and 0.88; bivalent versus unmethylated or H3K4me3-only' 그대로 있음. 93% = 0.93.
- 판정자: 보조 (사람 확인 필요)

**P0019** (paragraph, Chromatin dynamics predictions)

> Bivalent chromatin structure is known to mark key developmental genes in embryonic stem cells (ESCs), maintaining their promoters poised for activation 28 . Bivalent domains consist of large regions of H3K27me3 harbouring smaller regions of H3K4me3. We fine-tuned Geneformer to distinguish bivalently marked genes from those whose promoters were unmethylated or marked solely by H3K4me3 using transcriptomes from about 15,000 ESCs 29 . The labelled gene set used for this fine-tuning included only genes found in 56 conserved regions of the genome, as previously reported 28 . Geneformer significantly boosted the ability to predict bivalently marked genes compared to alternative methods (AUC 0.93 and 0.88; bivalent versus unmethylated or H3K4me3-only, respectively) (Fig. 3a,b and Extended Data Fig. 7d,e). Furthermore, predictions were generalizable to the remainder of the genome that was excluded from fine-tuning (Fig. 3c and Extended Data Fig. 8a-c). Thus, by fine-tuning Geneformer using solely transcriptional data with only 56 labelled loci in about 15,000 ESCs, the model could predict the results of more recent studies 30 that included genome-wide profiling of bivalent domains.

### 12. **Network Centrality**: Identified central vs. peripheral factors in the N1-dependent network with 81% AUC, even with as few as 5,000 training cells.

- 1차 검사: **supported**
- 근거로 든 문장: We found that nearly equivalent predictive potential was retained even when reducing the fine-tuning data to only 5,000 ECs

- 판정:
- 메모:

**P0022** (paragraph, Network dynamics predictions)

> We tested whether Geneformer could be fine-tuned to distinguish central versus peripheral factors within the N1-dependent gene network using only single-cell transcriptional data from about 30,000 normal endothelial cells (ECs) from the Heart Atlas 32 without any perturbation data. Again, Geneformer significantly boosted the ability to predict central versus peripheral factors compared to alternative methods (AUC 0.81) (Fig. 4a and Extended Data Fig. 8e). Furthermore, fine-tuning the pretrained Geneformer on the Heart Atlas ECs 32 was able to distinguish N1 downstream targets from non-targets without any perturbation data, further demonstrating the ability of the model to encode key features of gene network dynamics and again significantly boosting predictions compared to alternative methods (Fig. 4b and Extended Data Fig. 9a). To investigate the threshold for minimal data needed for fine-tuning, we fine-tuned the pretrained Geneformer with progressively smaller numbers of normal ECs from the Heart Atlas 32 to distinguish central versus peripheral factors within the N1-dependent gene network. We found that nearly equivalent predictive potential was retained even when reducing the fine-tuning data to only 5,000 ECs (Fig. 4c). Then, to determine whether Geneformer could generate meaningful predictions using an even more miniscule number of fine-tuning training examples when the task-specific data were more relevant to the learning objective, we fine-tuned the pretrained Geneformer using only 884 ECs from healthy versus dilated aortas 14 . Interestingly, Geneformer was able to distinguish central versus peripheral factors in the N1-dependent network with fine-tuning on this very minimal data to a better degree than the predictions of alternative methods trained on the larger dataset of about 30,000 ECs 32 , demonstrating the strength of pretraining in enabling predictions from increasingly limited data (Fig. 4d and Extended Data Fig. 9b). More than twice as many general cardiac ECs were needed to gain similar predictive potential as was possible from fine-tuning with the more relevant data from healthy versus dilated aortas, suggesting that the minimum amount of fine-tuning data needed is dependent on both the specific application and relevance of the data to that task.

### 13. **Experimental Validation**: CRISPR-mediated knockout of TEAD4 reduced contractile stress in iPSC-derived cardiac microtissues, validating therapeutic potential.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 인용틀림
- 메모: 사실은 맞음 — P0018에 'CRISPR-mediated knockout of candidate TEAD4 ... caused a significant reduction in their ability to generate contractile stress'. 인용한 P0031은 GSN·PLN이 수축력을 개선한 실험이므로 유전자도 방향도 다름. 또 'therapeutic potential'은 TEAD4가 아니라 GSN·PLN 쪽 서술.
- 판정자: 보조 (사람 확인 필요)

**P0031** (paragraph, In silico treatment analysis)

> We then performed experimental validation to determine whether inhibition of Geneformer-predicted therapeutic candidates for dilated cardiomyopathy could improve cardiomyocyte function in an experimental model of the disease. Titin (TTN) truncating mutations are the leading cause of dilated cardiomyopathy in humans and are found in about 20% of affected patients 36 . iPSC-derived cardiac microtissues harbouring a truncating variant (TTN +/-) in the A-band are known to exhibit reduced contractile stress compared to isogenic TTN +/+ controls 36 . Strikingly, CRISPR-mediated knockout of both Geneformer-predicted targets GSN and PLN in the TTN +/-cells significantly improved the contractile stress of the TTN +/-cardiac microtissues, validating these genes as promising candidate therapeutic targets for this disease (Fig. 6f,g and Extended Data Fig. 10e). These findings provide experimental validation in support of the utility of Geneformer as a tool for discovery of candidate therapeutic targets in human disease.

### 14. **Batch Robustness**: Geneformer embeddings were invariant to sequencing platforms, preservation methods, and patient variability.

- 1차 검사: **supported**
- 근거로 든 문장: gene embeddings were robust to sequencing platform 11 , preservation method 12,13 and individual patient variability 14

- 판정:
- 메모:

**P0009** (paragraph, Context awareness and batch integration)

> For each single-cell transcriptome presented to Geneformer, the model embeds each gene into a 256-dimensional space that encodes the characteristics of the gene specific to the context of that cell. We first tested whether the pretrained Geneformer's embedding of genes was impacted by common batch-dependent technical artefacts. We found that the gene embeddings were robust to sequencing platform 11 , preservation method 12,13 and individual patient variability 14 (Extended Data Fig. 2a). However, gene embeddings were dependent on the context of other genes expressed in the cell, highlighting Geneformer's context awareness. When we in silico reprogrammed fibroblasts 15 by artificially adding OCT4, SOX2, KLF4 and MYC to the front of their rank value encodings, the remaining genes in the transcriptome significantly shifted their embedding towards the iPSC state (Extended Data Fig. 2b,c). Embeddings of genes in iPSC-derived myogenic cells 16 showed similar context awareness with in silico differentiation by MYOD (Extended Data Fig. 2d,e). Furthermore, genes known to be highly context-dependent, such as NOTCH receptors, showed more variability in their embeddings across variable cell types 14 compared to the known housekeeping gene GAPDH (Extended Data Fig. 3).

## 5. Limitations and Future Work

### 15. **Data Dependency**: Requires large-scale pretraining corpora; performance may degrade with highly specialized or rare datasets.

- 1차 검사: **supported**
- 근거로 든 문장: More than twice as many general cardiac ECs were needed to gain similar predictive potential as was possible from fine-tuning with the more relevant data from healthy versus dilated aortas

- 판정:
- 메모:

**P0022** (paragraph, Network dynamics predictions)

> We tested whether Geneformer could be fine-tuned to distinguish central versus peripheral factors within the N1-dependent gene network using only single-cell transcriptional data from about 30,000 normal endothelial cells (ECs) from the Heart Atlas 32 without any perturbation data. Again, Geneformer significantly boosted the ability to predict central versus peripheral factors compared to alternative methods (AUC 0.81) (Fig. 4a and Extended Data Fig. 8e). Furthermore, fine-tuning the pretrained Geneformer on the Heart Atlas ECs 32 was able to distinguish N1 downstream targets from non-targets without any perturbation data, further demonstrating the ability of the model to encode key features of gene network dynamics and again significantly boosting predictions compared to alternative methods (Fig. 4b and Extended Data Fig. 9a). To investigate the threshold for minimal data needed for fine-tuning, we fine-tuned the pretrained Geneformer with progressively smaller numbers of normal ECs from the Heart Atlas 32 to distinguish central versus peripheral factors within the N1-dependent gene network. We found that nearly equivalent predictive potential was retained even when reducing the fine-tuning data to only 5,000 ECs (Fig. 4c). Then, to determine whether Geneformer could generate meaningful predictions using an even more miniscule number of fine-tuning training examples when the task-specific data were more relevant to the learning objective, we fine-tuned the pretrained Geneformer using only 884 ECs from healthy versus dilated aortas 14 . Interestingly, Geneformer was able to distinguish central versus peripheral factors in the N1-dependent network with fine-tuning on this very minimal data to a better degree than the predictions of alternative methods trained on the larger dataset of about 30,000 ECs 32 , demonstrating the strength of pretraining in enabling predictions from increasingly limited data (Fig. 4d and Extended Data Fig. 9b). More than twice as many general cardiac ECs were needed to gain similar predictive potential as was possible from fine-tuning with the more relevant data from healthy versus dilated aortas, suggesting that the minimum amount of fine-tuning data needed is dependent on both the specific application and relevance of the data to that task.

### 16. **Small-Data Challenges**: While effective with limited task-specific data, further optimization is needed for ultra-low-data scenarios.

- 1차 검사: **supported**
- 근거로 든 문장: nearly equivalent predictive potential was retained even when reducing the fine-tuning data to only 5,000 ECs

- 판정:
- 메모:

**P0022** (paragraph, Network dynamics predictions)

> We tested whether Geneformer could be fine-tuned to distinguish central versus peripheral factors within the N1-dependent gene network using only single-cell transcriptional data from about 30,000 normal endothelial cells (ECs) from the Heart Atlas 32 without any perturbation data. Again, Geneformer significantly boosted the ability to predict central versus peripheral factors compared to alternative methods (AUC 0.81) (Fig. 4a and Extended Data Fig. 8e). Furthermore, fine-tuning the pretrained Geneformer on the Heart Atlas ECs 32 was able to distinguish N1 downstream targets from non-targets without any perturbation data, further demonstrating the ability of the model to encode key features of gene network dynamics and again significantly boosting predictions compared to alternative methods (Fig. 4b and Extended Data Fig. 9a). To investigate the threshold for minimal data needed for fine-tuning, we fine-tuned the pretrained Geneformer with progressively smaller numbers of normal ECs from the Heart Atlas 32 to distinguish central versus peripheral factors within the N1-dependent gene network. We found that nearly equivalent predictive potential was retained even when reducing the fine-tuning data to only 5,000 ECs (Fig. 4c). Then, to determine whether Geneformer could generate meaningful predictions using an even more miniscule number of fine-tuning training examples when the task-specific data were more relevant to the learning objective, we fine-tuned the pretrained Geneformer using only 884 ECs from healthy versus dilated aortas 14 . Interestingly, Geneformer was able to distinguish central versus peripheral factors in the N1-dependent network with fine-tuning on this very minimal data to a better degree than the predictions of alternative methods trained on the larger dataset of about 30,000 ECs 32 , demonstrating the strength of pretraining in enabling predictions from increasingly limited data (Fig. 4d and Extended Data Fig. 9b). More than twice as many general cardiac ECs were needed to gain similar predictive potential as was possible from fine-tuning with the more relevant data from healthy versus dilated aortas, suggesting that the minimum amount of fine-tuning data needed is dependent on both the specific application and relevance of the data to that task.

### 17. **Biological Interpretation**: Requires integration with experimental validation to confirm predicted gene interactions.

- 1차 검사: **supported**
- 근거로 든 문장: These findings provide experimental validation in support of the utility of Geneformer as a tool for discovery of candidate therapeutic targets in human disease.

- 판정:
- 메모:

**P0031** (paragraph, In silico treatment analysis)

> We then performed experimental validation to determine whether inhibition of Geneformer-predicted therapeutic candidates for dilated cardiomyopathy could improve cardiomyocyte function in an experimental model of the disease. Titin (TTN) truncating mutations are the leading cause of dilated cardiomyopathy in humans and are found in about 20% of affected patients 36 . iPSC-derived cardiac microtissues harbouring a truncating variant (TTN +/-) in the A-band are known to exhibit reduced contractile stress compared to isogenic TTN +/+ controls 36 . Strikingly, CRISPR-mediated knockout of both Geneformer-predicted targets GSN and PLN in the TTN +/-cells significantly improved the contractile stress of the TTN +/-cardiac microtissues, validating these genes as promising candidate therapeutic targets for this disease (Fig. 6f,g and Extended Data Fig. 10e). These findings provide experimental validation in support of the utility of Geneformer as a tool for discovery of candidate therapeutic targets in human disease.

### 18. **Future Directions**: Expanding pretraining to include more diverse tissues and leveraging multi-omics data for enhanced context-awareness.

- 1차 검사: **supported**
- 근거로 든 문장: pretraining with larger and more diverse corpuses consistently improved Geneformer's predictive power

- 판정:
- 메모:

**P0032** (paragraph, Discussion)

> In sum, we developed a context-aware deep learning model, Geneformer, pretrained on large-scale transcriptomic data to enable predictions in settings with limited data. Through the observation of a vast number of cell states during the pretraining process, Geneformer gained a fundamental understanding of network dynamics, encoding network hierarchy in the attention weights of the model in a completely self-supervised manner. Geneformer's ability to predict dosage-sensitive disease genes through the context-aware in silico deletion approach represents a valuable asset for interpretation of genetic variants, including prioritization of GWAS hits driving complex traits, and the specific tissues they are expected to affect. of GATA4 was significantly more deleterious to previously reported GATA4 direct targets 33 than to housekeeping genes, previously reported NOTCH1 targets 4 , previously reported NKX2-5 targets 46 or GATA4 indirect targets 33 (*P < 0.05 Wilcoxon, FDR-corrected; centre line, median; box limits, upper and lower quartiles; whiskers, 1.5× interquartile range; points, outliers). b, In silico deletion of GATA4 or TBX5 alone was significantly more deleterious to previously reported GATA4/TBX5 cobound targets 33 than to housekeeping genes; in silico deletion of the combination of GATA4 and TBX5 was even more deleterious to cobound targets, significantly more than to housekeeping genes and significantly more than the sum of the effect of GATA4 or TBX5 enable therapeutic discovery in innumerable diseases that have been previously impeded by limited data because they are rare or affect clinically inaccessible tissue. Furthermore, we found that pretraining with larger and more diverse corpuses consistently improved Geneformer's predictive power, in agreement with observations that large-scale pretraining allows training of deeper models that ultimately have greater predictive potential in fields including natural language understanding, computer vision and mathematical problem-solving 44 . Furthermore, exposure to hundreds of experimental datasets during pretraining also seemed to promote robustness to batch-dependent technical artefacts and individual variability that commonly impact single-cell analyses in biology. These findings suggest that as the amount of publicly available transcriptomic data continues to expand, future models pretrained on even larger-scale corpuses may open opportunities to achieve meaningful predictions in even more elusive tasks with increasingly limited task-specific data. Overall, Geneformer represents a pretrained deep learning model whose fundamental understanding of network dynamics can now be democratized to a broad range of downstream applications to accelerate discovery of key network regulators and candidate therapeutic targets in settings with limited data.

