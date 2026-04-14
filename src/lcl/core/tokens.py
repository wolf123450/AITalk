import tiktoken


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    if not text:
        return 0
    enc = tiktoken.get_encoding(encoding)
    return len(enc.encode(text))


def compression_ratio(english: str, lcl: str, encoding: str = "cl100k_base") -> float:
    eng_tokens = count_tokens(english, encoding)
    lcl_tokens = count_tokens(lcl, encoding)
    if eng_tokens == 0:
        return 0.0
    return 1 - (lcl_tokens / eng_tokens)
