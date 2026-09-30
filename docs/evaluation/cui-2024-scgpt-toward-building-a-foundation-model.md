# 검토표: cui-2024-scgpt-toward-building-a-foundation-model

- 논문: scGPT: toward building a foundation model for single-cell multi-omics using generative AI
- 학술지·연도: Nature Methods 2024  (출처 openalex, DOI 10.1038/s41592-024-02201-0)
- 노트 revision: `71afe9f36b46490a934e92203e9056f3`  sha256 `8d54f543779e43ab`
- 추출: partial, 블록 131개, 생성 경로 chunked, 제시 131/131
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

### 1. **Large-scale pretraining**: scGPT was pretrained on 33 million cells from 51 organs/tissues, enabling robust downstream tasks like batch correction and gene network inference.

- 1차 검사: **supported**
- 근거로 든 문장: we assembled scRNA-seq data from 33 million human cells under normal (non-disease) conditions

- 판정:
- 메모:

**P0005** (paragraph, Body)

> To collect diverse and extensive sequencing data for self-supervised pretraining of scGPT, we assembled scRNA-seq data from 33 million human cells under normal (non-disease) conditions, obtained from the CELLxGENE collection (https://cellxgene.cziscience. com/; Fig. 1d). This comprehensive dataset encompasses a wide range of cell types from 51 organs or tissues and 441 studies, providing a rich representation of cellular heterogeneity across the human body. After pretraining, we visualized the scGPT cell embeddings on 10% of the human cells of the 33 million cells using uniform manifold approximation and projection (UMAP) visualization 28 (Fig. 1e). The resulting UMAP plot exhibits intriguing clarity, with cell types accurately represented by distinct colors at localized regions and clusters. Considering the inclusion of over 400 studies in the dataset, this demonstrates the remarkable capability of pretraining to distill biological variation.

### 2. **High-precision cell type annotation**: Achieved >0.8 precision for most cell types in pancreas datasets, with 0.98 precision for cell type A and 0.92 for cell type B in myeloid datasets.

- 1차 검사: **supported**
- 근거로 든 문장: scGPT achieved high precision (>0.8) for most cell types shown in the confusion matrix

- 판정:
- 메모:

**P0006** (paragraph, scGPT improves the precision of cell type annotation)

> To fine-tune the pretrained scGPT for cell type annotation, a neural network classifier takes the scGPT transformer output cell embedding as input and outputs categorical predictions for cell types. The whole model was trained with cross-entropy on a reference dataset with expert annotations and then used to predict cell types on a held-out query data partition. We conducted extensive experiments on diverse datasets to evaluate the performance of scGPT for cell type annotation. First, we adapted scGPT to predict cell types in a human pancreas dataset. We visualized the predictions in Fig. 2a. Notably, scGPT achieved high precision (>0.8) for most cell types shown in the confusion matrix (Fig. 2b), except only for rare cell types with extremely low cell numbers in the reference partition. For example, fewer than 50 cells belong to mast and major histocompatibility (MHC) class II cell types out of the 10,600 cells in the reference set. Fig. 2c visualizes the cell embeddings in the fine-tuned scGPT, which demonstrate high intra-cell type similarities.

**P0018** (paragraph, Prediction of unseen gene perturbations.)

> a Accuracy Precision Recall Macro F1 hPancreas Myeloid MS hPancreas Myeloid MS hPancreas Myeloid MS hPancreas Myeloid MS b f g h i j Confusion matrix for MS Heatmap of emb for MS Confusion matrix for myeloid Heatmap of emb for myeloid Annotated Predicted Confusion matrix Heatmap of cell emb hPancreas c Tumor-infiltrating myeloid cells (myeloid) Reference Query Annotated Predicted Cancer types Cell types d e Cell types PP PSC Acinar Alpha Beta Delta Ductal Endothelial Epsilon Mast MHC class II 0.98 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.01 0.00 0.01 0.00 0.04 0.03 0.00 0.00 0.00 0.00 0.00 0.00 0.14 0.00 0.00 0.00 0.00 0.01 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.02 0.05 0.01 0.01 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.01 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.29 0.00 0.00 0.92 0.84 1.00 1.00 0.91 0.98 1.00 1.00 1.00 0.71 1.00 0.75 0.50 0.25 0 Kidney LYM PAAD THCA UCEC cDC2 ESCA MYE OV-FTC Macro_C1QC Macro_INHBA Macro_LYVE1 Macro_NLRP3 Macro_SPP1 Mono_CD14 Mono_CD16 pDC_LILRA4 Others cDC1_CLEC9A cDC2_CD1C cDC3_LAMP3

### 3. **Perturbation prediction**: Outperformed GEARS and linear regression baselines by 5–20% margins in Perturb-seq datasets, predicting 91.4% of relevant perturbations in top 1 predictions.

- 1차 검사: **flagged** — cited elsewhere: 20% as 0.2/20%  (모델: supported)
- 근거로 든 문장: scGPT identified on average 91.4% relevant perturbations (6.4 of seven) within the top 1 predictions

- 판정: 인용틀림
- 메모: 91.4%는 인용한 P0023에 있음('91.4% relevant perturbations (6.4 of seven) within the top 1 predictions'). 그러나 '5–20% 마진'은 인용한 P0014·P0023에 없고 논문 다른 곳에 있음.
- 판정자: 보조 (사람 확인 필요)

**P0014** (paragraph, Prediction of unseen gene perturbations.)

> For the perturbation prediction task, we evaluated our model using three Perturb-seq datasets of leukemia cell lines: the Adamson dataset 33 consisting of 87 one-gene perturbations, the curated Replogle dataset 34 consisting of 1,823 one-gene perturbations and the Norman dataset 35 consisting of 131 two-gene perturbations and 105 one-gene perturbations. To assess the perturbation prediction capability of scGPT, we fine-tuned the model on a subset of perturbations to predict the perturbed expression profile given an input control cell state and the genes of intervention. Next, the model was tested on perturbations involving unseen genes (Methods). We calculated the Pearson delta metric, which measures the correlation between predicted and observed post-perturbation expression changes. Additionally, we reported this metric on the top 20 most significantly changed genes for each perturbation, denoted as Pearson delta on differentially expressed genes. See Supplementary Note 12 for details on metric calculations. We conducted a performance

**P0023** (paragraph, Prediction of unseen gene perturbations.)

> A hypothetical example application of such capability could be to predict CRISPR target genes that influence cells to recover from a disease state. To showcase the effectiveness of reverse perturbation prediction, we used a subset of the Norman dataset focusing on perturbations involving 20 genes (Fig. 3f). This combinatorial space consists of a total of 210 one-gene or two-gene perturbation combinations. We fine-tuned scGPT using 39 (18%) known perturbations (the training group in Fig. 3f). We then tested the model on queries of unseen perturbed cell states, and scGPT successfully predicted the source of perturbations (within top-ranked predictions) that would generate the observed results. For example, scGPT ranked the correct perturbation of CNN1 + MAPK1 genes as the top prediction for one test example, and the correct perturbation of FOSB + UBASH3B genes was ranked as the second prediction for another case (Fig. 3f). Overall, scGPT identified on average 91.4% relevant perturbations (6.4 of seven) within the top 1 predictions (blue bars in Fig. 3g) and 65.7% correct perturbations (4.6 of seven test cases) within the top 8 predictions (pink bars in Fig. 3g), outperforming GEARS and the differential gene baseline by a considerable margin. We envision that these predictions can be used for planning perturbation experiments by maximizing the possibility of deriving target cell states. Compared to random tryouts, which would on average require 105.5 attempts of the 210 possible perturbations in this subset, finding the correct source of genetic change with fewer attempts offers a valuable tool for accelerating the discovery of important genetic drivers and optimizing perturbation experiments.

### 4. **Multi-omic integration**: Demonstrated superior performance in integrating scRNA-seq and scATAC-seq data, achieving AvgBIO scores 5–10% higher than scVI, Seurat, and Harmony.

- 1차 검사: **supported**
- 근거로 든 문장: with an AvgBIO score of 0.821, which was 5-10% higher than that of the compared methods

- 판정:
- 메모:

**P0024** (paragraph, scGPT enables multi-batch and multi-omic integration)

> Multi-batch scRNA-seq integration. Integrating multiple scRNA-seq datasets from different batches poses unique challenges in simultaneously preserving the biological variance of integrated data and removing technical batch effects. To integrate sequencing samples, we fine-tuned scGPT in a self-supervised manner by learning unified cell presentations that recover masked gene expression (Methods). In our benchmarking experiments, we compared scGPT with three popular integration methods: scVI 38 , Seurat 39 and Harmony 40 . The evaluation was conducted on three integration datasets, namely, COVID-19 (18 batches) 12 , peripheral blood mononuclear cell (PBMC) 10k (two batches) 41 and perirhinal cortex (two batches) 42 datasets. In the PBMC 10k dataset, scGPT successfully separated all cell types (Fig. 4a). The superior integration performance of scGPT was further supported by its high biological conservation score, with an AvgBIO score of 0.821, which was 5-10% higher than that of the compared methods.

### 5. **Gene-gene interaction discovery**: Uncovered cell-type-specific gene interactions via gene embeddings and attention weights, highlighting pathways like TCR signaling and MHC class II antigen presentation.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: scGPT uncovers valuable biological insights into gene-gene interactions specific to various conditions, such as cell types and perturbation states.

- 판정: 인용틀림
- 메모: 앞부분(gene embeddings·attention weights로 세포유형별 유전자 상호작용)은 P0012가 뒷받침함. 그러나 'TCR signaling·MHC class II antigen presentation'은 P0028에 있고 그 문단을 인용하지 않았음.
- 판정자: 보조 (사람 확인 필요)

**P0012** (paragraph, scGPT predicts unseen genetic perturbation responses)

> Our model, scGPT, demonstrates the transformative potential of the single-cell foundation model through three key aspects. First, scGPT represents a large-scale generative foundation model that enables transfer learning across a diverse range of downstream tasks. By achieving state-of-the-art performance on cell type annotation, genetic perturbation prediction, batch correction and multi-omic integration, we showcase the effectiveness of the 'pretraining universally, fine-tuning on demand' approach as a generalist solution for computational applications in single-cell omics. Second, through the comparison of gene embeddings and attention weights between fine-tuned and raw pretrained models, scGPT uncovers valuable biological insights into genegene interactions specific to various conditions, such as cell types and perturbation states. Third, our observations reveal a scaling effect: larger pretraining data sizes yield superior pretrained embeddings and further lead to improved performance on downstream tasks. This finding highlights the exciting prospect that foundation models can continuously improve alongside the expansion of available sequencing data in the research community. Based on these findings, we envision that the adoption of pretrained foundation models will greatly expand our understanding of cellular biology and serve as a solid foundation for future discoveries. The release of the scGPT models and workflow aims to empower and expedite research in these areas and beyond.

**P0026** (paragraph, Single-cell multi-omic integration.)

> Single-cell multi-omic (scMultiomic) data, which combine multiple views of genetic regulation such as epigenetic, transcriptomic and translation activities, present a unique challenge in aggregating cell representations while preserving biological signals 8,9 . scGPT addresses this challenge by effectively extracting integrated cell embeddings across different omics datasets. In the case of the 10x Multiome PBMC dataset 43 , which includes joint gene expression and chromatin accessibility measurements, we compared scGPT with two state-of-the-art methods, scGLUE 13 and Seurat (v.4) 44 . As depicted in Fig. 4b, scGPT stands out as the only method that successfully generates a distinct cluster for CD8 + naive cells. Next, we tested scGPT on the paired gene expression and protein abundance dataset from bone marrow mononuclear cells (BMMCs) 45 as illustrated in Fig. 4c. This dataset contains additional complexity from the large amount of data (90,000 cells), multiple batches (12 donors) and fine-grained subgroup annotations (48 cell types). scGPT presented more defined cluster structures than Seurat (v.4), with a 9% improvement in the AvgBIO score. Notably, scGPT was able to separate CD4 + naive T cells and CD4 + activated T cells as two distinct clusters. It also teased apart integrin β 7 + activated CD4 + T cells from other CD4 + T cells, which further endorsed the ability of the model to capture subtle differences between immune cell subgroups. In the mosaic data-integration setting, sequenced samples share some, but not all, data modalities, posing a challenge for integration methods. To showcase the capabilities of scGPT in this context, we used the ATAC with select antigen profiling (ASAP) human PBMC dataset 46 as an example. This dataset consists of four sequencing batches with three data modalities. In the benchmark experiment with scMoMat 14 , scGPT demonstrated superior batch correction performance as shown in Fig. 4d, especially in groups of B, myeloid and natural killer (NK) cells. Overall, scGPT demonstrates superior cell type-clustering performance and exhibits robustness across diverse benchmarked biological conservation metrics (Supplementary Table 4).

## 3. Methodology and Architecture

### 6. **Transformer-based architecture**: scGPT uses a generative pretrained transformer with 512 embedding size, 12 transformer blocks, and 8 attention heads, trained on gene tokens and condition tokens.

- 1차 검사: **flagged** — cited elsewhere: 512 as 512, 12 as 12  (모델: not_in_paragraph)
- 근거로 든 문장: none

- 판정: 인용틀림
- 메모: 512·12·8 중 어느 것도 인용한 P0011·P0017에 없음. 512와 12는 논문 다른 곳에 있음.
- 판정자: 보조 (사람 확인 필요)

**P0011** (paragraph, scGPT predicts unseen genetic perturbation responses)

> In this work, we present the single-cell foundation model scGPT by pretraining on over 33 million cells. We establish a unified generative pretraining workflow specifically for non-sequential omics data and adapt the transformer architecture to simultaneously learn cell and gene representations. Additionally, we provide fine-tuning pipelines with task-specific objectives, designed to facilitate application of the pretrained model across a range of diverse tasks.

**P0017** (paragraph, Prediction of unseen gene perturbations.)

> The ability to predict unseen perturbation responses could expand the scope of perturbation experiments, as depicted in Fig. 3c. To explore the expanded space of predicted perturbation responses, we conducted clustering analysis using the Norman dataset to validate biologically relevant functional signals. The original Perturb-seq study covered 236 perturbations targeting 105 genes. However, considering all possible combinations of these target genes, there are a total of 5,565 potential perturbations, indicating that the experimental Perturb-seq data only represent 5% of the entire perturbation space. Therefore, we applied the

### 7. **Input processing**: Gene expression values are binned into relative values to ensure semantic consistency across batches, with preprocessing including log1p transformation and HVG selection.

- 1차 검사: **supported**
- 근거로 든 문장: Variations in sequencing depths and the presence of sparsely expressed genes result in substantial differences in data scales among different batches of sequencing samples.

- 판정:
- 메모:

**P0043** (paragraph, Expression values.)

> The gene expression matrix X requires additional processing before being used as input for modeling. A fundamental challenge in gene expression modeling is the variability in absolute magnitudes across different sequencing protocols 55 . Variations in sequencing depths and the presence of sparsely expressed genes result in substantial differences in data scales among different batches of sequencing samples. These differences are not easily mitigated with common preprocessing techniques such as transcripts-per-million normalization and log1p transformation 56 . Even after these transformations, the same absolute value can convey different 'semantic' meanings across sequencing batches. To address this scale difference, we propose the value binning technique to convert all expression counts into relative values. For each non-zero expression count in each cell, we calculate the raw absolute values and divide them into B consecutive intervals [b k , b k+1 ], where k ∈ {1, 2, …, B}. Each interval represents an equal portion of all expressed genes (1/B). It is important to note that a new set of bin edges is computed for each cell, so the interval edges b k may vary among cells. The binned expression value x (i) j for cell i is defined as:

**P0044** (paragraph, Expression values.)

> Through this binning technique, the semantic meaning of x (i) j is consistent across cells from various sequencing batches. For instance, a value of x (i) j = B consistently indicates the highest expression among genes. Notably, for fine-tuning tasks, we also performed log1p transformation and HVG selection before the value binning step. To simplify the notation, we use X i,j to represent both the raw and preprocessed data matrices before binning. Therefore, the final input vector of binned expression values for cell i is denoted as

### 8. **Attention masking**: Specialized masking mechanisms prevent attention between unknown genes during pretraining, enabling iterative prediction of gene expressions.

- 1차 검사: **supported**
- 근거로 든 문장: Attention is only applied between the known genes and the query unknown gene itself but not to the positions of other unknown genes.

- 판정:
- 메모:

**P0063** (paragraph, QK T)

> We specifically designed the scGPT attention mask to support both gene-prompt and cell-prompt generations in a unified way. The attention mask A A A mask ∈ {0, -inf } M×M is visualized in Supplementary Fig. 1a, where queries are organized in rows and keys in columns. As annotated at the bottom of the figure, each token in the input embedding h h h (i) l can be one of these three groups: (1) the reserved < cls > token for cell embedding (introduced in Cell representation), (2) known genes with token embeddings and expression value embeddings and (3) unknown genes for which expression values are to be predicted. The rule of thumb for scGPT attention masking is to only allow attention computation between embeddings of the 'known genes' and the query gene itself. This is achieved by using the elements a i,j in A mask as follows:

**P0066** (paragraph, QK T)

> As illustrated in Supplementary Fig. 1a, during training, we randomly pick a proportion of the genes as unknown so that their expression values are omitted in the input. Attention is only applied between the known genes and the query unknown gene itself but not to the positions of other unknown genes. For example, the gene to predict at position j has attention scores with the cell embedding, known genes and itself only but not the other unknown genes, as illustrated in the last row of the attention mask. The scGPT model predicts expression for these unknown genes via stacked transformer blocks with the masked-attention map described above. The inference steps are illustrated in Supplementary Fig. 1b. During inference for cell-prompt generation, scGPT generates all genome-wide gene expression conditioned on the specific cell types. A trained cell embedding is inputted at the first position representing the cell type condition. The whole generation process of thousands of gene expression values is conducted in K iterative steps (that is, K = 3 steps in Supplementary Fig. 1b). For example, in one iteration i ∈ {1, 2, …K}, the attention-masking mechanism allows attention with all predicted genes from previous 0 to i -1 iterations. In each iteration, scGPT selects the top 1/K genes from the unknown set with the highest prediction confidence to be included as known genes in the next iteration i + 1. Intuitively, this workflow streamlines the generation of gene expression in an autoregressive manner, in which gene expression values with highest prediction confidence are first generated and used to help subsequent rounds of generation. Gene-prompt generation works similarly in an iterative manner. The difference is that it starts with a set of known genes with observed expression values instead of a cell embedding.

### 9. **Fine-tuning objectives**: Includes gene expression prediction (GEP), perturbation-GEP, and cell-type classification, with losses optimized for biological validity.

- 1차 검사: **supported**
- 근거로 든 문장: GEP presents a general self-supervised fine-tuning objective that aims to forecast gene expression values.

- 판정:
- 메모:

**P0071** (paragraph, Fine-tuning objectives)

> scGPT leverages various fine-tuning objectives to facilitate learning of biologically valid representations of cells and genes as well as for regularization purposes such as batch correction.

**P0075** (paragraph, Gene expression prediction.)

> . GEP presents a general self-supervised fine-tuning objective that aims to forecast gene expression values. In certain downstream tasks, such as perturbation prediction, the model is required to predict perturbed gene expression values instead of the original values. We refer to this variation as perturb-GEP. We maintain the MLP estimator in equation ( 13) but use post-perturbation gene expression as the target

### 10. **Batch correction**: Modality and batch tokens are integrated to model gene expression dependencies, mitigating batch effects via reverse backpropagation.

- 1차 검사: **supported**
- 근거로 든 문장: This serves as a technique to facilitate batch correction.

- 판정:
- 메모:

**P0052** (paragraph, Cell representation.)

> The difference between the tokens described in Input embeddings and the batch and modality tokens is that these embeddings of batch and modality tokens are not used as input to the transformer blocks. Instead, they are concatenated with the transformer output on either the feature or cell level before entering specific fine-tuning objectives. This is to prevent the transformer from amplifying the attention within features of the same modalities while underestimating those of different modalities. Furthermore, knowing the modality and/or batch identities facilitates gene expression modeling in the downstream fine-tuning objectives. As the model learns to predict expression values conditioned on modality and/or batch identities, such biases are implicitly removed from the gene and cell representations themselves. This serves as a technique to facilitate batch correction.

**P0081** (paragraph, Domain adaptation via reverse back propagation.)

> Cell representation learning is hindered by the presence of batch effects, which result from non-biological batch differences introduced by sequencing technologies 64,65 . To mitigate this problem, we use a distinct MLP classifier to predict the sequencing batch associated with each input cell from their cell representations h h h (i) c and to modify the back-propagation process by reversing the gradients within the model. This approach leverages insights from the robust domain-adaptation method proposed by Ganin and Lempitsky 66 .

## 4. Key Results and Benchmarks

### 11. **Cell type annotation**: Achieved 0.84–0.98 precision across pancreas, myeloid, and MS datasets, outperforming scBERT and TOSICA.

- 1차 검사: **supported**
- 근거로 든 문장: scGPT constantly outperformed the other methods in all classification metrics, including accuracy, precision, recall and macro F1

- 판정:
- 메모:

**P0006** (paragraph, scGPT improves the precision of cell type annotation)

> To fine-tune the pretrained scGPT for cell type annotation, a neural network classifier takes the scGPT transformer output cell embedding as input and outputs categorical predictions for cell types. The whole model was trained with cross-entropy on a reference dataset with expert annotations and then used to predict cell types on a held-out query data partition. We conducted extensive experiments on diverse datasets to evaluate the performance of scGPT for cell type annotation. First, we adapted scGPT to predict cell types in a human pancreas dataset. We visualized the predictions in Fig. 2a. Notably, scGPT achieved high precision (>0.8) for most cell types shown in the confusion matrix (Fig. 2b), except only for rare cell types with extremely low cell numbers in the reference partition. For example, fewer than 50 cells belong to mast and major histocompatibility (MHC) class II cell types out of the 10,600 cells in the reference set. Fig. 2c visualizes the cell embeddings in the fine-tuned scGPT, which demonstrate high intra-cell type similarities.

**P0007** (paragraph, scGPT improves the precision of cell type annotation)

> Next, we tested the model on a disease dataset of multiple sclerosis (MS) 29 . The model was fine-tuned on a reference partition of healthy human immune cells and evaluated on the prediction for cells with the MS condition. The fine-tuned model demonstrated strong alignment with the cell type annotations provided by the original study and achieved a high accuracy of around 0.85 (Fig. 2f,g). Furthermore, we applied the model to a more challenging scenario for generalization across disease types using a tumor-infiltrating myeloid dataset 30 . The model was fine-tuned on six cancer types in a reference data partition (Methods) and evaluated on the query partition of three unseen cancer types (Fig. 2d). The results demonstrated high precision in distinguishing immune cell subtypes (Fig. 2e,h), and the cell embeddings exhibited clear separability among different cell types (Fig. 2i). Finally, we benchmarked the fine-tuned scGPT against two other recent transformer-based methods, TOSICA 31 and scBERT 32 , across the three datasets (Methods). scGPT constantly outperformed the other methods in all classification metrics, including accuracy, precision, recall and macro F1 (Fig. 2j).

**P0018** (paragraph, Prediction of unseen gene perturbations.)

> a Accuracy Precision Recall Macro F1 hPancreas Myeloid MS hPancreas Myeloid MS hPancreas Myeloid MS hPancreas Myeloid MS b f g h i j Confusion matrix for MS Heatmap of emb for MS Confusion matrix for myeloid Heatmap of emb for myeloid Annotated Predicted Confusion matrix Heatmap of cell emb hPancreas c Tumor-infiltrating myeloid cells (myeloid) Reference Query Annotated Predicted Cancer types Cell types d e Cell types PP PSC Acinar Alpha Beta Delta Ductal Endothelial Epsilon Mast MHC class II 0.98 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.01 0.00 0.01 0.00 0.04 0.03 0.00 0.00 0.00 0.00 0.00 0.00 0.14 0.00 0.00 0.00 0.00 0.01 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.02 0.05 0.01 0.01 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.01 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.29 0.00 0.00 0.92 0.84 1.00 1.00 0.91 0.98 1.00 1.00 1.00 0.71 1.00 0.75 0.50 0.25 0 Kidney LYM PAAD THCA UCEC cDC2 ESCA MYE OV-FTC Macro_C1QC Macro_INHBA Macro_LYVE1 Macro_NLRP3 Macro_SPP1 Mono_CD14 Mono_CD16 pDC_LILRA4 Others cDC1_CLEC9A cDC2_CD1C cDC3_LAMP3

### 12. **Perturbation prediction**: ScGPT achieved 0.98 Pearson delta on DE genes in Adamson dataset, outperforming GEARS and linear baselines by 5–20%.

- 1차 검사: **flagged** — cited elsewhere: 0.98 as 0.98  (모델: supported)
- 근거로 든 문장: scGPT excelled in predicting post-perturbation changes, consistently outperforming the others by 5-20% margins.

- 판정: 인용틀림
- 메모: 0.98은 논문에 있으나(P0018) 인용한 P0016은 그림 라벨 더미이고 P0023은 역방향 perturbation 예시임. 세션 초반에 사람이 읽어 확인한 항목.
- 판정자: 보조 (사람 확인 필요)

**P0016** (paragraph, Prediction of unseen gene perturbations.)

> Gene 1 … + Separate embedding layers + + … Gene tokens CCR7 TLR4 CCL1 Gene G … 1 3 ? Condition tokens 2 Full embeddings Element-wise sum Input embedding Masked multi-head attention Feed forward Add + norm Add + norm Expression values gene … c Masked-attention transformer d e UMAP of sampled normal human cells using scGPT emb + Gene 2 Gene 3 Gene G Gene 1 Gene 3 Gene G Gene Gene Embedding when expression is known Embedding when expression is unknown Gene 2 Cell numbers and origin tissues included in the pretraining Whole human 33M Brain 13.2M Lung 2.1M Heart 1.8M Kidney 814k Intestine 94.5k Blood 10.3M Pancreas 210k GABAergic neuron L2/3-6 intratelencephalic projecting glutamatergic cortical neuron Astrocyte Cardiocyte Cell of skeletal muscle Columnar/cuboidal epithelial cell Conjunctival epithelial cell Connective tissue cell Duct epithelial cell Ecto-epithelial cell Endo-epithelial cell Epithelial cell of pancreas Epithelial cell of urethra Extraembryonic cell Fibroblast Follicular epithelial cell Glandular epithelial cell Glutamatergic neuron Hematopoietic cell Hepatocyte Inflammatory cell Ionocyte Kidney cell Macrophage Mammary gland epithelial cell Melanocyte Mesenchymal cell Meso-epithelial cell Multi-fate stem cell Mural cell Muscle cell Muscle precursor cell Myofibroblast cell Naive thymus-derived CD4-positive, αβ T cell NK cell Neural cell Neuron Oligodendrocyte Others Salivary gland cell Sensory epithelial cell Somatic stem cell Stratified epithelial cell Transitional epithelial cell Vertebrate lens cell Cell atlas comparison between scGPT and two other methods, GEARS 36 and a linear regression baseline (Methods). Our results demonstrate that scGPT achieved the highest scores for all three datasets (Fig. 3a and Supplementary Table 6). Particularly, scGPT excelled in predicting post-perturbation changes, consistently outperforming the others by 5-20% margins. Additionally, we visualized predictions for two example perturbations in the Adamson dataset in Fig. 3b, where scGPT accurately predicted the trend of expression change for all top 20 differentially expressed genes.

**P0023** (paragraph, Prediction of unseen gene perturbations.)

> A hypothetical example application of such capability could be to predict CRISPR target genes that influence cells to recover from a disease state. To showcase the effectiveness of reverse perturbation prediction, we used a subset of the Norman dataset focusing on perturbations involving 20 genes (Fig. 3f). This combinatorial space consists of a total of 210 one-gene or two-gene perturbation combinations. We fine-tuned scGPT using 39 (18%) known perturbations (the training group in Fig. 3f). We then tested the model on queries of unseen perturbed cell states, and scGPT successfully predicted the source of perturbations (within top-ranked predictions) that would generate the observed results. For example, scGPT ranked the correct perturbation of CNN1 + MAPK1 genes as the top prediction for one test example, and the correct perturbation of FOSB + UBASH3B genes was ranked as the second prediction for another case (Fig. 3f). Overall, scGPT identified on average 91.4% relevant perturbations (6.4 of seven) within the top 1 predictions (blue bars in Fig. 3g) and 65.7% correct perturbations (4.6 of seven test cases) within the top 8 predictions (pink bars in Fig. 3g), outperforming GEARS and the differential gene baseline by a considerable margin. We envision that these predictions can be used for planning perturbation experiments by maximizing the possibility of deriving target cell states. Compared to random tryouts, which would on average require 105.5 attempts of the 210 possible perturbations in this subset, finding the correct source of genetic change with fewer attempts offers a valuable tool for accelerating the discovery of important genetic drivers and optimizing perturbation experiments.

### 13. **Multi-omic integration**: AvgBIO score of 0.821 on PBMC 10k dataset, 5–10% higher than scVI, Seurat, and Harmony.

- 1차 검사: **supported**
- 근거로 든 문장: with an AvgBIO score of 0.821, which was 5-10% higher than that of the compared methods

- 판정:
- 메모:

**P0024** (paragraph, scGPT enables multi-batch and multi-omic integration)

> Multi-batch scRNA-seq integration. Integrating multiple scRNA-seq datasets from different batches poses unique challenges in simultaneously preserving the biological variance of integrated data and removing technical batch effects. To integrate sequencing samples, we fine-tuned scGPT in a self-supervised manner by learning unified cell presentations that recover masked gene expression (Methods). In our benchmarking experiments, we compared scGPT with three popular integration methods: scVI 38 , Seurat 39 and Harmony 40 . The evaluation was conducted on three integration datasets, namely, COVID-19 (18 batches) 12 , peripheral blood mononuclear cell (PBMC) 10k (two batches) 41 and perirhinal cortex (two batches) 42 datasets. In the PBMC 10k dataset, scGPT successfully separated all cell types (Fig. 4a). The superior integration performance of scGPT was further supported by its high biological conservation score, with an AvgBIO score of 0.821, which was 5-10% higher than that of the compared methods.

### 14. **Gene network inference**: Identified 22 unique pathways, including adaptive immune and TCR signaling, with 15 shared pathways compared to coexpression networks.

- 1차 검사: **supported**
- 근거로 든 문장: scGPT uniquely identified an additional 22 pathways, 14 of which were immune related.

- 판정:
- 메모:

**P0028** (paragraph, scGPT uncovers gene networks for specific cell states)

> scGPT (fine-tuned) scGLUE Seurat version 4 b d Cell type, AvgBIO = 0.758 Cell type, AvgBIO = 0.747 Cell type, AvgBIO = 0.722 scGPT (fine-tuned) scMoMaT Batch, AvgBATCH = 0.951 Cell type, AvgBIO = 0.587 Batch, AvgBATCH = 0.916 Cell type, AvgBIO = 0.546 Seurat version 4 Cell type, AvgBIO = 0.600 c Cell type, AvgBIO = 0.697 scGPT (fine-tuned) a scGPT (fine-tuned) scVI Seurat version 3 Cell type, AvgBIO = 0.821 Cell type, AvgBIO = 0.753 Cell type, AvgBIO = 0.724 Harmony Cell type, AvgBIO = 0.784 PBMC 10k 10x Multiome PBMC BMMC ASAP human PBMC 0 1 2 3 B cell Myeloid NK T cell 0 1 2 3 B cell Myeloid NK T cell B cells CD14 + monocytes CD4 + T cells CD8 + T cells Dendritic cells FCGR3A + monocytes Megakaryocytes NK cells Other MAIT CD14 + mono CD16 + mono CD4 + naive CD4 + T CM CD4 + T EM CD8 + naive CD8 + TEM 1 CD8 + TEM 2 HSPC Intermediate B Memory B NK Naive B Plasma T reg cDC γδT pDC B1 B IGKC + Plasma cell IGKC + CD8 + T naive CD8 + T naive CD127 + CD26 -CD101 -Erythroblast G/M prog HSC ILC ILC1 Lymph prog MAIT MK/E prog NK NK CD158e1+ Naive CD20 + B IGKC + Naive CD20 + B IGKC -Normoblast Plasma cell IGKC -Plasmablast IGKC + Plasmablast IGKC -Proerythroblast Reticulocyte T prog cycling T reg Transitional B cDC1 cDC2 dnT γδT CD158b + γδT TCRVD2 + pDC B1 B IGKC -CD14 + mono CD16 + mono CD4 + T CD314 + CD45RA + CD4 + T activated CD4 + T activated integrin β 7 + CD4 + T naive CD8 + T CD49f + CD8 + T CD57 + CD45RA + CD8 + T CD57 used for the integration task (Methods) for the purpose of GRN analysis. The pretrained scGPT model successfully identified the group of genes (CD3E, CD3D and CD3G) encoding the T3 complex for T cell activation as well as CD79A and CD79B for B cell signaling and CD8A and CD8B as co-receptors for HLA class I molecules 49 (Fig. 5b). Furthermore, the fine-tuned scGPT model highlighted the connection between CD36 and CD14 (Fig. 5b). scGPT is able to uncover meaningful gene programs that exhibit cell type-specific activation. Gene programs are subsequently selected and clustered using gene embeddings from scGPT (Methods). In Fig. 5c, we visualize gene programs extracted by the fine-tuned scGPT model on highly variable genes (HVGs) in the immune human dataset 50 and their expression in different cell types. We observed that a set of HLA class II genes was identified as group 2. Similarly, the CD3 genes involved in the T3 complex were identified as group 3, with the highest expression present in T cells. To systematically validate the extracted gene programs, we performed pathway enrichment analysis against the Reactome database (https://reactome.org/) and identified high-confidence 'pathway hits' using stringent multiple-testing correction (https://mathworld.wolfram.com/BonferroniCorrection.html and Methods). In Fig. 5d, we compare the results obtained from scGPT with those from the coexpression network. Notably, scGPT consistently demonstrates a substantially higher number of enriched pathways across all clustering resolutions. Furthermore, we examined similarities and differences in the identified pathways between scGPT and the coexpression network, as depicted in Fig. 5e. Both methods identified 15 common pathways, including those associated with the cell cycle and the immune system. scGPT uniquely identified an additional 22 pathways, 14 of which were immune related. Notably, scGPT specifically highlighted pathways related to the adaptive immune system, T cell receptor signaling, PD-1 signaling and MHC class II presentation. This is concordant with the fact that adaptive immune populations exist in the fine-tuning datasets. These findings demonstrate the superior ability of scGPT to capture intricate gene-gene connections and unravel specific mechanisms within a broader biological context. The detailed list of enriched pathways is provided in Supplementary Table 5.

### 15. **Batch correction**: Separated all cell types in PBMC 10k dataset and achieved 9% higher AvgBIO score than Seurat (v.4) on BMMC data.

- 1차 검사: **supported**
- 근거로 든 문장: scGPT presented more defined cluster structures than Seurat (v.4), with a 9% improvement in the AvgBIO score.

- 판정:
- 메모:

**P0026** (paragraph, Single-cell multi-omic integration.)

> Single-cell multi-omic (scMultiomic) data, which combine multiple views of genetic regulation such as epigenetic, transcriptomic and translation activities, present a unique challenge in aggregating cell representations while preserving biological signals 8,9 . scGPT addresses this challenge by effectively extracting integrated cell embeddings across different omics datasets. In the case of the 10x Multiome PBMC dataset 43 , which includes joint gene expression and chromatin accessibility measurements, we compared scGPT with two state-of-the-art methods, scGLUE 13 and Seurat (v.4) 44 . As depicted in Fig. 4b, scGPT stands out as the only method that successfully generates a distinct cluster for CD8 + naive cells. Next, we tested scGPT on the paired gene expression and protein abundance dataset from bone marrow mononuclear cells (BMMCs) 45 as illustrated in Fig. 4c. This dataset contains additional complexity from the large amount of data (90,000 cells), multiple batches (12 donors) and fine-grained subgroup annotations (48 cell types). scGPT presented more defined cluster structures than Seurat (v.4), with a 9% improvement in the AvgBIO score. Notably, scGPT was able to separate CD4 + naive T cells and CD4 + activated T cells as two distinct clusters. It also teased apart integrin β 7 + activated CD4 + T cells from other CD4 + T cells, which further endorsed the ability of the model to capture subtle differences between immune cell subgroups. In the mosaic data-integration setting, sequenced samples share some, but not all, data modalities, posing a challenge for integration methods. To showcase the capabilities of scGPT in this context, we used the ATAC with select antigen profiling (ASAP) human PBMC dataset 46 as an example. This dataset consists of four sequencing batches with three data modalities. In the benchmark experiment with scMoMat 14 , scGPT demonstrated superior batch correction performance as shown in Fig. 4d, especially in groups of B, myeloid and natural killer (NK) cells. Overall, scGPT demonstrates superior cell type-clustering performance and exhibits robustness across diverse benchmarked biological conservation metrics (Supplementary Table 4).

## 5. Limitations and Future Work

### 16. **Rare cell types**: Precision drops for cell types with <50 cells in reference sets.

- 1차 검사: **supported**
- 근거로 든 문장: fewer than 50 cells belong to mast and major histocompatibility (MHC) class II cell types out of the 10,600 cells in the reference set.

- 판정:
- 메모:

**P0006** (paragraph, scGPT improves the precision of cell type annotation)

> To fine-tune the pretrained scGPT for cell type annotation, a neural network classifier takes the scGPT transformer output cell embedding as input and outputs categorical predictions for cell types. The whole model was trained with cross-entropy on a reference dataset with expert annotations and then used to predict cell types on a held-out query data partition. We conducted extensive experiments on diverse datasets to evaluate the performance of scGPT for cell type annotation. First, we adapted scGPT to predict cell types in a human pancreas dataset. We visualized the predictions in Fig. 2a. Notably, scGPT achieved high precision (>0.8) for most cell types shown in the confusion matrix (Fig. 2b), except only for rare cell types with extremely low cell numbers in the reference partition. For example, fewer than 50 cells belong to mast and major histocompatibility (MHC) class II cell types out of the 10,600 cells in the reference set. Fig. 2c visualizes the cell embeddings in the fine-tuned scGPT, which demonstrate high intra-cell type similarities.

### 17. **Batch effects**: Pretraining does not inherently mitigate batch effects, requiring additional correction during fine-tuning.

- 1차 검사: **supported**
- 근거로 든 문장: Notably, the current pretraining does not inherently mitigate batch effects

- 판정:
- 메모:

**P0037** (paragraph, Discussion)

> We introduce scGPT, a foundation model that harnesses the power of pretrained transformers on a vast amount of single-cell data. Building upon the success of self-supervised pretraining in language models, we adopted a similar approach in the single-cell domain to unravel complex biological interactions. The use of transformers in scGPT enables simultaneous learning of gene and cell embeddings, which facilitates the modeling of various aspects of cellular processes. By leveraging the attention mechanism of transformers, scGPT captures gene-to-gene interactions at the single-cell level, providing an additional layer of interpretability. We demonstrated the benefits of pretraining with comprehensive experiments in both zero-shot and fine-tuning settings. The pretrained model showcases strong capabilities of extrapolating to unseen datasets, presenting meaningful clustering patterns in accordance with cell types in zero-shot experiments. In addition, the learned gene networks in scGPT exhibit strong alignment with known functional groups. Furthermore, the pretrained model's knowledge can be transferred to multiple downstream tasks through fine-tuning. In a variety of tasks such as cell type annotation, perturbation prediction and multi-batch and multi-omic integration, the fine-tuned scGPT model consistently outperforms models trained from scratch. This demonstrates the value of the pretrained model to downstream tasks, enabling more accurate and biologically meaningful analyses. Notably, the current pretraining does not inherently mitigate batch effects, and thus the model's zero-shot performance could be constrained on datasets with substantial technical variation. Evaluating the model is also complex, given the frequent absence of definitive biological ground truths and the variation in data quality (detailed in Supplementary Note 10).

### 18. **Technical variation**: Zero-shot performance may be constrained on datasets with high technical variation.

- 1차 검사: **supported**
- 근거로 든 문장: Notably, the current pretraining does not inherently mitigate batch effects, and thus the model's zero-shot performance could be constrained on datasets with substantial technical variation.

- 판정:
- 메모:

**P0037** (paragraph, Discussion)

> We introduce scGPT, a foundation model that harnesses the power of pretrained transformers on a vast amount of single-cell data. Building upon the success of self-supervised pretraining in language models, we adopted a similar approach in the single-cell domain to unravel complex biological interactions. The use of transformers in scGPT enables simultaneous learning of gene and cell embeddings, which facilitates the modeling of various aspects of cellular processes. By leveraging the attention mechanism of transformers, scGPT captures gene-to-gene interactions at the single-cell level, providing an additional layer of interpretability. We demonstrated the benefits of pretraining with comprehensive experiments in both zero-shot and fine-tuning settings. The pretrained model showcases strong capabilities of extrapolating to unseen datasets, presenting meaningful clustering patterns in accordance with cell types in zero-shot experiments. In addition, the learned gene networks in scGPT exhibit strong alignment with known functional groups. Furthermore, the pretrained model's knowledge can be transferred to multiple downstream tasks through fine-tuning. In a variety of tasks such as cell type annotation, perturbation prediction and multi-batch and multi-omic integration, the fine-tuned scGPT model consistently outperforms models trained from scratch. This demonstrates the value of the pretrained model to downstream tasks, enabling more accurate and biologically meaningful analyses. Notably, the current pretraining does not inherently mitigate batch effects, and thus the model's zero-shot performance could be constrained on datasets with substantial technical variation. Evaluating the model is also complex, given the frequent absence of definitive biological ground truths and the variation in data quality (detailed in Supplementary Note 10).

### 19. **Future directions**: Expand pretraining on larger, diverse datasets with multi-omic, spatial omics, and diseased conditions; explore causal relationships and in-context instruction learning.

- 1차 검사: **supported**
- 근거로 든 문장: we plan to pretrain on a larger-scale dataset with more diversity, including multi-omic data, spatial omics and various diseased conditions

- 판정:
- 메모:

**P0038** (paragraph, Discussion)

> For future directions, we plan to pretrain on a larger-scale dataset with more diversity, including multi-omic data, spatial omics and various diseased conditions. It is also interesting to incorporate perturbation and temporal data in the pretraining stage, enabling the model to learn causal relationships and infer how genes and cells respond to changes over time. We also aim to explore in-context instruction learning for single-cell data. This involves developing techniques that allow the pretrained model to understand and adapt to different tasks and contexts in a zero-shot setting without the need for fine-tuning. By enabling scGPT to grasp the nuances and specific requirements of different analyses, we can enhance its usability and applicability in a wide range of research scenarios. We envision that the pretraining paradigm will be readily integrated into single-cell research and serve as a foundation to leverage existing knowledge from the exponentially growing cell atlases for new discoveries.

