from __future__ import annotations
from spacy.tokens import Span, Token

SCOPE_TERMINATORS = {",", ".", ";", "but", "however", "except", "although", "though", "yet"}


def tokens_between(doc, start_idx: int, end_idx: int) -> list[Token]:
    """Return tokens between two positions (exclusive)."""
    lo, hi = min(start_idx, end_idx), max(start_idx, end_idx)
    return [doc[i] for i in range(lo + 1, hi)]


def scope_broken(doc, from_idx: int, to_idx: int) -> bool:
    """Return True if a scope-terminating token exists between from_idx and to_idx."""
    for tok in tokens_between(doc, from_idx, to_idx):
        if tok.lower_ in SCOPE_TERMINATORS or tok.text in SCOPE_TERMINATORS:
            return True
    return False
