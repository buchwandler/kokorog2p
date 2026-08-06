"""Cross-package checks for the abbr2words abbreviation source of truth."""

from abbr2words import abbr2words, get_shared_expander
from kokorog2p import reset_abbreviations
from kokorog2p.abbreviation_utils import get_abbreviation_entries
from kokorog2p.en.normalizer import EnglishNormalizer
from kokorog2p.pipeline_api import _expand_abbreviation, _get_abbreviation_expander


def test_shared_custom_entry_reaches_all_kokorog2p_consumers() -> None:
    reset_abbreviations()
    shared = get_shared_expander("en")
    shared.add_custom_abbreviation("X.Y.", "Ex Why")

    assert abbr2words("X.Y.", lang="en") == "Ex Why"
    assert EnglishNormalizer().normalize_token("X.Y.") == "Ex Why"
    assert ("X.Y.", False) in get_abbreviation_entries("en-us")
    assert _get_abbreviation_expander("en-us") is shared
    assert _expand_abbreviation("X.Y.", "", "", "en-us") == "Ex Why"

    reset_abbreviations()

    assert abbr2words("X.Y.", lang="en") == "X.Y."
    assert ("X.Y.", False) not in get_abbreviation_entries("en-us")

