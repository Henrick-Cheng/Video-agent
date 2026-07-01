# Video-agent — working conventions

Temporal-scene-graph video Q&A agent. Two agent lines live in
`src/agents/react_agent.py`:

- **v2 `build_agent_v2`** — current line (lazy 3-layer memory + confidence loop:
  search_memory / explore_segment / inspect_frame). Powers both the benchmark
  path and `main.py`'s real backend (single + interactive), via `prepare_l0`
  (summary + ASR base) + `build_l0_context`. Has **no offline mock yet**.
- **v1 `build_agent`** — legacy ReAct line (extract_keyframes / build_scene_graph
  / query_scene_graph / inspect_frame). Retained as a benchmark baseline and as
  `main.py`'s `--mock` path only (`use_mock`, the offline mock lives here).

## Testing & AI-assisted development

These are the guardrails for code produced with AI assistance. AI generates
plausible-looking filler; these rules are the contract that catches it.

- **Mock / fallback paths must be explicitly labeled** (e.g. a `[MOCK]` prefix)
  and stay visually distinguishable from real output. They must **never
  fabricate domain data** — no scene-graph triplets (`--[rel]-->`), timestamps,
  entities, or invented video content. The mock in `_get_mock_llm` drives the
  real tool loop and returns a labeled placeholder; keep it that way. This rule
  applies equally to any future v2 mock.
- **Every CLI mode / fallback path needs at least one end-to-end behavior
  test.** Assert behavior, not existence — `assert agent is not None` is not a
  test. See `tests/test_agent.py` mock-mode guards for the pattern.
- **Human-review placeholder/example content before merge.** For new behavior,
  write (or co-write) the constraining test first — it is the human/AI contract.

## Project conventions

- Code and model-facing output are in English (post English-migration).
- Tests live in `tests/`, run with `python3 -m pytest`.
