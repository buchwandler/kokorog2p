"""English abbreviation lexicon for G2P processing.

This module contains a comprehensive list of common English abbreviations
and their expansions, organized by category.
"""

import warnings

from kokorog2p.pipeline.abbreviations import (
    AbbreviationContext,
    AbbreviationEntry,
    AbbreviationExpander,
)


class EnglishAbbreviationExpander(AbbreviationExpander):
    """Expands English abbreviations with context awareness."""

    def add_custom_abbreviation(
        self,
        abbreviation: str,
        expansion: str | dict[str, str],
        description: str = "",
        case_sensitive: bool = False,
    ) -> None:
        """Add or update a custom abbreviation (user-friendly API).

        This provides a convenient way to add custom abbreviations
        or override existing ones without constructing entries.

        Args:
            abbreviation: The abbreviation string (e.g., "Dr.", "Tech.")
            expansion: Either a simple string expansion or a dict mapping context
                names to expansions. For dict, use context names like:
                "default", "title", "place", "time", "academic", "religious"
            description: Optional description of the abbreviation
            case_sensitive: Whether matching should be case-sensitive

        Examples:
            >>> expander = get_expander()
            >>> # Simple expansion
            >>> expander.add_custom_abbreviation("Tech.", "Technology")
            >>> # Context-aware expansion
            >>> expander.add_custom_abbreviation(
            ...     "Dr.",
            ...     {"default": "Drive", "title": "Doctor"},
            ...     "Doctor or Drive (context-dependent)"
            ... )
        """
        # Handle dict-based context expansions
        context_expansions = None
        default_expansion = expansion

        if isinstance(expansion, dict):
            # Convert string keys to AbbreviationContext enums
            context_expansions = {}
            for key, value in expansion.items():
                key_lower = key.lower()
                if key_lower == "default":
                    default_expansion = value
                elif key_lower == "title":
                    context_expansions[AbbreviationContext.TITLE] = value
                elif key_lower == "place":
                    context_expansions[AbbreviationContext.PLACE] = value
                elif key_lower == "time":
                    context_expansions[AbbreviationContext.TIME] = value
                elif key_lower == "academic":
                    context_expansions[AbbreviationContext.ACADEMIC] = value
                elif key_lower == "religious":
                    context_expansions[AbbreviationContext.RELIGIOUS] = value
                else:
                    raise ValueError(
                        f"Unknown context '{key}'. Valid contexts are: "
                        "default, title, place, time, academic, religious"
                    )

            # Ensure we have a default expansion
            if "default" not in expansion:
                # Use the first available expansion as default
                default_expansion = next(iter(expansion.values()))

        # Create and add the entry
        entry = AbbreviationEntry(
            abbreviation=abbreviation,
            expansion=str(default_expansion),
            context_expansions=context_expansions,
            case_sensitive=case_sensitive,
            description=description,
        )
        self.add_abbreviation(entry)

    def _initialize_abbreviations(self) -> None:
        """Initialize comprehensive English abbreviation list."""

        # =====================================================================
        # TITLES AND HONORIFICS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mr.",
                expansion="Mister",
                description="Male honorific",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mrs.",
                expansion="Misses",
                description="Married female honorific",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ms.",
                expansion="Miss",
                description="Female honorific",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Dr.",
                expansion="Doctor",
                context_expansions={
                    AbbreviationContext.PLACE: "Drive",
                    AbbreviationContext.TITLE: "Doctor",
                },
                description="Doctor (title) or Drive (place)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Prof.",
                expansion="Professor",
                description="Professor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Rev.",
                expansion="Reverend",
                description="Reverend (religious title)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Hon.",
                expansion="Honorable",
                description="Honorable",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mx.",
                expansion="Mix",
                description="Gender-neutral honorific",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Esq.",
                expansion="Esquire",
                description="Lawyer suffix",
            )
        )

        # =====================================================================
        # MILITARY RANKS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Lt.",
                expansion="Lieutenant",
                description="Lieutenant",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Gen.",
                expansion="General",
                description="General",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Col.",
                expansion="Colonel",
                description="Colonel",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Maj.",
                expansion="Major",
                description="Major",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Capt.",
                expansion="Captain",
                description="Captain",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sgt.",
                expansion="Sergeant",
                description="Sergeant",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Cpl.",
                expansion="Corporal",
                description="Corporal",
            )
        )

        # =====================================================================
        # DAYS OF THE WEEK
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mon.",
                expansion="Monday",
                description="Monday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Tue.",
                expansion="Tuesday",
                description="Tuesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Tues.",
                expansion="Tuesday",
                description="Tuesday (alternative)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Wed.",
                expansion="Wednesday",
                description="Wednesday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Thu.",
                expansion="Thursday",
                description="Thursday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Thur.",
                expansion="Thursday",
                description="Thursday (alternative)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Thurs.",
                expansion="Thursday",
                description="Thursday (alternative)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Fri.",
                expansion="Friday",
                description="Friday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sat.",
                expansion="Saturday",
                description="Saturday",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sun.",
                expansion="Sunday",
                description="Sunday",
            )
        )

        # =====================================================================
        # MONTHS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Jan.",
                expansion="January",
                description="January",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Feb.",
                expansion="February",
                description="February",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mar.",
                expansion="March",
                description="March",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Apr.",
                expansion="April",
                description="April",
            )
        )

        # May has no abbreviation

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Jun.",
                expansion="June",
                description="June",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Jul.",
                expansion="July",
                description="July",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Aug.",
                expansion="August",
                description="August",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sep.",
                expansion="September",
                description="September",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sept.",
                expansion="September",
                description="September (alternative)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Oct.",
                expansion="October",
                description="October",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Nov.",
                expansion="November",
                description="November",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Dec.",
                expansion="December",
                description="December",
            )
        )

        # =====================================================================
        # PLACES (STREETS, LOCATIONS)
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="St.",
                expansion="Saint",
                context_expansions={
                    AbbreviationContext.PLACE: "Street",
                    AbbreviationContext.RELIGIOUS: "Saint",
                },
                description="Street or Saint (context-dependent)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ave.",
                expansion="Avenue",
                description="Avenue",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Rd.",
                expansion="Road",
                description="Road",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Blvd.",
                expansion="Boulevard",
                description="Boulevard",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ln.",
                expansion="Lane",
                description="Lane",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ct.",
                expansion="Court",
                description="Court",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Pl.",
                expansion="Place",
                description="Place",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Pkwy.",
                expansion="Parkway",
                description="Parkway",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Apt.",
                expansion="Apartment",
                description="Apartment",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ste.",
                expansion="Suite",
                description="Suite",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Fl.",
                expansion="Floor",
                description="Floor",
            )
        )

        # US State abbreviations (common ones)
        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="N.Y.",
                expansion="New York",
                description="New York",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="L.A.",
                expansion="Los Angeles",
                description="Los Angeles",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="D.C.",
                expansion="District of Columbia",
                description="District of Columbia",
            )
        )

        # =====================================================================
        # TIME-RELATED
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="A.M.",
                expansion="A M",  # Spell out for TTS
                description="Ante Meridiem (morning)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="P.M.",
                expansion="P M",  # Spell out for TTS
                description="Post Meridiem (afternoon/evening)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="A.D.",
                expansion="A D",  # Anno Domini
                description="Anno Domini",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="B.C.",
                expansion="B C",  # Before Christ
                description="Before Christ",
            )
        )

        # =====================================================================
        # ACADEMIC DEGREES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Ph.D.",
                expansion="P H D",  # Spell out
                description="Doctor of Philosophy",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="M.D.",
                expansion="M D",  # Medical Doctor
                description="Medical Doctor",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="B.A.",
                expansion="B A",  # Bachelor of Arts
                description="Bachelor of Arts",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="M.A.",
                expansion="M A",  # Master of Arts
                description="Master of Arts",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="B.S.",
                expansion="B S",  # Bachelor of Science
                description="Bachelor of Science",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="M.S.",
                expansion="M S",  # Master of Science
                description="Master of Science",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Jr.",
                expansion="Junior",
                description="Junior",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sr.",
                expansion="Senior",
                description="Senior",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="M.B.A.",
                expansion="M B A",
                description="Master of Business Administration",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="D.D.S.",
                expansion="D D S",
                description="Doctor of Dental Surgery",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="D.V.M.",
                expansion="D V M",
                description="Doctor of Veterinary Medicine",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="R.N.",
                expansion="R N",
                description="Registered Nurse",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="L.P.N.",
                expansion="L P N",
                description="Licensed Practical Nurse",
            )
        )

        # =====================================================================
        # COMMON ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="etc.",
                expansion="et cetera",
                description="Et cetera (and so on)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="vs.",
                expansion="versus",
                description="Versus",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="v.",
                expansion="versus",
                description="Versus (alternative)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="e.g.",
                expansion="for example",
                description="Exempli gratia (for example)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="i.e.",
                expansion="that is",
                description="Id est (that is)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="dept.",
                expansion="department",
                description="Department",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="govt.",
                expansion="government",
                description="Government",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="approx.",
                expansion="approximately",
                description="Approximately",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="est.",
                expansion="estimated",
                description="Estimated",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="inc.",
                expansion="incorporated",
                description="Incorporated",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="corp.",
                expansion="corporation",
                description="Corporation",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ltd.",
                expansion="limited",
                description="Limited",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="co.",
                expansion="company",
                description="Company",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="no.",
                expansion="number",
                description="Number",
                only_if_followed_by=r"\s*\d",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="vol.",
                expansion="volume",
                description="Volume",
                only_if_followed_by=r"\s*\d",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pg.",
                expansion="page",
                description="Page",
                only_if_followed_by=r"\s*\d",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pp.",
                expansion="pages",
                description="Pages",
                only_if_followed_by=r"\s*\d",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ch.",
                expansion="chapter",
                description="Chapter",
                only_if_followed_by=r"\s*\d",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="fig.",
                expansion="figure",
                description="Figure",
                only_if_followed_by=r"\s*\d",
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

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="misc.",
                expansion="miscellaneous",
                description="Miscellaneous",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="assn.",
                expansion="association",
                description="Association",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="assoc.",
                expansion="association",
                description="Association (alternative)",
            )
        )

        # =====================================================================
        # DIRECTIONAL ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="N.",
                expansion="North",
                description="North",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="S.",
                expansion="South",
                description="South",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="E.",
                expansion="East",
                description="East",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="W.",
                expansion="West",
                description="West",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="NE.",
                expansion="Northeast",
                description="Northeast",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="N.E.",
                expansion="Northeast",
                description="Northeast (with periods)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="NW.",
                expansion="Northwest",
                description="Northwest",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="N.W.",
                expansion="Northwest",
                description="Northwest (with periods)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="SE.",
                expansion="Southeast",
                description="Southeast",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="S.E.",
                expansion="Southeast",
                description="Southeast (with periods)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="SW.",
                expansion="Southwest",
                description="Southwest",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="S.W.",
                expansion="Southwest",
                description="Southwest (with periods)",
            )
        )

        # =====================================================================
        # COUNTRIES AND REGIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="U.S.",
                expansion="U S",  # Spell out as letters for TTS
                description="United States",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="U.K.",
                expansion="U K",  # Spell out as letters for TTS
                description="United Kingdom",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="U.S.A.",
                expansion="U S A",  # Spell out as letters for TTS
                description="United States of America",
            )
        )

        # =====================================================================
        # GEOGRAPHIC FEATURES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mt.",
                expansion="Mount",
                description="Mount (mountain)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Mtn.",
                expansion="Mountain",
                description="Mountain",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Pk.",
                expansion="Park",
                description="Park",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Cir.",
                expansion="Circle",
                description="Circle (street type)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Sq.",
                expansion="Square",
                description="Square (street type)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Bldg.",
                expansion="Building",
                description="Building",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="Cyn.",
                expansion="Canyon",
                description="Canyon",
            )
        )

        # =====================================================================
        # TIME ZONES
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="EST",
                expansion="E S T",
                description="Eastern Standard Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="EDT",
                expansion="E D T",
                description="Eastern Daylight Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="CST",
                expansion="C S T",
                description="Central Standard Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="CDT",
                expansion="C D T",
                description="Central Daylight Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="MST",
                expansion="M S T",
                description="Mountain Standard Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="MDT",
                expansion="M D T",
                description="Mountain Daylight Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="PST",
                expansion="P S T",
                description="Pacific Standard Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="PDT",
                expansion="P D T",
                description="Pacific Daylight Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="GMT",
                expansion="G M T",
                description="Greenwich Mean Time",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="UTC",
                expansion="U T C",
                description="Coordinated Universal Time",
            )
        )

        # =====================================================================
        # CALENDAR (Additional)
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="BCE",
                expansion="B C E",
                description="Before Common Era",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="CE",
                expansion="C E",
                description="Common Era",
            )
        )

        # =====================================================================
        # LATIN ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="et al.",
                expansion="et al",
                description="Et alii (and others)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="viz.",
                expansion="namely",
                description="Videlicet (namely)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cf.",
                expansion="compare",
                description="Confer (compare)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ibid.",
                expansion="ibidem",
                description="Ibidem (in the same place)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ca.",
                expansion="circa",
                description="Circa (approximately)",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="c.",
                expansion="circa",
                description="Circa (approximately)",
            )
        )

        # =====================================================================
        # MEASUREMENTS - LENGTH
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="in.",
                expansion="inch",
                description="Inch",
                # Only expand as a unit when preceded by a number
                # (10 in., 10.0 in., 1,000 in.)
                # This avoids false positives in weird sentence-end cases
                # and proper names.
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ft.",
                expansion="foot",
                description="Foot",
                # Avoid "Ft. Lauderdale" -> "foot Lauderdale"
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="yd.",
                expansion="yard",
                description="Yard",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mi.",
                expansion="mile",
                description="Mile",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mm",
                expansion="millimeter",
                description="Millimeter",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="cm",
                expansion="centimeter",
                description="Centimeter",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="km",
                expansion="kilometer",
                description="Kilometer",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        # =====================================================================
        # MEASUREMENTS - WEIGHT
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="oz.",
                expansion="ounce",
                description="Ounce",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="lb.",
                expansion="pound",
                description="Pound",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="lbs.",
                expansion="pounds",
                description="Pounds",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="mg",
                expansion="milligram",
                description="Milligram",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="kg",
                expansion="kilogram",
                description="Kilogram",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        # =====================================================================
        # MEASUREMENTS - VOLUME
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="gal.",
                expansion="gallon",
                description="Gallon",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="qt.",
                expansion="quart",
                description="Quart",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="pt.",
                expansion="pint",
                description="Pint",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tsp.",
                expansion="teaspoon",
                description="Teaspoon",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="tbsp.",
                expansion="tablespoon",
                description="Tablespoon",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        # =====================================================================
        # TIME UNITS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="hr.",
                expansion="hour",
                description="Hour",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="hrs.",
                expansion="hours",
                description="Hours",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="sec.",
                expansion="second",
                description="Second",
                only_if_preceded_by=r"\d[\d,]*(?:\.\d+)?\s*$",
            )
        )

        # =====================================================================
        # COMMON EMAIL/BUSINESS ABBREVIATIONS
        # =====================================================================

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="attn.",
                expansion="attention",
                description="Attention",
            )
        )

        self.add_abbreviation(
            AbbreviationEntry(
                abbreviation="ref.",
                expansion="reference",
                description="Reference",
            )
        )


# Create a singleton instance for easy access
_expander: EnglishAbbreviationExpander | None = None
_expander_context_detection: bool | None = None


def get_expander(enable_context_detection: bool = True) -> EnglishAbbreviationExpander:
    """Get the English abbreviation expander instance.

    Args:
        enable_context_detection: Whether to enable context-aware expansion

    Returns:
        The abbreviation expander instance
    """
    global _expander, _expander_context_detection
    if _expander is None:
        _expander = EnglishAbbreviationExpander(
            enable_context_detection=enable_context_detection
        )
        _expander_context_detection = enable_context_detection
    elif _expander_context_detection != enable_context_detection:
        warnings.warn(
            "English abbreviation expander already initialized with "
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
