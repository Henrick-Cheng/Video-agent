# Video-agent — working conventions

Temporal-scene-graph video Q&A agent. Two agent lines live in
`src/agents/react_agent.py`:

- **v2 `build_agent_v2`** — current line (lazy 3-layer memory + confidence loop:
  search_memory / explore_segment / inspect_frame). Powers the benchmark path,
  `main.py`'s real backend (single + interactive), and the FastAPI service
  (`src/api/app.py`), via `prepare_l0` (summary + ASR base) + `build_l0_context`
  and the shared runtime helpers (`get_recursion_limit` / `invoke_with_retry`).
  Has **no offline mock yet**.
- **v1 `build_agent`** — legacy ReAct line (extract_keyframes / build_scene_graph
  / query_scene_graph / inspect_frame). Retained as a benchmark baseline and as
  the offline mock path (`use_mock`) for `main.py --mock` and the API's
  `{"mock": true}` sessions (tests/test_api.py holds the e2e guards).

## Testing & AI-assisted development

These are the guardrails for code produced with AI assistance. AI generates
plausible-looking filler; these rules are the contract that catches it.

- **Mock / fallback paths must be explicitly labeled** (e.g. a `[MOCK]` prefix)
  and stay visually distinguishable from real output. They must **never
  fabricate domain data** — no scene-graph triplets (`--[rel]-->`), timestamps,
  entities, `source:"vlm"`, or invented video content. The mock in
  `_get_mock_llm` drives the real tool loop and returns a labeled placeholder;
  keep it that way. This rule applies equally to any future v2 mock.
- **A real run must fail loud, never silently fall back to fabricated data.**
  Mock output is opt-in only (`cfg.mock.enabled` / `--mock`) and uses
  unmistakably synthetic `mock_*` names with `source:"mock"`. When the backend
  is unavailable on a real run, tools return `{"_mode": "error", ...}` with a
  clear reason instead of inventing evidence — see `scene_graph_builder._fail_loud`
  and `frame_inspector._fail_loud_inspect`. A silent fabricating fallback can
  leak fake evidence into answers and benchmark scores.
- **Every CLI mode / fallback path needs at least one end-to-end behavior
  test.** Assert behavior, not existence — `assert agent is not None` is not a
  test. See `tests/test_agent.py` mock-mode guards for the pattern.
- **Human-review placeholder/example content before merge.** For new behavior,
  write (or co-write) the constraining test first — it is the human/AI contract.

## Project conventions

- Code and model-facing output are in English (post English-migration).
- Tests live in `tests/`, run with `python3 -m pytest`.
