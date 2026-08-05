"""Regression tests for structured German normalization."""

from pathlib import Path

import pytest

from kokorog2p.de.normalizer import GermanNormalizer


@pytest.fixture
def normalizer() -> GermanNormalizer:
    return GermanNormalizer()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Lfd. Nr. 12.", "laufende Nummer zwölf."),
        ("z.B. ein Test", "zum Beispiel ein Test"),
        ("z. B. ein Test", "zum Beispiel ein Test"),
        ("z.\tB. ein Test", "zum Beispiel ein Test"),
        ("zB ein Test", "zum Beispiel ein Test"),
        ("d.h. heute", "das heißt heute"),
        ("d. h. heute", "das heißt heute"),
        ("u.a. Bücher", "unter anderem Bücher"),
        ("u. a. Bücher", "unter anderem Bücher"),
        ("etc.", "ezetera"),
        ("usw.", "und so weiter"),
        ("ca.", "zirka"),
        ("ggf.", "gegebenenfalls"),
        ("zzgl.", "zuzüglich"),
        (
            "Dr. Prof. Abk. Abb. geb. bspw.",
            "Doktor Professor Abkürzung Abbildung geboren beispielsweise",
        ),
        ("Nr. ggü. Kap. Abs.", "Nummer gegenüber Kapitel Absatz"),
        ("Tsd. Mio. Mrd.", "Tausend Millionen Milliarden"),
        ("S. 12", "Seite zwölf"),
        ("GmbH AG", "Geh Em Beh Hah Ah Geh"),
    ],
)
def test_requested_lexical_abbreviations(normalizer, source, expected):
    assert normalizer(source) == expected


def test_abbreviation_false_positive_protection(normalizer):
    assert normalizer("Variable z b bleibt") == "Variable z b bleibt"
    assert normalizer("b. Abschnitt") == "b. Abschnitt"
    assert normalizer("Ein Satz endet mit z.") == "Ein Satz endet mit z."
    assert normalizer("S. Müller") == "S. Müller"
    assert normalizer("ag ist ein Wort") == "ag ist ein Wort"
    assert normalizer("G-M-B-H G M B H") == "G-M-B-H G M B H"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 kWh", "eine Kilowattstunde"),
        ("2 kWh", "zwei Kilowattstunden"),
        ("1 Wh", "eine Wattstunde"),
        ("2 Wh", "zwei Wattstunden"),
        ("1 GHz", "ein Gigahertz"),
        ("2 MHz", "zwei Megahertz"),
        ("2 kHz", "zwei Kilohertz"),
        ("2 Hz", "zwei Hertz"),
        ("1 Std.", "eine Stunde."),
        ("2 Std.", "zwei Stunden."),
        ("1 Min.", "eine Minute."),
        ("2 Min.", "zwei Minuten."),
        ("1 Sek.", "eine Sekunde."),
        ("2 Sek.", "zwei Sekunden."),
        ("1 Stck.", "ein Stück."),
        ("2 Stck.", "zwei Stück."),
        ("1 mAh", "eine Milliamperestunde"),
        ("2 mAh", "zwei Milliamperestunden"),
        ("1 mA", "ein Milliampere"),
        ("2 mA", "zwei Milliampere"),
        ("1 kg", "ein Kilogramm"),
        ("2 kg", "zwei Kilogramm"),
        ("1 g", "ein Gramm"),
        ("2 g", "zwei Gramm"),
        ("1 km", "ein Kilometer"),
        ("2 km", "zwei Kilometer"),
        ("1 cm", "ein Zentimeter"),
        ("2 mm", "zwei Millimeter"),
        ("1 m3", "ein Kubikmeter"),
        ("2 m³", "zwei Kubikmeter"),
        ("1 m", "ein Meter"),
        ("2 ltr.", "zwei Liter."),
        ("1 EUR", "ein Euro"),
        ("2 W", "zwei Watt"),
        ("1 V", "ein Volt"),
        ("1 Tsd.", "ein Tausend."),
        ("1 Mio.", "eine Million."),
        ("2 Mio.", "zwei Millionen."),
        ("1 Mrd.", "eine Milliarde."),
        ("2 Mrd.", "zwei Milliarden."),
    ],
)
def test_numbered_units(normalizer, source, expected):
    assert normalizer(source) == expected


def test_numbered_units_handle_decimals_negatives_and_overlap(normalizer):
    assert normalizer("1,0 kg") == "ein Kilogramm"
    assert normalizer("1,5 kg") == "eins Komma fünf Kilogramm"
    assert normalizer("-2 kg") == "minus zwei Kilogramm"
    assert normalizer("2kg, 3kWh, 4mAh") == (
        "zwei Kilogramm, drei Kilowattstunden, vier Milliamperestunden"
    )
    assert normalizer("2 mA, 2 ma") == "zwei Milliampere, zwei ma"
    assert normalizer("G-M-B-H") == "G-M-B-H"


def test_unit_letters_are_not_expanded_without_numbers(normalizer):
    assert normalizer("g m kg km cm mm mA MHz W V") == "g m kg km cm mm mA MHz W V"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 EUR", "ein Euro"),
        ("2 EUR", "zwei Euro"),
        ("12,50 EUR", "zwölf Euro fünfzig Cent"),
        ("12.50 EUR", "zwölf Euro fünfzig Cent"),
        ("-1,25 EUR", "minus ein Euro fünfundzwanzig Cent"),
        ("0,05 EUR", "null Euro fünf Cent"),
        ("EUR 12,50", "zwölf Euro fünfzig Cent"),
    ],
)
def test_currency(normalizer, source, expected):
    assert normalizer(source) == expected


def test_dates_times_and_invalid_forms(normalizer):
    assert normalizer("03.01.2026") == "dritte Januar zweitausendsechsundzwanzig"
    assert normalizer("3.1.2026") == "dritte Januar zweitausendsechsundzwanzig"
    assert (
        normalizer("am 3. Januar 2026") == "am dritte Januar zweitausendsechsundzwanzig"
    )
    assert normalizer("14:05") == "vierzehn Uhr fünf"
    assert normalizer("14:05 Uhr") == "vierzehn Uhr fünf"
    assert normalizer("01:00") == "ein Uhr"
    assert normalizer("32.13.2026") == "32.13.2026"
    assert normalizer("25:99") == "25:99"


def test_temperature_and_numeric_classification(normalizer):
    assert normalizer("3°C") == "drei Grad Celsius"
    assert normalizer("3 °C") == "drei Grad Celsius"
    assert normalizer("3,5°C") == "drei Komma fünf Grad Celsius"
    assert normalizer("-1,2 °C") == "minus eins Komma zwei Grad Celsius"
    assert normalizer("1.000") == "eintausend"
    assert normalizer("1.000,50") == "eintausend Komma fünf null"
    assert normalizer("3,14") == "drei Komma eins vier"
    assert normalizer(".02") == "null Komma null zwei"
    assert normalizer(",02") == "null Komma null zwei"
    assert normalizer("Nummer 12.") == "Nummer zwölf."
    assert normalizer("Gleis 7.") == "Gleis sieben."
    assert normalizer("am 3. Tag") == "am dritten Tag"
    assert normalizer("der 3. Versuch") == "der dritte Versuch"
    assert normalizer("20°") == "zwanzig°"


def test_structured_numbers_are_independent_of_lexical_abbreviations():
    normalizer = GermanNormalizer(expand_abbreviations=False)
    assert normalizer("1 Std. 42 kg") == "eine Stunde zweiundvierzig Kilogramm"
    assert normalizer("z.B. 42") == "z.B. zweiundvierzig"


def test_structured_normalization_is_tracked():
    normalizer = GermanNormalizer(track_changes=True)
    normalized, changes = normalizer.normalize("2 kg")
    assert normalized == "zwei Kilogramm"
    assert any(change.rule_name == "german_structured_numbers" for change in changes)


def test_german_lexicon_data_is_packaged():
    data_file = Path(__file__).parents[1] / "kokorog2p" / "de" / "data" / "de_gold.json"
    assert data_file.is_file()
