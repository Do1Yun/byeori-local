# 검토표: bai-2026-sclong-a-billion-parameter-foundation-model

- 논문: scLong: a billion-parameter foundation model for capturing long-range gene context in single-cell transcriptomics
- 학술지·연도: Nature Communications 2026  (출처 openalex, DOI 10.1038/s41467-026-69102-y)
- 노트 revision: `97df6a5e3f524de9ac59d89f77f3fab3`  sha256 `3628129574022f3c`
- 추출: partial, 블록 90개, 생성 경로 chunked, 제시 90/90
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

### 1. **Dual Encoder Architecture**: scLong uses a gene encoder (GO-based GCN) and a contextual encoder (self-attention with Performer encoders) to process high- and low-expression genes separately.

- 1차 검사: **supported**
- 근거로 든 문장: scLong includes a gene encoder, an expression encoder, and a contextual encoder.

- 판정: 
- 메모: 

**P0005** (paragraph, scLong overview)

> scLong takes a cell's gene expression vector as input, generating a representation for each element in the vector (Fig. 1a). Each element corresponds to a specific gene, with its value indicating the level of gene transcription into RNA at a given moment, which may reflect potential protein production. scLong includes a gene encoder, an expression encoder, and a contextual encoder. The expression encoder, a multi-layer perceptron (MLP), produces a representation vector for each scalar expression value. The gene encoder leverages GO 22 to extract a representation vector for each gene. For each element in the expression vector-defined by a gene ID and its expression value-we combine the gene's representation (from the gene encoder) with its expression representation (from the expression encoder) to represent the element. These element representations are then fed into the contextual encoder, which learns contextualized representations that capture relationships among elements (Methods).

### 2. **GO Integration**: Gene Ontology domains (Biological Process, Molecular Function, Cellular Component) are embedded into gene representations via a GCN, enriching functional understanding.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: Gene Ontology domains (Biological Process, Molecular Function, Cellular Component) are embedded into gene representations via a GCN

- 판정: 
- 메모: 

**P0006** (paragraph, scLong overview)

> The gene encoder constructs a gene graph using the GO and applies a GCN 14,23 to this graph to learn gene representations. The GO 22 offers a structured vocabulary for describing gene functions, organized into three primary domains: Biological Process, which refers to the biological roles or processes in which a gene is involved, such as cell division or metabolic pathways; Molecular Function, which specifies the biochemical activities of a gene product, such as enzyme activity or binding; and Cellular Component, indicating the cellular locations where a gene product operates, such as the nucleus or mitochondria. Each gene's functions are annotated with GO terms from this vocabulary. The gene graph is constructed based on the method in ref. 14, where each node represents a gene. For each pair of genes, u and v, the Jaccard index is calculated to measure the overlap between their sets of annotated GO terms. If the overlap is sufficiently high, an edge is added between the two genes in the graph. The gene graph captures functional relationships between genes based on shared GO annotations. Genes with overlapping GO terms are connected, reflecting similarities in biological processes, molecular functions, and cellular localization. For example, genes involved in related biological processes, such as metabolic pathways, are linked, suggesting shared roles in complex cellular functions. Genes with similar molecular functions, like enzymatic activities or binding properties, are also connected, indicating biochemical similarities or cooperative interactions. Additionally, genes localized to the same cellular components, such as the nucleus or mitochondria, are linked, suggesting potential spatial co-localization. On top of the gene graph, we construct a GCN 24 , which learns representations for each gene. Through a process called message passing, the GCN enables each node to aggregate information from its neighboring nodes, effectively capturing the relationships between genes.

### 3. **Low-Expression Gene (LEG) Handling**: LEGs are critical for regulatory mechanisms and are explicitly modeled, improving GRN inference and batch integration.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: LEGs play essential roles in a range of biological processes and cannot be disregarded

- 판정: 
- 메모: 

**P0008** (paragraph, scLong overview)

> While low-expression genes (LEGs) are less prominent in terms of overall abundance, they play essential roles in a range of biological processes and cannot be disregarded. Many LEGs are involved in regulatory mechanisms that influence the behavior of high-expression genes, acting as switches or modulators in complex cellular networks 17 . These genes can also be crucial in rare or specialized cell types, where their subtle expression may drive specific phenotypes or responses to environmental stimuli 18,19 . Ignoring them could lead to incomplete models that overlook important aspects of cellular function. Moreover, LEGs often participate in context-specific pathways that become active only under certain conditions, such as stress responses, immune signaling, or disease progression 18,19 . These genes may also be important for rare cell populations, whose contributions to tissue function or disease states could be missed if low-expression signals are not adequately represented 20,21 . Thus, while high-expression genes often drive primary biological processes, LEGs provide the fine-tuned regulation and specialized functions necessary for a complete understanding of cellular behavior.

### 4. **Pretraining on 48M Cells**: scLong is pretrained on 48 million cells and 27,874 genes, enabling generalizable gene expression patterns across diverse conditions.

- 1차 검사: **supported**
- 근거로 든 문장: scLong, a scRNA-seq foundation model with one billion parameters pretrained on 48 million cells, captures long-range context across 27,874 genes

- 판정: 
- 메모: 

**P0010** (paragraph, scLong overview)

> To pretrain scLong, we compiled a large-scale scRNA-seq dataset comprising ~48 million human cells from diverse tissues and cell types Fig. 1 | scLong, a scRNA-seq foundation model with one billion parameters pretrained on 48 million cells, captures long-range context across 27,874 genes by employing a dual encoder architecture and leveraging Gene Ontology knowledge. a Model architecture of scLong. scLong generates a representation for each element in a cell's gene expression vector using three main components: a gene encoder, an expression encoder, and a contextual encoder. The expression encoder, a multi-layer perceptron (MLP), produces a representation vector for each scalar expression value, while the gene encoder utilizes Gene Ontology to derive a representation vector for each gene. These representations are combined for each element and fed into the contextual encoder, which learns context-aware representations that capture inter-element relationships. Specifically, the gene encoder constructs a gene graph from Gene Ontology and applies a graph convolutional network (GCN) to learn gene-specific representations. To capture long-range relationships between genes, the contextual encoder leverages self-attention. To optimize efficiency and representation quality, scLong employs two Performers of different sizes, with high-expression elements processed by a larger Performer for detailed interaction modeling, and low-expression elements by a smaller Performer for efficiency. The outputs from these two encoders are then passed through a final full-length Performer, generating the final scLong representations. b scLong is pretrained by reconstructing masked expression values. For each input cell, we randomly mask a subset of expression values and use scLong to learn representations for both the masked and unmasked elements. The representations of the masked elements are passed to an MLP-based decoder to predict their expression values. A reconstruction loss is calculated between the predicted and actual values, and pretraining involves minimizing this reconstruction loss. c The pretraining data for scLong includes 48 million cells and 27,874 genes (~20,000 protein-coding and 8000 non-coding genes) derived from 1,618 scRNA-seq datasets spanning over 50 tissues.

### 5. **Superior Performance**: Outperforms Geneformer, scGPT, scFoundation, UCE, and task-specific models in perturbation prediction (Pearson 0.625–0.878), drug response (AUC 0.652–0.878), and GRN inference (AUPR 1.35).

- 1차 검사: **flagged** — cited elsewhere: 0.652 as 0.652  (모델: supported)
- 근거로 든 문장: scLong outperformed all baselines (Fig. 4b), with a Pearson correlation score of 0.878, surpassing Geneformer's score of 0.852 (P = 0.001), scGPT's 0.841 (P = 0.001), scFoundation's 0.867 (P = 0.025), UCE's 0.837 (P = 0.001), DeepCDR's 0.837 (P = 0.001), and the linear model's 0.746 (P < 0.001) (Supplementary Table 3).

- 판정: 
- 메모: 

**P0014** (paragraph, scLong predicts transcriptional outcomes of genetic perturbations)

> scLong outperformed the seven baseline methods in most cases, across both Pearson correlation and MSE metrics, and under various test scenarios, including Seen 0/2, Seen 1/2, Seen 2/2, and Seen 0/1 (Fig. 2b and Supplementary Table 1; since the errors of ALM and No-Change are considerably larger than those of other baselines, we excluded them from Fig. 2 and instead provided their results in Supplementary Table 1). The improvement of scLong was particularly notable in the Seen 0/1 and Seen 0/2 scenarios, where the perturbation conditions in the test data are not encountered during training. For example, in the Seen 0/1 scenario, scLong achieved a Pearson correlation of 0.625, compared to 0.561 (P = 0.001, two-sided t-test after the Benjamini-Hochberg procedure of multiple hypothesis correction 29 ; the detailed results of the two-sided t-test, with sample size = 5 and most effect sizes >1, are provided in Supplementary Table 11), 0.576 (P = 0.002), 0.577 (P = 0.002), 0.581 (P = 0.002), 0.530 (P < 0.001), 0.509 (P < 0.001), and -0.012 (P < 0.001) for GEARS, Geneformer, scGPT, scFoundation, UCE, ALM, and No-Change, respectively. In the Seen 0/2 scenario, scLong obtained an MSE of 0.170, while the baseline models recorded errors of 0.218 (P = 0.001), 0.185 (P = 0.107), 0.199 (P = 0.005), 0.190 (P = 0.005), 0.276 (P < 0.001), 0.346 (P < 0.001), and 0.503 (P < 0.001), respectively. This demonstrates that scLong has a stronger out-of-domain generalization capability compared to the baseline models.

**P0021** (paragraph, scLong predicts cancer drug response)

> In this task, the input includes the molecular structure of a potential cancer drug and the bulk gene expression profile of a cancer cell line. The output is a prediction of the drug's efficacy against the cancer cell line, measured by its half-maximal inhibitory concentration (IC50) value 34 . We use scLong to extract a representation vector from the input gene expression data, which is then concatenated with the drug molecule representation obtained through a GCN 35 (Fig. 4a). The combined representation is subsequently fed into a regression module to predict the IC50 value (Methods). We used the dataset from DeepCDR 36 , which includes 102,074 training examples and 5,372 testing examples. We compared scLong with other foundation models, including Geneformer, scGPT, scFoundation, and UCE. Additionally, we evaluated its performance against task-specific models, including the deep neural network DeepCDR and a linear model 36,37 . Pearson correlation was used as the evaluation metric, where higher values indicate better performance. scLong outperformed all baselines (Fig. 4b), with a Pearson correlation score of 0.878, surpassing Geneformer's score of 0.852 (P = 0.001), scGPT's 0.841 (P = 0.001), scFoundation's 0.867 (P = 0.025), UCE's 0.837 (P = 0.001), DeepCDR's 0.837 (P = 0.001), and the linear model's 0.746 (P < 0.001) (Supplementary Table 3).

**P0026** (paragraph, scLong infers gene regulatory networks)

> We compared scLong's performance with Geneformer, scGPT, scFoundation, UCE, and task-specific methods including DeepSEM and GENIE3 48 . Additionally, we included a simple baseline, GO Graph, which directly utilizes the corresponding subgraph of the gene graph (Fig. 1a) derived from the GO as the GRN for the 17,735 genes. scLong outperformed all baselines across both metrics (Fig. 5b and Supplementary Table 5). For instance, scLong achieved an AUPR of 1.35, significantly surpassing Geneformer (1.12, P < 0.001), scGPT (1.17, P < 0.001), scFoundation (1.04, P < 0.001), UCE (1.10, P = 0.001), DeepSEM (1.11, P < 0.001), GENIE3 (1.08, P < 0.001), and GO Graph (1.02, P < 0.001) (Supplementary Table 5). These results indicate that scLong's learned representations effectively capture gene interactions. A two-sided t-test (Supplementary Table 14) confirmed the significance of these improvements (P < 0.04 for both AUPR and EPR comparisons after multiple hypothesis correction), with sample sizes of 5 and most effect sizes exceeding 2.

## 3. Methodology and Architecture

### 6. **Dual Encoder Strategy**: High-expression genes (top 4096) use a larger Performer encoder (42 layers, 32 heads, hidden dim 1280), while low-expression genes use a smaller encoder (2 layers, 8 heads, hidden dim 200).

- 1차 검사: **flagged** — 1280 is nowhere in the paper  (모델: supported)
- 근거로 든 문장: First, we rank the elements in the gene expression vector in descending order of expression values and select the top 4096 with the highest values for processing by the large Performer encoder.

- 판정: 
- 메모: 

**P0056** (paragraph, scLong model architecture)

> Given the extracted representation vectors for each element in the input gene expression vector, we feed them into self-attention layers 13 to learn enhanced representations of these elements. Selfattention computes pairwise correlations between elements, capturing the relationships among them. To balance computational efficiency with representation effectiveness, we employ a large Performer 25 encoder and a mini Performer encoder to process elements with varying expression magnitudes. First, we rank the elements in the gene expression vector in descending order of expression values and select the top 4096 with the highest values for processing by the large Performer encoder. This encoder applies self-attention across all 4096 high-expression elements, comprising 42 Performer layers with 32 attention heads and a hidden dimension of 1,280, and produces 200-dimensional output vectors. The remaining K -4, 096 elements, where K = 27, 874 represents the total number of genes, are processed by a mini Performer encoder tailored for lower expression values. This encoder performs self-attention across all K -4, 096 elements. This mini encoder has 2 layers, 8 attention heads, and a hidden dimension of 200, yielding 200-dimensional output representations as well. After processing by these encoders, each element in the input expression vector has a 200-dimensional representation, derived from either the large or mini encoder. These representations are then fed into a fulllength Performer encoder, which performs self-attention across all 27,874 elements. This final encoder has 2 layers, 8 attention heads, and a hidden dimension of 200. The resulting representations from the full-length encoder serve as the final outputs of scLong and are utilized for a range of downstream tasks.

### 7. **Gene Graph Construction**: GO terms are used to build a gene graph with edges based on Jaccard index of shared annotations, selecting top 20 genes per node.

- 1차 검사: **supported**
- 근거로 든 문장: for each gene u, we select the top 20 genes v i with the highest J u, v i values and connect them to u.

- 판정: 
- 메모: 

**P0053** (paragraph, scLong model architecture)

> between the two sets of GO terms, which quantifies the fraction of shared GO terms and indicates the functional similarity of each gene pair. Using this similarity measure, we construct a graph where each gene is represented as a node, and edges are assigned between gene pairs with high Jaccard index values. Specifically, for each gene u, we select the top 20 genes v i with the highest J u, v i values and connect them to u.

### 8. **Pretraining**: Masked expression reconstruction with an MLP decoder minimizes reconstruction loss, using 15% masked non-zero values per gene vector.

- 1차 검사: **supported**
- 근거로 든 문장: 15% of the non-zero values in each input gene expression vector were randomly masked

- 판정: 
- 메모: 

**P0057** (paragraph, scLong pretraining)

> scLong was pretrained using a masked value reconstruction task. In this approach, 15% of the non-zero values in each input gene expression vector were randomly masked, and the model was trained to predict the masked values based on the unmasked portions of the vector. The 15% masking ratio followed that used in BERT 12 . Let M x represent the set of indices corresponding to masked gene expressions in an input gene expression vector x. We create a masked expression vector x 0 by assigning a special symbol [MASK] to each masked gene while leaving unmasked values intact:

**P0058** (paragraph, scLong pretraining)

> We then obtain a representation vector for each element in x 0 . For unmasked expression values x i , we apply an MLP to generate their representation vectors as previously described. For each [MASK] symbol, we use a learnable representation vector specific to [MASK]. These representation vectors for elements in x 0 are subsequently fed into the remaining layers of scLong to compute a final representation for each element. Finally, the representation vector corresponding to each masked gene is processed through a gene-specific MLP, producing a scalar representing the reconstructed value for that gene's masked expression. Let b x i and x i represent the reconstructed value and the ground truth (pre-masking) value of a masked gene i, respectively. The reconstruction loss is measured as the MSE between b x i and x i . Pretraining is performed by minimizing the reconstruction loss across the dataset. Let D denote the entire pretraining dataset. The overall pretraining loss is defined as:

### 9. **Task-Specific Adaptation**: For perturbation prediction, scLong combines gene representations with GEARS perturbation conditions via a decoder, using a 3-layer MLP for post-perturbation prediction.

- 1차 검사: **supported**
- 근거로 든 문장: Each vector is subsequently passed through a three-layer MLP with hidden dimensions of 200, 400, and 200

- 판정: 
- 메모: 

**P0061** (paragraph, Prediction of transcriptional responses to genetic perturbations)

> Supplementary Fig. 4 illustrates the model architecture used for this downstream task. The input includes a gene expression vector of a cell prior to perturbation and the associated perturbation condition. The output is the gene expression vector of the cell following perturbation. We use the pretrained scLong model to derive a representation vector for each element of the pre-perturbation expression vector, while the GEARS method generates a representation for the perturbation condition. These vectors are then combined and processed through the GEARS decoder to predict the post-perturbation gene expression vector. Specifically, GEARS generates a 200-dimensional representation vector for each single-gene perturbation. For a doublegene perturbation, its representation is obtained by summing the vectors of the two individual single-gene perturbations it comprises. The representation vector for the perturbation condition is added to the representation vector of each element in the gene expression vector extracted by scLong. A ReLU activation is then applied to each dimension of the resulting vectors. Each vector is subsequently passed through a three-layer MLP with hidden dimensions of 200, 400, and 200, followed by a batch normalization 77 layer, producing a 200dimensional post-perturbation representation for each expression element. Finally, each post-perturbation representation vector is processed by a decoder to generate post-perturbation values. The decoder begins with a one-layer MLP, which takes a post-perturbation representation as input and outputs an initial predicted postperturbation value. Simultaneously, the decoder concatenates the post-perturbation representations of all expression elements, passing this combined vector through a two-layer MLP (with hidden dimensions of 5045 and 200) to produce a 200-dimensional vector. This vector is then concatenated with the initial predicted postperturbation value of each element and fed into another MLP, which outputs an additional scalar prediction for each element. This scalar is then added to the corresponding pre-perturbation expression value to yield the final predicted post-perturbation value.

### 10. **Drug Response Prediction**: Gene and drug representations (via GCN) are concatenated with cell line and dosage embeddings in a multi-head cross-attention module.

- 1차 검사: **supported**
- 근거로 든 문장: These representations are passed through a multi-head cross-attention module 13 , combined with embeddings of cell line indices and dosage information

- 판정: 
- 메모: 

**P0019** (paragraph, scLong predicts transcriptional outcomes of chemical perturbations)

> In this task, we used a subset of the L1000 dataset 31 , which contains 7 distinct cell lines, 978 genes, and 810 drug compounds, with drugs tested at 6 different dosage levels. The prediction model takes two inputs: (1) the index of the perturbed cell line and (2) the molecular graph and dosage of the drug used to perturb it. The output is the gene expression profile of the cell line after perturbation. The dataset does not include pre-perturbation gene expression data. Each data sample in L1000 consists of these inputs and outputs, totaling 5005 examples, with 3965 used for training, 544 for validation, and 496 for testing. We used scLong to extract representation vectors for each gene and a GCN to extract representations from the drug molecule graph (Fig. 3a). These representations are passed through a multi-head cross-attention module 13 , combined with embeddings of cell line indices and dosage information, and then fed into an MLP to predict post-perturbation gene expression (Methods). We compared scLong with four foundation models, Geneformer, scGPT, scFoundation, and UCE, as well as the task-specific model DeepCE 32 . Evaluation metrics included root mean square error (RMSE), Spearman and Pearson correlation scores, and top-100 precision for the highest (Pos-P@100) and lowest (Neg-P@100) predicted expression values (Methods). For RMSE, lower values indicate better performance, while higher values are better for the other metrics. scLong significantly outperformed all baseline methods across all evaluation metrics (Fig. 3b) (all P < 0.04, two-sided t-test with sample sizes of 5 and effect sizes greater than 2; see Supplementary Table 12).

## 4. Key Results and Benchmarks

### 11. **Perturbation Prediction**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 12. **Seen 0/1**: Pearson 0.625 (vs. GEARS 0.561, P=0.001).

- 1차 검사: **supported**
- 근거로 든 문장: scLong achieved a Pearson correlation of 0.625, compared to 0.561 (P = 0.001

- 판정: 
- 메모: 

**P0014** (paragraph, scLong predicts transcriptional outcomes of genetic perturbations)

> scLong outperformed the seven baseline methods in most cases, across both Pearson correlation and MSE metrics, and under various test scenarios, including Seen 0/2, Seen 1/2, Seen 2/2, and Seen 0/1 (Fig. 2b and Supplementary Table 1; since the errors of ALM and No-Change are considerably larger than those of other baselines, we excluded them from Fig. 2 and instead provided their results in Supplementary Table 1). The improvement of scLong was particularly notable in the Seen 0/1 and Seen 0/2 scenarios, where the perturbation conditions in the test data are not encountered during training. For example, in the Seen 0/1 scenario, scLong achieved a Pearson correlation of 0.625, compared to 0.561 (P = 0.001, two-sided t-test after the Benjamini-Hochberg procedure of multiple hypothesis correction 29 ; the detailed results of the two-sided t-test, with sample size = 5 and most effect sizes >1, are provided in Supplementary Table 11), 0.576 (P = 0.002), 0.577 (P = 0.002), 0.581 (P = 0.002), 0.530 (P < 0.001), 0.509 (P < 0.001), and -0.012 (P < 0.001) for GEARS, Geneformer, scGPT, scFoundation, UCE, ALM, and No-Change, respectively. In the Seen 0/2 scenario, scLong obtained an MSE of 0.170, while the baseline models recorded errors of 0.218 (P = 0.001), 0.185 (P = 0.107), 0.199 (P = 0.005), 0.190 (P = 0.005), 0.276 (P < 0.001), 0.346 (P < 0.001), and 0.503 (P < 0.001), respectively. This demonstrates that scLong has a stronger out-of-domain generalization capability compared to the baseline models.

### 13. **Seen 0/2**: MSE 0.170 (vs. GEARS 0.218, P=0.001).

- 1차 검사: **supported**
- 근거로 든 문장: In the Seen 0/2 scenario, scLong obtained an MSE of 0.170, while the baseline models recorded errors of 0.218 (P = 0.001)

- 판정: 
- 메모: 

**P0014** (paragraph, scLong predicts transcriptional outcomes of genetic perturbations)

> scLong outperformed the seven baseline methods in most cases, across both Pearson correlation and MSE metrics, and under various test scenarios, including Seen 0/2, Seen 1/2, Seen 2/2, and Seen 0/1 (Fig. 2b and Supplementary Table 1; since the errors of ALM and No-Change are considerably larger than those of other baselines, we excluded them from Fig. 2 and instead provided their results in Supplementary Table 1). The improvement of scLong was particularly notable in the Seen 0/1 and Seen 0/2 scenarios, where the perturbation conditions in the test data are not encountered during training. For example, in the Seen 0/1 scenario, scLong achieved a Pearson correlation of 0.625, compared to 0.561 (P = 0.001, two-sided t-test after the Benjamini-Hochberg procedure of multiple hypothesis correction 29 ; the detailed results of the two-sided t-test, with sample size = 5 and most effect sizes >1, are provided in Supplementary Table 11), 0.576 (P = 0.002), 0.577 (P = 0.002), 0.581 (P = 0.002), 0.530 (P < 0.001), 0.509 (P < 0.001), and -0.012 (P < 0.001) for GEARS, Geneformer, scGPT, scFoundation, UCE, ALM, and No-Change, respectively. In the Seen 0/2 scenario, scLong obtained an MSE of 0.170, while the baseline models recorded errors of 0.218 (P = 0.001), 0.185 (P = 0.107), 0.199 (P = 0.005), 0.190 (P = 0.005), 0.276 (P < 0.001), 0.346 (P < 0.001), and 0.503 (P < 0.001), respectively. This demonstrates that scLong has a stronger out-of-domain generalization capability compared to the baseline models.

### 14. **Drug Pair Responses**: AUROC 0.652 (vs. Geneformer 0.635, P=0.006).

- 1차 검사: **supported**
- 근거로 든 문장: with an AUROC score of 0.652, surpassing Geneformer's score of 0.635 (P = 0.006)

- 판정: 
- 메모: 

**P0023** (paragraph, scLong predicts cancer drug response)

> including DeepDDS 41 and random forest 37,41 . scLong outperformed all baselines in terms of the area under the receiver operating characteristic curve (AUROC) (Fig. 4c), with an AUROC score of 0.652, surpassing Geneformer's score of 0.635 (P = 0.006), scGPT's 0.616 (P = 0.002), scFoundation's 0.593 (P < 0.001), UCE's 0.603 (P = 0.002), DeepDDS's 0.604 (P = 0.001), and random forest's 0.533 (P < 0.001) (Supplementary Table 4). The results of the two-sided t-test after multiple hypothesis correction for both single-drug response prediction and drug-combination response prediction are presented in Supplementary Table 13, with a sample size of 5 for each test and an effect size greater than 2.

### 15. **Drug Response Prediction**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 16. Pearson 0.878 (vs. Geneformer 0.852, P=0.001) on DeepCDR dataset.

- 1차 검사: **supported**
- 근거로 든 문장: scLong outperformed all baselines (Fig. 4b), with a Pearson correlation score of 0.878, surpassing Geneformer's score of 0.852 (P = 0.001)

- 판정: 
- 메모: 

**P0021** (paragraph, scLong predicts cancer drug response)

> In this task, the input includes the molecular structure of a potential cancer drug and the bulk gene expression profile of a cancer cell line. The output is a prediction of the drug's efficacy against the cancer cell line, measured by its half-maximal inhibitory concentration (IC50) value 34 . We use scLong to extract a representation vector from the input gene expression data, which is then concatenated with the drug molecule representation obtained through a GCN 35 (Fig. 4a). The combined representation is subsequently fed into a regression module to predict the IC50 value (Methods). We used the dataset from DeepCDR 36 , which includes 102,074 training examples and 5,372 testing examples. We compared scLong with other foundation models, including Geneformer, scGPT, scFoundation, and UCE. Additionally, we evaluated its performance against task-specific models, including the deep neural network DeepCDR and a linear model 36,37 . Pearson correlation was used as the evaluation metric, where higher values indicate better performance. scLong outperformed all baselines (Fig. 4b), with a Pearson correlation score of 0.878, surpassing Geneformer's score of 0.852 (P = 0.001), scGPT's 0.841 (P = 0.001), scFoundation's 0.867 (P = 0.025), UCE's 0.837 (P = 0.001), DeepCDR's 0.837 (P = 0.001), and the linear model's 0.746 (P < 0.001) (Supplementary Table 3).

### 17. **GRN Inference**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 18. AUPR 1.35 (vs. Geneformer 1.12, P<0.001) using cosine similarity between gene representations.

- 1차 검사: **supported**
- 근거로 든 문장: scLong achieved an AUPR of 1.35, significantly surpassing Geneformer (1.12, P < 0.001)

- 판정: 
- 메모: 

**P0026** (paragraph, scLong infers gene regulatory networks)

> We compared scLong's performance with Geneformer, scGPT, scFoundation, UCE, and task-specific methods including DeepSEM and GENIE3 48 . Additionally, we included a simple baseline, GO Graph, which directly utilizes the corresponding subgraph of the gene graph (Fig. 1a) derived from the GO as the GRN for the 17,735 genes. scLong outperformed all baselines across both metrics (Fig. 5b and Supplementary Table 5). For instance, scLong achieved an AUPR of 1.35, significantly surpassing Geneformer (1.12, P < 0.001), scGPT (1.17, P < 0.001), scFoundation (1.04, P < 0.001), UCE (1.10, P = 0.001), DeepSEM (1.11, P < 0.001), GENIE3 (1.08, P < 0.001), and GO Graph (1.02, P < 0.001) (Supplementary Table 5). These results indicate that scLong's learned representations effectively capture gene interactions. A two-sided t-test (Supplementary Table 14) confirmed the significance of these improvements (P < 0.04 for both AUPR and EPR comparisons after multiple hypothesis correction), with sample sizes of 5 and most effect sizes exceeding 2.

### 19. **Batch Integration**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 20. Batch ASW 0.96 (vs. UCE 0.83, P<0.001) on pancreas dataset.

- 1차 검사: **flagged** — cited elsewhere: 0.001 as 0.001; the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: scLong achieved a batch ASW score of 0.96, markedly surpassing all baselines (Fig. 6), including UCE (0.83)

- 판정: 
- 메모: 

**P0030** (paragraph, scLong supports zero-shot batch integration)

> scLong achieved a batch ASW score of 0.96, markedly surpassing all baselines (Fig. 6), including Raw (0.70), HVG (0.89), scVI (0.85), Geneformer (0.62), scGPT (0.89), scFoundation (0.71), and UCE (0.83). These results indicate that the representations learned by scLong effectively mitigate batch effects. Notably, despite not being pretrained or fine-tuned on the pancreas dataset, scLong outperformed scVI, which was trained on this dataset, highlighting its strong zeroshot capability.

## 5. Limitations and Future Work

### 21. **Limitations**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 22. High parameter count (1 billion) requires significant computational resources.

- 1차 검사: **supported**
- 근거로 든 문장: The model's billion-parameter architecture, although optimized for efficiency, still demands significant computational resources for training and inference

- 판정: 
- 메모: 

**P0044** (paragraph, Discussion)

> Despite its advancements, scLong has certain limitations that merit consideration. The model's billion-parameter architecture, although optimized for efficiency, still demands significant computational resources for training and inference, which may hinder accessibility for groups lacking high-performance infrastructure. Additionally, scLong relies on static, predefined relationships from sources like the GO, which, while providing valuable contextual information, may restrict adaptability to dynamic gene interactions and condition-specific regulatory changes not represented in these databases. Another limitation is the potential sensitivity of scLong's performance to the choice of high-and low-expression gene thresholds in its dual encoder design; selecting these thresholds inappropriately could lead to suboptimal representations, particularly in cell types with unusual gene expression distributions. Addressing these limitations could make scLong a more versatile and broadly applicable tool in single-cell transcriptomics research.

### 23. Reliance on static GO data may limit adaptability to new biological knowledge.

- 1차 검사: **supported**
- 근거로 든 문장: scLong relies on static, predefined relationships from sources like the GO, which, while providing valuable contextual information, may restrict adaptability to dynamic gene interactions and condition-specific regulatory changes not represented in these databases.

- 판정: 
- 메모: 

**P0044** (paragraph, Discussion)

> Despite its advancements, scLong has certain limitations that merit consideration. The model's billion-parameter architecture, although optimized for efficiency, still demands significant computational resources for training and inference, which may hinder accessibility for groups lacking high-performance infrastructure. Additionally, scLong relies on static, predefined relationships from sources like the GO, which, while providing valuable contextual information, may restrict adaptability to dynamic gene interactions and condition-specific regulatory changes not represented in these databases. Another limitation is the potential sensitivity of scLong's performance to the choice of high-and low-expression gene thresholds in its dual encoder design; selecting these thresholds inappropriately could lead to suboptimal representations, particularly in cell types with unusual gene expression distributions. Addressing these limitations could make scLong a more versatile and broadly applicable tool in single-cell transcriptomics research.

### 24. Sensitivity to thresholds for distinguishing high/low-expression genes.

- 1차 검사: **supported**
- 근거로 든 문장: Another limitation is the potential sensitivity of scLong's performance to the choice of high-and low-expression gene thresholds in its dual encoder design

- 판정: 
- 메모: 

**P0044** (paragraph, Discussion)

> Despite its advancements, scLong has certain limitations that merit consideration. The model's billion-parameter architecture, although optimized for efficiency, still demands significant computational resources for training and inference, which may hinder accessibility for groups lacking high-performance infrastructure. Additionally, scLong relies on static, predefined relationships from sources like the GO, which, while providing valuable contextual information, may restrict adaptability to dynamic gene interactions and condition-specific regulatory changes not represented in these databases. Another limitation is the potential sensitivity of scLong's performance to the choice of high-and low-expression gene thresholds in its dual encoder design; selecting these thresholds inappropriately could lead to suboptimal representations, particularly in cell types with unusual gene expression distributions. Addressing these limitations could make scLong a more versatile and broadly applicable tool in single-cell transcriptomics research.

### 25. **Future Work**:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 
- 메모: 

> 인용 없음

### 26. Integrate pathway databases, protein interactions, and epigenetic data.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: incorporate of additional biological datasets, such as pathway databases 58 , protein-protein interaction networks 59 , and epigenetic data 60

- 판정: 
- 메모: 

**P0045** (paragraph, Discussion)

> Future work on scLong can focus on several key areas to further enhance its capabilities and broaden its applications. One promising direction is the incorporation of additional biological datasets, such as pathway databases 58 , protein-protein interaction networks 59 , and epigenetic data 60 , to enrich the context-awareness of the model and improve its ability to capture more complex regulatory mechanisms. Expanding the model's pretraining on diverse datasets from various species and tissues could also boost its generalizability across different biological contexts. Another area for improvement is model interpretability; future versions of scLong could integrate more advanced explainability techniques, such as attention-based visualization tools or saliency maps 61 , to provide clearer insights into the gene interactions driving its predictions. Additionally, exploring methods to reduce the computational demands of training and deploying scLong, such as model pruning 62 or distillation 63 , would make the model more accessible to a wider range of researchers. Furthermore, applying scLong to novel downstream tasks, such as predicting cell signaling pathways 5 or identifying gene interactions in rare cell populations, could further validate its versatility and expand its impact in single-cell biology.

### 27. Improve interpretability with attention visualization tools.

- 1차 검사: **supported**
- 근거로 든 문장: integrate more advanced explainability techniques, such as attention-based visualization tools or saliency maps 61

- 판정: 
- 메모: 

**P0045** (paragraph, Discussion)

> Future work on scLong can focus on several key areas to further enhance its capabilities and broaden its applications. One promising direction is the incorporation of additional biological datasets, such as pathway databases 58 , protein-protein interaction networks 59 , and epigenetic data 60 , to enrich the context-awareness of the model and improve its ability to capture more complex regulatory mechanisms. Expanding the model's pretraining on diverse datasets from various species and tissues could also boost its generalizability across different biological contexts. Another area for improvement is model interpretability; future versions of scLong could integrate more advanced explainability techniques, such as attention-based visualization tools or saliency maps 61 , to provide clearer insights into the gene interactions driving its predictions. Additionally, exploring methods to reduce the computational demands of training and deploying scLong, such as model pruning 62 or distillation 63 , would make the model more accessible to a wider range of researchers. Furthermore, applying scLong to novel downstream tasks, such as predicting cell signaling pathways 5 or identifying gene interactions in rare cell populations, could further validate its versatility and expand its impact in single-cell biology.

### 28. Reduce computational demands via pruning or distillation.

- 1차 검사: **supported**
- 근거로 든 문장: exploring methods to reduce the computational demands of training and deploying scLong, such as model pruning 62 or distillation 63

- 판정: 
- 메모: 

**P0045** (paragraph, Discussion)

> Future work on scLong can focus on several key areas to further enhance its capabilities and broaden its applications. One promising direction is the incorporation of additional biological datasets, such as pathway databases 58 , protein-protein interaction networks 59 , and epigenetic data 60 , to enrich the context-awareness of the model and improve its ability to capture more complex regulatory mechanisms. Expanding the model's pretraining on diverse datasets from various species and tissues could also boost its generalizability across different biological contexts. Another area for improvement is model interpretability; future versions of scLong could integrate more advanced explainability techniques, such as attention-based visualization tools or saliency maps 61 , to provide clearer insights into the gene interactions driving its predictions. Additionally, exploring methods to reduce the computational demands of training and deploying scLong, such as model pruning 62 or distillation 63 , would make the model more accessible to a wider range of researchers. Furthermore, applying scLong to novel downstream tasks, such as predicting cell signaling pathways 5 or identifying gene interactions in rare cell populations, could further validate its versatility and expand its impact in single-cell biology.

