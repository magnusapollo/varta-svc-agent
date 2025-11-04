import re

def sentence_chunks(text: str, max_len: int = 200):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    buf = ""
    for p in parts:
        if len(buf) + len(p) + 1 > max_len and buf:
            yield buf + " "
            buf = p
        else:
            buf = (buf + " " + p).strip()
    if buf:
        yield buf + " "
