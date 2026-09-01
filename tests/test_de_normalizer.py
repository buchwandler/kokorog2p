"""Regression tests for structured German normalization."""

from importlib import resources
from itertools import pairwise
from pathlib import Path

import pytest

from kokorog2p.de.g2p import GermanG2P
from kokorog2p.de.normalizer import GermanNormalizer
from kokorog2p.de.numbers import iter_structured_replacements


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
        ("etc.", "et cetera"),
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
        ("GmbH AG", "G m b H A G"),
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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 mm²", "ein Quadratmillimeter"),
        ("2 mm²", "zwei Quadratmillimeter"),
        ("1 cm²", "ein Quadratzentimeter"),
        ("2 cm²", "zwei Quadratzentimeter"),
        ("1 m²", "ein Quadratmeter"),
        ("2 m²", "zwei Quadratmeter"),
        ("1 km²", "ein Quadratkilometer"),
        ("2 km²", "zwei Quadratkilometer"),
        ("1 ha", "ein Hektar"),
        ("2 ha", "zwei Hektar"),
        ("1 mm³", "ein Kubikmillimeter"),
        ("2 mm³", "zwei Kubikmillimeter"),
        ("1 cm³", "ein Kubikzentimeter"),
        ("2 cm³", "zwei Kubikzentimeter"),
        ("1 m³", "ein Kubikmeter"),
        ("2 m³", "zwei Kubikmeter"),
        ("1 m/s", "ein Meter pro Sekunde"),
        ("2 m/s", "zwei Meter pro Sekunde"),
        ("1 km/h", "ein Kilometer pro Stunde"),
        ("2 km/h", "zwei Kilometer pro Stunde"),
        ("1 m2", "ein Quadratmeter"),
        ("1 m3", "ein Kubikmeter"),
        ("1 cm2", "ein Quadratzentimeter"),
        ("1 cm3", "ein Kubikzentimeter"),
    ],
)
def test_extended_quantities_use_released_spokenform_grammar(
    normalizer, source, expected
):
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
    assert normalizer("g m kg km cm mm mA MHz W V ltr. Ltr.") == (
        "g m kg km cm mm mA MHz W V ltr. Ltr."
    )


def test_numbered_unit_boundaries_and_attached_forms(normalizer):
    assert normalizer("Model5kg abcg") == "Model5kg abcg"
    assert normalizer("3cm 3 cm 3\u00a0cm") == (
        "drei Zentimeter drei Zentimeter drei Zentimeter"
    )


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


@pytest.mark.parametrize(
    ("source", "month"),
    [
        ("15.01.2026", "Januar"),
        ("15.02.2026", "Februar"),
        ("15.03.2026", "März"),
        ("15.04.2026", "April"),
        ("15.05.2026", "Mai"),
        ("15.06.2026", "Juni"),
        ("15.07.2026", "Juli"),
        ("15.08.2026", "August"),
        ("15.09.2026", "September"),
        ("15.10.2026", "Oktober"),
        ("15.11.2026", "November"),
        ("15.12.2026", "Dezember"),
    ],
)
def test_numeric_date_month_mapping(normalizer, source, month):
    assert month in normalizer(source)


def test_dates_times_and_invalid_forms(normalizer):
    assert normalizer("03.01.2026") == "dritte Januar zweitausendsechsundzwanzig"
    assert normalizer("3.1.2026") == "dritte Januar zweitausendsechsundzwanzig"
    assert normalizer("14.05.2026") == "vierzehnte Mai zweitausendsechsundzwanzig"
    assert (
        normalizer("31.12.2026")
        == "einunddreißigste Dezember zweitausendsechsundzwanzig"
    )
    assert normalizer("am 3. Januar 2026") == (
        "am dritten Januar zweitausendsechsundzwanzig"
    )
    assert (
        normalizer("Zum 14.05.2026") == "Zum vierzehnten Mai zweitausendsechsundzwanzig"
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
    assert normalizer("20°") == "zwanzig Grad"


def test_contextual_ordinal_before_capitalized_noun(normalizer):
    assert normalizer("auf die 2. Schiene") == "auf die zweite Schiene"
    assert normalizer("im 3. Kapitel") == "im dritten Kapitel"
    assert normalizer("die 4. Version") == "die vierte Version"
    assert normalizer("der 5. Abschnitt") == "der fünfte Abschnitt"
    assert normalizer("zur 6. Version") == "zur sechsten Version"
    assert normalizer("auf der 7. Etage") == "auf der siebten Etage"
    assert normalizer("in dem 8. Raum") == "in dem achten Raum"
    assert normalizer("vom 9. März 2026") == (
        "vom neunten März zweitausendsechsundzwanzig"
    )
    assert normalizer("Nummer 2. bleibt") == "Nummer zwei. bleibt"


def test_requested_cooking_paragraph(normalizer):
    source = (
        "Zum 14.05.2026 um 18:20 Uhr ist das Abendessen geplant. "
        "Für den Auflauf brauchen wir 1,5 kg Kartoffeln, 500 g Quark, "
        "2 Eier, 1 ltr. Milch und ggf. 3 cm mehr Backpapier. "
        'Prof. Klein sagt: "Bitte stelle die Form auf die 2. Schiene, '
        "backe alles für 45 Min. und lass es danach 1 Min. oder auch "
        '2 Min. ruhen." Die Kosten liegen bei ca. 12,80 EUR zzgl. Pfand.'
    )
    expected = (
        "Zum vierzehnten Mai zweitausendsechsundzwanzig um achtzehn Uhr "
        "zwanzig ist das Abendessen geplant. Für den Auflauf brauchen wir "
        "eins Komma fünf Kilogramm Kartoffeln, fünfhundert Gramm Quark, "
        "zwei Eier, ein Liter Milch und gegebenenfalls drei Zentimeter mehr "
        'Backpapier. Professor Klein sagt: "Bitte stelle die Form auf die '
        "zweite Schiene, backe alles für fünfundvierzig Minuten und lass es "
        'danach eine Minute oder auch zwei Minuten ruhen." Die Kosten liegen '
        "bei zirka zwölf Euro achtzig Cent zuzüglich Pfand."
    )
    assert normalizer(source) == expected


def test_requested_cooking_paragraph_reaches_rule_based_g2p(normalizer):
    source = (
        "Zum 14.05.2026 um 18:20 Uhr ist das Abendessen geplant. "
        "Für den Auflauf brauchen wir 1,5 kg Kartoffeln, 500 g Quark, "
        "2 Eier, 1 ltr. Milch und ggf. 3 cm mehr Backpapier. "
        'Prof. Klein sagt: "Bitte stelle die Form auf die 2. Schiene, '
        "backe alles für 45 Min. und lass es danach 1 Min. oder auch "
        '2 Min. ruhen." Die Kosten liegen bei ca. 12,80 EUR zzgl. Pfand.'
    )
    g2p = GermanG2P(
        use_lexicon=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )

    tokens = g2p(normalizer(source))

    assert all(
        not any(character.isdigit() for character in token.text) for token in tokens
    )
    assert all(token.text == "." or "." not in token.text for token in tokens)
    assert all(
        token.phonemes != "?"
        for token in tokens
        if any(character.isalnum() for character in token.text)
    )


def test_structured_numbers_are_independent_of_lexical_abbreviations():
    normalizer = GermanNormalizer(expand_abbreviations=False)
    assert normalizer("1 Std. 42 kg") == "eine Stunde zweiundvierzig Kilogramm"
    assert normalizer("z.B. 42") == "z.B. zweiundvierzig"


def test_structured_normalization_is_tracked():
    normalizer = GermanNormalizer(track_changes=True)
    normalized, changes = normalizer.normalize("2 kg")
    assert normalized == "zwei Kilogramm"
    assert any(change.rule_name == "german_structured_numbers" for change in changes)


def test_structured_replacements_are_source_aligned_and_prioritized():
    source = "1,5 kg und 12,80 EUR sowie 32.13.2026"
    replacements = iter_structured_replacements(source)

    assert [(item.start, item.end, item.kind, item.text) for item in replacements] == [
        (0, 6, "unit", "eins Komma fünf Kilogramm"),
        (11, 20, "currency_suffix", "zwölf Euro achtzig Cent"),
    ]
    assert all(left.end <= right.start for left, right in pairwise(replacements))
    assert not iter_structured_replacements("32.13.2026")
    assert not iter_structured_replacements("25:99")


def test_german_lexicon_data_is_packaged():
    source_file = (
        Path(__file__).parents[1] / "lexicons" / "sources" / "de" / "de_gold.json"
    )
    assert source_file.is_file()
    assert (
        resources.files("kokorog2p.lexicons.data").joinpath("de_gold.g2lex").is_file()
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1.234 EUR", "eintausendzweihundertvierunddreißig Euro"),
        ("EUR 1.234", "eintausendzweihundertvierunddreißig Euro"),
        ("-1.234 EUR", "minus eintausendzweihundertvierunddreißig Euro"),
        (
            "1.234,56 EUR",
            "eintausendzweihundertvierunddreißig Euro sechsundfünfzig Cent",
        ),
    ],
)
def test_grouped_integer_currency_keeps_currency_name(normalizer, source, expected):
    assert normalizer(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("45 min. backen", "fünfundvierzig Minuten backen"),
        ("1 MIN. warten", "eine Minute warten"),
        ("1 Ltr. Milch", "ein Liter Milch"),
        ("2 STCK. Eier", "zwei Stück Eier"),
        ("1 mio.", "eine Million."),
        ("2 mrd.", "zwei Milliarden."),
    ],
)
def test_numbered_unit_case_variants_use_numeric_grammar(normalizer, source, expected):
    assert normalizer(source) == expected


def test_minimum_and_minute_abbreviations_do_not_collide(normalizer):
    assert normalizer("min. 5 Zeichen") == "minimal fünf Zeichen"
    assert normalizer("Min. Beispiel") == "Min. Beispiel"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("(Prof.) Klein", "(Professor) Klein"),
        ('Er sagte "ggf."', 'Er sagte "gegebenenfalls"'),
        ("Prof.–Klein", "Professor—Klein"),
        ("Dr.foo", "Dr.foo"),
    ],
)
def test_dotted_abbreviations_before_closers_and_punctuation(
    normalizer, source, expected
):
    assert normalizer(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("an der 2. Stelle", "an der zweiten Stelle"),
        ("auf den 2. Rost", "auf den zweiten Rost"),
        ("in den 3. Raum", "in den dritten Raum"),
        ("ins 4. Fach", "ins vierte Fach"),
        ("ans 5. Ende", "ans fünfte Ende"),
    ],
)
def test_contextual_ordinals_keep_full_prepositional_context(
    normalizer, source, expected
):
    assert normalizer(source) == expected
