"""Pure request-boundary predicate for the local fictional HomeOps browser demo.

Only loopback Host values are admitted, and browser POSTs must be same-origin JSON.
A deliberate local CLI with no Origin may still use the documented JSON endpoint.
No customer data or external-effect authorization is involved.
"""


def allow_local_request(
    host_headers: list[str],
    origin_headers: list[str],
    port: int,
    *,
    require_json: bool = False,
    content_type: str | None = None,
) -> bool:
    if type(port) is not int or not (0 < port < 65536):
        return False
    if len(host_headers) != 1 or type(host_headers[0]) is not str:
        return False
    host = host_headers[0].lower()
    if host not in {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}:
        return False
    if len(origin_headers) > 1:
        return False
    if origin_headers:
        if type(origin_headers[0]) is not str or origin_headers[0].lower() != f"http://{host}":
            return False
    if require_json and (
        type(content_type) is not str
        or content_type.split(";", 1)[0].strip().lower() != "application/json"
    ):
        return False
    return True
