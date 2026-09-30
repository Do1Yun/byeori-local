# 검토표: blampe-2025-novae-a-graph-based-foundation-model

- 논문: Novae: a graph-based foundation model for spatial transcriptomics data
- 학술지·연도: Nature Methods 2025  (출처 openalex, DOI 10.1038/s41592-025-02899-6)
- 노트 revision: `fbab36d6769b4b34857f59c95b93d543`  sha256 `d4cbff78bb064109`
- 추출: partial, 블록 77개, 생성 경로 single, 제시 77/77
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

### 1. **Zero-shot domain inference**: Novae learns spatial domains without retraining, enabling cross-slide and cross-technology analysis.

- 1차 검사: **supported**
- 근거로 든 문장: allowing Novae to perform zero-shot domain inference across multiple gene panels, tissues and technologies

- 판정:
- 메모:

**P0001** (paragraph, Body)

> Spatial transcriptomics is advancing molecular biology by providing high-resolution insights into gene expression within the spatial context of tissues. This context is essential for identifying spatial domains, enabling the understanding of microenvironment organizations and their implications for tissue function and disease progression. To improve current model limitations on multiple slides, we have designed Novae (https://github. com/MICS-Lab/novae), a graph-based foundation model that extracts representations of cells within their spatial contexts. Our model was trained on a large dataset of nearly 30 million cells across 18 tissues, allowing Novae to perform zero-shot domain inference across multiple gene panels, tissues and technologies. Unlike other models, it also natively corrects batch effects and constructs a nested hierarchy of spatial domains. Furthermore, Novae supports various downstream tasks, including spatially variable gene or pathway analysis and spatial domain trajectory analysis. Overall, Novae provides a robust and versatile tool for advancing spatial transcriptomics and its applications in biomedical research.

**P0005** (paragraph, A foundation model for spatial transcriptomics)

> Novae is a graph-based foundation model 18,19 that we trained on a large single-cell spatial transcriptomics dataset composed of about 30 million cells. This model, aware of 18 different tissues, is hosted on a public hub and can be reused by the user for multiple downstream tasks on any technology or gene panel, as illustrated in Fig. 1a. The main application of Novae is to learn spatial domains, which can be performed with the shared model without any retraining (called zero-shot inference 17 ). If desired, the user can also retrain Novae to obtain refined results (fine-tuning). Two distinguishing properties of Novae are that (1) it provides a nested organization of spatial domains for different resolutions and (2) it natively corrects batch effect across slides. This consistent domain assignment across slides enables comparison analyses of a study containing multiple slides. Additionally, Novae can perform multiple downstream analysis tasks, such as (1) spatial pathway analysis; external tools need to be re-run for each new analysis or when adjusting spatial domain resolutions (choosing different number of spatial domains). Additionally, owing to their reliance on specific gene sets, these methods often necessitate training on the intersection of gene sets, which can significantly reduce the number of available genes and, consequently, impact performance. Notably, even when applied to slides with a shared panel, these models tend to identify primarily slide-specific domains, which limits the comparison of domains across a broader study and reduces the potential for discovering new spatial biomarkers.

### 2. **Batch-effect correction**: Native correction via optimal transport and prototype alignment, eliminating reliance on external tools like Harmony or Leiden.

- 1차 검사: **supported**
- 근거로 든 문장: natively corrects batch effect across slides

- 판정:
- 메모:

**P0005** (paragraph, A foundation model for spatial transcriptomics)

> Novae is a graph-based foundation model 18,19 that we trained on a large single-cell spatial transcriptomics dataset composed of about 30 million cells. This model, aware of 18 different tissues, is hosted on a public hub and can be reused by the user for multiple downstream tasks on any technology or gene panel, as illustrated in Fig. 1a. The main application of Novae is to learn spatial domains, which can be performed with the shared model without any retraining (called zero-shot inference 17 ). If desired, the user can also retrain Novae to obtain refined results (fine-tuning). Two distinguishing properties of Novae are that (1) it provides a nested organization of spatial domains for different resolutions and (2) it natively corrects batch effect across slides. This consistent domain assignment across slides enables comparison analyses of a study containing multiple slides. Additionally, Novae can perform multiple downstream analysis tasks, such as (1) spatial pathway analysis; external tools need to be re-run for each new analysis or when adjusting spatial domain resolutions (choosing different number of spatial domains). Additionally, owing to their reliance on specific gene sets, these methods often necessitate training on the intersection of gene sets, which can significantly reduce the number of available genes and, consequently, impact performance. Notably, even when applied to slides with a shared panel, these models tend to identify primarily slide-specific domains, which limits the comparison of domains across a broader study and reduces the potential for discovering new spatial biomarkers.

**P0007** (paragraph, A foundation model for spatial transcriptomics)

> In terms of technical details, Novae is a graph-based neural network that is trained in a self-supervised manner based on the SwAV 24 framework. It learns representations of the local microenvironment at the single-cell (or spot) resolution. More specifically, for each cell or spot, a representation of its neighborhood is provided by a Graph Attention Network 16 , after embedding each cell into a panel-invariant representation. To effectively assign domains, we learn embeddings in the latent space, called prototypes, which represent elementary spatial domains. Depending on the desired level of resolution, these elementary domains are regrouped to form the domains at the desired resolution. We project the spatial domain representations into these prototypes to get probabilities of assignments. These probabilities are corrected via an algorithm of Optimal Transport 25 to ensure a smooth representation of the different prototypes. Afterwards, we use cross-entropy loss to make the representation of two cells in the same domain closer together. This methodological approach is illustrated in Fig. 1c.

### 3. **Nested spatial hierarchy**: Supports multi-resolution domain organization, allowing analysis at varying granularities.

- 1차 검사: **supported**
- 근거로 든 문장: Two distinguishing properties of Novae are that (1) it provides a nested organization of spatial domains for different resolutions

- 판정:
- 메모:

**P0005** (paragraph, A foundation model for spatial transcriptomics)

> Novae is a graph-based foundation model 18,19 that we trained on a large single-cell spatial transcriptomics dataset composed of about 30 million cells. This model, aware of 18 different tissues, is hosted on a public hub and can be reused by the user for multiple downstream tasks on any technology or gene panel, as illustrated in Fig. 1a. The main application of Novae is to learn spatial domains, which can be performed with the shared model without any retraining (called zero-shot inference 17 ). If desired, the user can also retrain Novae to obtain refined results (fine-tuning). Two distinguishing properties of Novae are that (1) it provides a nested organization of spatial domains for different resolutions and (2) it natively corrects batch effect across slides. This consistent domain assignment across slides enables comparison analyses of a study containing multiple slides. Additionally, Novae can perform multiple downstream analysis tasks, such as (1) spatial pathway analysis; external tools need to be re-run for each new analysis or when adjusting spatial domain resolutions (choosing different number of spatial domains). Additionally, owing to their reliance on specific gene sets, these methods often necessitate training on the intersection of gene sets, which can significantly reduce the number of available genes and, consequently, impact performance. Notably, even when applied to slides with a shared panel, these models tend to identify primarily slide-specific domains, which limits the comparison of domains across a broader study and reduces the potential for discovering new spatial biomarkers.

**P0007** (paragraph, A foundation model for spatial transcriptomics)

> In terms of technical details, Novae is a graph-based neural network that is trained in a self-supervised manner based on the SwAV 24 framework. It learns representations of the local microenvironment at the single-cell (or spot) resolution. More specifically, for each cell or spot, a representation of its neighborhood is provided by a Graph Attention Network 16 , after embedding each cell into a panel-invariant representation. To effectively assign domains, we learn embeddings in the latent space, called prototypes, which represent elementary spatial domains. Depending on the desired level of resolution, these elementary domains are regrouped to form the domains at the desired resolution. We project the spatial domain representations into these prototypes to get probabilities of assignments. These probabilities are corrected via an algorithm of Optimal Transport 25 to ensure a smooth representation of the different prototypes. Afterwards, we use cross-entropy loss to make the representation of two cells in the same domain closer together. This methodological approach is illustrated in Fig. 1c.

### 4. **Multimodal integration**: Combines spatial transcriptomics with histopathology (H&E) and proteomics data.

- 1차 검사: **supported**
- 근거로 든 문장: In addition to spatial transcriptomics and/or proteomics, H&E-stained images can be integrated into Novae to provide complementary morphological context.

- 판정:
- 메모:

**P0021** (paragraph, Incorporating histopathology information)

> In addition to spatial transcriptomics and/or proteomics, H&E-stained images can be integrated into Novae to provide complementary morphological context. Specifically, we compute patch embeddings over cell neighborhoods using a pathology foundation model such as CONCH 42 . These embeddings are then fused with Novae's graph-level representations to produce multimodal cell neighborhood embeddings (see 'Novae usage on multimodal spatial data with H&E'). We demonstrate this multimodal integration using a Xenium 5k human lung slide, for which a corresponding H&E image has been prealigned by 10x Genomics (see 'Datasets used'). In this sample, we compare three methodologies: (1) CONCH embeddings clustered with Leiden;

**P0060** (paragraph, Novae usage on protein expression)

> By default, Novae was trained on a large spatial transcriptomic dataset, but we can also use it on spatial proteomics data such as PhenoCycler 47 or MACSima 48 . Instead of using the scGPT gene embeddings, we use the components of a PCA fitted on the cell-by-protein expression table for the dataset of interest. The latter table can be extracted by averaging the mean intensity of all proteins over all the cell masks, for instance via Sopa 23 . Afterward, we can train Novae as for spatial transcriptomic dataset, with the protein embeddings behaving similarly to the gene embeddings.

### 5. **Efficiency**: Faster than state-of-the-art methods due to reduced dependency on external clustering and correction tools.

- 1차 검사: **supported**
- 근거로 든 문장: Indeed, this can take up to several days on 6 million cells, whereas Novae can perform these two operations in several seconds.

- 판정:
- 메모:

**P0015** (paragraph, Time and memory efficiency)

> After running inference (computing the cell's spatial representations), Novae can perform the attribution of the niches and correct batch effect in a short time. Indeed, the attribution of spatial domains is a mapping between the prototypes and the desired resolution (see 'Assignment to spatial domains'), which is performed in a short time. Regarding batch-effect correction, as the categorical domain assignments are already corrected through Novae, we can use the assignments to align the spatial representations (as detailed in 'Batch-effect correction'). This vectorial operation is also fast and in linear time. In contrast, for the two latter operations, the other state-of-the-art models depend on external tools, usually (1) Harmony 12 for batch-effect correction and (2) Leiden 13 or mclust 14 to assign spatial domains to the representations. As shown by Fig. 3h (bottom), using Harmony and Leiden can be slow, especially on large datasets of millions of cells. Indeed, this can take up to several days on 6 million cells, whereas Novae can perform these two operations in several seconds. Furthermore, during experimentation, it is common to try multiple resolutions of spatial domains, hence requiring clustering to be run multiple times. Novae can perform this very rapidly, thus easing the analysis of different resolutions, while the other methods require running a time-consuming clustering again. Actually, the dependency on Harmony and Leiden becomes the main time bottleneck for large datasets, that is, even longer than the model training itself. To show that, we also conducted a timing analysis to run (1) training; (2) inference; (3) batch-effect correction; and (4) clustering for the different methods as the cell count increased. All models were trained on an A100 GPU with an early-stopping mechanism that triggered after ten epochs of no improvement, allowing us to fairly assess each method's convergence speed. We included both the trained and zero-shot versions of Novae in our comparisons, with timings summarized in Fig. 3h (top). Notably, despite being a larger model, the speed gain due to not depending on Harmony and Leiden makes Novae faster than the other methods. The speed gap is even larger when Novae is used in zero-shot mode. Also, regarding random-access-memory (RAM) usage, Novae supports lazy loading (instead of storing the full graph dataset in memory, each subgraph is created on the fly before running through the model). This prevents an important amount of RAM from being dedicated to loading the dataset. This allowed us to train Novae on a dataset composed of nearly 30 million cells using a GPU with 40 GB of RAM (see 'Implementation and training details'). In addition, Novae runs on local subgraphs instead of running on a full slide, which is new for two reasons. First, the subgraphs are smaller and therefore require less memory. Second, it is possible to use a larger number of layers in the neural network without aggregating information from further environments. For instance, having a graph neural network of 16 layers operating on the full slide would lead to mixed information between on the left, Xenium 5k on the right). d, JSD between the Xenium v1 and Xenium 5k slides after cropping the second slide. A high JSD, above the red line, means either under or over batch-effect correction. e, Comparison of the Novae spatial domains over two segmentation methods (the default 10x Genomics segmentation (left) and Baysor 34 (right)). f, Relative sensitivity of Novae to node shuffle and edge-length drop over the breast and colon slides.

**P0016** (paragraph, Time and memory efficiency)

> Article https://doi.org/10.1038/s41592-025-02899-6 two cells at a distance of 300 microns, which is usually not intended. Instead, using local subgraphs ensures only aggregating information from local microenvironments. Practically, due to the latter implementations, the maximum video-random-access-memory (VRAM) required by a GPU is the model size (128 MB for our current model on Hugging Face) and one mini-batch of graphs that is generated on the fly (between 2 MB and 20 MB depending on hyperparameters). This GPU VRAM usage is independent of the AnnData dataset, which stays on the CPU, and whose RAM usage is therefore independent of Novae.

## 3. Methodology and Architecture

### 6. **Graph-based framework**: Novae uses a Graph Attention Network (GAT) to encode spatial relationships, with subgraphs representing local neighborhoods.

- 1차 검사: **supported**
- 근거로 든 문장: The graph encoder utilized in Novae is a Graph Attention Network 16 (GAT), which employs attention mechanisms to aggregate information from neighboring cells.

- 판정:
- 메모:

**P0041** (paragraph, Graph encoder)

> The graph encoder utilized in Novae is a Graph Attention Network 16 (GAT), which employs attention mechanisms to aggregate information from neighboring cells. The GAT is composed of multiple layers, with each layer potentially having multiple attention heads. The input to the GAT is a subgraph 𝒢𝒢, where node features are embedded cell features (as described in 'Cell embedding'). For each cell i, the initial node feature is h (0

**P0042** (paragraph, Graph encoder)

> , 𝒫𝒫 ′ ) during training, and h (0) i = embed(x i , 𝒫𝒫) during inference. For each layer l, the node features for the next layer are calculated as:

### 7. **Self-supervised learning**: Leverages SwAV (Self-Training with Augmented Views) for prototype learning, using optimal transport to align spatial domains.

- 1차 검사: **supported**
- 근거로 든 문장: we will leverage self-supervised learning 15,50 , which is well-suited for capturing meaningful data representations. Among the different self-supervision frameworks, SwAV 24 is a self-supervised learning algorithm that integrates contrastive learning and clustering.

- 판정:
- 메모:

**P0047** (paragraph, Prototypes and swapped assignment task)

> As the dataset lacks ground truth, we need to train Novae using an unsupervised approach. Specifically, as we aim to pretrain a foundation model, we will leverage self-supervised learning 15,50 , which is well-suited for capturing meaningful data representations. Among the different self-supervision frameworks, SwAV 24 is a self-supervised learning algorithm that integrates contrastive learning and clustering.

**P0049** (paragraph, Prototypes and swapped assignment task)

> where τ is a temperature parameter that controls the sharpness of the softmax distribution. Intuitively, p ik represents the probability that the neighborhood representation of cell i belongs to the prototype k. Again, to avoid confusion, we remind that the neighborhood representation of a cell i is assimilated to the representation z i of its corresponding subgraph 𝒢𝒢 i . To prevent the representations from collapsing into a single prototype, we define a 'corrected' assignment q i that aligns with the distribution p i while considering global mini-batch statistics. Essentially, we aim for each mini-batch to represent all prototypes as evenly as possible. This assignment q i is derived from the result of an optimal transport 25 (OT) problem over a mini-batch of size B (with each mini-batch being dedicated to one slide). Specifically, given a mini-batch of B subgraph representations Z = (z 1 , … , z B ) ∈ ℝ B×O and the matrix of all prototypes C = (c 1 , … , c K ) ∈ ℝ K×O , the OT problem is defined as:

### 8. **Data augmentation**: Introduces pseudo-batch effects and gene panel subsampling to improve generalization.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: introduces a 'pseudo batch effect' noise to reduce the model's sensitivity to batch effects

- 판정: 맞음
- 메모: P0035에 'pseudo batch effect' noise, P0036에 'randomly subset the gene panel according to a ratio γ' 모두 그대로 있음. 1차 검사의 인용문 축자 실패로 인한 거짓 경보.
- 판정자: 보조 (사람 확인 필요)

**P0035** (paragraph, Augmentation)

> First, we introduce a 'pseudo batch effect' noise to reduce the model's sensitivity to batch effects. For a given subgraph input, we sample two vectors: a ~ exponential(λ) P and s ~ Normal (0, σ 2 I P ), where λ and σ are hyperparameters, and I P is the identity matrix of size P × P. The gene expression vector for each cell i is then updated as x (noise

**P0036** (paragraph, Augmentation)

> Second, we randomly subset the gene panel according to a ratio γ ∈ [0, 1]. For a given panel 𝒫𝒫, we select ⌊γP⌋ genes, resulting in a new panel 𝒫𝒫 ′ ⊂ 𝒫𝒫. This augmentation simulates the effect of different panels of genes, as if multiple machines generated the data, or as if the panel was updated during a study. After applying these augmentations, each cell is represented by the expression vector x (augmented

### 9. **Panel-invariant embeddings**: Gene expressions are normalized and projected onto trainable embeddings, enabling cross-panel analysis.

- 1차 검사: **supported**
- 근거로 든 문장: After augmentation, cells are transformed into panel-invariant embeddings

- 판정:
- 메모:

**P0038** (paragraph, Cell embedding)

> After augmentation, cells are transformed into panel-invariant embeddings, which serve as the node features for the graph encoder described in the subsequent section. Let v 1 , … , v G ∈ ℝ E denote a list of trainable gene embeddings, where E represents the embedding size. For a given gene panel 𝒫𝒫 𝒫 𝒫1, … , G}, we consider only the embeddings corresponding to the genes in this panel. These embeddings are L2-normalized and then multiplied by the cell's scaled gene expression vector x ∈ ℝ P . Specifically, the embedding for a cell i is calculated as follows:

**P0039** (paragraph, Cell embedding)

> where the square root, square and division operations are performed element-wise. The purpose of the L2 normalization is to ensure that the embedding weights are comparable across different gene panel sizes. This can be compared to a principal-component analysis (PCA) reduction, where the components are trainable gene embeddings, and the L2 normalization ensures that each panel has consistent weights across different 'gene programs'. Specifically, for each e ≤ E, v ge represents the weight of gene v g in the gene program e. Additionally, rather than training all gene embeddings from scratch, we can initialize with pretrained gene embeddings from scGPT 49 . To prevent domain shift for genes not present in the Novae dataset, these pretrained embeddings are frozen, and we introduce a trainable linear layer afterward. Thus, the updated cell embedding formula becomes

### 10. **Hierarchical clustering**: Prototypes are clustered at multiple resolutions, with optional Leiden clustering for resolution parameter control.

- 1차 검사: **supported**
- 근거로 든 문장: In addition to the hierarchical-based assignment, we offer the possibility to use Leiden 13 on the prototypes.

- 판정:
- 메모:

**P0055** (paragraph, Assignment to spatial domains)

> Prototypes can be considered as centroids of elementary spatial domains. As the desired number of spatial domains may vary, we employ hierarchical clustering on the prototypes. In this setup, the prototypes serve as the leaves of a hierarchical tree, with each level of the tree representing increasingly coarse-grained spatial domains. For a given subgraph representation z i , we assign it to the closest prototype by selecting the one with the highest dot product, defined as C (leaf) i ∶= arg max K k=1 z T i c k . This assignment C (leaf) i indicates to which tree-leaf the cell i is associated. At a particular level l of the tree, the spatial domain assignment for cell i is determined by C (l

**P0056** (paragraph, Assignment to spatial domains)

> where Map (l, ⋅ ) is a mapping function that associates the leaf prototype C (leaf) i with a cluster at level l (the level l is chosen according to the number of desired clusters). This hierarchical approach allows each cell representation to be assigned to spatial domains of varying resolutions efficiently (constant time). In other words, the prototypes serve as elementary spatial domains, used to define spatial domains at the desired resolution. In addition to the hierarchical-based assignment, we offer the possibility to use Leiden 13 on the prototypes. While this does not keep the hierarchy property, it has the benefit of depending on a resolution parameter instead of a number of spatial domains. Therefore, this option can sometimes be preferred to the hierarchical clustering of the prototypes, depending on the user use cases. This prototype Leiden clustering is also very fast, as the number of prototypes (typically 512) is very small compared to the number of cells. Finally, the cell assignment to the spatial domain also uses an arg max and a mapping, as described above for the hierarchical clustering.

## 4. Key Results and Benchmarks

### 11. **Benchmark superiority**: Novae outperformed six state-of-the-art methods (SpaceFlow, GraphST, STAGATE, etc.) in FIDE and JSD scores across breast, colon, and synthetic datasets.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: Novae outperformed six state-of-the-art methods (SpaceFlow, GraphST, STAGATE, etc.) in FIDE and JSD scores across breast, colon, and synthetic datasets.

- 판정: 맞음
- 메모: 여섯 방법 이름·FIDE·JSD·breast는 P0011, colon 우위는 P0012, synthetic은 P0014가 뒷받침. 다만 synthetic 데이터셋의 지표는 ARI와 FIDE이고 JSD가 아니므로 'FIDE and JSD across ... synthetic'은 다소 일반화됨.
- 판정자: 보조 (사람 확인 필요)

**P0011** (paragraph, Integration and continuity of the spatial domains)

> In this study, we compared Novae in both zero-shot and fine-tuning modes to six state-of-the-art methods: SpaceFlow 10 , GraphST 9 , SEDR 11 , STAGATE 8 , NicheCompass 29 and Scanpy 30 (more details are in 'Spatial domains assignment benchmark'). We evaluated the performance of these methods across three distinct test cases. In the first test case, we used the breast dataset, composed of two slides with different gene panels. As mentioned earlier, Novae can be trained across multiple gene panels; hence, a single Novae model was trained for both panels. In contrast, the other methods were trained on the intersection of 185 common genes across the two panels (as illustrated in Fig. 3a), followed by batch-effect correction using Harmony 12 and clustering with mclust 14 (using 7, 10 and 15 clusters). To evaluate model performance, we used the FIDE (F1-score of inter-domain edges) score and Jensen-Shannon Divergence ( JSD) score to assess spatial domain continuity and cross-slide homogeneity, respectively (see 'Metrics for model comparison'). Figure 3b presents the results of this benchmark, highlighting a notable improvement in performance by Novae, even in the zero-shot case (using a pretrained model directly).

**P0012** (paragraph, Integration and continuity of the spatial domains)

> The second test case involved the colon dataset, where Novae was again trained across all slides. For the other methods, due to the limited intersection of genes between panels, we employed a different approach: a separate model was trained for each slide (as illustrated in Fig. 3c). The spatial representations from each model were then concatenated, followed by batch-effect correction and clustering. Figure 3d presents the result metrics for all methods on the colon dataset, again showing a superior performance by Novae in both zero-shot and fine-tuning modes.

**P0014** (paragraph, Integration and continuity of the spatial domains)

> The third comparison was conducted on a synthetic dataset consisting of five slides and seven spatial domains (see 'Datasets used' for more details). Unlike the previous cases, this dataset used the same gene panel across all slides, allowing the other methods to run without requiring gene panel intersection. In this case, we did not use Novae in zero-shot mode, as the gene expression was synthetic, meaning the generated cell types may not correspond to real data. Likewise, we did not use NicheCompass 29 here, as it relies on prior gene programs that reflect real biological interactions (such as ligand-receptor pairs and transcription factor-target relationships) to guide its embedding. Because these programs must map to actual genetic features, using purely synthetic data (with no direct biological meaning) breaks NicheCompass's fundamental assumptions about gene-gene interactions. The models were evaluated using the adjusted Rand index (ARI) 33 for clustering accuracy against the known ground truth, as well as the FIDE score. Figure 3f shows the ARI of the different methods across five seeds, and Fig. 3g presents the FIDE score across five seeds. Again, Novae outperformed the other methods, demonstrating higher ARI and FIDE scores with notably low s.d. in ARI (Fig. 3f). The ground truth and the spatial domain predictions of the different models are shown in Supplementary Fig. 4.

### 12. **Zero-shot performance**: Achieved high FIDE scores (e.g., 0.85) without retraining, demonstrating robust cross-slide domain continuity.

- 1차 검사: **flagged** — 0.85 is nowhere in the paper  (모델: supported)
- 근거로 든 문장: In the first test case, we used the breast dataset, composed of two slides with different gene panels.

- 판정: 수치틀림
- 메모: zero-shot으로 좋은 FIDE를 냈다는 취지는 P0011이 뒷받침하나, 제시한 값 0.85는 논문 어디에도 없음.
- 판정자: 보조 (사람 확인 필요)

**P0011** (paragraph, Integration and continuity of the spatial domains)

> In this study, we compared Novae in both zero-shot and fine-tuning modes to six state-of-the-art methods: SpaceFlow 10 , GraphST 9 , SEDR 11 , STAGATE 8 , NicheCompass 29 and Scanpy 30 (more details are in 'Spatial domains assignment benchmark'). We evaluated the performance of these methods across three distinct test cases. In the first test case, we used the breast dataset, composed of two slides with different gene panels. As mentioned earlier, Novae can be trained across multiple gene panels; hence, a single Novae model was trained for both panels. In contrast, the other methods were trained on the intersection of 185 common genes across the two panels (as illustrated in Fig. 3a), followed by batch-effect correction using Harmony 12 and clustering with mclust 14 (using 7, 10 and 15 clusters). To evaluate model performance, we used the FIDE (F1-score of inter-domain edges) score and Jensen-Shannon Divergence ( JSD) score to assess spatial domain continuity and cross-slide homogeneity, respectively (see 'Metrics for model comparison'). Figure 3b presents the results of this benchmark, highlighting a notable improvement in performance by Novae, even in the zero-shot case (using a pretrained model directly).

**P0014** (paragraph, Integration and continuity of the spatial domains)

> The third comparison was conducted on a synthetic dataset consisting of five slides and seven spatial domains (see 'Datasets used' for more details). Unlike the previous cases, this dataset used the same gene panel across all slides, allowing the other methods to run without requiring gene panel intersection. In this case, we did not use Novae in zero-shot mode, as the gene expression was synthetic, meaning the generated cell types may not correspond to real data. Likewise, we did not use NicheCompass 29 here, as it relies on prior gene programs that reflect real biological interactions (such as ligand-receptor pairs and transcription factor-target relationships) to guide its embedding. Because these programs must map to actual genetic features, using purely synthetic data (with no direct biological meaning) breaks NicheCompass's fundamental assumptions about gene-gene interactions. The models were evaluated using the adjusted Rand index (ARI) 33 for clustering accuracy against the known ground truth, as well as the FIDE score. Figure 3f shows the ARI of the different methods across five seeds, and Fig. 3g presents the FIDE score across five seeds. Again, Novae outperformed the other methods, demonstrating higher ARI and FIDE scores with notably low s.d. in ARI (Fig. 3f). The ground truth and the spatial domain predictions of the different models are shown in Supplementary Fig. 4.

### 13. **Efficiency gains**: Reduced inference and clustering times by orders of magnitude compared to Harmony/Leiden/mclust.

- 1차 검사: **supported**
- 근거로 든 문장: Indeed, this can take up to several days on 6 million cells, whereas Novae can perform these two operations in several seconds.

- 판정:
- 메모:

**P0015** (paragraph, Time and memory efficiency)

> After running inference (computing the cell's spatial representations), Novae can perform the attribution of the niches and correct batch effect in a short time. Indeed, the attribution of spatial domains is a mapping between the prototypes and the desired resolution (see 'Assignment to spatial domains'), which is performed in a short time. Regarding batch-effect correction, as the categorical domain assignments are already corrected through Novae, we can use the assignments to align the spatial representations (as detailed in 'Batch-effect correction'). This vectorial operation is also fast and in linear time. In contrast, for the two latter operations, the other state-of-the-art models depend on external tools, usually (1) Harmony 12 for batch-effect correction and (2) Leiden 13 or mclust 14 to assign spatial domains to the representations. As shown by Fig. 3h (bottom), using Harmony and Leiden can be slow, especially on large datasets of millions of cells. Indeed, this can take up to several days on 6 million cells, whereas Novae can perform these two operations in several seconds. Furthermore, during experimentation, it is common to try multiple resolutions of spatial domains, hence requiring clustering to be run multiple times. Novae can perform this very rapidly, thus easing the analysis of different resolutions, while the other methods require running a time-consuming clustering again. Actually, the dependency on Harmony and Leiden becomes the main time bottleneck for large datasets, that is, even longer than the model training itself. To show that, we also conducted a timing analysis to run (1) training; (2) inference; (3) batch-effect correction; and (4) clustering for the different methods as the cell count increased. All models were trained on an A100 GPU with an early-stopping mechanism that triggered after ten epochs of no improvement, allowing us to fairly assess each method's convergence speed. We included both the trained and zero-shot versions of Novae in our comparisons, with timings summarized in Fig. 3h (top). Notably, despite being a larger model, the speed gain due to not depending on Harmony and Leiden makes Novae faster than the other methods. The speed gap is even larger when Novae is used in zero-shot mode. Also, regarding random-access-memory (RAM) usage, Novae supports lazy loading (instead of storing the full graph dataset in memory, each subgraph is created on the fly before running through the model). This prevents an important amount of RAM from being dedicated to loading the dataset. This allowed us to train Novae on a dataset composed of nearly 30 million cells using a GPU with 40 GB of RAM (see 'Implementation and training details'). In addition, Novae runs on local subgraphs instead of running on a full slide, which is new for two reasons. First, the subgraphs are smaller and therefore require less memory. Second, it is possible to use a larger number of layers in the neural network without aggregating information from further environments. For instance, having a graph neural network of 16 layers operating on the full slide would lead to mixed information between on the left, Xenium 5k on the right). d, JSD between the Xenium v1 and Xenium 5k slides after cropping the second slide. A high JSD, above the red line, means either under or over batch-effect correction. e, Comparison of the Novae spatial domains over two segmentation methods (the default 10x Genomics segmentation (left) and Baysor 34 (right)). f, Relative sensitivity of Novae to node shuffle and edge-length drop over the breast and colon slides.

**P0016** (paragraph, Time and memory efficiency)

> Article https://doi.org/10.1038/s41592-025-02899-6 two cells at a distance of 300 microns, which is usually not intended. Instead, using local subgraphs ensures only aggregating information from local microenvironments. Practically, due to the latter implementations, the maximum video-random-access-memory (VRAM) required by a GPU is the model size (128 MB for our current model on Hugging Face) and one mini-batch of graphs that is generated on the fly (between 2 MB and 20 MB depending on hyperparameters). This GPU VRAM usage is independent of the AnnData dataset, which stays on the CPU, and whose RAM usage is therefore independent of Novae.

### 14. **Multimodal accuracy**: Combined Novae + CONCH achieved the highest FIDE score (0.89) for H&E-integrated spatial domains.

- 1차 검사: **flagged** — 0.89 is nowhere in the paper  (모델: supported)
- 근거로 든 문장: the fused Novae + CONCH model achieves the highest FIDE score

- 판정: 수치틀림
- 메모: 'fused Novae + CONCH model achieves the highest FIDE score'는 P0022에 그대로 있으나 값 0.89는 논문 어디에도 없음.
- 판정자: 보조 (사람 확인 필요)

**P0022** (paragraph, Incorporating histopathology information)

> (2) Novae domains derived from transcriptomics alone; and (3) multimodal Novae domains combining transcriptomic and H&E embedding. As shown in Fig. 5d, the multimodal Novae domains (right) delineate spatial structures more precisely than CONCH alone (left). Quantitatively, Fig. 5e shows that while Novae outperforms CONCH individually, the fused Novae + CONCH model achieves the highest FIDE score, indicating improved performance through multimodal integration. Biologically, this added information enhances domain specificity. For instance, domain D2030, identified by multimodal Novae, is enriched in inflammatory monocytes (a distinction not captured by CONCH alone; Supplementary Fig. 16). Moreover, the latter heatmaps show that, while CONCH tends to underrepresent cell-type heterogeneity, Novae (with or without H&E) captures it more effectively. Also, the combination of Novae and CONCH enables the separation of domains D2032 and D2027, whereas Novae alone merges them into a single domain D2037 (Supplementary Fig. 16e). This improved resolution can be explained by the distinct morphology of region D2032, corresponding to the bronchus. Overall, adding the H&E information can add context and improve Novae's capabilities to identify heterogeneous spatial domains compared to the usage of spatial transcriptomics alone.

### 15. **Robustness**: Maintained performance under segmentation changes and batch effects, with minimal degradation at 60% data loss.

- 1차 검사: **supported**
- 근거로 든 문장: performance drops at a slide degradation of 60%

- 판정:
- 메모:

**P0018** (paragraph, Robustness to missing domains and perturbations)

> An overcorrection would result in artificially identical domain proportions across the slide A-split and slide B-complete, leading to major discrepancies after splitting slide B and comparing it to slide A-split. Conversely, under-correction (with slide-specific domains) would preserve distinct domain proportions, yielding a high JSD score. The results, summarized in Fig. 4b, show that Novae achieves both a high FIDE score (indicating domain continuity) and a low post-split JSD (indicating that Novae is not overcorrecting). The spatial domains of the other methods are shown in Supplementary Fig. 11. To further assess robustness, we created a second benchmark dataset using two adjacent Xenium slides (one processed with the Xenium v1 machine and the other with Xenium Prime 5k). Here, we altered the Xenium v1 slide by removing half of its data (Fig. 4c). The results, presented in Fig. 4d, confirm that removing a large part of the domain D1012 is not affecting too much the proportions on the Xenium v1 slide. In the opposite, some methods such as GraphST, SpaceFlow, STAGATE and Scanpy show a high JSD, due to under-correction. Beyond these benchmarks, we tested Novae's robustness against other perturbations, such as variations in segmentation methods. In Fig. 4e, we compare Novae's results using both the default 10x Genomics default segmentation (staining-based) and Baysor 34 (transcript-based), demonstrating that Novae consistently identifies the same spatial domains despite methodological differences in the segmentation. An interesting thing to note here is that the other models are also able to perform this task (Supplementary Fig. 13). Therefore, while a good segmentation is crucial for cell-level tasks (for example, cell-type annotation or ligand-receptor analysis), it shows a lower importance for the spatial domains definition. Last, Fig. 4f examines the sensitivity of Novae's output to node shuffling in input graphs and to an important reduction in edge length/weights (set to 0.01). As we could expect, we observe that node shuffling primarily affects domain interfaces, while edge-length reduction impacts mostly stromal and sparse regions. Additionally, we tested Novae's robustness to increasingly degraded tissue slides and with extreme batch effect. The experiments can be found in Supplementary Fig. 17 (showing performance drops at a slide degradation of 60%) and Supplementary Fig. 19. More details can be found in 'Perturbation analysis'.

**P0068** (paragraph, Perturbation analysis)

> , where y 1 is the Novae output post-perturbation for one subgraph, and y 0 is the Novae output before the perturbation for the same subgraph. We studied two perturbations, first a node shuffle, and second, setting the edge length to 0.01. Finally, we also averaged the attention of Novae across the layers, then applied a softmax with temperature 0.01, and computed the entropy of the aggregated attention (Supplementary Fig. 10). Also, to evaluate Novae's robustness to batch effects and consistency of spatial domain assignments, we implemented a systematic perturbation approach using inter-slide batch effect simulation. We selected representative spatial transcriptomics datasets from lung and brain tissues as test cases, generating five progressively perturbed versions of each slide to mimic realistic experimental batch effects encountered in multislide studies. Each perturbation level applied whole-slide modifications, including library size scaling with log-normal distribution (σ ranging from 0.02 for minimal to 0.5 for extreme effects), gene-specific efficiency changes affecting 3-50% of genes with varying capture rates, ambient RNA contamination targeting 5-100 randomly selected genes and spatial field gradients for stronger perturbation levels. Finally, to evaluate robustness to slide quality, we simulate degradation on a slide by randomly removing a proportion δ ∈ [0, 1] of cells and masking the expression of a proportion δ of genes. We then train Novae using the degraded slide alongside the corresponding reference (nondegraded) slide. After training, we compare the cell assignments in the degraded slide to the corresponding cells in the reference. This comparison yields an accuracy score that reflects the model's robustness to data degradation (Supplementary Fig. 17).

## 5. Limitations and Future Work

### 16. **Data dependency**: Pretrained models rely on spatial transcriptomics data, limiting multimodal training.

- 1차 검사: **supported**
- 근거로 든 문장: the pretrained Novae models rely exclusively on spatial transcriptomics data

- 판정:
- 메모:

**P0031** (paragraph, Discussion)

> We also demonstrated that Novae can be trained on spatial proteomics data (for example, the CosMX Protein Assays 7 , PhenoCycler 47 or MACSima 48 ) or in a multimodal spatial context. Yet, the pretrained Novae models rely exclusively on spatial transcriptomics data. This limitation arises from the current absence of large-scale datasets combining spatial transcriptomics, spatial proteomics and histopathology on the same slides, which limits our capacity to train a foundation model across multiple spatial modalities. This lack of multimodal datasets also complicates the evaluation of multimodal models across diverse tissues and large cohorts of slides. In terms of robustness, we conducted a range of experiments to assess sensitivity to various perturbations, including segmentation changes, extreme batch effects and artificial slide degradation. While Novae exhibited strong stability against segmentation variation and batch effects, the degradation benchmark revealed a performance drop when approximately 60% of cells and gene expression were lost. Further investigations into sensitivity to segmentation changes could benefit from including tissues with extreme variations in cellular density. For example, densely packed tissues (where tightly clustered cells make segmentation more challenging) could be studied alongside sparser, lower-quality slides where cell boundaries are harder to define due to poor contrast or resolution. Additionally, because Novae operates on cell centroids, it is currently limited in its ability to represent complex tissue structures such as axons, which are not yet accurately segmented with current methods. Future segmentation advances that capture such structures could allow updating Novae's input graph to try solving this challenge. Looking ahead, incorporating a mixture-of-experts approach could enable joint analysis of both spot resolution and single-cell-resolution data within a unified framework. More broadly, expanding the size and heterogeneity of the training data would improve Novae's generalizability and its robustness to missing data domains (an area that remains a challenge). Addressing these limitations will be key to advancing Novae's utility and impact in spatial transcriptomics research.

### 17. **Segmentation constraints**: Current methods struggle with highly dense or low-quality slides, requiring improved segmentation.

- 1차 검사: **supported**
- 근거로 든 문장: the degradation benchmark revealed a performance drop when approximately 60% of cells and gene expression were lost

- 판정:
- 메모:

**P0031** (paragraph, Discussion)

> We also demonstrated that Novae can be trained on spatial proteomics data (for example, the CosMX Protein Assays 7 , PhenoCycler 47 or MACSima 48 ) or in a multimodal spatial context. Yet, the pretrained Novae models rely exclusively on spatial transcriptomics data. This limitation arises from the current absence of large-scale datasets combining spatial transcriptomics, spatial proteomics and histopathology on the same slides, which limits our capacity to train a foundation model across multiple spatial modalities. This lack of multimodal datasets also complicates the evaluation of multimodal models across diverse tissues and large cohorts of slides. In terms of robustness, we conducted a range of experiments to assess sensitivity to various perturbations, including segmentation changes, extreme batch effects and artificial slide degradation. While Novae exhibited strong stability against segmentation variation and batch effects, the degradation benchmark revealed a performance drop when approximately 60% of cells and gene expression were lost. Further investigations into sensitivity to segmentation changes could benefit from including tissues with extreme variations in cellular density. For example, densely packed tissues (where tightly clustered cells make segmentation more challenging) could be studied alongside sparser, lower-quality slides where cell boundaries are harder to define due to poor contrast or resolution. Additionally, because Novae operates on cell centroids, it is currently limited in its ability to represent complex tissue structures such as axons, which are not yet accurately segmented with current methods. Future segmentation advances that capture such structures could allow updating Novae's input graph to try solving this challenge. Looking ahead, incorporating a mixture-of-experts approach could enable joint analysis of both spot resolution and single-cell-resolution data within a unified framework. More broadly, expanding the size and heterogeneity of the training data would improve Novae's generalizability and its robustness to missing data domains (an area that remains a challenge). Addressing these limitations will be key to advancing Novae's utility and impact in spatial transcriptomics research.

**P0068** (paragraph, Perturbation analysis)

> , where y 1 is the Novae output post-perturbation for one subgraph, and y 0 is the Novae output before the perturbation for the same subgraph. We studied two perturbations, first a node shuffle, and second, setting the edge length to 0.01. Finally, we also averaged the attention of Novae across the layers, then applied a softmax with temperature 0.01, and computed the entropy of the aggregated attention (Supplementary Fig. 10). Also, to evaluate Novae's robustness to batch effects and consistency of spatial domain assignments, we implemented a systematic perturbation approach using inter-slide batch effect simulation. We selected representative spatial transcriptomics datasets from lung and brain tissues as test cases, generating five progressively perturbed versions of each slide to mimic realistic experimental batch effects encountered in multislide studies. Each perturbation level applied whole-slide modifications, including library size scaling with log-normal distribution (σ ranging from 0.02 for minimal to 0.5 for extreme effects), gene-specific efficiency changes affecting 3-50% of genes with varying capture rates, ambient RNA contamination targeting 5-100 randomly selected genes and spatial field gradients for stronger perturbation levels. Finally, to evaluate robustness to slide quality, we simulate degradation on a slide by randomly removing a proportion δ ∈ [0, 1] of cells and masking the expression of a proportion δ of genes. We then train Novae using the degraded slide alongside the corresponding reference (nondegraded) slide. After training, we compare the cell assignments in the degraded slide to the corresponding cells in the reference. This comparison yields an accuracy score that reflects the model's robustness to data degradation (Supplementary Fig. 17).

### 18. **Complex structures**: Cannot represent subcellular features like axons due to reliance on cell centroids.

- 1차 검사: **supported**
- 근거로 든 문장: Additionally, because Novae operates on cell centroids, it is currently limited in its ability to represent complex tissue structures such as axons, which are not yet accurately segmented with current methods.

- 판정:
- 메모:

**P0031** (paragraph, Discussion)

> We also demonstrated that Novae can be trained on spatial proteomics data (for example, the CosMX Protein Assays 7 , PhenoCycler 47 or MACSima 48 ) or in a multimodal spatial context. Yet, the pretrained Novae models rely exclusively on spatial transcriptomics data. This limitation arises from the current absence of large-scale datasets combining spatial transcriptomics, spatial proteomics and histopathology on the same slides, which limits our capacity to train a foundation model across multiple spatial modalities. This lack of multimodal datasets also complicates the evaluation of multimodal models across diverse tissues and large cohorts of slides. In terms of robustness, we conducted a range of experiments to assess sensitivity to various perturbations, including segmentation changes, extreme batch effects and artificial slide degradation. While Novae exhibited strong stability against segmentation variation and batch effects, the degradation benchmark revealed a performance drop when approximately 60% of cells and gene expression were lost. Further investigations into sensitivity to segmentation changes could benefit from including tissues with extreme variations in cellular density. For example, densely packed tissues (where tightly clustered cells make segmentation more challenging) could be studied alongside sparser, lower-quality slides where cell boundaries are harder to define due to poor contrast or resolution. Additionally, because Novae operates on cell centroids, it is currently limited in its ability to represent complex tissue structures such as axons, which are not yet accurately segmented with current methods. Future segmentation advances that capture such structures could allow updating Novae's input graph to try solving this challenge. Looking ahead, incorporating a mixture-of-experts approach could enable joint analysis of both spot resolution and single-cell-resolution data within a unified framework. More broadly, expanding the size and heterogeneity of the training data would improve Novae's generalizability and its robustness to missing data domains (an area that remains a challenge). Addressing these limitations will be key to advancing Novae's utility and impact in spatial transcriptomics research.

### 19. **Future directions**: Expand training data to include proteomics and histopathology, integrate mixture-of-experts for multi-resolution analysis, and enhance robustness to extreme batch effects.

- 1차 검사: **supported**
- 근거로 든 문장: expanding the size and heterogeneity of the training data would improve Novae's generalizability and its robustness to missing data domains

- 판정:
- 메모:

**P0031** (paragraph, Discussion)

> We also demonstrated that Novae can be trained on spatial proteomics data (for example, the CosMX Protein Assays 7 , PhenoCycler 47 or MACSima 48 ) or in a multimodal spatial context. Yet, the pretrained Novae models rely exclusively on spatial transcriptomics data. This limitation arises from the current absence of large-scale datasets combining spatial transcriptomics, spatial proteomics and histopathology on the same slides, which limits our capacity to train a foundation model across multiple spatial modalities. This lack of multimodal datasets also complicates the evaluation of multimodal models across diverse tissues and large cohorts of slides. In terms of robustness, we conducted a range of experiments to assess sensitivity to various perturbations, including segmentation changes, extreme batch effects and artificial slide degradation. While Novae exhibited strong stability against segmentation variation and batch effects, the degradation benchmark revealed a performance drop when approximately 60% of cells and gene expression were lost. Further investigations into sensitivity to segmentation changes could benefit from including tissues with extreme variations in cellular density. For example, densely packed tissues (where tightly clustered cells make segmentation more challenging) could be studied alongside sparser, lower-quality slides where cell boundaries are harder to define due to poor contrast or resolution. Additionally, because Novae operates on cell centroids, it is currently limited in its ability to represent complex tissue structures such as axons, which are not yet accurately segmented with current methods. Future segmentation advances that capture such structures could allow updating Novae's input graph to try solving this challenge. Looking ahead, incorporating a mixture-of-experts approach could enable joint analysis of both spot resolution and single-cell-resolution data within a unified framework. More broadly, expanding the size and heterogeneity of the training data would improve Novae's generalizability and its robustness to missing data domains (an area that remains a challenge). Addressing these limitations will be key to advancing Novae's utility and impact in spatial transcriptomics research.

**P0068** (paragraph, Perturbation analysis)

> , where y 1 is the Novae output post-perturbation for one subgraph, and y 0 is the Novae output before the perturbation for the same subgraph. We studied two perturbations, first a node shuffle, and second, setting the edge length to 0.01. Finally, we also averaged the attention of Novae across the layers, then applied a softmax with temperature 0.01, and computed the entropy of the aggregated attention (Supplementary Fig. 10). Also, to evaluate Novae's robustness to batch effects and consistency of spatial domain assignments, we implemented a systematic perturbation approach using inter-slide batch effect simulation. We selected representative spatial transcriptomics datasets from lung and brain tissues as test cases, generating five progressively perturbed versions of each slide to mimic realistic experimental batch effects encountered in multislide studies. Each perturbation level applied whole-slide modifications, including library size scaling with log-normal distribution (σ ranging from 0.02 for minimal to 0.5 for extreme effects), gene-specific efficiency changes affecting 3-50% of genes with varying capture rates, ambient RNA contamination targeting 5-100 randomly selected genes and spatial field gradients for stronger perturbation levels. Finally, to evaluate robustness to slide quality, we simulate degradation on a slide by randomly removing a proportion δ ∈ [0, 1] of cells and masking the expression of a proportion δ of genes. We then train Novae using the degraded slide alongside the corresponding reference (nondegraded) slide. After training, we compare the cell assignments in the degraded slide to the corresponding cells in the reference. This comparison yields an accuracy score that reflects the model's robustness to data degradation (Supplementary Fig. 17).

