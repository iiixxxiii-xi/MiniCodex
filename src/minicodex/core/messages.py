def make_message(role: str, content: str, **extra) -> dict:
    """Build an internal chat message.

    Extra fields (``tool_call_id``, ``tool_calls``, ``tool_name``, …) are placed
    at the top level so provider adapters can translate them into the protocol
    shape each API expects (OpenAI's ``tool_call_id`` on ``tool`` messages,
    Anthropic's ``tool_use``/``tool_result`` blocks, …).
    """
    return {"role": role, "content": content, **extra}
