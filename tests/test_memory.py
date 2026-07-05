"""测试 MemoryStore 模块"""

from agent.memory import MemoryStore

SYSTEM_PROMPT = "你是一个 AI 助手"


def test_memory_creation():
    """验证 MemoryStore 实例化."""
    mem = MemoryStore(max_history=10)
    assert mem.max_history == 10
    assert mem.session is not None
    assert mem.history_count() == 0


def test_memory_add_and_count():
    """验证添加消息后计数正确."""
    mem = MemoryStore()
    mem.add_user_message("你好")
    mem.add_assistant_message("你好！")

    assert mem.history_count() == 2


def test_memory_get_context():
    """验证 get_context 返回 system_prompt + 对话历史."""
    mem = MemoryStore()
    mem.add_user_message("你好")
    mem.add_assistant_message("你好！")

    context = mem.get_context(SYSTEM_PROMPT)

    assert len(context) == 3
    assert context[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert context[1] == {"role": "user", "content": "你好"}
    assert context[2] == {"role": "assistant", "content": "你好！"}


def test_memory_history_limit():
    """验证超过 max_history 时旧消息被裁剪."""
    mem = MemoryStore(max_history=2)  # 最多 2 轮 = 4 条消息

    for i in range(5):             # 添加 5 轮
        mem.add_user_message(f"问题 {i}")
        mem.add_assistant_message(f"回答 {i}")
    # 一共 10 条消息，max_history=2 所以只保留最近 4 条

    context = mem.get_context(SYSTEM_PROMPT)

    # system + 最近 4 条（问题3→回答3→问题4→回答4）
    assert len(context) == 5
    assert context[1]["content"] == "问题 3"
    assert context[-1]["content"] == "回答 4"


def test_memory_clear():
    """验证 clear 清空记忆."""
    mem = MemoryStore()
    mem.add_user_message("测试")
    mem.clear()

    assert mem.history_count() == 0