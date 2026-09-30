# 검토표: kalfon-2025-scprint-pre-training-on-50-million

- 논문: scPRINT: pre-training on 50 million cells allows robust gene network predictions
- 학술지·연도: Nature Communications 2025  (출처 openalex, DOI 10.1038/s41467-025-58699-1)
- 노트 revision: `ad82a9d8d821497388b004cf32d9ffda`  sha256 `4917825be543ff1b`
- 추출: partial, 블록 241개, 생성 경로 chunked, 제시 241/241
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

### 1. **Superior GN inference**: scPRINT outperforms state-of-the-art methods like scGPT, GENIE3, and Geneformer v2 on most atlas-level tasks, including recovering 67% more connections than GENIE3 and 42% more than scGPT.

- 1차 검사: **supported**
- 근거로 든 문장: scGPT and scPRINT respectively recover 42% and 67% more connections than GENIE3

- 판정:
- 메모:

**P0005** (paragraph, Body)

> We extensively benchmark scPRINT on challenging GN inference tasks, from literature-based networks to cell type-specific ones generated via orthogonal sequencing methods. We show that scPRINT outperforms the state of the art on most of these atlas-level benchmarks. In addition, our model focused on GN inference, is also competitive on a compendium of tasks like denoising, cell type prediction, and embedding with batch effect correction. This suggests that by learning a cell model, scPRINT gains zero-shot abilities in many tasks of cellular biology.

**P0033** (paragraph, scPRINT recovers biological features in its gene networks)

> AUPRC results are very low overall because we do not expect most Omnipath connections to be present in the cell type's gene network, as many connections in Omnipath might only be true in some cellular contexts. Moreover, we do not expect most connections in our generated network to exist in Omnipath as it only contains a small fraction of all real gene-gene connections. Although overall AUPRC values are small, we can see that both scGPT and scPRINT outperform the other methods in the number of connections recovered. Indeed, on average, scGPT and scPRINT respectively recover 42% and 67% more connections than GENIE3.

### 2. **Zero-shot capabilities**: scPRINT achieves zero-shot predictions for denoising, batch correction, and cell type annotation without fine-tuning, leveraging pre-trained cell models.

- 1차 검사: **supported**
- 근거로 든 문장: This suggests that by learning a cell model, scPRINT gains zero-shot abilities in many tasks of cellular biology.

- 판정:
- 메모:

**P0004** (paragraph, Body)

> Inspired by these efforts, we propose scPRINT, a foundation model designed for GN inference. scPRINT brings inductive biases and pretraining strategies better suited to GN inference while answering issues in current models (see Table S1). scPrint outputs cell typespecific genome-wide gene networks but also generates predictions on many related tasks, such as cell annotations, batch effect correction, and denoising, without fine-tuning.

**P0005** (paragraph, Body)

> We extensively benchmark scPRINT on challenging GN inference tasks, from literature-based networks to cell type-specific ones generated via orthogonal sequencing methods. We show that scPRINT outperforms the state of the art on most of these atlas-level benchmarks. In addition, our model focused on GN inference, is also competitive on a compendium of tasks like denoising, cell type prediction, and embedding with batch effect correction. This suggests that by learning a cell model, scPRINT gains zero-shot abilities in many tasks of cellular biology.

### 3. **Biological insights**: scPRINT identifies connections between ion exchange, senescence, and chronic inflammation in BPH, including novel pathways like oxidative stress response and metal/ion exchange in fibroblast networks.

- 1차 검사: **supported**
- 근거로 든 문장: We find key interconnected pathways of the oxidative stress response and extracellular matrix building via metal and ion exchange in the gene network of BPH-associated fibroblasts.

- 판정:
- 메모:

**P0001** (paragraph, Body)

> A cell is governed by the interaction of myriads of macromolecules. Inferring such a network of interactions has remained an elusive milestone in cellular biology. Building on recent advances in large foundation models and their ability to learn without supervision, we present scPRINT, a large cell model for the inference of gene networks pre-trained on more than 50 million cells from the cellxgene database. Using innovative pretraining tasks and model architecture, scPRINT pushes large transformer models towards more interpretability and usability when uncovering the complex biology of the cell. Based on our atlas-level benchmarks, scPRINT demonstrates superior performance in gene network inference to the state of the art, as well as competitive zero-shot abilities in denoising, batch effect correction, and cell label prediction. On an atlas of benign prostatic hyperplasia, scPRINT highlights the profound connections between ion exchange, senescence, and chronic inflammation.

**P0006** (paragraph, Body)

> We use scPRINT to analyze an atlas of normal and senescent prostate tissues where we identify rare cell populations with early markers of the tumor microenvironment in B-cells. In fibroblasts, we study GNs and recover known hubs such as PAGE4, linking the senescence of fibroblasts to changes in the ECM and downstream inflammation. We find key interconnected pathways of the oxidative stress response and extracellular matrix building via metal and ion exchange in the gene network of BPH-associated fibroblasts. We also show that healthy and diseaserelated cells exhibit different network patterns, demonstrating that scPRINT can help identify novel pathways and targets while considering them in their specific cellular and molecular contexts.

### 4. **Scalability**: scPRINT generates genome-wide gene networks for 1–10,000 cells using commodity hardware, with disentangled embeddings for cell type, disease, and other attributes.

- 1차 검사: **supported**
- 근거로 든 문장: compute attention heads-based gene networks for 1 to 10,000 cells, at the genome scale, with commodity hardware and in a few minutes

- 판정:
- 메모:

**P0022** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> As shown in Fig. 1C, at inference time, scPRINT can generate multiple outputs across any scRNA-seq-like cellular profile of various mammalian species without the need for fine-tuning. Figure 1D shows scPRINT's prediction at the scale of an atlas of 2 M randomly sampled cells from cellxgene. A critical emergent output of scPRINT is its cell-specific gene networks. Following a similar approach to ESM2, we generate cell-level gene networks via the bidirectional transformer's input-wise weighted matrices, called attention matrices -or heads-. They represent general gene-gene connections and can be subsetted to TF-gene connections (i.e., GRNs). Remarkably, we made this approach scalable enough to compute attention heads-based gene networks for 1 to 10,000 cells, at the genome scale, with commodity hardware and in a few minutes. These networks both showcase the ability of scPRINT to model cellular biology and help make it a more explainable tool for the community, showing the network assumptions made during inference. The attention heads are either all aggregated by averaging or can be selected to better reflect connections of interest (Fig. 1C). This is done using the average of the heads most correlated with literature or perturbation-based ground truth networks. Finally, while we do not assess scPRINT's ability to model inhibition due to the scarcity of such annotations, we leave open the possibility of using our head selection technique for such a task.

**P0014** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> Finally, the cell's gene network should represent the cell state and its different phenotypic facets. Effectively, scPRINT generates not just one embedding per cell but multiple. A hierarchical classifier is then applied to each distinct cell embedding to predict its associated class, such as cell type, disease, sex, organism, ethnicity, and sequencing platform. The embeddings thus become disentangled, each representing a specific facet of the cell state 42 . This last training task pushes the large cell model and its gene network to represent the cell state 42 .

## 3. Methodology and Architecture

### 5. **Pre-training tasks**: scPRINT learns gene connections via denoising, bottleneck learning, and label prediction, using flashattention2 for efficiency on 50 million cells (~80 billion tokens).

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT pre-training tasks: denoising task whose goal is to recover the known transcriptomic profile from a purposefully downsampled expression profile. Bottleneck learning reconstructs the expression of requested genes using only their cell embedding.

- 판정:
- 메모:

**P0008** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> We propose scPRINT (single-cell PRe-trained Inference of Networks with Transformers, Fig. 1A), a state-of-the-art bidirectional transformer designed for cell-specific gene network (GN) inference at the scale of the genome. scPRINT is trained with a custom weighted-randomsampling method 37 over 50 million cells from the cellxgene 34 database from multiple species, diseases, and ethnicities, representing around 80 billion tokens (see Methods). We train scPRINT at various scales Fig. 1 | presentation of the scPRINT model and training. A Schematic representation of scPRINT with its bidirectional encoder, gene expression embedding, gene location encoding, matched ESM2 protein embedding, and gene expression decoder. B scPRINT pre-training tasks: denoising task whose goal is to recover the known transcriptomic profile from a purposefully downsampled expression profile. Bottleneck learning reconstructs the expression of requested genes using only their cell embedding. The same model is used for both The encoding and decoding steps. Classification is achieved by applying a hierarchical classifier to each disentangled embedding. This pushes the first embedding to contain cell type information, the second embedding to contain disease info, and so on (see methods). C The different outputs in scPRINT. scPRINT generates label predictions of cell type, tissue, disease, sex, sequencer, ethnicity, and organism. scPRINT generates multiple embeddings (which we call disentangled embedding), a general one, as well as a specific embedding for each class. scPRINT also generates a reconstructed expression profile at any requested sequencing depth (i.e., total transcript count). scPRINT also generates a Gene Network by selecting and combining various attention heads into a gene by gene matrix. D Example of a scPRINT output from a random subset of 2.5 million cells from the cellxgene database. (from 2 M to 100 M parameters) and very efficiently by using flashattention2 38 , e.g., only requiring an A40 GPU for 48 h to train our medium model, significantly reducing the barrier to entry for any computational biology lab (see Table S2).

**P0010** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> scPRINT's pretraining is composed of three tasks which loss are added and optimized together: a denoising task, a bottleneck learning task, and a label prediction task. The objective is to let scPRINT learn to represent meaningful gene connections while also endowing it with a breadth of zero-shot prediction abilities.

### 6. **Gene embeddings**: Gene expression is encoded using ESM2 protein embeddings, genomic location (positional encoding), and log-normalized counts.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT encodes the gene IDs using protein embeddings.

- 판정:
- 메모:

**P0016** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> scPRINT converts the gene expression of a cell to an embedding by summing three representations or tokens: its id, expression, and genomic location (Fig. 1A, see Methods). scPRINT encodes the gene IDs using protein embeddings. This gene representation is made using the ESM2 43 amino-acid embedding of its most common protein product (see Supp Fig. S1). First proposed in UCE 44 , the model learns to leverage representations that can potentially apply to unseen genes and species, using the structural and evolutionary conservation of the sequence encoded by ESM2. While drastically reducing the number of weights trained for the model compared to scGPT and Geneformer (see Methods), this representation also contains some priors needed to infer protein-protein 45 interactions (Fig. 1A).

**P0017** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> The gene's expression is tokenized via a multi-layer perceptron (MLP) using log-normalized counts. This MLP lets the model learn a metric behind gene expression, whereas scGPT and Geneformer apply a specific prior for the encoding of their gene expression (see Methods).

**P0018** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> Finally, we help the model know that genes with similar locations tend to be regulated by identical DNA regions, using the positional encoding of their location in the genome (see Methods).

### 7. **Input structure**: Input matrices combine gene embeddings and cell placeholders for transformer processing, with 2200 expressed genes per cell profile.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT is pretrained using 2200 randomly selected expressed genes in a cell profile.

- 판정:
- 메모:

**P0019** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> These three embeddings are summed and then concatenated across the genes expressed in a cell together with additional placeholder cell embeddings to form the transformer model's input matrix.

**P0020** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> scPRINT is pretrained using 2200 randomly selected expressed genes in a cell profile. If a cell doesn't have enough expressed genes, the list is padded with randomly selected unexpressed genes. A context of 2200 genes, while not genome-wide, captures all the expressed genes in more than 80% of the cell profiles in the cellxgene database. We also show that scPRINT can make predictions on much larger sequences of genes at inference time without using attention approximation methods 46 .

### 8. **Attention mechanisms**: Gene-gene and TF-gene connections are inferred via bidirectional transformer input-wise weighted matrices (attention matrices), with heads selected for Omnipath or Han et al. ground truth.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT (omnipath's heads), based on the average of heads selected with our abovementioned head selection method inspired by ESM2

- 판정:
- 메모:

**P0022** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> As shown in Fig. 1C, at inference time, scPRINT can generate multiple outputs across any scRNA-seq-like cellular profile of various mammalian species without the need for fine-tuning. Figure 1D shows scPRINT's prediction at the scale of an atlas of 2 M randomly sampled cells from cellxgene. A critical emergent output of scPRINT is its cell-specific gene networks. Following a similar approach to ESM2, we generate cell-level gene networks via the bidirectional transformer's input-wise weighted matrices, called attention matrices -or heads-. They represent general gene-gene connections and can be subsetted to TF-gene connections (i.e., GRNs). Remarkably, we made this approach scalable enough to compute attention heads-based gene networks for 1 to 10,000 cells, at the genome scale, with commodity hardware and in a few minutes. These networks both showcase the ability of scPRINT to model cellular biology and help make it a more explainable tool for the community, showing the network assumptions made during inference. The attention heads are either all aggregated by averaging or can be selected to better reflect connections of interest (Fig. 1C). This is done using the average of the heads most correlated with literature or perturbation-based ground truth networks. Finally, while we do not assess scPRINT's ability to model inhibition due to the scarcity of such annotations, we leave open the possibility of using our head selection technique for such a task.

**P0030** (paragraph, scPRINT recovers biological features in its gene networks)

> For scPRINT, we generate three network versions: one simply called scPRINT, based on the average of all heads in the model. scPRINT (omnipath's heads), based on the average of heads selected with our abovementioned head selection method inspired by ESM2, and scPRINT (genome), which is like the scPRINT network but uses our method to generate genome-wide networks (see Methods) instead of using the 5000 most differentially expressed genes. Indeed, in transformer models, the choice of attention heads is important. Although transformers can learn the causal structure of their input, it has been shown that some attention heads, especially in larger networks, can become unused, containing predominantly random connections 62 . Some work has been done at pruning these heads 63 or forcing a head selection mechanism at inference and training 64 . For scPRINT (omnipath's heads), we select heads based on a linear classifier's prediction of the best set of heads to predict a subset of Omnipath (see Methods). Similarly to the scPRINT network, these heads are then averaged to generate the scPRINT (omnipath's heads) gene network. To perform this selection, we split the omnipath dataset into train/test and select heads, using 50% of the ground truth and only the first cell type of each dataset. We then use the same combination of heads across all other cell types. This shows that our selection process builds consistent networks across cell types and parts of the ground truth. This approach contrasts with previous ones like scGPT's and GENIE3 by using part of an available ground truth to select heads.

### 9. **Expression decoding**: A zero-inflated negative binomial (ZiNB) model predicts gene expression from embeddings, with parameters μ, θ, and π derived from an MLP.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT uses a novel expression decoder for foundation models, which outputs the parameters of a zero-inflated negative binomial (ZiNB) function for each gene j in cell i.

- 판정:
- 메모:

**P0021** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> Using unexpressed genes, combined with the denoising task, let scPRINT discriminate the true zeros from dropouts in scRNAseq 47 . The expression decoder of scPRINT further helps model this statistic of the data. It is a zero-inflated negative binomial graphical model inspired by previous literature in single-cell RNAseq modeling 48 . Here, the loss (also used for bottleneck learning) is thus the negative log-likelihood of the gene expression given the distribution parameters.

**P0106** (paragraph, Model.)

> Expression decoder. scPRINT uses a novel expression decoder for foundation models, which outputs the parameters of a zero-inflated negative binomial (ZiNB) function for each gene j in cell i. The ZiNB distribution is defined as

## 4. Key Results and Benchmarks

### 10. **Benchmark performance**: scPRINT outperforms scGPT, GENIE3, and Geneformer v2 on MCalla and gwps datasets, achieving higher AUPRC and EPR metrics (e.g., 20% ENCODE TF-target enrichment vs. no enrichment in scGPT).

- 1차 검사: **supported**
- 근거로 든 문장: In the scPRINT networks, 20% of the Transcription Factors for which we have data on ENCODE have connections significantly enriched for their ENCODE-validated gene targets

- 판정:
- 메모:

**P0044** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> Based on both AUPRC and EPR, scPRINT outperforms all other methods on this benchmark (Fig. 3B). This means, for example, that when training GENIE3 to only predict a gene's expression based on TF expressions, it is not selecting the right TFs amongst the set of a few dozen assessed in MCalla et al.

**P0037** (paragraph, scPRINT recovers biological features in its gene networks)

> Finally, we also examine how much the connections of each TF are enriched for that TF's target. Here, scPRINT overperforms all other methods (Fig. 2D). In the scPRINT networks, 20% of the Transcription Factors for which we have data on ENCODE have connections significantly enriched for their ENCODE-validated gene targets 66 . Interestingly, only our large cell model achieved a great performance, and scGPT did not display any enrichment across the 26 cell types assessed. While we acknowledge that ENCODE is used in the Omnipath database, we cannot expect Omnipath to represent the ENCODE targets. Indeed, it combines and processes 57 additional data sources to build its consensus network.

**P0049** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> GENIE3 performs best, directly followed by scPRINT. Interestingly, Geneformer v2 shows poor performance (Fig. 3C). Perturbation experiments are known to correlate somewhat to expression correlation, and this might explain GENIE3's strong performance. However, when using our head selection mechanism, scPRINT (gwps' heads) outperforms GENIE3. Again in this dataset, selecting heads based on Omnipath does not help; the small overlap between the gwps network and the Omnipath ground truth network seems likely to be the culprit (see Table S7). These overlaps show that the three ground truth networks are very different and that a different set of heads predicts each type of ground truth. We also assess the networks on the TF-gene only subset of the gwps ground truth. Here, we see a large drop in performances for most methods, except GENIE3 (see Supp. Fig. S4).

### 11. **Denoising**: scPRINT competes with MAGIC and KNNsmoothing2 on Spearman correlation, excelling in rare cell states like pericytes and microglial cells.

- 1차 검사: **supported**
- 근거로 든 문장: We show that since scPRINT does not aggregate profiles over neighboring cells, it outperforms MAGIC and KNNsmoothing2 in rare cell states subsets of the datasets (respectively: pericytes, microfold cells of epithelium of small intestine and microglial cells) with around 10 to 200 cells

- 판정:
- 메모:

**P0053** (paragraph, scPRINT is competitive on tasks orthogonal to GN inference)

> Similarly to our pretraining task, we simulate lower transcript count profiles and then ask scPRINT and two other state-of-the-art methods, MAGIC 72 and KNNsmoothing2 73 , to recreate the true expression profile. We use Spearman correlation to the original gene expression profile as our metric. In Fig. 4A, we show the increase in correlation after denoising the downsampled profile on 3 test set datasets, composed of ciliary body, colon, and retina tissues 58,74,75 , randomly selected from cellxgene (see Methods).

**P0054** (paragraph, scPRINT is competitive on tasks orthogonal to GN inference)

> scPRINT is competitive with both SOTA methods, while contrary to MAGIC and KNNSmoothing2, it operates independently over each cell in the test set (see Methods). We have also seen a 10% variability in denoising ability across the different datasets used (see Table S10). This was similar across all tools and possibly related to the number of genes expressed in each dataset. However, these test cases mostly contain very similar cell states, whereas denoising is helpful in cases with rare cell types or transitory cell states that have low cell counts by default. We show that since scPRINT does not aggregate profiles over neighboring cells, it outperforms MAGIC and KNNsmoothing2 in rare cell states subsets of the datasets (respectively: pericytes, microfold cells of epithelium of small intestine and microglial cells) with around 10 to 200 cells (Fig. 4A, Supp Fig. S5). Computing MAGIC and KNNsmoothing2 over only this rare cell population gives even lower performances for MAGIC and creates an error for KNNsmoothing2 (see Table S10). These results suggest that a good cell model, that has learned reliable gene-gene interactions, can help denoise an expression profile.

### 12. **Cell type prediction**: scPRINT achieves 62% accuracy (vs. CellTypist’s 70%) using zero-shot prediction, predicting >200 cell types.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT also makes predictions over >200 cell type labels

- 판정:
- 메모:

**P0056** (paragraph, scPRINT is competitive on tasks orthogonal to GN inference)

> scPRINT is a zero-shot predictor of cell labels. Indeed, it does not need to train on the dataset itself to make its predictions, unlike other methods that often need to use >70% of the test dataset for training. scPRINT also makes predictions over >200 cell type labels, while other methods often only predict a few cell types. Conversely, the other classifier methods, like Logistic Regression or XGBoost, and previous foundation models are trained or fine-tuned on the test dataset, thus giving a strong advantage over scPRINT. We, therefore, also compare scPRINT to the marker-based classifier CellTypist 78 and its pancreas marker database (see Methods). A method that also does not use the labels of the test dataset.

**P0057** (paragraph, scPRINT is competitive on tasks orthogonal to GN inference)

> In this benchmark, scPRINT reaches 62% classification accuracy, largely outperforming CellTypist (Fig. 4B, Supp Fig. S6). Interestingly, with the macro F1 score, which considers each cell type group equally regardless of its size, scPRINT achieves similar results to the state-ofthe-art 77 methods: Logistic Regression and XGBoost. This is probably because scPRINT is not influenced by the number of cells in each category.

### 13. **Batch correction**: scPRINT’s embeddings match state-of-the-art methods in preserving biological information and removing batch effects.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT cell embeddings preserve biological information competitively to state-of-the-art methods

- 판정:
- 메모:

**P0059** (paragraph, scPRINT is competitive on tasks orthogonal to GN inference)

> Here, we have shown the accuracy of scPRINT independently of cell neighborhood. However, like gene marker-based methods, scPRINT can annotate cell types in novel datasets. In this context, its predictions could be smoothed and improved using majority voting over predefined cell clusters. Finally, scPRINT predictions are given as probability vector overall cell type labels. They can be used to display the top K labels and learn about the model's uncertainty. Thanks to its disentangled embeddings, scPRINT can also generate cell representations that partially remove batch effects from cell profiles. On the human pancreas and lung datasets of openproblem 79 , we see that, based on the scIB metrics, scPRINT shows convincing batch effects removal ability, while not on par with the SOTA methods scGEN and scVI (Fig. 4C, Supp Fig. S7). Concerning foundation models, scPRINT and scFoundation show strong zero-shot performances compared to Geneformer v2 and scGPT. Except for Geneformer v2, scGPT, and scFoundation, we did not rerun previous algorithms for this benchmark and show their performances from the openproblems portal 77 (open-problems-v2.3.6, march 2024). However, we also ran the Geneformer v2 and scGPT foundation models on the openproblems benchmark and showed that without fine tuning on this specific dataset, they are not able to meaningfully correct for batch effect (see Methods).

**P0060** (paragraph, scPRINT is competitive on tasks orthogonal to GN inference)

> Moreover, scPRINT is one of the few methods that do not train on the test dataset and do not use already annotated batch labels. When only looking at methods that do not use batch labels as prior information, e.g. SAUCIE 80 , LIGER 81 , scPRINT is the top performer. We have also noticed that the scPRINT cell embeddings preserve biological information competitively to state-of-the-art methods (Fig. 4D, Supp Fig. S8). This also exemplifies that a reliable cell model can perform well at disentangling the different facets of a cell expression profile and its underlying batch effect.

### 14. **Network validation**: scPRINT networks align with Omnipath and perturb-seq ground truths, enriched for cell-type markers and TFs.

- 1차 검사: **supported**
- 근거로 든 문장: scPRINT also predicts networks that agree with the Omnipath ground truth and are again enriched for cell type markers and TFs

- 판정:
- 메모:

**P0050** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> Finally, we have seen that on both MCalla and gwps, scPRINT also predicts networks that agree with the Omnipath ground truth and are again enriched for cell type markers and TFs (see Tables S8, S9).

**P0040** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> Although we have shown that our networks represent meaningful biology, the Omnipath ground truth is literature-based and not cell type-specific. Here, we use two different modalities, perturb-seq 67 , and ChIP-seq 68 , as ground truths to compare predicted gene networks against.

## 5. Limitations and Future Work

### 15. **Inhibition modeling**: scPRINT does not assess inhibition due to scarce annotations.

- 1차 검사: **not_in_paragraph**
- 근거로 든 문장: none

- 판정: 맞음
- 메모: 인용 문단 P0022의 마지막 문장에 그대로 있음: 'while we do not assess scPRINT's ability to model inhibition due to the scarcity of such annotations'. 1차 검사의 거짓 누락.
- 판정자: 보조 (사람 확인 필요)

**P0022** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> As shown in Fig. 1C, at inference time, scPRINT can generate multiple outputs across any scRNA-seq-like cellular profile of various mammalian species without the need for fine-tuning. Figure 1D shows scPRINT's prediction at the scale of an atlas of 2 M randomly sampled cells from cellxgene. A critical emergent output of scPRINT is its cell-specific gene networks. Following a similar approach to ESM2, we generate cell-level gene networks via the bidirectional transformer's input-wise weighted matrices, called attention matrices -or heads-. They represent general gene-gene connections and can be subsetted to TF-gene connections (i.e., GRNs). Remarkably, we made this approach scalable enough to compute attention heads-based gene networks for 1 to 10,000 cells, at the genome scale, with commodity hardware and in a few minutes. These networks both showcase the ability of scPRINT to model cellular biology and help make it a more explainable tool for the community, showing the network assumptions made during inference. The attention heads are either all aggregated by averaging or can be selected to better reflect connections of interest (Fig. 1C). This is done using the average of the heads most correlated with literature or perturbation-based ground truth networks. Finally, while we do not assess scPRINT's ability to model inhibition due to the scarcity of such annotations, we leave open the possibility of using our head selection technique for such a task.

### 16. **Imbalanced data**: Performance on MCalla et al. dataset is limited by high imbalances and small cell counts.

- 1차 검사: **supported**
- 근거로 든 문장: the high data imbalance (i.e., TFs being not connected or highly connected) combined with the small dataset size (i.e., only a few dozen TFs assessed) and the low number of cells make the results in MCalla et al. very variable

- 판정:
- 메모:

**P0047** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> This shows that scPRINT can better decipher direct from indirect TF-gene connections than scGPT, DeepSEM, Geneformer v2, and GENIE3, although more tests would likely be needed. However, the results also highlight that the high data imbalance (i.e., TFs being not connected or highly connected) combined with the small dataset size (i.e., only a few dozen TFs assessed) and the low number of cells make the results in MCalla et al. very variable. Some of this might be true biology or explained by ChIP-seq, which can be very noisy depending on the quality of its antibodies 70 .

### 17. **Head selection**: Omnipath-based head selection shows marginal gains, while ground-truth-based selection improves performance.

- 1차 검사: **supported**
- 근거로 든 문장: selecting heads based on the ground truth itself, only using 50% of the connections available, shows substantial improvement.

- 판정:
- 메모:

**P0036** (paragraph, scPRINT recovers biological features in its gene networks)

> We also expect biologically meaningful gene networks to have their central nodes enriched for TFs. In addition, because these networks are cell type-specific, we expect their central nodes to be enriched for some marker genes of their associated cell types (see Methods). In this regard, both scGPT and scPRINT achieve very similar and strong network enrichment for TFs compared to GENIE3, DeepSEM, and Geneformer v2, whose networks are not enriched for TFs (Fig. 2C). Moreover, amongst the 178 cell types we have marker gene sets for in pangaloDB 65 , all methods find some enrichments, especially GENIE3 and scGPT (see Methods). We notice that selecting heads based on Omnipath significantly improves scPRINT's network enrichment for cell-type markers. Of note, our goal is not to annotate cell types from the gene network but mainly to showcase the network's cell type specificity.

**P0046** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> It also appeared that selecting heads based on Omnipath, although helping slightly in one instance, is not a net benefit for this dataset (see Table S9). This makes sense since MCalla et al. itself does not overlap much with Omnipath (see Table S7). However, selecting heads based on the ground truth itself, only using 50% of the connections available, shows substantial improvement. These same heads also show reliable behavior when using them on the second dataset and ground truth of the same species.

### 18. **Future work**: Improve head selection for imbalanced datasets, validate inhibition pathways, and expand to other species.

- 1차 검사: **supported**
- 근거로 든 문장: Finally, while we do not assess scPRINT's ability to model inhibition due to the scarcity of such annotations, we leave open the possibility of using our head selection technique for such a task.

- 판정:
- 메모:

**P0022** (paragraph, scPRINT: a scRNAseq foundation model for gene network inference)

> As shown in Fig. 1C, at inference time, scPRINT can generate multiple outputs across any scRNA-seq-like cellular profile of various mammalian species without the need for fine-tuning. Figure 1D shows scPRINT's prediction at the scale of an atlas of 2 M randomly sampled cells from cellxgene. A critical emergent output of scPRINT is its cell-specific gene networks. Following a similar approach to ESM2, we generate cell-level gene networks via the bidirectional transformer's input-wise weighted matrices, called attention matrices -or heads-. They represent general gene-gene connections and can be subsetted to TF-gene connections (i.e., GRNs). Remarkably, we made this approach scalable enough to compute attention heads-based gene networks for 1 to 10,000 cells, at the genome scale, with commodity hardware and in a few minutes. These networks both showcase the ability of scPRINT to model cellular biology and help make it a more explainable tool for the community, showing the network assumptions made during inference. The attention heads are either all aggregated by averaging or can be selected to better reflect connections of interest (Fig. 1C). This is done using the average of the heads most correlated with literature or perturbation-based ground truth networks. Finally, while we do not assess scPRINT's ability to model inhibition due to the scarcity of such annotations, we leave open the possibility of using our head selection technique for such a task.

**P0047** (paragraph, scPRINT outperforms the state of the art on cell type-specific ground truths)

> This shows that scPRINT can better decipher direct from indirect TF-gene connections than scGPT, DeepSEM, Geneformer v2, and GENIE3, although more tests would likely be needed. However, the results also highlight that the high data imbalance (i.e., TFs being not connected or highly connected) combined with the small dataset size (i.e., only a few dozen TFs assessed) and the low number of cells make the results in MCalla et al. very variable. Some of this might be true biology or explained by ChIP-seq, which can be very noisy depending on the quality of its antibodies 70 .

