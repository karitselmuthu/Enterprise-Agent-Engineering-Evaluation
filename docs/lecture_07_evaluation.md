# Lecture 7 — LLM evaluation

## Phase 7.1: LLM-as-a-Judge

`OllamaJudge` assesses an answer against a reference and supplied evidence with
a versioned rubric. It requests JSON from Ollama and validates the returned
score and rationale. The local model is optional: unit tests inject a fake
transport, so the default development loop does not load a model.

Run a real local judge after starting Ollama and installing a model:

```sh
python3 experiments/lecture_07/01_llm_as_judge.py --model YOUR_MODEL
```

Judge scores are estimates. The model can still be inconsistent or biased even
when temperature is zero; later phases measure these failure modes.
