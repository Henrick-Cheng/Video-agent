"""
End-to-end mock demo for Video Agent.

Demonstrates the full tool pipeline without a running GPU or model server.
The Agent's decision loop is simulated manually so you can see the data
flowing through each stage.

Usage:
    python -m examples.demo
    python -m examples.demo --video path/to/video.mp4 --question "..."
    python -m examples.demo --agent   # use LangChain AgentExecutor with mock LLM
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.session import VideoSession
from src.tools.frame_inspector import make_inspect_frame
from src.tools.keyframe import make_extract_keyframes
from src.tools.scene_graph_builder import make_build_scene_graph
from src.tools.scene_graph_query import make_query_scene_graph


SEP = "=" * 64


def run_manual_pipeline(video_path: str, question: str) -> str:
    """
    Manually walk through the 4-tool pipeline to show data at each step.
    This mirrors what the ReAct Agent does autonomously in real mode.
    """
    print(f"\n{SEP}")
    print(f"  Video Agent — Manual Mock Pipeline")
    print(f"{SEP}")
    print(f"  Video    : {video_path}")
    print(f"  Question : {question}")
    print(f"{SEP}\n")

    # ── shared state ──────────────────────────────────────────────────────────
    session = VideoSession(video_path=video_path)
    session.add_query(question)

    # ── bind tools to session via closure ─────────────────────────────────────
    extract_keyframes    = make_extract_keyframes(session)
    build_scene_graph    = make_build_scene_graph(session)
    query_scene_graph    = make_query_scene_graph(session)
    inspect_frame        = make_inspect_frame(session)

    # ── Step 1: extract keyframes ─────────────────────────────────────────────
    print("[Step 1] extract_keyframes(strategy='uniform', count=8)")
    r1 = json.loads(extract_keyframes.invoke({"strategy": "uniform", "count": 8}))
    print(f"  → {r1['total_cached']} frames cached")
    print(f"  → first 3 ids : {r1['frame_ids'][:3]}")
    print(f"  → timestamps  : {[round(t, 1) for t in r1['timestamps'][:3]]} ...\n")

    # ── Step 2: build scene graph ─────────────────────────────────────────────
    frame_ids_str = ",".join(r1["frame_ids"])
    print("[Step 2] build_scene_graph(frame_ids=<all>, focus_entities='')")
    r2 = json.loads(build_scene_graph.invoke({"frame_ids": frame_ids_str, "focus_entities": ""}))
    print(f"  → nodes_added : {r2['nodes_added']}")
    print(f"  → edges_added : {r2['edges_added']}")
    print(f"  → new triplets: {len(r2['new_triplets'])}")
    print(f"\n{r2['graph_summary']}\n")

    # ── Step 3: query scene graph ─────────────────────────────────────────────
    print(f"[Step 3] query_scene_graph(question='{question}')")
    r3 = json.loads(query_scene_graph.invoke({"question": question}))
    print(f"  → found       : {r3['found']}")
    print(f"  → {r3['entity_summary']}")
    print(f"  → matched triplets ({len(r3['triplets'])}):")
    for t in r3["triplets"][:4]:
        print(f"      ({t['subject']}) --[{t['relation']}]--> ({t['object']}) "
              f"@ [{t['t_start']:.1f}s, {t['t_end']:.1f}s]")

    # ── Step 4 (conditional): inspect frame ───────────────────────────────────
    if not r3["found"]:
        print("\n[Step 4] Scene graph empty → inspect_frame(timestamp=30.0)")
        r4 = json.loads(inspect_frame.invoke(
            {"timestamp": 30.0, "question": question}
        ))
        print(f"  → VLM answer  : {r4['answer']}")
        print(f"  → new entities: {r4['new_entities']}")
        final_answer = r4["answer"]
    else:
        print("\n[Step 4] Scene graph sufficient → skipping inspect_frame")
        triplet_texts = [
            f"({t['subject']}) --[{t['relation']}]--> ({t['object']})"
            for t in r3["triplets"][:3]
        ]
        final_answer = "Based on the scene graph: " + "; ".join(triplet_texts) + "."

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  Final Answer : {final_answer}")
    print(f"{SEP}")
    print(f"\n  Session: {session.summary()}\n")

    return final_answer


def run_agent_pipeline(video_path: str, question: str) -> str:
    """
    Run the LangChain AgentExecutor with the mock LLM.
    Shows how the real agent loop will work once connected to Qwen3-8B.
    """
    from src.agents.react_agent import build_agent

    print(f"\n{SEP}")
    print(f"  Video Agent — LangChain ReAct Pipeline (mock LLM)")
    print(f"{SEP}")
    print(f"  Video    : {video_path}")
    print(f"  Question : {question}")
    print(f"{SEP}\n")

    session = VideoSession(video_path=video_path)
    executor = build_agent(session, use_mock=True, verbose=True)

    result = executor.invoke({"input": question})

    print(f"\n{SEP}")
    print(f"  Final Answer : {result['output']}")
    print(f"  Steps taken  : {len(result['intermediate_steps'])}")
    print(f"{SEP}")
    print(f"\n  Session: {session.summary()}\n")

    return result["output"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Video Agent mock demo")
    parser.add_argument("--video",    default="sample_video.mp4",
                        help="Path to video file (can be a fake path in mock mode)")
    parser.add_argument("--question", default="视频中有哪些人物？他们在做什么？",
                        help="Question about the video")
    parser.add_argument("--agent",    action="store_true",
                        help="Use LangChain AgentExecutor instead of manual pipeline")
    args = parser.parse_args()

    if args.agent:
        run_agent_pipeline(args.video, args.question)
    else:
        run_manual_pipeline(args.video, args.question)


if __name__ == "__main__":
    main()
