import time

import httpx


class HttpClient:
    def __init__(self, timeout: float = 15.0):
        self.client = httpx.Client(
            timeout=timeout, headers={"user-agent": "deeptech-radar/0.1"}
        )

    def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ):
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        if extra_headers:
            headers.update(extra_headers)
        backoff = 1.0
        for _attempt in range(5):
            resp = self.client.get(url, params=params, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff *= 2
                continue
            return resp
        return resp
