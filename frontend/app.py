"""
Gradio frontend for Video Agent.

Three-column layout:
  Left  : Video upload / player + "Build Scene Graph" button
  Middle: Multi-turn chat + example question buttons
  Right : Agent trace (colored, streaming) + scene graph status

Usage:
    python frontend/app.py
    # Open http://localhost:7860
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Generator

import gradio as gr

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── State containers ──────────────────────────────────────────────────────────

class _AppState:
    def __init__(self):
        self.session = None
        self.agent = None
        self.video_path: str | None = None
        self.graph_built = False
        self.entity_count_prev = 0
        self.edge_count_prev = 0

    def reset(self):
        self.__init__()

    def is_ready(self):
        return self.session is not None and self.agent is not None


_EXAMPLE_QUESTIONS = [
    "视频里有哪些游戏角色？",
    "骑着骡子打鸟穿什么颜色的衣服？",
    "哪些角色在游戏大厅等待？谁手持武器？",
    "视频中出现了几个角色？分别叫什么？",
    "视频经历了怎样的场景变化？",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _graph_status_html(session, prev_entities: int = 0, prev_edges: int = 0) -> str:
    if session is None:
        return "<div style='color:#888'>（尚未加载视频）</div>"
    sg = session.scene_graph
    n_e = len(sg.entities)
    n_t = len(sg)
    delta_e = n_e - prev_entities
    delta_t = n_t - prev_edges
    de_str = f" <span style='color:#22c55e'>+{delta_e}</span>" if delta_e > 0 else ""
    dt_str = f" <span style='color:#22c55e'>+{delta_t}</span>" if delta_t > 0 else ""

    recent_entities = list(sg.entities.keys())[-5:]
    recent_html = "".join(
        f"<span style='background:#1e3a5f;border-radius:4px;padding:2px 6px;"
        f"margin:2px;display:inline-block'>{e}</span>"
        for e in recent_entities
    )
    return (
        f"<div style='font-family:monospace;font-size:13px'>"
        f"<div>实体数: <b>{n_e}</b>{de_str} &nbsp; 边数: <b>{n_t}</b>{dt_str}</div>"
        f"<div style='margin-top:6px;font-size:11px;color:#aaa'>最近实体：</div>"
        f"<div style='margin-top:4px'>{recent_html}</div>"
        f"</div>"
    )


def _format_trace_step(step_type: str, content: str) -> str:
    icons = {
        "thought": "🧠",
        "action":  "🔧",
        "observe": "👁️",
        "answer":  "✅",
        "error":   "❌",
    }
    colors = {
        "thought": "#a78bfa",
        "action":  "#60a5fa",
        "observe": "#34d399",
        "answer":  "#fbbf24",
        "error":   "#f87171",
    }
    icon = icons.get(step_type, "•")
    color = colors.get(step_type, "#e5e7eb")
    safe = content.replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"<div style='margin:4px 0;border-left:3px solid {color};"
        f"padding-left:8px;color:{color}'>"
        f"{icon} <b>{step_type.upper()}</b>: "
        f"<span style='color:#e5e7eb'>{safe}</span></div>\n"
    )


def _get_video_info(video_path: str) -> str:
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        duration = frames / fps if fps > 0 else 0
        return f"时长: {duration:.1f}s | 分辨率: {w}×{h} | FPS: {fps:.1f}"
    except Exception:
        return "（视频信息读取失败）"


# ── Event handlers ────────────────────────────────────────────────────────────

def on_video_upload(video_file, state: _AppState):
    if video_file is None:
        return state, "（未选择视频）", "（未选择视频）", _graph_status_html(None)

    state.reset()

    # Gradio may give us a path string or a temp file path
    video_path = video_file if isinstance(video_file, str) else str(video_file)
    state.video_path = video_path

    # Build session and agent immediately (lightweight — no VLM call yet)
    from src.memory.session import VideoSession
    from src.agents.react_agent import build_agent

    state.session = VideoSession(video_path=video_path)
    state.agent = build_agent(state.session)

    info = _get_video_info(video_path)
    graph_html = _graph_status_html(state.session)
    return (
        state,
        info,
        f"视频已加载：{Path(video_path).name}",
        graph_html,
    )


def on_build_graph(state: _AppState):
    if state.session is None:
        yield state, "请先上传视频", _graph_status_html(None)
        return

    yield state, "⏳ 正在提取关键帧...", _graph_status_html(state.session)

    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph

    kf_tool = make_extract_keyframes(state.session)
    sg_tool = make_build_scene_graph(state.session)

    from src.config import get_settings as _gs
    kf_result = json.loads(kf_tool.invoke({"strategy": "uniform", "count": _gs().perception.keyframe_count}))
    n_frames = len(kf_result.get("frame_ids", []))
    yield state, f"⏳ 已提取 {n_frames} 帧，正在构建场景图...", _graph_status_html(state.session)

    frame_ids = ",".join(kf_result["frame_ids"])
    sg_tool.invoke({"frame_ids": frame_ids, "focus_entities": ""})
    state.graph_built = True

    n_e = len(state.session.scene_graph.entities)
    n_t = len(state.session.scene_graph)
    yield (
        state,
        f"✅ 场景图构建完成：{n_e} 个实体，{n_t} 条关系",
        _graph_status_html(state.session),
    )


def on_chat(
    message: str,
    history: list,
    state: _AppState,
) -> Generator:
    if not state.is_ready():
        history = history + [{"role": "user", "content": message},
                             {"role": "assistant", "content": "请先上传视频"}]
        yield history, "", _graph_status_html(None), state
        return

    if not message.strip():
        yield history, "", _graph_status_html(state.session), state
        return

    state.session.add_query(message)
    prev_e = len(state.session.scene_graph.entities)
    prev_t = len(state.session.scene_graph)

    history = history + [{"role": "user", "content": message}]
    yield history, "", _graph_status_html(state.session, prev_e, prev_t), state

    trace_html = "<div style='font-family:monospace;font-size:12px'>"

    from src.config import get_settings
    cfg = get_settings()
    rl = getattr(state.agent, "_va_max_iterations", 6) * 3 + 1

    answer = ""
    try:
        for chunk in state.agent.stream(
            {"messages": [("user", message)]},
            config={"recursion_limit": rl},
        ):
            for node_name, values in chunk.items():
                msgs = values.get("messages", [])
                for msg in msgs:
                    msg_type = getattr(msg, "type", "")

                    if msg_type == "ai":
                        tcs = getattr(msg, "tool_calls", [])
                        if tcs:
                            for tc in tcs:
                                args_str = json.dumps(
                                    tc.get("args", {}), ensure_ascii=False
                                )[:120]
                                trace_html += _format_trace_step(
                                    "action", f"{tc['name']}({args_str})"
                                )
                        else:
                            content = str(getattr(msg, "content", "")).strip()
                            if content:
                                answer = content
                                trace_html += _format_trace_step("answer", content[:300])

                    elif msg_type == "tool":
                        obs = str(getattr(msg, "content", ""))
                        try:
                            obs_d = json.loads(obs)
                            obs_summary = json.dumps(obs_d, ensure_ascii=False)[:200]
                        except Exception:
                            obs_summary = obs[:200]
                        trace_html += _format_trace_step("observe", obs_summary)

                    graph_html = _graph_status_html(
                        state.session, prev_e, prev_t
                    )
                    yield (
                        history,
                        trace_html + "</div>",
                        graph_html,
                        state,
                    )

    except Exception as e:
        trace_html += _format_trace_step("error", str(e))

    # Finalize answer
    if not answer:
        answer = "（未获得答案，请检查 API Key 或网络连接）"

    history = history + [{"role": "assistant", "content": answer}]
    trace_html += "</div>"
    graph_html = _graph_status_html(state.session, prev_e, prev_t)
    yield history, trace_html, graph_html, state


def on_reset(state: _AppState):
    state.reset()
    return state, [], "", _graph_status_html(None), "Session 已重置"


def on_example_click(example: str, history: list, state: _AppState):
    return example


# ── UI Layout ─────────────────────────────────────────────────────────────────

_CSS = """
.trace-box textarea { background: #0f172a !important; color: #e5e7eb !important;
    font-family: 'Fira Code', monospace !important; font-size: 12px !important; }
.graph-box { background: #0f172a; padding: 10px; border-radius: 8px;
    min-height: 120px; color: #e5e7eb; }
.example-btn { font-size: 12px !important; }
"""

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Video Agent Demo", css=_CSS, theme=gr.themes.Default()) as demo:
        state = gr.State(_AppState())

        gr.Markdown("# 🎬 Video Agent — 视频理解 Demo")
        gr.Markdown(
            "上传视频 → 可选先构建场景图 → 多轮提问 | "
            "右侧实时显示 Agent 推理 trace 和场景图状态"
        )

        with gr.Row():
            # ── LEFT COLUMN ───────────────────────────────────────────────────
            with gr.Column(scale=3):
                video_input = gr.Video(label="上传视频", height=240)
                video_info = gr.Textbox(
                    label="视频信息",
                    value="（请上传视频）",
                    interactive=False,
                    lines=1,
                )
                build_btn = gr.Button("🔨 构建场景图（可选，问问题时会自动构建）",
                                      variant="secondary")
                build_status = gr.Textbox(
                    label="构建状态",
                    value="",
                    interactive=False,
                    lines=2,
                )

            # ── MIDDLE COLUMN ─────────────────────────────────────────────────
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=360,
                    type="messages",
                    bubble_full_width=False,
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="输入问题，按 Enter 发送...",
                        label="",
                        scale=5,
                        container=False,
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)

                gr.Markdown("**示例问题（点击直接发送）：**")
                with gr.Row():
                    ex_btns = [
                        gr.Button(q[:18] + "…" if len(q) > 18 else q,
                                  size="sm", elem_classes=["example-btn"])
                        for q in _EXAMPLE_QUESTIONS[:3]
                    ]
                with gr.Row():
                    ex_btns2 = [
                        gr.Button(q[:18] + "…" if len(q) > 18 else q,
                                  size="sm", elem_classes=["example-btn"])
                        for q in _EXAMPLE_QUESTIONS[3:]
                    ]
                reset_btn = gr.Button("🔄 重置 Session（切换视频或重新开始）",
                                      variant="stop", size="sm")

            # ── RIGHT COLUMN ──────────────────────────────────────────────────
            with gr.Column(scale=3):
                gr.Markdown("### Agent Trace")
                trace_box = gr.HTML(
                    value="<div style='color:#888;font-size:12px'>（等待提问）</div>",
                    label="",
                )
                gr.Markdown("### 场景图状态")
                graph_box = gr.HTML(
                    value=_graph_status_html(None),
                    elem_classes=["graph-box"],
                )

        # ── Wiring ────────────────────────────────────────────────────────────

        video_input.change(
            on_video_upload,
            inputs=[video_input, state],
            outputs=[state, video_info, build_status, graph_box],
        )

        build_btn.click(
            on_build_graph,
            inputs=[state],
            outputs=[state, build_status, graph_box],
        )

        def _submit(message, history, state):
            yield from on_chat(message, history, state)

        msg_input.submit(
            _submit,
            inputs=[msg_input, chatbot, state],
            outputs=[chatbot, trace_box, graph_box, state],
        ).then(lambda: "", outputs=[msg_input])

        send_btn.click(
            _submit,
            inputs=[msg_input, chatbot, state],
            outputs=[chatbot, trace_box, graph_box, state],
        ).then(lambda: "", outputs=[msg_input])

        reset_btn.click(
            on_reset,
            inputs=[state],
            outputs=[state, chatbot, trace_box, graph_box, build_status],
        )

        # Example button wiring
        all_ex = list(zip(_EXAMPLE_QUESTIONS[:3], ex_btns)) + \
                 list(zip(_EXAMPLE_QUESTIONS[3:], ex_btns2))
        for q_text, btn in all_ex:
            btn.click(
                fn=lambda q=q_text: q,
                outputs=[msg_input],
            )

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    # Verify API key is present
    from src.config import get_settings
    cfg = get_settings()
    if not cfg.dashscope_api_key and cfg.backend == "dashscope":
        print("WARNING: DASHSCOPE_API_KEY not set. Set it in .env or export before running.")
        print("         The app will start but API calls will fail.")

    print(f"Starting Video Agent Gradio UI on port {args.port}...")
    demo = build_ui()
    demo.launch(server_port=args.port, share=args.share, server_name="0.0.0.0")
