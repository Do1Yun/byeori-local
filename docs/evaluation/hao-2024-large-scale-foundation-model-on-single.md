# 검토표: hao-2024-large-scale-foundation-model-on-single

- 논문: Large-scale foundation model on single-cell transcriptomics
- 학술지·연도: Nature Methods 2024  (출처 openalex, DOI 10.1038/s41592-024-02305-7)
- 노트 revision: `af90b050b0da47c3b483a31a30e04314`  sha256 `dfd8bfccb5401f1b`
- 추출: partial, 블록 86개, 생성 경로 single, 제시 86/86
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

### 1. **scFoundation as a foundation model**: Achieved superior performance in single-cell tasks, including gene expression enhancement, drug response prediction, and cell type annotation, with 100 million parameters and 20,000 gene coverage.

- 1차 검사: **supported**
- 근거로 든 문장: scFoundation is a large-scale model in terms of the size of trainable parameters, dimensionality of genes and volume of training data.

- 판정: 
- 메모: 

**P0001** (paragraph, Body)

> Large pretrained models have become foundation models leading to breakthroughs in natural language processing and related fields. Developing foundation models for deciphering the 'languages' of cells and facilitating biomedical research is promising yet challenging. Here we developed a large pretrained model scFoundation, also named 'xTrimoscFoundation α ', with 100 million parameters covering about 20,000 genes, pretrained on over 50 million human single-cell transcriptomic profiles. scFoundation is a large-scale model in terms of the size of trainable parameters, dimensionality of genes and volume of training data. Its asymmetric transformer-like architecture and pretraining task design empower effectively capturing complex context relations among genes in a variety of cell types and states. Experiments showed its merit as a foundation model that achieved state-of-the-art performances in a diverse array of single-cell analysis tasks such as gene expression enhancement, tissue drug response prediction, single-cell drug response classification, single-cell perturbation prediction, cell type annotation and gene module inference.

### 2. **Asymmetric transformer architecture**: Designed to handle sparse scRNA-seq data efficiently, with an encoder-decoder structure that processes nonzero and masked gene expressions.

- 1차 검사: **supported**
- 근거로 든 문장: The asymmetric encoder-decoder architecture had a similar form to the masked autoencoder

- 판정: 
- 메모: 

**P0012** (paragraph, The scFoundation pretraining framework)

> We developed xTrimoGene, a scalable transformer-based model with strategies for both algorithmic efficiency and engineering acceleration 18 . It included an embedding module and an asymmetric encoderdecoder structure. The embedding module converted continuous gene expression scalars into learnable high-dimensional vectors ensuring full retention of raw expression values, which was a notable improvement over the discretized values used in previous models 13,19 . The asymmetric encoder-decoder architecture had a similar form to the masked autoencoder 20 model in computer vision but was designed to accommodate the high sparsity of scRNA-seq data, achieving efficient learning of all gene relationships without any selection. Moreover, we incorporated a variety of large-scale model training optimization techniques in the model deployment to ensure efficient training (Methods).

### 3. **Read-depth-aware (RDA) pretraining task**: Enabled models to enhance read depth and predict gene expression, outperforming imputation methods like scVI and SAVER.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 
- 메모: 

**P0013** (paragraph, The scFoundation pretraining framework)

> We designed a pretraining task called the RDA modeling, an extension of masked language modeling 21 , by considering the high variance of read depth in large-scale data. In RDA modeling, the model predicted the masked gene expression of a cell on the basis of its context genes. The context was from a duplication or a low-read-depth variant of that cell's gene expression profile (Methods). We treated the total count as one cell's read depth and defined two total counts indicators: T ('target') and S ('source'), for the total counts of the raw and the input samples,

### 4. **Scalable read-depth enhancement**: Reduced MAE and MRE by up to 50% in low-read-depth scenarios, with performance plateauing at T/S ratios >3.5.

- 1차 검사: **flagged** — 50% is nowhere in the paper; cited elsewhere: 3.5 as 3.5  (모델: supported)
- 근거로 든 문장: scFoundation demonstrated a notable reduction of half the MAE and MRE from the downsampled data even when the downsampling rate was below 10%.

- 판정: 
- 메모: 

**P0008** (paragraph, Scalable read-depth enhancement model without fine-tuning)

> The RDA modeling enables scFoundation to enhance the read depth of the input cell by setting T as a higher number than S. We assessed this ability on independent test data of 10,000 cells randomly sampled from the validation dataset. We downsampled the total counts to 1%, 5%, 10% and 20% of the original profiles, generating four corresponding datasets with varying total count fold changes. For each dataset, we utilized non-fine-tuned scFoundation to enhance the cells with low total counts by setting the desired total counts T as the reciprocal of the sampling rate. We measured the mean absolute error (MAE), mean relative error (MRE) and Pearson correlation coefficient (PCC) between predicted and actual nonzero gene expressions. As shown in Fig. 2b and Supplementary Fig. 1, scFoundation demonstrated a notable reduction of half the MAE and MRE from the downsampled data even when the downsampling rate was below 10%. These observations showed the ability of scFoundation to enhance gene expressions in scenarios even with extremely low total counts. gene expression pretraining data need to encompass a landscape of cells across different statuses and types. Currently, most scRNA-seq data are loosely organized, and a comprehensive and complete database is still lacking. Second, when modeling each cell as a sentence and each gene expression value as a word, the nearly 20,000 protein-coding genes make the 'sentence' exceptionally long, a scenario that traditional transformers struggle to handle 16,17 . Existing work often had to restrict their models to a small list of selected genes. Third, scRNA-seq data across different techniques and laboratories exhibit high variance in sequencing read depth. Unlike random noises due to technical effects such as contamination that would be reduced by training on large-volume data, read depth is not random and its variation hinders models from learning uniform and meaningful cell and gene representations.

### 5. **Cross-task generalization**: Facilitated drug response prediction, perturbation analysis, and gene module inference without fine-tuning, using embeddings for downstream models.

- 1차 검사: **supported**
- 근거로 든 문장: scFoundation had a higher SIL score, showing its generalization ability in non-fine-tuning mode

- 판정: 
- 메모: 

**P0020** (paragraph, The scFoundation pretraining framework)

> distinguished CD14 monocytes and CD34 cells better (Fig. 2e). We compared our results with scVI trained on the same dataset. Both methods outperformed the raw data in clustering. While their NMI and ARI metrics were similar, scFoundation had a higher SIL score, showing its generalization ability in non-fine-tuning mode (Fig. 2f).

## 3. Methodology and Architecture

### 6. **Data collection**: Aggregated 50 million single-cell RNA-seq profiles from GEO, HCA, and other sources, aligned to 19,264 genes.

- 1차 검사: **supported**
- 근거로 든 문장: aligned all data to a gene list composed of 19,264 protein-coding and common mitochondrial genes

- 판정: 
- 메모: 

**P0005** (paragraph, Body)

> We constructed a comprehensive single-cell dataset by collecting data from all publicly available single-cell resources, including Gene Expression Omnibus (GEO) 22 , Single Cell Portal, HCA 3 , human Ensemble Cell Atlas (hECA) 4 , Deeply Integrated human Single-Cell Omics data (DISCO) 7 , European Molecular Biology Laboratory-European Bioinformatics Institute database (EMBL-EBI) 8 and so on. We aligned all data to a gene list composed of 19,264 protein-coding and common mitochondrial genes, as identified by the HUGO Gene Nomenclature Committee 23 . After data quality control (Methods), we got over 50 million human scRNA-seq data for pretraining. The abundant data sources made the pretraining dataset rich in biological patterns. Anatomically, it spans over 100 tissue types across various diseases, tumors and normal states (Fig. 1a), encompassing almost all known human cell types and states.

### 7. **Model architecture**: xTrimoGene, an asymmetric transformer-based model with an embedding module converting gene expression scalars to learnable vectors, and an encoder-decoder structure for gene context modeling.

- 1차 검사: **supported**
- 근거로 든 문장: We developed xTrimoGene, a scalable transformer-based model with strategies for both algorithmic efficiency and engineering acceleration 18 . It included an embedding module and an asymmetric encoderdecoder structure.

- 판정: 
- 메모: 

**P0012** (paragraph, The scFoundation pretraining framework)

> We developed xTrimoGene, a scalable transformer-based model with strategies for both algorithmic efficiency and engineering acceleration 18 . It included an embedding module and an asymmetric encoderdecoder structure. The embedding module converted continuous gene expression scalars into learnable high-dimensional vectors ensuring full retention of raw expression values, which was a notable improvement over the discretized values used in previous models 13,19 . The asymmetric encoder-decoder architecture had a similar form to the masked autoencoder 20 model in computer vision but was designed to accommodate the high sparsity of scRNA-seq data, achieving efficient learning of all gene relationships without any selection. Moreover, we incorporated a variety of large-scale model training optimization techniques in the model deployment to ensure efficient training (Methods).

### 8. **RDA pretraining task**: Masked gene expressions and predicted values using total count indicators (T and S), with loss computed at masked positions.

- 1차 검사: **supported**
- 근거로 든 문장: We treated the total count as one cell's read depth and defined two total counts indicators: T ('target') and S ('source'), for the total counts of the raw and the input samples

- 판정: 
- 메모: 

**P0013** (paragraph, The scFoundation pretraining framework)

> We designed a pretraining task called the RDA modeling, an extension of masked language modeling 21 , by considering the high variance of read depth in large-scale data. In RDA modeling, the model predicted the masked gene expression of a cell on the basis of its context genes. The context was from a duplication or a low-read-depth variant of that cell's gene expression profile (Methods). We treated the total count as one cell's read depth and defined two total counts indicators: T ('target') and S ('source'), for the total counts of the raw and the input samples,

### 9. **Read-depth enhancement**: Set T > S to generate enhanced gene expression, validated on 10,000 cells with downsampling rates of 1–20%.

- 1차 검사: **supported**
- 근거로 든 문장: We downsampled the total counts to 1%, 5%, 10% and 20% of the original profiles

- 판정: 
- 메모: 

**P0008** (paragraph, Scalable read-depth enhancement model without fine-tuning)

> The RDA modeling enables scFoundation to enhance the read depth of the input cell by setting T as a higher number than S. We assessed this ability on independent test data of 10,000 cells randomly sampled from the validation dataset. We downsampled the total counts to 1%, 5%, 10% and 20% of the original profiles, generating four corresponding datasets with varying total count fold changes. For each dataset, we utilized non-fine-tuned scFoundation to enhance the cells with low total counts by setting the desired total counts T as the reciprocal of the sampling rate. We measured the mean absolute error (MAE), mean relative error (MRE) and Pearson correlation coefficient (PCC) between predicted and actual nonzero gene expressions. As shown in Fig. 2b and Supplementary Fig. 1, scFoundation demonstrated a notable reduction of half the MAE and MRE from the downsampled data even when the downsampling rate was below 10%. These observations showed the ability of scFoundation to enhance gene expressions in scenarios even with extremely low total counts. gene expression pretraining data need to encompass a landscape of cells across different statuses and types. Currently, most scRNA-seq data are loosely organized, and a comprehensive and complete database is still lacking. Second, when modeling each cell as a sentence and each gene expression value as a word, the nearly 20,000 protein-coding genes make the 'sentence' exceptionally long, a scenario that traditional transformers struggle to handle 16,17 . Existing work often had to restrict their models to a small list of selected genes. Third, scRNA-seq data across different techniques and laboratories exhibit high variance in sequencing read depth. Unlike random noises due to technical effects such as contamination that would be reduced by training on large-volume data, read depth is not random and its variation hinders models from learning uniform and meaningful cell and gene representations.

### 10. **Downstream tasks**: Encoded cell and gene embeddings for clustering, drug response prediction, and perturbation analysis.

- 1차 검사: **supported**
- 근거로 든 문장: cell-level tasks including clustering (within and across datasets), bulk and single-cell level drug response prediction and cell type annotation

- 판정: 
- 메모: 

**P0006** (paragraph, Body)

> After pretraining, we applied the scFoundation model to multiple downstream tasks (Fig. 1c). The outputs of the scFoundation encoder were pooled into cell-level embeddings, which were used for cell-level tasks including clustering (within and across datasets), bulk and single-cell level drug response prediction and cell type annotation. The outputs of the scFoundation decoder were gene-level context embeddings, which were used for gene-level tasks such as perturbation prediction and gene module inference.

## 4. Key Results and Benchmarks

### 11. **Clustering performance**: scFoundation outperformed scVI and imputation methods (e.g., SAVER) in NMI, ARI, and SIL scores, with higher SIL values at T/S ratios >3.5.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: scFoundation's performance reached a plateau on higher T/S folds, indicating the cell embeddings were not sensitive to the value of T higher than 3.5S.

- 판정: 
- 메모: 

**P0016** (paragraph, The scFoundation pretraining framework)

> scFoundation outperformed both the baseline and scImpute in all metrics when T was set equal to S (fold change of 1; Fig. 2c) but it exhibited lower performance compared with smaller models like SAVER. This phenomenon wherein the read depth is unaltered has also been reported in a recent work 29 . As the T/S fold increased, we observed a quick jump in scFoundation's performance that surpassed all other methods. Its performance reached a plateau on higher T/S folds, indicating the cell embeddings were not sensitive to the value of T higher than 3.5S. We visualized the scFoundation embedding results at fold change 5 and results from other methods (Fig. 2d). Notably, scFoundation's cell embeddings exhibited more distinctive cluster boundaries compared with the baselines and other methods. Furthermore, we clustered the results of all methods and applied the cluster labels back onto the reference Uniform Manifold Approximation and Projection (UMAP). Other methods showed mixed labels, especially for cluster 0 in the ground truth. scFoundation was the only method that aligned all cell cluster assignments consistently with the reference results.

### 12. **Drug response prediction**: Achieved PCC >0.93 for IC50 predictions, outperforming baseline models by 0.2–0.7 in AUC for drugs like PHA-793887.

- 1차 검사: **flagged** — cited elsewhere: 0.2 as 0.2  (모델: supported)
- 근거로 든 문장: the scFoundation-based DeepCDR model could predict accurate values and achieved a PCC above 0.93

- 판정: 
- 메모: 

**P0025** (paragraph, Improving cancer drug response prediction)

> We evaluated the performance of scFoundation-based results with gene expression-based results across multiple drugs and cancer cell lines (Fig. 3b). Most drugs and all cancer types achieved a higher PCC by using scFoundation embeddings. We visualized the best prediction case of drug and cancer types (Fig. 3c). Regardless of high or low lC 50 , the scFoundation-based DeepCDR model could predict accurate values and achieved a PCC above 0.93. In a drug-blind test that left out one drug at a time from the dataset, scFoundation-based models consistently outperformed the original model (Fig. 3d). The top 1 PCC-gaining drug PHA-793887, a potent ATP-competitive CDK inhibitor, improved the PCC from 0.07 to 0.73. Even for the 200th-ranked drug zobotentan used for blocking endothelin A receptor activity, its PCC improved from 0.49 to 0.64.

### 13. **Perturbation prediction**: scFoundation-based GEARS model reduced MSE by 15–20% compared to baseline, with higher accuracy in predicting gene expression distributions.

- 1차 검사: **flagged** — cited elsewhere: 15 as 15, 20% as 20%  (모델: supported)
- 근거로 든 문장: The scFoundation-based model achieved lower MSE values compared with the original GEARS baseline model.

- 판정: 
- 메모: 

**P0036** (paragraph, Facilitating perturbation response prediction)

> We trained and tested models on three perturbation datasets following the original study (Supplementary Note 5). Since there was no single-cell-level ground truth in the perturbed data, we computed the averaged mean square error (MSE) of the top 20 differentially expressed (DE) genes between pre-and post-gene expression profiles for evaluation. The scFoundation-based model achieved lower MSE values compared with the original GEARS baseline model. On the more challenging two-gene perturbations predictions, the model achieved the lowest averaged MSE in the 0/2 unseen case and outperformed GEARS and another baseline called CPA 56 model across all cases (Fig. 5b and Supplementary Fig. 6). For each two-gene perturbation in the test set, we further examined the proportion of the top 20 DE genes with mean predicted values falling in the 45-55% quantile of the true expression distribution interval. The scFoundation-based model exhibited a higher percentage compared with the baseline (Fig. 5c), indicating it predicted a more reasonable distribution of post-gene expression values. Figure 5d showcased the top 20 genes' expression changes of two-gene perturbation ETS2 + CEBPE. One application for predicting two-gene perturbations was to classify two-gene perturbation into different genetic interaction (GI) types. We identified synergy and suppressor GI types by using the magnitude score (Methods). We first computed the PCC of magnitude score between predicted and ground truth magnitude scores of all two-gene perturbations in test set, and we found that the scFoundation-based model achieved a higher PCC compared with the baseline (Fig. 5e). Then, we ranked two-gene perturbations by predicted magnitude scores, considering the top 20 as potential synergy and the bottom 20 as suppressor GIs. The Venn plot in Fig. 5f revealed that the scFoundation-based model identified a higher number of true perturbations for both synergy and suppressor types.

### 14. **Gene module inference**: Identified cell-type-specific gene modules, validated by enrichment analysis and GRN inference using SCENIC.

- 1차 검사: **supported**
- 근거로 든 문장: Gene enrichment analysis validated that the identified gene modules were enriched in their respective cell types

- 판정: 
- 메모: 

**P0041** (paragraph, Inferring gene modules and gene regulation networks)

> We clustered genes into modules based on their embeddings' similarity. Results showed that scFoundation could identify the differential expressed gene modules of each cell type (Supplementary Figs. 9 and 10). Gene enrichment analysis validated that the identified gene modules were enriched in their respective cell types (Supplementary Fig. 11), indicating that the gene embeddings have learned functional relations among genes. Further, we explored the gene network constructed within the top 1 DE gene module of T cells (Supplementary Fig. 12). Genes CD8A and CD8B encoding chains of the CD8 molecule exhibited strong similarities, while the S100A8 gene showed limited correlation with other T cell markers as expected. This suggested that the embeddings could provide insights into gene relations within modules. Additionally, we conducted experiments on gene regulatory network (GRN) inference with the downstream model SCENIC 63 (Methods). We identified cell-specific regulators such as KLF6, SPIB and MXD4, which were confirmed by the previous work as the regulators for monocyte 64 , B cell 65 and CD8 + T cell 66 , respectively (Supplementary Fig. 13). These examples underscored the potential of scFoundation gene embeddings for inferring GRNs.

### 15. **Batch effect mitigation**: Improved cell mapping across batches using BBKNN, reducing dispersion of cell types.

- 1차 검사: **supported**
- 근거로 든 문장: slightly reducing the dispersion of different cell types

- 판정: 
- 메모: 

**P0021** (paragraph, The scFoundation pretraining framework)

> scFoundation also showcased its capability to facilitate read depth enhanced clustering across different batches. Note that merely aligning the read depth would not eliminate the entire batch effect since batch effects can involve other variations such as donor gender, experiment treatment, cell cycle and so on 32 . We mapped single-cell data from different batches together by feeding the read-depth-enhanced cell embeddings into a nontrainable downstream header BBKNN 33 . Results on simulated data and on data collected from organoid and in vivo experiments showed that scFoundation can achieve better cell mapping while slightly reducing the dispersion of different cell types (Supplementary Table 3 and Supplementary Figs. 3 and 4; details in Supplementary Note 4).

## 5. Limitations and Future Work

### 16. **Data limitations**: Pretraining data may not fully capture human organ development or health states, requiring larger datasets.

- 1차 검사: **supported**
- 근거로 든 문장: Although the pretraining data contained virtually all human scRNA-seq data publicly available at the time of our curation, they may still not be sufficient to fully reflect the complexity of human organ development and health states.

- 판정: 
- 메모: 

**P0045** (paragraph, Discussion)

> We recommend using scFoundation to extract embeddings from datasets without explicit batch-effect or modality differences. Given that batch effects or modality differences may encompass a range of variations, we took the strategy in scFoundation to consider only read depth and leave other possible differences to cooperative methods on downstream tasks, such as BBKNN and SCAD. Furthermore, we suggest using cell and gene embeddings instead of the predicted gene expression values because the current data used as pretraining labels suffered from a high dropout rate and the model pretraining loss was not optimized to zero. scFoundation still faces some limitations. Although the pretraining data contained virtually all human scRNA-seq data publicly available at the time of our curation, they may still not be sufficient to fully reflect the complexity of human organ development and health states. The pretraining demands substantial computational resources, requiring further optimization for efficiency. The current model focused on transcriptomic data only, and did not include genomic or epigenomic data. Also, its unsupervised pretraining process had the advantage of not relying on human annotation of the massive data but overlooked the rich information in metadata. Including cells' metadata with transcriptomic data in the model may have the potential to link cells' molecular features with phenotypes.

### 17. **Computational costs**: Training demands substantial resources, necessitating optimization for efficiency.

- 1차 검사: **supported**
- 근거로 든 문장: The pretraining demands substantial computational resources, requiring further optimization for efficiency.

- 판정: 
- 메모: 

**P0045** (paragraph, Discussion)

> We recommend using scFoundation to extract embeddings from datasets without explicit batch-effect or modality differences. Given that batch effects or modality differences may encompass a range of variations, we took the strategy in scFoundation to consider only read depth and leave other possible differences to cooperative methods on downstream tasks, such as BBKNN and SCAD. Furthermore, we suggest using cell and gene embeddings instead of the predicted gene expression values because the current data used as pretraining labels suffered from a high dropout rate and the model pretraining loss was not optimized to zero. scFoundation still faces some limitations. Although the pretraining data contained virtually all human scRNA-seq data publicly available at the time of our curation, they may still not be sufficient to fully reflect the complexity of human organ development and health states. The pretraining demands substantial computational resources, requiring further optimization for efficiency. The current model focused on transcriptomic data only, and did not include genomic or epigenomic data. Also, its unsupervised pretraining process had the advantage of not relying on human annotation of the massive data but overlooked the rich information in metadata. Including cells' metadata with transcriptomic data in the model may have the potential to link cells' molecular features with phenotypes.

### 18. **Modality gaps**: Focus on transcriptomics excludes genomic/epigenomic data, limiting multi-omics integration.

- 1차 검사: **supported**
- 근거로 든 문장: The current model focused on transcriptomic data only, and did not include genomic or epigenomic data.

- 판정: 
- 메모: 

**P0045** (paragraph, Discussion)

> We recommend using scFoundation to extract embeddings from datasets without explicit batch-effect or modality differences. Given that batch effects or modality differences may encompass a range of variations, we took the strategy in scFoundation to consider only read depth and leave other possible differences to cooperative methods on downstream tasks, such as BBKNN and SCAD. Furthermore, we suggest using cell and gene embeddings instead of the predicted gene expression values because the current data used as pretraining labels suffered from a high dropout rate and the model pretraining loss was not optimized to zero. scFoundation still faces some limitations. Although the pretraining data contained virtually all human scRNA-seq data publicly available at the time of our curation, they may still not be sufficient to fully reflect the complexity of human organ development and health states. The pretraining demands substantial computational resources, requiring further optimization for efficiency. The current model focused on transcriptomic data only, and did not include genomic or epigenomic data. Also, its unsupervised pretraining process had the advantage of not relying on human annotation of the massive data but overlooked the rich information in metadata. Including cells' metadata with transcriptomic data in the model may have the potential to link cells' molecular features with phenotypes.

### 19. **Future directions**: Expand to larger models, integrate multiomics data, and leverage metadata for better cell-phenotype linkage.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 
- 메모: 

**P0046** (paragraph, Discussion)

> In the future, we will pretrain models with more parameters and larger datasets using our effective pretraining framework, and we believe several works could be developed on the basis of the insights from scFoundation. For instance, designing more effective pretraining tasks could potentially improve the model's performance 29 . The effect of various dataset characteristics on training performance also remains to be explored 29 . Furthermore, the emerging field of single-cell multiomics data 67,68 presents opportunities for developing models that can delineate multilevel complex laws of cells. One doable case can be to predict gene expression values based on assay for transposase-accessible chromatin with sequencing (ATAC-seq) context and vice versa (Supplementary Note 7).

### 20. **Enhanced pretraining tasks**: Designing novel tasks to improve model performance and adaptability.

- 1차 검사: **supported**
- 근거로 든 문장: designing more effective pretraining tasks could potentially improve the model's performance 29

- 판정: 
- 메모: 

**P0046** (paragraph, Discussion)

> In the future, we will pretrain models with more parameters and larger datasets using our effective pretraining framework, and we believe several works could be developed on the basis of the insights from scFoundation. For instance, designing more effective pretraining tasks could potentially improve the model's performance 29 . The effect of various dataset characteristics on training performance also remains to be explored 29 . Furthermore, the emerging field of single-cell multiomics data 67,68 presents opportunities for developing models that can delineate multilevel complex laws of cells. One doable case can be to predict gene expression values based on assay for transposase-accessible chromatin with sequencing (ATAC-seq) context and vice versa (Supplementary Note 7).

