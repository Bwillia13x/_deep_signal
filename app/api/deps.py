from fastapi import Header


def get_request_id(x_request_id: str | None = Header(default=None)):
    return x_request_id
