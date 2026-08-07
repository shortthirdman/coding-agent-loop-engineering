def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers