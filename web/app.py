"""Mini Agent Runtime — Streamlit Web UI

支持:
- 多用户、多会话同时管理
- 会话创建 / 切换 / 删除 / 续聊
- 实时对话 + 工具调用
"""

import asyncio
import logging
import sys
from pathlib import Path

# Streamlit 默认以脚本所在目录为工作目录，需把项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from agent.runtime import AgentRuntime

logger = logging.getLogger("mini-agent")

# ── 页面配置 ──
st.set_page_config(page_title="Mini Agent", page_icon="🤖", layout="wide")


@st.cache_resource
def get_runtime() -> AgentRuntime:
    """创建并缓存 AgentRuntime 实例（LLMClient 开销大，复用）."""
    return AgentRuntime()


def _short_id(session_id: str) -> str:
    return session_id[:10] + "..."


def _message_count_label(count: int) -> str:
    return f"{count} 条消息"


# ═══════════════════════════════════════
# 主函数
# ═══════════════════════════════════════

def main() -> None:
    st.title("🤖 Mini Agent Runtime")

    runtime = get_runtime()

    # ── 侧边栏：会话管理 ──
    with st.sidebar:
        st.header("📂 会话管理")

        user_id = st.text_input("👤 用户 ID", value="default", key="user_id")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ 新建会话", use_container_width=True):
                sid = runtime.create_session(user_id)
                st.session_state.current_sid = sid
                st.rerun()
        with col2:
            if st.button("🔄 刷新列表", use_container_width=True):
                st.rerun()

        st.divider()

        sessions = runtime.list_sessions(user_id)
        if not sessions:
            st.caption("暂无会话，点击「新建会话」开始")
        else:
            for meta in sessions:
                is_active = st.session_state.get("current_sid") == meta.session_id
                prefix = "🔵 " if is_active else "⚪ "
                label = f"{prefix}{meta.session_id[:8]}… [{_message_count_label(meta.message_count)}]"

                c1, c2 = st.columns([4, 1])
                with c1:
                    if st.button(label, key=f"s_{meta.session_id}", use_container_width=True):
                        st.session_state.current_sid = meta.session_id
                        st.rerun()
                with c2:
                    if st.button("🗑", key=f"del_{meta.session_id}", help="删除此会话"):
                        runtime.session_manager.delete_session(user_id, meta.session_id)
                        if st.session_state.get("current_sid") == meta.session_id:
                            st.session_state.current_sid = ""
                        st.rerun()

        st.divider()
        st.caption("数据目录: `data/sessions/`")

    # ── 主区域：对话界面 ──
    current_sid = st.session_state.get("current_sid", "")

    if not current_sid:
        st.info("👈 请在侧边栏创建或选择一个会话开始对话")
        return

    # 从 SessionManager 加载当前 session 并绑定到 Runtime
    session = runtime.session_manager.get_session(user_id, current_sid)
    runtime._bind_session(session)

    # 显示历史消息
    for msg in session.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── 输入框 ──
    if prompt := st.chat_input("输入消息…"):
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 思考中…"):
                reply = asyncio.run(
                    runtime.run_once(
                        prompt,
                        user_id=user_id,
                        session_id=current_sid,
                    )
                )
            st.markdown(reply)

        st.rerun()


if __name__ == "__main__":
    main()
