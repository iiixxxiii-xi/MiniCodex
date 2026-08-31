def make_message(role: str, content: str, **extra) -> dict:
    return {"role": role, "content": content, "extra": extra}
