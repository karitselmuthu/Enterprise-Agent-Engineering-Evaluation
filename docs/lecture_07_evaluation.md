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

## Phase 7.2: Evaluation metrics

JSONL cases contain a question, reference answer, required terms, and optional
evidence. The runner checks answer IDs and reports exact match, token F1, and
required-term recall. A model judge can add a separate score; lexical metrics
must not be read as factual correctness. Run the offline example with
`python3 experiments/lecture_07/02_evaluation_metrics.py`.

## Phase 7.3: Biases and pitfalls

The probes compare a pair of answers in both orders and measure score changes
after adding irrelevant length or a prompt-injection instruction. Run
`python3 experiments/lecture_07/03_biases_pitfalls.py` for a **mock simulation**.
Pass `--model YOUR_MODEL` for an actual local model. Position consistency and
score sensitivity are diagnostics, not proof of fairness or reliability.
