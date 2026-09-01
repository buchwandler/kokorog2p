"""Cross-package checks for the abbr2words abbreviation source of truth."""

from importlib.metadata import version

from abbr2words import abbr2words, get_shared_expander

from kokorog2p import reset_abbreviations
from kokorog2p.en.normalizer import EnglishNormalizer
from kokorog2p.pipeline_api import _expand_abbreviation, _get_abbreviation_expander


def test_runtime_abbr2words_is_the_unit_capable_release():
    installed = tuple(int(part) for part in version("abbr2words").split(".")[:3])
    assert (0, 2, 9) <= installed < (0, 3, 0)
    expander = get_shared_expander("de", context=True)
    assert hasattr(expander, "expand")
    assert expander.expand("1,5 kg") == "1,5 Kilogramm"


def test_abbr2words_029_lexical_policy_reaches_migrated_consumers() -> None:
    """Smoke-test the 0.2.9 lexical policy without copying its matching rules."""

    assert abbr2words("GmbH AG", lang="de") == "G m b H A G"
    assert EnglishNormalizer()("No. 244") == "No. 244"


def test_shared_custom_entry_reaches_all_kokorog2p_consumers() -> None:
    reset_abbreviations()
    shared = get_shared_expander("en")
    shared.add_custom_abbreviation("X.Y.", "Ex Why")

    assert abbr2words("X.Y.", lang="en") == "Ex Why."
    normalizer = EnglishNormalizer()
    assert normalizer.normalize("X.Y.")[0] == "X.Y."
    assert _get_abbreviation_expander("en-us") is None
    assert _expand_abbreviation("X.Y.", "", "", "en-us") is None

    reset_abbreviations()
    assert abbr2words("X.Y.", lang="en") == "Ex Why."
