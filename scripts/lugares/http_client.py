import http.cookiejar
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TIMEOUT = 900
PAUSE = 1.0
RETRIES = 3


class Response:
    def __init__(self, content: bytes, headers) -> None:
        self.content = content
        self.headers = headers


class Session:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, method: str, url: str, data: dict = None, params: dict = None) -> Response:
        if params:
            url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(params)}"
        body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
        last = None
        for attempt in range(RETRIES):
            req = urllib.request.Request(url, data=body, method=method, headers={"User-Agent": UA})
            try:
                with self.opener.open(req, timeout=TIMEOUT) as resp:
                    content = resp.read()
                    time.sleep(PAUSE)
                    return Response(content, resp.headers)
            except (urllib.error.URLError, OSError) as exc:
                last = exc
                time.sleep(5 * (attempt + 1))
        raise SystemExit(f"No se pudo descargar {url}: {last}")
