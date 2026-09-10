"""KokoroG2P candidate profiles and model encoding analysis."""

from __future__ import annotations

from collections.abc import Iterable

from .types import (
    CandidateOutput,
    CandidateProfile,
    CorpusCase,
    EncodingAnalysis,
    ErrorInfo,
)

CANDIDATE_PROFILES: dict[str, CandidateProfile] = {
    "en-us-default": CandidateProfile("en-us-default", "en-us", use_spacy=None),
    "en-gb-default": CandidateProfile("en-gb-default", "en-gb", use_spacy=None),
    "en-us-fallback-only": CandidateProfile(
        "en-us-fallback-only", "en-us", lexicons=(), use_spacy=False
    ),
    "en-gb-fallback-only": CandidateProfile(
        "en-gb-fallback-only", "en-gb", lexicons=(), use_spacy=False
    ),
    "de-default": CandidateProfile("de-default", "de", use_spacy=None),
    "de-gold-none": CandidateProfile(
        "de-gold-none", "de", lexicons=("gold",), fallback="none"
    ),
    "de-gold-espeak": CandidateProfile("de-gold-espeak", "de", lexicons=("gold",)),
    "de-crane-none": CandidateProfile(
        "de-crane-none", "de", lexicons=("crane",), fallback="none"
    ),
    "de-crane-espeak": CandidateProfile("de-crane-espeak", "de", lexicons=("crane",)),
    "de-espeak-primary": CandidateProfile(
        "de-espeak-primary", "de", lexicons=(), fallback="espeak", use_spacy=False
    ),
}


def analyze_model_encoding(phonemes: str, *, model: str = "1.0") -> EncodingAnalysis:
    """Validate and round-trip a phoneme string through a Kokoro model vocabulary."""
    from kokorog2p.vocab import ids_to_phonemes, phonemes_to_ids, validate_for_kokoro

    valid, invalid = validate_for_kokoro(phonemes, model=model)
    token_ids = tuple(phonemes_to_ids(phonemes, model=model))
    decoded = ids_to_phonemes(list(token_ids), model=model)
    return EncodingAnalysis(
        valid=valid,
        invalid_symbols=tuple(dict.fromkeys(invalid)),
        token_ids=token_ids,
        decoded=decoded,
        encoding_loss=not valid or decoded != phonemes,
    )


def _route_dict(route: object) -> dict[str, object]:
    return {
        "char_start": getattr(route, "char_start", None),
        "char_end": getattr(route, "char_end", None),
        "text": getattr(route, "text", ""),
        "default_language": getattr(route, "default_language", ""),
        "reason": getattr(route, "reason", ""),
        "confidence": getattr(route, "confidence", ""),
        "fragments": [
            {
                "text": getattr(fragment, "text", ""),
                "language": getattr(fragment, "language", ""),
                "source": getattr(fragment, "source", ""),
                "evidence_lexicon_id": getattr(fragment, "evidence_lexicon_id", None),
                "evidence_kind": getattr(fragment, "evidence_kind", None),
            }
            for fragment in getattr(route, "fragments", ())
        ],
    }


def run_candidate(case: CorpusCase, profile: CandidateProfile) -> CandidateOutput:
    """Run one reviewed case through the public prepared-text API."""
    try:
        from kokorog2p import phonemize_prepared

        result = phonemize_prepared(
            case.text,
            language=profile.language,
            lexicons=profile.lexicons,
            use_espeak_fallback=profile.fallback == "espeak",
            use_goruut_fallback=profile.fallback == "goruut"
            or profile.use_goruut_fallback,
            use_spacy=profile.use_spacy,
            spacy_model=profile.spacy_model,
            backend=profile.backend,
            target_model=profile.target_model,
            return_phonemes=True,
            return_ids=True,
        )
        phonemes = result.phonemes or ""
        encoding = analyze_model_encoding(phonemes, model=profile.target_model)
        return CandidateOutput(
            case_id=case.id,
            input_text=case.text,
            clean_text=result.clean_text,
            phonemes=phonemes,
            token_ids=tuple(result.token_ids or ()),
            encoding=encoding,
            warnings=tuple(result.warnings or ()),
            language_routes=tuple(
                _route_dict(route) for route in result.language_routes
            ),
        )
    except Exception as exc:
        return CandidateOutput(
            case_id=case.id,
            input_text=case.text,
            error=ErrorInfo.from_exception(exc, "candidate"),
        )


def run_candidates(
    cases: Iterable[CorpusCase], profile: CandidateProfile
) -> tuple[CandidateOutput, ...]:
    return tuple(run_candidate(case, profile) for case in cases)
