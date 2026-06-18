"""One-off (Phase 14.1 B线): re-run escalated failures with trace capture.

For each selected question, dump L0 summary + transcript hits + the
explore_segment window/focus/caption + final answer + gold, so each can be
classified: L0-answerable (context narrowed) vs needs-unseen-window (locating).
Not part of the library; run directly.
"""
import json
from src.memory.session import VideoSession
from src.eval.run_benchmark import _prepare_l0
from src.agents.react_agent import build_agent_v2, build_l0_context

ids = json.load(open("/tmp/trace_ids.json"))
ids = list(dict.fromkeys(ids))  # dedupe, preserve order
bench = {q["id"]: q for q in json.load(open("benchmarks/mmbv_150.json"))}

out = []
sessions = {}  # cache L0 per video (mirrors the benchmark: one session per video)

for qid in ids:
    q = bench[qid]
    vid = q["video"]
    if vid not in sessions:
        s = VideoSession(vid)
        _prepare_l0(s)
        sessions[vid] = s
    s = sessions[vid]

    agent = build_agent_v2(s, short_answer=False, explore=True)
    res = agent.invoke({"messages": [("user", build_l0_context(s) + q["question"])]},
                       config={"recursion_limit": 40})
    msgs = res["messages"]

    explores = []
    for m in msgs:
        for c in (getattr(m, "tool_calls", None) or []):
            if c["name"] == "explore_segment":
                explores.append(c["args"])
    # tool returns for explore (the caption)
    captions = []
    for m in msgs:
        if getattr(m, "type", "") == "tool" and getattr(m, "name", "") == "explore_segment":
            try:
                captions.append(json.loads(m.content).get("caption", ""))
            except Exception:
                captions.append(str(m.content)[:300])

    rec = {
        "id": qid,
        "dims": q["_source"]["dimensions"],
        "duration": q["_source"]["duration_sec"],
        "question": q["question"],
        "gold": q["reference_answer"],
        "l0_summary": sessions[vid].global_summary,
        "n_transcript": len(sessions[vid].transcript),
        "explore_windows": explores,
        "explore_captions": captions,
        "final_answer": str(msgs[-1].content) if msgs else "",
    }
    out.append(rec)
    print(f"[done] {qid}  windows={[(e.get('t_start'),e.get('t_end')) for e in explores]}")

json.dump(out, open("/tmp/trace_results.json", "w"), ensure_ascii=False, indent=2)
print(f"\nsaved {len(out)} traces → /tmp/trace_results.json")
