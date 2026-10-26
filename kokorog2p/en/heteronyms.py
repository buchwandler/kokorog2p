"""Deterministic, traceable context rules for a small set of English heteronyms."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass

_TOKEN_RE = re.compile(r"[\w]+(?:['’][\w]+)*", re.UNICODE)
ContextResult = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class HeteronymDecision:
    """One contextual reading decision and the evidence used to make it."""

    word: str
    ipa: str
    reason: str
    context_rule: str
    tag: str | None = None
    pos: str | None = None
    lemma: str | None = None
    morph: str | None = None
    context: str = ""
    source: str = "english-context-resolver"
    selector: str | None = None
    lexicon_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Return stable JSON-friendly decision metadata."""
        return asdict(self)


def _tokens(value: str | Sequence[str] | None) -> list[str]:
    if value is None:
        return []
    pieces = (value,) if isinstance(value, str) else value
    return [
        match.group(0).casefold().replace("’", "'")
        for piece in pieces
        for match in _TOKEN_RE.finditer(str(piece))
    ]


def _minute(left: list[str], right: list[str]) -> ContextResult | None:
    if right and right[0] in {"later", "ago", "after", "before", "past"}:
        return (
            "ˈmɪnɪt",
            "A time adverbial selects the unit-of-time reading.",
            "minute.time-unit",
        )
    if right and right[0] in {
        "crack",
        "difference",
        "detail",
        "amount",
        "particle",
        "fraction",
        "trace",
        "change",
        "mark",
    }:
        return (
            "maɪˈnuːt",
            "A tiny-object noun selects the extremely-small adjective.",
            "minute.tiny-adjective",
        )
    return None


def _bow(left: list[str], right: list[str]) -> ContextResult | None:
    if set(left[-4:]) & {"polite", "gesture", "courtesy"}:
        return "baʊ", "Polite etiquette selects the gesture sense.", "bow.gesture"
    if set(left[-5:]) & {"hunting", "archer's", "weapon"} or set(right[:5]) & {
        "arrow",
        "string",
        "weapon",
        "hunting",
    }:
        return (
            "boʊ",
            "Hunting or weapon context selects the archery sense.",
            "bow.weapon",
        )
    return None


def _bass(left: list[str], right: list[str]) -> ContextResult | None:
    if set(left[-5:]) & {"drawing", "fish", "fishing", "caught", "river"} or set(
        right[:5]
    ) & {"fish", "swam", "caught", "river"}:
        return "bæs", "Fish or fishing context selects the animal sense.", "bass.fish"
    if set(right[:5]) & {"player", "guitar", "drums", "instrument", "music"} or set(
        left[-5:]
    ) & {"musical", "music", "band", "instrument"}:
        return (
            "beɪs",
            "Music or instrument context selects the musical sense.",
            "bass.music",
        )
    return None


def _lead(left: list[str], right: list[str]) -> ContextResult | None:
    if right and right[0] in {"weight", "pipe", "metal", "pencil", "bullet", "ingot"}:
        return (
            "lɛd",
            "A metal-object complement selects the element pronunciation.",
            "lead.metal",
        )
    if right and right[0] in {"actor", "role", "singer", "character", "performer"}:
        return (
            "liːd",
            "A principal-role complement selects the leadership pronunciation.",
            "lead.principal",
        )
    return None


def _does(left: list[str], right: list[str]) -> ContextResult | None:
    if left and left[-1] in {"several", "many", "few", "those", "these", "herd"}:
        return (
            "doʊz",
            "A plural quantifier selects the female-deer reading.",
            "does.deer",
        )
    if right and right[0] in {"that", "this", "he", "she", "it", "they", "you", "we"}:
        return (
            "dʌz",
            "A following subject pronoun selects the auxiliary verb.",
            "does.auxiliary",
        )
    return None


def _refuse(left: list[str], right: list[str]) -> ContextResult | None:
    if (left and left[-1] in {"all", "some", "the", "household", "industrial"}) or (
        right
        and right[0] in {"should", "must", "is", "was", "were", "behind", "everywhere"}
    ):
        return (
            "ˈrɛfjuːs",
            "Determiner or predicate context selects the waste noun.",
            "refuse.waste-noun",
        )
    if left and left[-1] in {
        "could",
        "can",
        "will",
        "would",
        "may",
        "might",
        "must",
        "should",
        "to",
    }:
        return (
            "rɪˈfjuːz",
            "A modal or infinitive marker selects the verb.",
            "refuse.verb",
        )
    return None


def _learned(left: list[str], right: list[str]) -> ContextResult | None:
    if right and right[0] in {
        "professor",
        "scholar",
        "expert",
        "historian",
        "student",
        "colleague",
        "reader",
    }:
        return (
            "ˈlɝnɪd",
            "A scholarly person noun selects the two-syllable adjective.",
            "learned.scholarly-adjective",
        )
    contracted_had = left and left[-1] in {
        "had",
        "has",
        "have",
        "i'd",
        "you'd",
        "he'd",
        "she'd",
        "we'd",
        "they'd",
    }
    split_contraction = (
        len(left) > 1
        and left[-1] in {"d", "'d"}
        and left[-2] in {"i", "you", "he", "she", "we", "they"}
    )
    if contracted_had or split_contraction:
        return (
            "lɝnd",
            "A perfect auxiliary selects the past participle.",
            "learned.past-participle",
        )
    return None


_CONTEXT_RULES: dict[str, Callable[[list[str], list[str]], ContextResult | None]] = {
    "minute": _minute,
    "bow": _bow,
    "bass": _bass,
    "lead": _lead,
    "does": _does,
    "refuse": _refuse,
    "learned": _learned,
}


def resolve_english_heteronym(
    surface: str,
    *,
    lemma: str | None = None,
    pos: str | None = None,
    tag: str | None = None,
    morph: str | None = None,
    left_context: str | Sequence[str] | None = None,
    right_context: str | Sequence[str] | None = None,
    sentence_context: str | None = None,
) -> HeteronymDecision | None:
    """Choose a target IPA reading from narrow lexical and contextual evidence.

    The resolver deliberately does not infer a reading from POS alone. Unknown or
    ambiguous contexts return ``None`` so exact-tag lexicon selection and normal
    G2P fallback retain control.
    """
    word = surface.casefold().replace("’", "'")
    rule = _CONTEXT_RULES.get(word)
    if rule is None:
        return None

    left = _tokens(left_context)[-6:]
    right = _tokens(right_context)[:6]
    if not left and not right and sentence_context:
        all_tokens = _tokens(sentence_context)
        try:
            index = all_tokens.index(word)
        except ValueError:
            index = -1
        if index >= 0:
            left = all_tokens[max(0, index - 6) : index]
            right = all_tokens[index + 1 : index + 7]

    result = rule(left, right)
    if result is None:
        return None
    ipa, reason, context_rule = result
    context = " ".join((*left[-4:], surface, *right[:4]))
    return HeteronymDecision(
        word=surface,
        ipa=ipa,
        reason=reason,
        context_rule=context_rule,
        tag=tag,
        pos=pos,
        lemma=lemma,
        morph=morph,
        context=context,
    )


__all__ = ["HeteronymDecision", "resolve_english_heteronym"]
