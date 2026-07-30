---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:3952
- loss:MultipleNegativesRankingLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: A tread for a heavy truck tire that has a rib is provided. A sipe
    is located in the rib and extends from a first lateral surface to a second lateral
    surface. A first end of a teardrop of the sipe is located at the first lateral
    surface, and a second end is at the second lateral surface. A middle section is
    located between the first and second ends, and a lateral midpoint of the teardrop
    is located at the middle section. A cross-section of the middle section at the
    lateral midpoint is greater in size than a cross-section of the first end. The
    cross-section of the middle section at the lateral midpoint is greater in size
    than a cross-section of the second end.
  sentences:
  - 3 . The trumpet arm of claim 1 , wherein a cross section of the arm section is
    a box, a rectangle, a circle, an oval, an hourglass, or a combination of two or
    more of the aforementioned shapes.
  - wherein the first end farthest point of extension, the second end farthest point
    of extension, and the middle section farthest point of extension are all the same
    distance from the upper surface in the thickness direction.
  - wherein the first end is operably coupled to the center lug member proximate to
    an axis of rotation of the center lug member and the second end is disposed radially
    outward from the axis by a distance substantially equal to a length of the lever
    arm.
- source_sentence: Disclosed is a wheel assembly including a wheel portion, and optionally,
    a hub portion transmitting driving force transmitted through a drive shaft to
    the wheel portion. The wheel portion further includes a wheel flange portion connected
    to the hub portion, and the wheel flange portion includes a foreign matter discharge
    portion having a first discharge surface and a second discharge surface indented
    in different directions on an inner side surface.
  sentences:
  - the tire is a bicycle tire for operation with a tube.
  - the first discharge surface is provided along the inner side surface of the wheel
    flange portion, and the second discharge surface is provided along an inner side
    surface of the hubcap coupling portion.
  - 5 . The work vehicle of claim 4 , wherein the locking pin is movable relative
    to the plunger over a free travel distance, wherein the free travel distance allows
    the latching solenoid to hold the plunger in the extended orientation when the
    pivoting support is not oriented in the predetermined rotation angle.
- source_sentence: A car tyre ( 100 ), in particular a high or ultra high performance
    car tyre also suitable for use on track, is described; the tread band ( 1 ) of
    the tyre has a central region (L 1 ), separated from two shoulder regions (L 2
    , L 3 ), respectively an outer shoulder region (L 2 ) and inner shoulder region
    (L 3 ); the outer shoulder region (L 2 ) has a width greater than the width of
    the inner shoulder region (L 3 ); the outer and inner shoulder regions are provided
    with relatively large grooves ( 5,6 ); in the outer shoulder region these grooves
    ( 5 ) alternate with narrower grooves ( 7 ), which reduce the stiffness of this
    tyre region only to a limited extend; the central region (L 1 ) of the tyre, instead,
    was designed so as to have a low void-to-rubber ratio of equal to or smaller than
    0.09.
  sentences:
  - 3 . A rim for a wheel according to claim 2 , wherein a second plurality of layers
    of structural fibres is the of the same or greater thickness than the thickness
    of the first plurality of layers.
  - 1 - 35 . (canceled)
  - wherein the or each sidewall insert (
- source_sentence: A vehicle wheel cover is provided. The vehicle wheel cover includes
    a base, and a printed layer formed at a first location of the base. The printed
    layer is formed from a plurality of layers of images, such that, at least a first
    layer of the plurality of layers is located at a first depth from other layers
    of the plurality of layers. The vehicle wheel cover further includes a plurality
    of brake cooling holes that is formed as a pattern at a second location of the
    base. The second location is different from the first location. Based on a movement
    and an illumination of the vehicle wheel cover, the printed layer forms a three-dimensional
    graphic image.
  sentences:
  - 20 . The tyre according to claim 18 , wherein the central annular sector is made
    of a vulcanized elastomeric material having static elastic modulus Ca3 measured
    at 70° C. greater than a static elastic modulus Ca3 measured at 70° C. of the
    vulcanized elastomeric material of the two lateral annular sectors.
  - 6 . The wheel cover of claim 5 , wherein the shaft assembly is removably attached
    to the disc via at least one screw.
  - at least a second layer of the plurality of layers is disposed at a second depth
    from the other layers of the plurality of layers, the second depth is different
    from the first depth, and the three-dimensional graphic image is formed based
    on the first depth and the second depth of the printed layer.
- source_sentence: A pneumatic tire including a center block row 21 provided in a
    center area of a tread surface 1 , wherein the center block row includes a plurality
    of center blocks 210 arranged along a tire circumferential direction, the plurality
    of center blocks includes a plurality of first center blocks 211 and a plurality
    of second center blocks 212 , the plurality of first center blocks and the plurality
    of second center blocks have polygonal shapes on the tread surface, the polygonal
    shape formed by each second center block has a same number of sides as, but a
    different shape than, the polygonal shape formed by each first center block, each
    first center block and each second center block has one or more sipes, and a number
    n of sipes included in each second center block is greater than a number m of
    sipes included in each first center block.
  sentences:
  - 3 . The system of claim 2 , wherein each the plurality of pawls include a groove
    for receiving the biasing member.
  - 8 . The tire of claim 1 , wherein the rubber composition comprises at least one
    selected from a group consisting of silicone, a silicone-based polyurethane, and
    a fluorine-based polyurethane.
  - 5 . The pneumatic tire according to claim 1 , wherein, on the tread surface, a
    total length of sipes per area in each first center block and a total length of
    sipes per area in each second center block are 0.02 to 0.20 mm/mm 2 .
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 256, 'do_lower_case': False, 'architecture': 'BertModel'})
  (1): Pooling({'word_embedding_dimension': 384, 'pooling_mode_cls_token': False, 'pooling_mode_mean_tokens': True, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
  (2): Normalize()
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'A pneumatic tire including a center block row 21 provided in a center area of a tread surface 1 , wherein the center block row includes a plurality of center blocks 210 arranged along a tire circumferential direction, the plurality of center blocks includes a plurality of first center blocks 211 and a plurality of second center blocks 212 , the plurality of first center blocks and the plurality of second center blocks have polygonal shapes on the tread surface, the polygonal shape formed by each second center block has a same number of sides as, but a different shape than, the polygonal shape formed by each first center block, each first center block and each second center block has one or more sipes, and a number n of sipes included in each second center block is greater than a number m of sipes included in each first center block.',
    '5 . The pneumatic tire according to claim 1 , wherein, on the tread surface, a total length of sipes per area in each first center block and a total length of sipes per area in each second center block are 0.02 to 0.20 mm/mm 2 .',
    '8 . The tire of claim 1 , wherein the rubber composition comprises at least one selected from a group consisting of silicone, a silicone-based polyurethane, and a fluorine-based polyurethane.',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.7061, 0.4631],
#         [0.7061, 1.0000, 0.4228],
#         [0.4631, 0.4228, 1.0000]])
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 3,952 training samples
* Columns: <code>sentence_0</code> and <code>sentence_1</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                           | sentence_1                                                                        |
  |:--------|:-------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------|
  | type    | string                                                                               | string                                                                            |
  | details | <ul><li>min: 12 tokens</li><li>mean: 146.73 tokens</li><li>max: 256 tokens</li></ul> | <ul><li>min: 5 tokens</li><li>mean: 68.0 tokens</li><li>max: 256 tokens</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | sentence_1                                                                                                              |
  |:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------|
  | <code>A braking assembly can include a brake disc that may have a first segment and a second segment arranged to form a portion of a friction ring. The assembly can also include a fastening assembly that can include a first bracket that may have a first face configured to contact the wheel web and a second face opposite to the first face. The fastening assembly may also include a fastening device with a sliding pin disposed around a shaft. The first bracket may be disposed around the sliding pin and secured between the wheel web and a first component of the fastening device. The shaft may be disposed through the wheel web and the first bracket. The first component can contact the second face of the first bracket and may compress the first bracket against the wheel web to secure the first segment and the second segment to the wheel.</code> | <code>8 . The assembly of claim 1 , wherein the first segment includes a fin element.</code>                            |
  | <code>A nipple assembly for a spoke wheel according to the present disclosure is coupled to at least one end of a spoke provided on a spoke wheel and includes a main body including a nipple head, and a column portion having a smaller diameter than the nipple head and elongated from the nipple head toward one side, a nipple base having a first through-hole and fitted with the column portion through the first through-hole, and a vibration attenuation member having a second through-hole and positioned between the nipple head and the nipple base by being fitted with the column portion through the second through-hole.</code>                                                                                                                                                                                                                                | <code>the nipple base has a convex surface formed to be tapered in an extension direction of the column portion.</code> |
  | <code>Described herein are tires comprising a rubber composition based on at least an elastomer and a hydrocarbon resin. The hydrocarbon resin is based on a cyclic monomer selected from the group consisting of a distillation cut from a petroleum refinery stream, C 4 , C 5 and C 6 cyclic olefins and mixtures thereof. The hydrocarbon resin has a content of aromatic protons (H Ar, expressed in mol %), a glass transition temperature (Tg, expressed in ° C.), and a number average molecular weight (Mn, expressed in g/mol) that are represented by (1) 12 mol %≤H Ar≤19 mol %, (2) Tg≥95-2.2*(H Ar), (3) Tg≥−53+(0.265*Mn) and (4) 300 g/mol≤Mn≤450 g/mol.</code>                                                                                                                                                                                                    | <code>1 .- 15 . (canceled)</code>                                                                                       |
* Loss: [<code>MultipleNegativesRankingLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#multiplenegativesrankingloss) with these parameters:
  ```json
  {
      "scale": 20.0,
      "similarity_fct": "cos_sim",
      "gather_across_devices": false
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `num_train_epochs`: 1
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: no
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 1
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Framework Versions
- Python: 3.9.6
- Sentence Transformers: 5.1.2
- Transformers: 4.57.6
- PyTorch: 2.8.0
- Accelerate: 1.10.1
- Datasets: 4.5.0
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

#### MultipleNegativesRankingLoss
```bibtex
@misc{henderson2017efficient,
    title={Efficient Natural Language Response Suggestion for Smart Reply},
    author={Matthew Henderson and Rami Al-Rfou and Brian Strope and Yun-hsuan Sung and Laszlo Lukacs and Ruiqi Guo and Sanjiv Kumar and Balint Miklos and Ray Kurzweil},
    year={2017},
    eprint={1705.00652},
    archivePrefix={arXiv},
    primaryClass={cs.CL}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->