"""Portuguese abbreviation expansion for kokorog2p.

This module provides Portuguese-specific abbreviation expansion,
including titles, days, months, streets, and common abbreviations.

Supports both European Portuguese (pt-PT) and Brazilian Portuguese (pt-BR).
"""

from __future__ import annotations

import warnings

from kokorog2p.pipeline.abbreviations import (
    AbbreviationEntry,
    AbbreviationExpander,
)

# Singleton instance
_expander_instance: PortugueseAbbreviationExpander | None = None
_expander_context_detection: bool | None = None


class PortugueseAbbreviationExpander(AbbreviationExpander):
    """Expand common Portuguese abbreviations to full words."""

    def _initialize_abbreviations(self) -> None:
        """Initialize Portuguese abbreviations."""

        # =====================================================================
        # TITLES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sr.",
                expansion="Senhor",
                description="Title for Mr.",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sra.",
                expansion="Senhora",
                description="Title for Mrs.",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Srta.",
                expansion="Senhorita",
                description="Title for Miss",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Dr.",
                expansion="Doutor",
                description="Title for Doctor (male)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Dra.",
                expansion="Doutora",
                description="Title for Doctor (female)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Prof.",
                expansion="Professor",
                description="Title for Professor (male)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Profa.",
                expansion="Professora",
                description="Title for Professor (female)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Eng.",
                expansion="Engenheiro",
                description="Title for Engineer",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Arq.",
                expansion="Arquiteto",
                description="Title for Architect",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Adv.",
                expansion="Advogado",
                description="Title for Lawyer",
            )
        )

        # =====================================================================
        # DAYS OF THE WEEK
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="seg.",
                expansion="segunda-feira",
                description="Monday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="2ª",
                expansion="segunda-feira",
                description="Monday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ter.",
                expansion="terça-feira",
                description="Tuesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="3ª",
                expansion="terça-feira",
                description="Tuesday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="qua.",
                expansion="quarta-feira",
                description="Wednesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="4ª",
                expansion="quarta-feira",
                description="Wednesday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="qui.",
                expansion="quinta-feira",
                description="Thursday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="5ª",
                expansion="quinta-feira",
                description="Thursday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sex.",
                expansion="sexta-feira",
                description="Friday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="6ª",
                expansion="sexta-feira",
                description="Friday (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sáb.",
                expansion="sábado",
                description="Saturday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="dom.",
                expansion="domingo",
                description="Sunday",
            )
        )

        # =====================================================================
        # MONTHS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="jan.",
                expansion="janeiro",
                description="January",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="fev.",
                expansion="fevereiro",
                description="February",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mar.",
                expansion="março",
                description="March",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="abr.",
                expansion="abril",
                description="April",
            )
        )

        # Maio (May) is not typically abbreviated

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="jun.",
                expansion="junho",
                description="June",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="jul.",
                expansion="julho",
                description="July",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ago.",
                expansion="agosto",
                description="August",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="set.",
                expansion="setembro",
                description="September",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="out.",
                expansion="outubro",
                description="October",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="nov.",
                expansion="novembro",
                description="November",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="dez.",
                expansion="dezembro",
                description="December",
            )
        )

        # =====================================================================
        # STREETS AND PLACES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="R.",
                expansion="Rua",
                description="Street",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Av.",
                expansion="Avenida",
                description="Avenue",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Avda.",
                expansion="Avenida",
                description="Avenue (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Pç.",
                expansion="Praça",
                description="Square/Plaza",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Pça.",
                expansion="Praça",
                description="Square (alternate)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Trav.",
                expansion="Travessa",
                description="Alley/Lane",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Lgo.",
                expansion="Largo",
                description="Small square",
            )
        )

        # =====================================================================
        # COMMON ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="etc.",
                expansion="etcétera",
                description="Et cetera",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pág.",
                expansion="página",
                description="Page",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="págs.",
                expansion="páginas",
                description="Pages",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="p.",
                expansion="página",
                description="Page (short form)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pp.",
                expansion="páginas",
                description="Pages (short form)",
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
                abbreviation="cap.",
                expansion="capítulo",
                description="Chapter",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="nº",
                expansion="número",
                description="Number",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="n.º",
                expansion="número",
                description="Number (European Portuguese form)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="art.",
                expansion="artigo",
                description="Article",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cf.",
                expansion="confira",
                description="Compare (confer)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="aprox.",
                expansion="aproximadamente",
                description="Approximately",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ed.",
                expansion="edição",
                description="Edition",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ex.",
                expansion="exemplo",
                description="Example",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="p.ex.",
                expansion="por exemplo",
                description="For example",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="obs.",
                expansion="observação",
                description="Observation/note",
            )
        )

        # =====================================================================
        # TIME UNITS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="h",
                expansion="horas",
                description="Hour(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="min",
                expansion="minutos",
                description="Minute(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="min.",
                expansion="minutos",
                description="Minute(s) with period",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="seg",
                expansion="segundos",
                description="Second(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="seg.",
                expansion="segundos",
                description="Second(s) with period",
            )
        )

        # Note: "seg." can also mean segunda-feira (Monday), context matters

        # =====================================================================
        # MEASUREMENTS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="km",
                expansion="quilômetros",  # Brazilian spelling
                description="Kilometer(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="m",
                expansion="metros",
                description="Meter(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cm",
                expansion="centímetros",
                description="Centimeter(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mm",
                expansion="milímetros",
                description="Millimeter(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="kg",
                expansion="quilogramas",  # Brazilian spelling
                description="Kilogram(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="g",
                expansion="gramas",
                description="Gram(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mg",
                expansion="miligramas",
                description="Milligram(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="l",
                expansion="litros",
                description="Liter(s)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ml",
                expansion="mililitros",
                description="Milliliter(s)",
            )
        )

        # =====================================================================
        # BUSINESS & ORGANIZATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="S.A.",
                expansion="Sociedade Anônima",  # Brazilian
                description="Corporation (Brazilian)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ltda.",
                expansion="Limitada",
                description="Limited Liability Company",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Cia.",
                expansion="Companhia",
                description="Company",
            )
        )


def get_expander(
    enable_context_detection: bool = True,
) -> PortugueseAbbreviationExpander:
    """Get the singleton Portuguese abbreviation expander instance.

    Args:
        enable_context_detection: Whether to enable context-aware expansion.
            If False, uses simple pattern matching without context analysis.

    Returns:
        The Portuguese abbreviation expander instance.
    """
    global _expander_instance, _expander_context_detection
    if _expander_instance is None:
        _expander_instance = PortugueseAbbreviationExpander(
            enable_context_detection=enable_context_detection
        )
        _expander_context_detection = enable_context_detection
    elif _expander_context_detection != enable_context_detection:
        warnings.warn(
            "Portuguese abbreviation expander already initialized with "
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
