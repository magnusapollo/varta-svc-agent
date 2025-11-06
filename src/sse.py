import json


def sse_event(event: str, data: dict) -> bytes:
    payload = f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"
    return payload.encode("utf-8")
