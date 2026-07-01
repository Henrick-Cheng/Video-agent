"""
main.py — Video Agent CLI entry point.

Usage:
    # Single question (real DashScope)
    python main.py --video data/videos/test1.mp4 --question "视频里发生了什么?"

    # Interactive multi-turn (reuses session/scene-graph across questions)
    python main.py --video data/videos/test1.mp4 --interactive

    # Override backend
    python main.py --video ... --question "..." --backend vllm

    # Offline mock (no API key needed)
    python main.py --video ... --question "..." --mock
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent))


SEP = "=" * 70
THIN = "-" * 70


def _print_trace(messages: list) -> None:
    """Pretty-print the agent's Thought / Action / Observation steps."""
    # Skip first message (user question)
    steps = messages[1:]
    if not steps:
        return

    print(f"\n{THIN}")
    print("  REASONING TRACE")
    print(THIN)

    step_num = 0
    for msg in steps:
        msg_type = getattr(msg, "type", "")

        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", [])
            if tool_calls:
                step_num += 1
                tc = tool_calls[0]
                print(f"\n  [Step {step_num}]")
                print(f"  Action      : {tc['name']}")
                args_str = json.dumps(tc.get("args", {}), ensure_ascii=False)
                print(f"  Action Input: {args_str}")

        elif msg_type == "tool":
            obs_str = str(getattr(msg, "content", ""))
            try:
                obs_dict = json.loads(obs_str)
                obs_preview = json.dumps(obs_dict, ensure_ascii=False, indent=2)
                if len(obs_preview) > 600:
                    obs_preview = obs_preview[:600] + "\n  ... (truncated)"
                formatted = "\n".join(f"  {line}" for line in obs_preview.splitlines())
                print(f"  Observation :\n{formatted}")
            except (json.JSONDecodeError, TypeError):
                print(f"  Observation : {obs_str[:400]}")


def _get_recursion_limit(agent) -> int:
    """Derive LangGraph recursion_limit from agent's stored max_iterations."""
    iters = getattr(agent, "_va_max_iterations", 6)
    return iters * 3 + 1  # each iteration = up to 3 graph steps


def run_single(video: str, question: str, mock: bool = False) -> str:
    """Run the agent on one question and print the full trace."""
    from src.agents.react_agent import (
        build_agent, build_agent_v2, build_l0_context, prepare_l0)
    from src.memory.session import VideoSession

    session = VideoSession(video_path=video)
    session.add_query(question)

    print(f"\n{SEP}")
    print(f"  Video Agent — Single Question Mode  (v2: lazy memory)")
    print(SEP)
    print(f"  Video   : {video}")
    print(f"  Question: {question}")
    print(f"  Session : {session.session_id}")
    print(f"  Backend : {'MOCK' if mock else 'DashScope/vLLM (see configs/default.yaml)'}")
    print(f"{SEP}\n")

    # v2: build the lightweight L0 base (summary + ASR) before answering; the
    # mock LLM path keeps v1 (no API / no L0 needed for the offline smoke test).
    if mock:
        agent = build_agent(session, use_mock=True)
        user_text = question
    else:
        print("  Preparing memory (L0: summary + transcript)...")
        prepare_l0(session)
        agent = build_agent_v2(session, short_answer=False)
        user_text = build_l0_context(session) + question

    print("\n  Reasoning...\n")

    result = agent.invoke(
        {"messages": [("user", user_text)]},
        config={"recursion_limit": _get_recursion_limit(agent)},
    )

    _print_trace(result["messages"])

    answer = result["messages"][-1].content
    sg = session.scene_graph
    tool_steps = sum(
        1 for m in result["messages"]
        if getattr(m, "type", "") == "tool"
    )

    print(f"\n{SEP}")
    print(f"  FINAL ANSWER")
    print(SEP)
    print(f"  {answer}")
    print(SEP)
    print(f"\n  Scene graph : {len(sg.entities)} entities, {len(sg)} triplets")
    print(f"  Frames used : {len(session.cached_frames)}")
    print(f"  Tool calls  : {tool_steps}\n")

    return answer


def run_interactive(video: str, mock: bool = False) -> None:
    """
    Multi-turn interactive mode.

    The VideoSession is preserved across questions so the scene graph
    accumulates — later questions reuse earlier work.
    """
    from src.agents.react_agent import (
        build_agent, build_agent_v2, build_l0_context, prepare_l0)
    from src.memory.session import VideoSession

    session = VideoSession(video_path=video)

    # v2: build L0 once; the session (explored windows + memory) persists across
    # turns, so later questions reuse earlier exploration. Mock keeps v1 offline.
    if mock:
        agent = build_agent(session, use_mock=True)
    else:
        print("  Preparing memory (L0: summary + transcript)...")
        prepare_l0(session)
        agent = build_agent_v2(session, short_answer=False)
    recursion_limit = _get_recursion_limit(agent)

    print(f"\n{SEP}")
    print(f"  Video Agent — Interactive Mode  (type 'exit' to quit)")
    print(SEP)
    print(f"  Video   : {video}")
    print(f"  Session : {session.session_id}")
    print(f"  Backend : {'MOCK' if mock else 'DashScope/vLLM (see configs/default.yaml)'}")
    print(f"  Tip     : Memory (explored windows) persists across questions.\n")

    turn = 0
    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question or question.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            break

        turn += 1
        session.add_query(question)
        print(f"\n[Turn {turn}] Reasoning...\n")

        # Recompute L0 context each turn so it reflects windows explored in
        # earlier turns (mock path has no L0 and answers from the question alone).
        user_text = question if mock else build_l0_context(session) + question
        result = agent.invoke(
            {"messages": [("user", user_text)]},
            config={"recursion_limit": recursion_limit},
        )

        _print_trace(result["messages"])

        sg = session.scene_graph
        tool_steps = sum(1 for m in result["messages"] if getattr(m, "type", "") == "tool")
        print(f"\n  Answer: {result['messages'][-1].content}")
        print(f"  (Scene graph: {len(sg.entities)} entities, {len(sg)} triplets "
              f"| {tool_steps} tool calls)\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Video Agent — multimodal video Q&A with scene graphs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--video", required=True,
        help="Path to video file (e.g. data/videos/test1.mp4)",
    )
    parser.add_argument(
        "--question", default=None,
        help="Question to answer (required unless --interactive is set)",
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Multi-turn interactive mode; reuses scene graph across questions",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use mock LLM — no API key or model server required",
    )
    parser.add_argument(
        "--backend", choices=["dashscope", "vllm"], default=None,
        help="Override backend from configs/default.yaml",
    )
    args = parser.parse_args()

    if args.backend:
        os.environ["BACKEND"] = args.backend

    if args.interactive:
        run_interactive(args.video, mock=args.mock)
    elif args.question:
        run_single(args.video, args.question, mock=args.mock)
    else:
        parser.error("Provide --question for single mode or --interactive for multi-turn.")


if __name__ == "__main__":
    main()
