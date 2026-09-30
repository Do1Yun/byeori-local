# 검토표: madhu-2025-heist-a-graph-foundation-model-for

- 논문: HEIST: A GRAPH FOUNDATION MODEL FOR SPATIAL TRANSCRIPTOMICS AND PROTEOMICS DATA
- 학술지·연도:  2025  (출처 extraction, DOI -)
- 노트 revision: `0bc6c270c79a4f68a3ed8b136d6bd493`  sha256 `ad21dec379f6fad7`
- 추출: complete, 블록 117개, 생성 경로 single, 제시 117/117
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

### 1. **Modeling inter-cellular and hierarchical effects of co-expression networks**: HEIST is the first foundation model for spatial omics to explicitly incorporate co-expression networks alongside spatial graphs in a hierarchical graph, enabling local gene programs to influence tissue-level organization.

- 1차 검사: **supported**
- 근거로 든 문장: Modeling inter-cellular and hierarchical effects of co-expression networks: HEIST is the first foundation model for spatial omics to explicitly incorporate co-expression networks alongside spatial graphs in a hierarchical graph

- 판정:
- 메모:

**P0006** (paragraph, INTRODUCTION)

> • Modeling inter-cellular and hierarchical effects of co-expression networks: HEIST is the first foundation model for spatial omics to explicitly incorporate co-expression networks alongside spatial graphs in a hierarchical graph, enabling a local gene programs to influence tissue-level organization, and vice versa.

### 2. **Hierarchical representation learning with biological inductive bias**: HEIST captures fine-grained gene co-expression within cells and long-range cellular interactions via cross-level message passing, producing biologically contextualized embeddings.

- 1차 검사: **supported**
- 근거로 든 문장: Using biologically motivated hierarchical modeling, HEIST captures fine-grained gene co-expression within cells and long-range cellular interactions through novel cross-level message passing, producing biologically contextualized embeddings.

- 판정:
- 메모:

**P0007** (paragraph, INTRODUCTION)

> • Hierarchical representation learning with biological inductive bias: Using biologically motivated hierarchical modeling, HEIST captures fine-grained gene co-expression within cells and long-range cellular interactions through novel cross-level message passing, producing biologically contextualized embeddings.

### 3. **Task-agnostic, general-purpose foundation model**: HEIST is pretrained on 22.3M cells from 124 tissues across 15 organs using spatially-aware contrastive and masked autoencoding objectives, achieving state-of-the-art performance across four downstream tasks and generalizing to proteomics data.

- 1차 검사: **supported**
- 근거로 든 문장: HEIST is trained in a self-supervised manner on a large-scale corpus of spatial transcriptomics data comprising over 22.3M cells spanning 15 organs and 124 tissues

- 판정:
- 메모:

**P0008** (paragraph, INTRODUCTION)

> • A task-agnostic, general-purpose foundation model: HEIST is trained in a self-supervised manner on a large-scale corpus of spatial transcriptomics data comprising over 22.3M cells spanning 15 organs and 124 tissues. In downstream evaluations, HEIST achieves state-of-the-art performance across four diverse tasks-outperforming prior models, generalizes to proteomics data, while being computationally efficient.

## 3. Methodology and Architecture

### 4. HEIST models tissues as hierarchical graphs, with a spatial cell graph at the higher level and gene co-expression networks at the lower level. Key components include:

- 1차 검사: **no_evidence** — the note cites nothing here
- 근거로 든 문장: -

- 판정: 무인용
- 메모: 노트가 이 주장에 문단 인용을 달지 않았음. 구조 검증은 2~4절에 인용이 하나라도 있으면 통과시키므로 개별 주장의 무인용을 잡지 못함. 내용의 진위는 별도 확인이 필요함.
- 판정자: 보조 (사람 확인 필요)

> 인용 없음

### 5. **Hierarchical graph construction**: Spatial cell-cell graphs are built using Voronoi polygons, and gene co-expression networks are derived from mutual information between denoised genes within cell types.

- 1차 검사: **supported**
- 근거로 든 문장: We create the spatial cell-cell graph by computing Voronoi polygons from cell coordinates and connecting cells in adjacent polygons.

- 판정:
- 메모:

**P0011** (paragraph, Hierarchical Graph Construction.)

> As shown in Figure A1, we first preprocess the data by removing outliers, normalizing gene expression, and retaining highly variable genes. Then we apply MAGIC (Dijk et al., 2017) to denoise gene expression values and reduce dropout noise. To build the gene co-expression networks, we first subset the cells based on cell-types using provided annotations or Leiden clustering. Following this, we compute pairwise mutual information between denoised genes within each type, and connect gene pairs above a threshold τ . This results in total of |T | gene co-expression networks with mutual information prior. We create the spatial cell-cell graph by computing Voronoi polygons from cell coordinates and connecting cells in adjacent polygons. We then connect each cell with the gene co-expression network of that cell-type. The resulting outputs are a spatial graph G c (C, E, P, T ) and a set of gene co-expression

### 6. **Intra- and cross-level message passing**: Intra-level message passing updates cell and gene embeddings within each graph, while cross-level message passing integrates spatial and gene modalities via directional attention mechanisms.

- 1차 검사: **supported**
- 근거로 든 문장: Intra-level message passing (Equation 1) within each graph, followed by cross-level message passing (Equation 2) to integrate multi-modal information.

- 판정:
- 메모:

**P0013** (paragraph, Hierarchical Graph Construction.)

> As shown in Figure 2, the model first performs intra-level message passing (Equation 1) within each graph, followed by cross-level message passing (Equation 2) to integrate multi-modal information. HEIST is pretrained using a combination of contrastive and auto-encoding objectives on gene expression and cell locations. By using these components, HEIST can learn expressive and context-aware cell and gene embeddings that reflect biologically meaningful relationships between cells and genes. Note that as a result of this setup, gene representations are themselves learned in the context of the hierarchical graph, instead of based on a fixed gene vocabulary. They are initialized with rank-based and sinusoidal positional encodings, and dynamically updated through message passing in co-expression graphs, allowing HEIST to generalize to unseen genes or proteomic features by grounding embeddings in co-expression dynamics.

### 7. **Positional encodings**: Sinusoidal positional encodings are used for spatial coordinates and gene ranks, enabling context-aware embeddings.

- 1차 검사: **supported**
- 근거로 든 문장: HEIST incorporates positional encodings (PE) at both the cell and gene levels to inject spatial and coexpression structure into the learned representations.

- 판정:
- 메모:

**P0066** (paragraph, C.1 POSITIONAL ENCODINGS)

> HEIST incorporates positional encodings (PE) at both the cell and gene levels to inject spatial and coexpression structure into the learned representations. As opposed to traditional graph PEs such has Laplacian PE (Dwivedi & Bresson, 2020), random walk PE (Dwivedi & Bresson, 2020), node-centrality based PE (Ying et al., 2021), we make use of sinusoidal PEs. This design choice is motivated by the fact that sinusoidal PE yields expressive representations and are computationally in-expensive as opposed to traditional graph PEs, leading to efficient and expressive representations (Wen et al., 2023b). Below, we describe how these encodings are constructed and why they are suitable for spatial transcriptomics.

### 8. **Pre-training tasks**: Contrastive learning aligns cell and gene representations, while masked autoencoding reconstructs spatial locations and gene expression.

- 1차 검사: **supported**
- 근거로 든 문장: masked auto-encoding loss to improve reconstruction and robustness

- 판정:
- 메모:

**P0029** (paragraph, Masked-auto encoding.)

> We also train HEIST with a masked auto-encoding loss to improve reconstruction and robustness. By masking subsets of cell and gene nodes, the model learns to reconstruct gene expression and spatial coordinates from the remaining context, reflecting real-world challenges like dropout and noise in spatial transcriptomics. This encourages the model to infer missing data, generalize across datasets, and use gene signals to recover spatial context and spatial cues to predict gene expression. After reconstructing the spatial locations and gene-expression, the masked auto-encoding loss is calculated using equation below:

## 4. Key Results and Benchmarks

### 9. **Gene imputation**: HEIST achieves 82.1% Pearson correlation on placenta data (fine-tuned) and 80.7% on skin data, outperforming MAGIC (74.9%) and CellPLM (80.1%).

- 1차 검사: **supported**
- 근거로 든 문장: HEIST (Fine-tuned) | 0.821 ± 0.041 0.807 ± 0.020

- 판정:
- 메모:

**P0113** (table, Body)

> Table 1 : Model | Placenta | Skin MAGIC | 0.749 ± 0.000 0.671 ± 0.000 ScFoundation (Fine-tuned) 0.721 ± 0.004 0.621 ± 0.003 CellPLM (Fine-tuned) | 0.801 ± 0.011 0.723 ± 0.007 scGPT-spatial (Fine-tuned) 0.718 ± 0.002 0.740 ± 0.002 HEIST (Zero-Shot) | 0.574 ± 0.000 0.350 ± 0.000 HEIST (Fine-tuned) | 0.821 ± 0.041 0.807 ± 0.020 HEIST Imp. % | 2.49 | 9.05

### 10. **Clinical outcome prediction**: HEIST attains AUC-ROC of 0.995 on skin cancer datasets, surpassing SCGPT-spatial (0.984) and CellPLM (0.930).

- 1차 검사: **flagged** — cited elsewhere: 0.984 as 0.984, 0.930 as 0.930  (모델: not_in_paragraph)
- 근거로 든 문장: none

- 판정: 수치틀림
- 메모: 0.995는 논문에 있으나(P0100) 그것은 ligand-receptor pair 예측의 AUC-ROC이고 임상 결과 예측이 아님. 과제를 잘못 붙였으므로 단순 인용 오류가 아님.
- 판정자: 보조 (사람 확인 필요)

**P0100** (paragraph, PE ablation.)

> Ligand-receptor pair prediction. We train a linear probe to predict ligand-receptor (LR) interactions for all edges in the tissue graphs. For each model, we extract the cell embeddings, concatenate the embeddings of the two cells involved in a pair, and pass this concatenated representation through a simple single layer perceptron that predicts whether the pair corresponds to an LR interaction. As shown in the Table A9, HEIST achieves the highest AUC-ROC and outperforms all baselines by a clear margin. In particular, HEIST reaches an AUC-ROC of 0.995 ± 0.002. This result combined with the attention based results indicates that its embeddings capture the spatial signatures of LR communication more effectively than scFoundation, CellPLM, and scGPT-spatial.

### 11. **Cell type annotation**: HEIST achieves 99.5% F1 score on SEA-AD data, outperforming SCFoundation (0.2495) and CellPLM (0.6701).

- 1차 검사: **supported**
- 근거로 든 문장: HEIST | 0.5126 ± 0.1170 0.9953 ± 0.0158 0.5340 ± 0.1293 0.2826 ± 0.0758 0.1124 ± 0.0521

- 판정:
- 메모:

**P0115** (table, Body)

> Table 3 : Organ | Lung | Brain | Colon | Neck | Neck Model | | SEA-AD | Charville | UPMC | DFCI STAGATE | 0.2187 ± 0.0570 0.3304 ± 0.0625 0.2759 ± 0.0490 0.0687 ± 0.0136 0.0685 ± 0.0213 GraphST | 0.4081 ± 0.0658 0.2296 ± 0.1772 0.3675 ± 0.0873 0.0617 ± 0.0199 0.0577 ± 0.0261 ScFoundation | 0.150 ± 0.014 | 0.2495 ± 0.1147 0.3220 ± 0.1421 0.0222 ± 0.0079 | 0.041 ± 0.021 Novae | NEM | 0.2332 ± 0.0434 0.2194 ± 0.0455 | NEM | 0.0736 ± 0.0215 CellPLM (unaligned) | 0.5044 ± 0.1607 0.6701 ± 0.0827 0.4760 ± 0.0669 0.0563 ± 0.0212 0.0565 ± 0.0179 CellPLM (aligned) | - | - | 0.3047 ± 0.0040 0.0337 ± 0.0032 0.0413 ± 0.0015 scGPT-spatial (unaligned) 0.5671 ± 0.1685 0.5907 ± 0.0029 0.3494 ± 0.0624 0.0464 ± 0.0162 0.0618 ± 0.0163 scGPT-spatial (aligned) | - | - | 0.3280 ± 0.0499 0.2195 ± 0.0490 0.0953 ± 0.0190 HEIST | 0.5126 ± 0.1170 0.9953 ± 0.0158 0.5340 ± 0.1293 0.2826 ± 0.0758 0.1124 ± 0.0521 HEIST Imp. | -9.6 % | 48.5 | 12.2 | 28.7 | 17.9

### 12. **Computational efficiency**: HEIST is 8× faster than SCGPT-SPATIAL and 48× faster than SCFOUNDATION for embedding extraction.

- 1차 검사: **supported**
- 근거로 든 문장: HEIST demonstrates significant computational advantages, achieving 8× faster embedding extraction time compared to SCGPT-SPATIAL and 48× faster than SCFOUNDATION.

- 판정:
- 메모:

**P0032** (paragraph, Masked-auto encoding.)

> , where λ is a regularization weight, σ is sigmoid function to balance the loss terms, and γ is a learnable scalar that dynamically balances two terms. Computational efficiency. As shown in Table A4 in the Appendix, HEIST demonstrates significant computational advantages, achieving 8× faster embedding extraction time compared to SCGPT-SPATIAL and 48× faster than SCFOUNDATION. This efficiency comes from HEIST's sparse modeling, which avoids the expensive full self-attention computations required by transformer based models like SCGPT-SPATIAL.

## 5. Limitations and Future Work

### 13. **Limitations**: HEIST relies on mutual information for gene co-expression networks, which may not capture causal relationships. It also assumes static spatial snapshots, lacking temporal dynamics.

- 1차 검사: **supported**
- 근거로 든 문장: the current gene co-expression network construction relies on co-expression relationships using mutual information, which may not fully capture causal gene co-expression mechanisms or directional influences

- 판정:
- 메모:

**P0105** (paragraph, F LIMITATIONS)

> While HEIST advances the state of foundation models for spatial transcriptomics (ST), it has several limitations. First, the current gene co-expression network construction relies on co-expression relationships using mutual information, which may not fully capture causal gene co-expression mechanisms or directional influences. This can be integrated by more sophisticated MI meassures like DREMI (Krishnaswamy et al., 2014). Furthermore, integrating more sophisticated gene co-expression network inference techniques could improve the biological interpretability and efficiency of gene embeddings. A potential direction for future work can be incorporating temporal dynamics by applying techniques such as Granger causality (Tong et al., 2023) over inferred pseudotime trajectories, allowing the model to capture not only static spatial and co-expression dependencies but also directional gene co-expression influence and developmental progression, which are currently not modeled in HEIST. Second, the model assumes static spatial snapshots of tissues and does not account for temporal dynamics or developmental trajectories, which are critical in understanding certain biological processes. Extending HEIST to model spatio-temporal transcriptomics data is an important direction for future work. Finally, while HEIST improves computational efficiency over prior foundation models, it still requires substantial computational resources for large-scale pretraining. Despite these limitations, HEIST provides a flexible and scalable foundation for modeling complex spatial and molecular interactions, and future work can address these challenges to further improve its generalization and interpretability.

### 14. **Future work**: Incorporating temporal dynamics via Granger causality over pseudotime trajectories, improving gene co-expression network inference, and extending to spatio-temporal transcriptomics.

- 1차 검사: **flagged** — the quoted support is not in the paragraphs  (모델: supported)
- 근거로 든 문장: incorporating temporal dynamics by applying techniques such as Granger causality over inferred pseudotime trajectories

- 판정: 맞음
- 메모: P0105 전문에 세 요소가 모두 있음: 'Granger causality ... over inferred pseudotime trajectories', 'integrating more sophisticated gene co-expression network inference techniques', 'Extending HEIST to model spatio-temporal transcriptomics data'. 1차 검사의 인용문 축자 실패.
- 판정자: 보조 (사람 확인 필요)

**P0105** (paragraph, F LIMITATIONS)

> While HEIST advances the state of foundation models for spatial transcriptomics (ST), it has several limitations. First, the current gene co-expression network construction relies on co-expression relationships using mutual information, which may not fully capture causal gene co-expression mechanisms or directional influences. This can be integrated by more sophisticated MI meassures like DREMI (Krishnaswamy et al., 2014). Furthermore, integrating more sophisticated gene co-expression network inference techniques could improve the biological interpretability and efficiency of gene embeddings. A potential direction for future work can be incorporating temporal dynamics by applying techniques such as Granger causality (Tong et al., 2023) over inferred pseudotime trajectories, allowing the model to capture not only static spatial and co-expression dependencies but also directional gene co-expression influence and developmental progression, which are currently not modeled in HEIST. Second, the model assumes static spatial snapshots of tissues and does not account for temporal dynamics or developmental trajectories, which are critical in understanding certain biological processes. Extending HEIST to model spatio-temporal transcriptomics data is an important direction for future work. Finally, while HEIST improves computational efficiency over prior foundation models, it still requires substantial computational resources for large-scale pretraining. Despite these limitations, HEIST provides a flexible and scalable foundation for modeling complex spatial and molecular interactions, and future work can address these challenges to further improve its generalization and interpretability.

