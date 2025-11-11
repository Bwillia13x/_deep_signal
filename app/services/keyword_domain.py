from collections.abc import Sequence

_DEFAULT_DOMAINS = ["cs.AI", "cs.LG", "cs.RO", "cs.CV"]


def classify_domain(text: str, candidates: Sequence[str] | None = None) -> str:
    choices = candidates or _DEFAULT_DOMAINS
    if not text:
        return choices[0]
    lowered = text.lower()
    for domain in choices:
        if domain.split(".")[-1].lower() in lowered:
            return domain
    return choices[0]
