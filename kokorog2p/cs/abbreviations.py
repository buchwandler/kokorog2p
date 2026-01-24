"""Czech abbreviation expansion for kokorog2p.

This module provides Czech-specific abbreviation expansion,
including titles, days, months, streets, and common abbreviations.
"""

from __future__ import annotations

import warnings

from kokorog2p.pipeline.abbreviations import (
    AbbreviationEntry,
    AbbreviationExpander,
)

# Singleton instance
_expander_instance: CzechAbbreviationExpander | None = None
_expander_context_detection: bool | None = None


class CzechAbbreviationExpander(AbbreviationExpander):
    """Expand common Czech abbreviations to full words."""

    def _initialize_abbreviations(self) -> None:
        """Initialize Czech abbreviations."""

        # =====================================================================
        # TITLES (Czech uses many academic and professional titles)
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ing.",
                expansion="Inženýr",
                description="Title for Engineer",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mgr.",
                expansion="Magistr",
                description="Title for Master's degree holder",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="MUDr.",
                expansion="Medicíny univerzitní doktor",
                description="Title for Medical Doctor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="PhDr.",
                expansion="Philosophiae doctor",
                description="Title for Doctor of Philosophy",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Prof.",
                expansion="Profesor",
                description="Title for Professor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Dr.",
                expansion="Doktor",
                description="Title for Doctor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Bc.",
                expansion="Bakalář",
                description="Title for Bachelor's degree",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="JUDr.",
                expansion="Juris utriusque doctor",
                description="Title for Doctor of Law",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="RNDr.",
                expansion="Rerum naturalium doctor",
                description="Title for Doctor of Natural Sciences",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="MVDr.",
                expansion="Medicíny veterinární doktor",
                description="Title for Veterinary Doctor",
            )
        )

        # =====================================================================
        # DAYS OF THE WEEK
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="po.",
                expansion="pondělí",
                description="Monday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pon.",
                expansion="pondělí",
                description="Monday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="út.",
                expansion="úterý",
                description="Tuesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="st.",
                expansion="středa",
                description="Wednesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="stř.",
                expansion="středa",
                description="Wednesday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="čt.",
                expansion="čtvrtek",
                description="Thursday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pá.",
                expansion="pátek",
                description="Friday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="so.",
                expansion="sobota",
                description="Saturday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ne.",
                expansion="neděle",
                description="Sunday",
            )
        )

        # =====================================================================
        # MONTHS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="led.",
                expansion="leden",
                description="January",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="úno.",
                expansion="únor",
                description="February",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="bře.",
                expansion="březen",
                description="March",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="dub.",
                expansion="duben",
                description="April",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="kvě.",
                expansion="květen",
                description="May",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="čvn.",
                expansion="červen",
                description="June",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="čvc.",
                expansion="červenec",
                description="July",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="srp.",
                expansion="srpen",
                description="August",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="zář.",
                expansion="září",
                description="September",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="říj.",
                expansion="říjen",
                description="October",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="lis.",
                expansion="listopad",
                description="November",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pro.",
                expansion="prosinec",
                description="December",
            )
        )

        # =====================================================================
        # STREETS AND PLACES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ul.",
                expansion="ulice",
                description="Street",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="nám.",
                expansion="náměstí",
                description="Square",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tř.",
                expansion="třída",
                description="Avenue/Boulevard",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="nábř.",
                expansion="nábřeží",
                description="Embankment/Waterfront",
            )
        )

        # =====================================================================
        # COMMON ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="atd.",
                expansion="a tak dále",
                description="Et cetera (and so on)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="apod.",
                expansion="a podobně",
                description="And similarly",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="např.",
                expansion="například",
                description="For example",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tzn.",
                expansion="to znamená",
                description="That means",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tzv.",
                expansion="takzvaný",
                description="So-called",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="resp.",
                expansion="respektive",
                description="Respectively",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tj.",
                expansion="to jest",
                description="That is",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Str.",
                expansion="strana",
                description="Page",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="str.",
                expansion="strana",
                description="Page (lowercase)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="s.",
                expansion="strana",
                description="Page (short form)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="č.",
                expansion="číslo",
                description="Number",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="čp.",
                expansion="číslo popisné",
                description="House number",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="odd.",
                expansion="oddíl",
                description="Section/Department",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="kap.",
                expansion="kapitola",
                description="Chapter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="obr.",
                expansion="obrázek",
                description="Picture/Figure",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tab.",
                expansion="tabulka",
                description="Table",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pozn.",
                expansion="poznámka",
                description="Note",
            )
        )

        # =====================================================================
        # TIME UNITS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="hod.",
                expansion="hodina",
                description="Hour",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="min.",
                expansion="minuta",
                description="Minute",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sek.",
                expansion="sekunda",
                description="Second",
            )
        )

        # =====================================================================
        # MEASUREMENTS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="km",
                expansion="kilometr",
                description="Kilometer",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="m",
                expansion="metr",
                description="Meter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cm",
                expansion="centimetr",
                description="Centimeter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mm",
                expansion="milimetr",
                description="Millimeter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="kg",
                expansion="kilogram",
                description="Kilogram",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="g",
                expansion="gram",
                description="Gram",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="l",
                expansion="litr",
                description="Liter",
            )
        )

        # =====================================================================
        # ORGANIZATIONS & COMPANIES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="s.r.o.",
                expansion="společnost s ručením omezeným",
                description="Limited Liability Company",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="a.s.",
                expansion="akciová společnost",
                description="Joint-stock company",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="o.p.s.",
                expansion="obecně prospěšná společnost",
                description="Public benefit corporation",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="o.s.",
                expansion="občanské sdružení",
                description="Civic association",
            )
        )


def get_expander(enable_context_detection: bool = True) -> CzechAbbreviationExpander:
    """Get the singleton Czech abbreviation expander instance.

    Args:
        enable_context_detection: Whether to enable context-aware expansion.
            If False, uses simple pattern matching without context analysis.

    Returns:
        The Czech abbreviation expander instance.
    """
    global _expander_instance, _expander_context_detection
    if _expander_instance is None:
        _expander_instance = CzechAbbreviationExpander(
            enable_context_detection=enable_context_detection
        )
        _expander_context_detection = enable_context_detection
    elif _expander_context_detection != enable_context_detection:
        warnings.warn(
            "Czech abbreviation expander already initialized with "
            f"enable_context_detection={_expander_context_detection}. "
            "Call reset_abbreviations() to rebuild with new settings.",
            RuntimeWarning,
            stacklevel=2,
        )
    return _expander_instance


def reset_expander() -> None:
    """Reset the singleton abbreviation expander."""
    global _expander_instance, _expander_context_detection
    _expander_instance = None
    _expander_context_detection = None
