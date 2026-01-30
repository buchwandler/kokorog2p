"""Tests for English abbreviation expansion."""

import pytest

from kokorog2p.en.abbreviations import (
    EnglishAbbreviationExpander,
    get_expander,
)
from kokorog2p.en.normalizer import EnglishNormalizer


class TestEnglishAbbreviationExpander:
    """Test the EnglishAbbreviationExpander class."""

    @pytest.fixture
    def expander(self):
        """Create an abbreviation expander."""
        return EnglishAbbreviationExpander(enable_context_detection=True)

    @pytest.fixture
    def expander_no_context(self):
        """Create an abbreviation expander without context detection."""
        return EnglishAbbreviationExpander(enable_context_detection=False)

    # =========================================================================
    # TITLES AND HONORIFICS
    # =========================================================================

    def test_professor_expansion(self, expander):
        """Test Prof. → Professor."""
        assert (
            expander.expand("Prof. Smith teaches math")
            == "Professor Smith teaches math"
        )

    def test_doctor_title_expansion(self, expander):
        """Test Dr. → Doctor when used as title."""
        assert expander.expand("Dr. Johnson is here") == "Doctor Johnson is here"

    def test_reverend_expansion(self, expander):
        """Test Rev. → Reverend."""
        assert expander.expand("Rev. Martin spoke") == "Reverend Martin spoke"

    def test_mister_expansion(self, expander):
        """Test Mr. → Mister."""
        assert expander.expand("Mr. Anderson called") == "Mister Anderson called"

    def test_misses_expansion(self, expander):
        """Test Mrs. → Misses."""
        assert expander.expand("Mrs. Wilson arrived") == "Misses Wilson arrived"

    def test_miss_expansion(self, expander):
        """Test Ms. → Miss."""
        assert expander.expand("Ms. Taylor is ready") == "Miss Taylor is ready"

    # =========================================================================
    # MILITARY RANKS
    # =========================================================================

    def test_lieutenant_expansion(self, expander):
        """Test Lt. → Lieutenant."""
        assert expander.expand("Lt. Davis reported") == "Lieutenant Davis reported"

    def test_general_expansion(self, expander):
        """Test Gen. → General."""
        assert expander.expand("Gen. Patton led") == "General Patton led"

    def test_colonel_expansion(self, expander):
        """Test Col. → Colonel."""
        assert expander.expand("Col. Sanders founded") == "Colonel Sanders founded"

    def test_captain_expansion(self, expander):
        """Test Capt. → Captain."""
        assert expander.expand("Capt. Kirk commands") == "Captain Kirk commands"

    def test_sergeant_expansion(self, expander):
        """Test Sgt. → Sergeant."""
        assert expander.expand("Sgt. York was brave") == "Sergeant York was brave"

    # =========================================================================
    # DAYS OF THE WEEK
    # =========================================================================

    def test_monday_expansion(self, expander):
        """Test Mon. → Monday."""
        assert expander.expand("See you Mon. morning") == "See you Monday morning"

    def test_tuesday_expansion(self, expander):
        """Test Tue. → Tuesday."""
        assert expander.expand("Meeting on Tue. at 3") == "Meeting on Tuesday at 3"

    def test_tuesday_alt_expansion(self, expander):
        """Test Tues. → Tuesday."""
        assert expander.expand("Tues. is busy") == "Tuesday is busy"

    def test_wednesday_expansion(self, expander):
        """Test Wed. → Wednesday."""
        assert expander.expand("Wed. schedule") == "Wednesday schedule"

    def test_thursday_expansion(self, expander):
        """Test Thu. → Thursday."""
        assert expander.expand("Thu. deadline") == "Thursday deadline"

    def test_friday_expansion(self, expander):
        """Test Fri. → Friday."""
        assert expander.expand("TGIF! Fri. party") == "TGIF! Friday party"

    def test_saturday_expansion(self, expander):
        """Test Sat. → Saturday."""
        assert expander.expand("Sat. brunch") == "Saturday brunch"

    def test_sunday_expansion(self, expander):
        """Test Sun. → Sunday."""
        assert expander.expand("Sun. service") == "Sunday service"

    # =========================================================================
    # MONTHS
    # =========================================================================

    def test_january_expansion(self, expander):
        """Test Jan. → January."""
        assert expander.expand("Born in Jan. 1990") == "Born in January 1990"

    def test_february_expansion(self, expander):
        """Test Feb. → February."""
        assert expander.expand("Feb. 14 is Valentine's") == "February 14 is Valentine's"

    def test_march_expansion(self, expander):
        """Test Mar. → March."""
        assert expander.expand("Mar. madness") == "March madness"

    def test_april_expansion(self, expander):
        """Test Apr. → April."""
        assert expander.expand("Apr. showers") == "April showers"

    def test_september_expansion(self, expander):
        """Test Sep. → September."""
        assert expander.expand("Sep. 11 memorial") == "September 11 memorial"

    def test_september_alt_expansion(self, expander):
        """Test Sept. → September."""
        assert expander.expand("Sept. is lovely") == "September is lovely"

    def test_october_expansion(self, expander):
        """Test Oct. → October."""
        assert expander.expand("Oct. Halloween") == "October Halloween"

    def test_november_expansion(self, expander):
        """Test Nov. → November."""
        assert expander.expand("Nov. election") == "November election"

    def test_december_expansion(self, expander):
        """Test Dec. → December."""
        assert expander.expand("Dec. holidays") == "December holidays"

    # =========================================================================
    # PLACES (CONTEXT-DEPENDENT)
    # =========================================================================

    def test_street_expansion_with_address(self, expander):
        """Test St. → Street when preceded by address number."""
        assert expander.expand("123 Main St. is here") == "123 Main Street is here"

    def test_saint_expansion_without_address(self, expander_no_context):
        """Test St. → Saint when no context detection."""
        assert expander_no_context.expand("St. Peter was") == "Saint Peter was"

    def test_saint_expansion_with_name(self, expander):
        """Test St. → Saint when followed by saint name."""
        assert expander.expand("St. Patrick's Day") == "Saint Patrick's Day"

    def test_avenue_expansion(self, expander):
        """Test Ave. → Avenue."""
        assert expander.expand("Park Ave. apartment") == "Park Avenue apartment"

    def test_road_expansion(self, expander):
        """Test Rd. → Road."""
        assert expander.expand("Oak Rd. closed") == "Oak Road closed"

    def test_boulevard_expansion(self, expander):
        """Test Blvd. → Boulevard."""
        assert expander.expand("Sunset Blvd. famous") == "Sunset Boulevard famous"

    def test_apartment_expansion(self, expander):
        """Test Apt. → Apartment."""
        assert expander.expand("Apt. 5B available") == "Apartment 5B available"

    # =========================================================================
    # TIME ABBREVIATIONS
    # =========================================================================

    def test_am_expansion(self, expander):
        """Test A.M. → A M."""
        assert expander.expand("Meeting at 9 A.M. today") == "Meeting at 9 A M today"

    def test_pm_expansion(self, expander):
        """Test P.M. → P M."""
        assert expander.expand("Dinner at 7 P.M. sharp") == "Dinner at 7 P M sharp"

    def test_ad_expansion(self, expander):
        """Test A.D. → A D."""
        assert expander.expand("Year 2024 A.D. now") == "Year 2024 A D now"

    def test_bc_expansion(self, expander):
        """Test B.C. → B C."""
        assert expander.expand("500 B.C. ancient") == "500 B C ancient"

    # =========================================================================
    # ACADEMIC DEGREES
    # =========================================================================

    def test_phd_expansion(self, expander):
        """Test Ph.D. → P H D."""
        assert expander.expand("She has a Ph.D. degree") == "She has a P H D degree"

    def test_md_expansion(self, expander):
        """Test M.D. → M D."""
        assert (
            expander.expand("John Smith, M.D. practices") == "John Smith, M D practices"
        )

    def test_ba_expansion(self, expander):
        """Test B.A. → B A."""
        assert expander.expand("Earned a B.A. last year") == "Earned a B A last year"

    def test_junior_expansion(self, expander):
        """Test Jr. → Junior."""
        assert (
            expander.expand("Martin Luther King Jr. spoke")
            == "Martin Luther King Junior spoke"
        )

    def test_senior_expansion(self, expander):
        """Test Sr. → Senior."""
        assert expander.expand("John Doe Sr. retired") == "John Doe Senior retired"

    # =========================================================================
    # COMMON ABBREVIATIONS
    # =========================================================================

    def test_et_cetera_expansion(self, expander):
        """Test etc. → et cetera."""
        assert (
            expander.expand("Apples, oranges, etc. are fruits")
            == "Apples, oranges, et cetera are fruits"
        )

    def test_versus_expansion(self, expander):
        """Test vs. → versus."""
        assert expander.expand("Team A vs. Team B") == "Team A versus Team B"

    def test_for_example_expansion(self, expander):
        """Test e.g. → for example."""
        assert expander.expand("Fruits, e.g. apples") == "Fruits, for example apples"

    def test_that_is_expansion(self, expander):
        """Test i.e. → that is."""
        assert (
            expander.expand("One apple, i.e. the red one")
            == "One apple, that is the red one"
        )

    # =========================================================================
    # GUARDED ABBREVIATIONS (NUMERIC CONTEXT)
    # =========================================================================

    def test_no_dot_only_expands_when_followed_by_number(self, expander):
        """Test No. stays No. unless followed by digits (No. 244 -> number 244)."""
        assert expander.expand("No.") == "No."
        assert expander.expand("He said No.") == "He said No."
        assert expander.expand("No. 244").lower() == "number 244"
        assert expander.expand("no. 244").lower() == "number 244"

    def test_inch_only_expands_when_preceded_by_number(self, expander):
        """Test in. expands to inch only after a number."""
        assert expander.expand("10.0 in. long") == "10.0 inch long"
        assert expander.expand("5 in.").endswith(
            "inch"
        )  # allow minor punctuation/spacing differences

        # "in." used as sentence punctuation should NOT become "inch"
        assert expander.expand("Check in.") == "Check in."
        assert expander.expand("Log in. Now.") == "Log in. Now."

    def test_foot_only_expands_when_preceded_by_number(self, expander):
        """Test ft. expands to foot only after a number, avoids Ft. place names."""
        assert expander.expand("He is 6 ft. tall") == "He is 6 foot tall"
        assert expander.expand("Ft. Lauderdale is sunny") == "Ft. Lauderdale is sunny"

    def test_ounce_only_expands_when_preceded_by_number(self, expander):
        """Test oz. expands to ounce only after a number; avoid Wizard of Oz."""
        assert expander.expand("Add 8 oz. of sugar") == "Add 8 ounce of sugar"
        assert expander.expand("Wizard of Oz.") == "Wizard of Oz."

    def test_pound_only_expands_when_preceded_by_number(self, expander):
        """Test lb. expands to pound only after a number."""
        assert expander.expand("A 2 lb. bag") == "A 2 pound bag"
        assert expander.expand("lb. is a unit") == "lb. is a unit"

    # =========================================================================
    # CASE INSENSITIVITY
    # =========================================================================

    def test_case_insensitive_prof(self, expander):
        """Test that prof. and Prof. both expand."""
        # Case-insensitive matching, but expansion uses default case from entry
        assert expander.expand("prof. smith teaches") == "Professor smith teaches"
        assert expander.expand("Prof. Smith teaches") == "Professor Smith teaches"

    def test_case_insensitive_dr(self, expander):
        """Test that dr. and Dr. both expand."""
        # Case-insensitive matching, but expansion uses default case from entry
        assert expander.expand("dr. jones") == "Doctor jones"
        assert expander.expand("Dr. Jones") == "Doctor Jones"

    # =========================================================================
    # WORD BOUNDARIES
    # =========================================================================

    def test_word_boundary_protection(self, expander):
        """Test that abbreviations are only expanded at word boundaries."""
        # "St" in "Stream" should NOT be expanded
        text = "Stream. St. Peter"
        result = expander.expand(text)
        assert "Stream" in result  # "St" in "Stream" not expanded
        assert "Saint Peter" in result  # But "St." is expanded

    def test_punctuation_boundary(self, expander):
        """Test abbreviations before punctuation are expanded."""
        assert expander.expand("See Dr. Smith, please.") == "See Doctor Smith, please."
        assert expander.expand("Meeting Mon. at noon!") == "Meeting Monday at noon!"

    # =========================================================================
    # MULTIPLE ABBREVIATIONS
    # =========================================================================

    def test_multiple_abbreviations_in_sentence(self, expander):
        """Test multiple abbreviations in one sentence."""
        text = "Dr. Smith met Prof. Jones on Mon. at 123 Main St."
        expected = "Doctor Smith met Professor Jones on Monday at 123 Main Street"
        assert expander.expand(text) == expected

    def test_same_abbreviation_multiple_times(self, expander):
        """Test same abbreviation appears multiple times."""
        text = "Dr. Smith and Dr. Jones are both doctors."
        expected = "Doctor Smith and Doctor Jones are both doctors."
        assert expander.expand(text) == expected

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    def test_empty_string(self, expander):
        """Test empty string returns empty."""
        assert expander.expand("") == ""

    def test_no_abbreviations(self, expander):
        """Test text with no abbreviations remains unchanged."""
        text = "This is a normal sentence with no abbreviations."
        assert expander.expand(text) == text

    def test_abbreviation_at_end_of_sentence(self, expander):
        """Test abbreviation at sentence end."""
        assert expander.expand("He has a Ph.D.") == "He has a P H D"

    def test_abbreviation_with_comma(self, expander):
        """Test abbreviation followed by comma."""
        assert expander.expand("On Mon., we meet") == "On Monday, we meet"


class TestEnglishNormalizerWithAbbreviations:
    """Test abbreviation expansion integrated in EnglishNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer with abbreviation expansion enabled."""
        return EnglishNormalizer(track_changes=True, expand_abbreviations=True)

    @pytest.fixture
    def normalizer_no_abbrev(self):
        """Create normalizer with abbreviation expansion disabled."""
        return EnglishNormalizer(track_changes=False, expand_abbreviations=False)

    def test_abbreviation_expansion_in_normalizer(self, normalizer):
        """Test that abbreviations are expanded during normalization."""
        text = "Dr. Smith met Prof. Jones on Mon."
        result, steps = normalizer.normalize(text)

        assert "Doctor" in result
        assert "Professor" in result
        assert "Monday" in result

        # Should have at least one abbreviation expansion step
        assert any(step.rule_name == "abbreviation_expansion" for step in steps)

    def test_abbreviation_disabled(self, normalizer_no_abbrev):
        """Test that abbreviations are NOT expanded when disabled."""
        text = "Dr. Smith met Prof. Jones"
        result = normalizer_no_abbrev(text)

        # Abbreviations should remain
        assert "Dr." in result
        assert "Prof." in result

    def test_abbreviation_with_quote_normalization(self, normalizer):
        """Test abbreviations work with other normalizations."""
        # Use curly quotes that should be normalized
        text = 'Dr. Smith said "hello" on Mon.'
        result, steps = normalizer.normalize(text)

        # Should expand abbreviations AND normalize quotes
        assert "Doctor" in result
        assert "Monday" in result
        assert '"hello"' in result  # Curly quotes normalized to straight

    def test_abbreviation_expansion_tracked(self, normalizer):
        """Test that abbreviation expansion is tracked in debug mode."""
        text = "Prof. Smith teaches"
        result, steps = normalizer.normalize(text)

        # Find the abbreviation expansion step
        abbrev_steps = [s for s in steps if s.rule_name == "abbreviation_expansion"]
        assert len(abbrev_steps) == 1

        step = abbrev_steps[0]
        assert "Prof" in step.original
        assert "Professor" in step.normalized

    def test_context_aware_st_street(self, normalizer):
        """Test St. → Street in address context."""
        text = "123 Main St. is the address"
        result = normalizer(text)
        assert "Main Street" in result

    def test_context_aware_st_saint(self, normalizer):
        """Test St. → Saint in religious context."""
        text = "St. Patrick celebrated"
        result = normalizer(text)
        assert "Saint Patrick" in result

    # =========================================================================
    # GUARDED ABBREVIATIONS IN NORMALIZER
    # =========================================================================

    def test_no_dot_guard_in_normalizer(self, normalizer):
        """No. should stay No.; No. 244 should expand to number 244."""
        assert normalizer("No.") == "No."
        assert "number 244" in normalizer("No. 244").lower()

    def test_units_guard_in_normalizer(self, normalizer):
        """Units should expand only when preceded by numbers."""
        assert "inch" in normalizer("10.0 in. long").lower()
        assert normalizer("Wizard of Oz.") == "Wizard of Oz."
        assert normalizer("Ft. Lauderdale").startswith("Ft. Lauderdale")


class TestStAbbreviationRobust:
    """Test robust multi-signal St. abbreviation detection with edge cases."""

    @pytest.fixture
    def expander(self):
        """Create an expander with context detection enabled."""
        return EnglishAbbreviationExpander(enable_context_detection=True)

    @pytest.fixture
    def normalizer(self):
        """Create a normalizer with context detection enabled."""
        return EnglishNormalizer(enable_context_detection=True)

    # =========================================================================
    # STREET cases - house number pattern
    # =========================================================================

    def test_st_street_typical_house_number(self, expander):
        """Test St. → Street with typical house number."""
        assert expander.expand("123 Main St.") == "123 Main Street"
        assert expander.expand("456 Oak St. is here") == "456 Oak Street is here"

    def test_st_street_with_direction(self, expander):
        """Test St. → Street with directional abbreviation."""
        assert "Street" in expander.expand("100 N. Elm St.")
        assert "Street" in expander.expand("456 S Oak St.")

    def test_st_street_single_digit_number(self, expander):
        """Test St. → Street with single digit house number."""
        assert "Street" in expander.expand("I live at 5 Park St.")

    def test_st_street_ordinal_number(self, expander):
        """Test St. → Street with ordinal number."""
        assert "Street" in expander.expand("The shop on 5th St.")

    # =========================================================================
    # SAINT cases - name recognition
    # =========================================================================

    def test_st_saint_common_saints(self, expander):
        """Test St. → Saint with common saint names."""
        assert "Saint Patrick" in expander.expand("St. Patrick's Day")
        assert "Saint Peter" in expander.expand("St. Peter was an apostle")
        assert "Saint John" in expander.expand("The church of St. John")
        assert "Saint Mary" in expander.expand("St. Mary church")

    def test_st_saint_city_names(self, expander):
        """Test St. → Saint for city names."""
        assert "Saint Louis" in expander.expand("Visit St. Louis")
        assert "Saint Paul" in expander.expand("St. Paul, Minnesota")
        assert "Saint Petersburg" in expander.expand("St. Petersburg is beautiful")
        assert "Saint Augustine" in expander.expand("St. Augustine, Florida")

    def test_st_saint_with_possessive(self, expander):
        """Test St. → Saint with possessive form."""
        assert "Saint Patrick's" in expander.expand("St. Patrick's Day")
        assert "Saint John's" in expander.expand("St. John's Church")

    # =========================================================================
    # SAINT cases - number far away / not address-related
    # =========================================================================

    def test_st_saint_with_distant_year(self, expander):
        """Test St. → Saint when year appears far from St."""
        result = expander.expand("Born in 1850, St. Peter was influential")
        assert "Saint Peter" in result
        assert "Street Peter" not in result

    def test_st_saint_with_birthday_number(self, expander):
        """Test St. → Saint with birthday/age number after."""
        result = expander.expand("St. Patrick celebrated his 50th birthday")
        assert "Saint Patrick" in result
        assert "Street Patrick" not in result

    def test_st_saint_with_zip_code(self, expander):
        """Test St. → Saint when zip code appears in sentence."""
        result = expander.expand("Move to St. Paul, MN 55101")
        assert "Saint Paul" in result
        assert "Street Paul" not in result

    # =========================================================================
    # AMBIGUOUS cases - name wins over distant number
    # =========================================================================

    def test_st_saint_before_numbered_avenue(self, expander):
        """Test St. → Saint when number before city name + Avenue."""
        # "123 St. Louis Avenue" - city name takes priority over distant number
        result = expander.expand("Visit 123 St. Louis Avenue")
        assert "Saint Louis" in result
        assert "Street Louis" not in result

    def test_st_saint_street_named_after_saint(self, expander):
        """Test St. → Saint when street is named after saint."""
        # "St. Patrick Street" - the street name itself, not an address
        result = expander.expand("I live on St. Patrick Street")
        assert "Saint Patrick" in result
        assert "Street Patrick" not in result

    def test_st_saint_with_apartment_number_after(self, expander):
        """Test St. → Saint when apartment number appears after."""
        # Number after St., not a house number before
        result = expander.expand("St. John, apartment 5")
        assert "Saint John" in result

    # =========================================================================
    # EDGE cases
    # =========================================================================

    def test_st_saint_in_middle_of_compound_address(self, expander):
        """Test St. → Saint in compound address with saint name."""
        # "123 N. St. Mary's Rd." - Mary is recognized as saint name
        result = expander.expand("123 N. St. Mary's Rd.")
        assert "Saint Mary's" in result

    def test_st_default_to_saint_unknown_name(self, expander):
        """Test St. → Saint for unknown names (default behavior)."""
        # Unknown name, no close number → defaults to Saint
        result = expander.expand("St. Christopher")
        assert "Saint Christopher" in result

    def test_st_saint_no_following_text(self, expander):
        """Test St. at end of sentence defaults to Saint."""
        result = expander.expand("Visit St.")
        assert "Saint" in result

    # =========================================================================
    # NORMALIZER integration tests
    # =========================================================================

    def test_normalizer_st_house_number(self, normalizer):
        """Test normalizer St. → Street with house number."""
        assert "Main Street" in normalizer("123 Main St.")

    def test_normalizer_st_saint_name(self, normalizer):
        """Test normalizer St. → Saint with saint name."""
        assert "Saint Patrick" in normalizer("St. Patrick celebrated")

    def test_normalizer_st_city_name(self, normalizer):
        """Test normalizer St. → Saint with city name."""
        assert "Saint Louis" in normalizer("Visit St. Louis")

    def test_normalizer_st_distant_number(self, normalizer):
        """Test normalizer St. → Saint with distant number."""
        result = normalizer("Born in 1850, St. Peter was")
        assert "Saint Peter" in result
        assert "Street Peter" not in result


class TestGetExpander:
    """Test the get_expander singleton function."""

    def test_get_expander_returns_instance(self):
        """Test that get_expander returns an instance."""
        expander = get_expander()
        assert isinstance(expander, EnglishAbbreviationExpander)

    def test_get_expander_is_singleton(self):
        """Test that get_expander returns same instance."""
        expander1 = get_expander()
        expander2 = get_expander()
        assert expander1 is expander2

    def test_expander_has_abbreviations(self):
        """Test that expander has abbreviations loaded."""
        expander = get_expander()
        abbrevs = expander.get_abbreviations_list()

        # Should have common abbreviations
        assert "Prof." in abbrevs
        assert "Dr." in abbrevs
        assert "Mon." in abbrevs
        assert "Jan." in abbrevs
        assert "St." in abbrevs
