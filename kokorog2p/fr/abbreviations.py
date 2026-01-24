"""French abbreviation lexicon for G2P processing.

This module contains a comprehensive list of common French abbreviations
and their expansions, organized by category.
"""

import warnings

from kokorog2p.pipeline.abbreviations import (
    AbbreviationEntry,
    AbbreviationExpander,
)


class FrenchAbbreviationExpander(AbbreviationExpander):
    """Expands French abbreviations with context awareness."""

    def _initialize_abbreviations(self) -> None:
        """Initialize comprehensive French abbreviation list."""

        # =====================================================================
        # TITLES AND HONORIFICS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="M.",
                expansion="monsieur",
                description="Mister",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="MM.",
                expansion="messieurs",
                description="Sirs/Gentlemen (plural)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mme",
                expansion="madame",
                description="Mrs/Ms",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mmes",
                expansion="mesdames",
                description="Ladies (plural)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mlle",
                expansion="mademoiselle",
                description="Miss",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mlles",
                expansion="mesdemoiselles",
                description="Misses (plural)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Dr",
                expansion="docteur",
                description="Doctor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Pr",
                expansion="professeur",
                description="Professor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Me",
                expansion="maître",
                description="Master (lawyer)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mgr",
                expansion="monseigneur",
                description="Monsignor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="St",
                expansion="saint",
                description="Saint (male)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ste",
                expansion="sainte",
                description="Saint (female)",
            )
        )

        # =====================================================================
        # DAYS OF THE WEEK
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="lun.",
                expansion="lundi",
                description="Monday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mar.",
                expansion="mardi",
                description="Tuesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mer.",
                expansion="mercredi",
                description="Wednesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="jeu.",
                expansion="jeudi",
                description="Thursday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ven.",
                expansion="vendredi",
                description="Friday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sam.",
                expansion="samedi",
                description="Saturday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="dim.",
                expansion="dimanche",
                description="Sunday",
            )
        )

        # =====================================================================
        # MONTHS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="janv.",
                expansion="janvier",
                description="January",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="févr.",
                expansion="février",
                description="February",
            )
        )

        # mars - no abbreviation

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="avr.",
                expansion="avril",
                description="April",
            )
        )

        # mai - no abbreviation

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="juin",
                expansion="juin",
                description="June (not typically abbreviated)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="juil.",
                expansion="juillet",
                description="July",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="août",
                expansion="août",
                description="August (not typically abbreviated)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sept.",
                expansion="septembre",
                description="September",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="oct.",
                expansion="octobre",
                description="October",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="nov.",
                expansion="novembre",
                description="November",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="déc.",
                expansion="décembre",
                description="December",
            )
        )

        # =====================================================================
        # COMMON ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="etc.",
                expansion="et cetera",
                description="Et cetera",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cf.",
                expansion="confer",
                description="Compare/refer to",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ex.",
                expansion="exemple",
                description="Example",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="p.",
                expansion="page",
                description="Page",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pp.",
                expansion="pages",
                description="Pages",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="vol.",
                expansion="volume",
                description="Volume",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="chap.",
                expansion="chapitre",
                description="Chapter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="éd.",
                expansion="édition",
                description="Edition",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="env.",
                expansion="environ",
                description="Approximately",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="n°",
                expansion="numéro",
                description="Number",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="N°",
                expansion="numéro",
                description="Number (capitalized)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="max.",
                expansion="maximum",
                description="Maximum",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="min.",
                expansion="minimum",
                description="Minimum",
            )
        )

        # =====================================================================
        # TIME UNITS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="h",
                expansion="heure",
                description="Hour",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="min",
                expansion="minute",
                description="Minute",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sec",
                expansion="seconde",
                description="Second",
            )
        )

        # =====================================================================
        # MEASUREMENTS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="km",
                expansion="kilomètre",
                description="Kilometer",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="m",
                expansion="mètre",
                description="Meter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cm",
                expansion="centimètre",
                description="Centimeter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mm",
                expansion="millimètre",
                description="Millimeter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="kg",
                expansion="kilogramme",
                description="Kilogram",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="g",
                expansion="gramme",
                description="Gram",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mg",
                expansion="milligramme",
                description="Milligram",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="l",
                expansion="litre",
                description="Liter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ml",
                expansion="millilitre",
                description="Milliliter",
            )
        )

        # =====================================================================
        # STREETS AND PLACES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="av.",
                expansion="avenue",
                description="Avenue",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="bd",
                expansion="boulevard",
                description="Boulevard",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="rue",
                expansion="rue",
                description="Street (not typically abbreviated)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pl.",
                expansion="place",
                description="Square",
            )
        )


# Create a singleton instance for easy access
_expander: FrenchAbbreviationExpander | None = None
_expander_context_detection: bool | None = None


def get_expander(enable_context_detection: bool = True) -> FrenchAbbreviationExpander:
    """Get the French abbreviation expander instance.

    Args:
        enable_context_detection: Whether to enable context-aware expansion

    Returns:
        The abbreviation expander instance
    """
    global _expander, _expander_context_detection
    if _expander is None:
        _expander = FrenchAbbreviationExpander(
            enable_context_detection=enable_context_detection
        )
        _expander_context_detection = enable_context_detection
    elif _expander_context_detection != enable_context_detection:
        warnings.warn(
            "French abbreviation expander already initialized with "
            f"enable_context_detection={_expander_context_detection}. "
            "Call reset_abbreviations() to rebuild with new settings.",
            RuntimeWarning,
            stacklevel=2,
        )
    return _expander


def reset_expander() -> None:
    """Reset the singleton abbreviation expander."""
    global _expander, _expander_context_detection
    _expander = None
    _expander_context_detection = None
