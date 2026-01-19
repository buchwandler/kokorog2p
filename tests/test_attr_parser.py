"""Tests for robust attribute parser."""

from kokorog2p.attr_parser import parse_attributes


class TestAttributeParser:
    """Tests for parse_attributes function."""

    def test_double_quotes(self):
        """Test basic double-quoted attributes."""
        attrs, warnings = parse_attributes('ph="hello"')
        assert attrs == {"ph": "hello"}
        assert len(warnings) == 0

    def test_single_quotes(self):
        """Test single-quoted attributes."""
        attrs, warnings = parse_attributes("ph='hello'")
        assert attrs == {"ph": "hello"}
        assert len(warnings) == 0

    def test_mixed_quotes(self):
        """Test mixed single and double quotes in same annotation."""
        attrs, warnings = parse_attributes("ph=\"hello\" lang='fr'")
        assert attrs == {"ph": "hello", "lang": "fr"}
        assert len(warnings) == 0

    def test_multiple_attributes(self):
        """Test multiple attributes."""
        attrs, warnings = parse_attributes('ph="wɝːld" lang="en" rate="fast"')
        assert attrs == {"ph": "wɝːld", "lang": "en", "rate": "fast"}
        assert len(warnings) == 0

    def test_hyphen_in_key(self):
        """Test keys with hyphens."""
        attrs, warnings = parse_attributes('voice-name="Amy"')
        assert attrs == {"voice-name": "Amy"}
        assert len(warnings) == 0

    def test_colon_in_key(self):
        """Test keys with colons."""
        attrs, warnings = parse_attributes('xml:lang="en-US"')
        assert attrs == {"xml:lang": "en-US"}
        assert len(warnings) == 0

    def test_complex_keys(self):
        """Test complex keys with hyphens and colons."""
        attrs, warnings = parse_attributes(
            'xml:lang="en-US" voice-name="Amy" ph="test"'
        )
        assert attrs == {"xml:lang": "en-US", "voice-name": "Amy", "ph": "test"}
        assert len(warnings) == 0

    def test_whitespace_variations(self):
        """Test various whitespace patterns."""
        attrs, warnings = parse_attributes('  ph  =  "hello"   lang="fr"  ')
        assert attrs == {"ph": "hello", "lang": "fr"}
        assert len(warnings) == 0

    def test_escape_double_quote(self):
        """Test escaped double quotes in value."""
        attrs, warnings = parse_attributes('ph="say \\"hello\\""')
        assert attrs == {"ph": 'say "hello"'}
        assert len(warnings) == 0

    def test_escape_single_quote(self):
        """Test escaped single quotes in value."""
        attrs, warnings = parse_attributes("ph='say \\'hello\\''")
        assert attrs == {"ph": "say 'hello'"}
        assert len(warnings) == 0

    def test_escape_backslash(self):
        """Test escaped backslash."""
        attrs, warnings = parse_attributes('ph="back\\\\slash"')
        assert attrs == {"ph": "back\\slash"}
        assert len(warnings) == 0

    def test_empty_value(self):
        """Test empty quoted value."""
        attrs, warnings = parse_attributes('ph=""')
        assert attrs == {"ph": ""}
        assert len(warnings) == 0

    def test_unquoted_value(self):
        """Test unquoted value."""
        attrs, warnings = parse_attributes("rate=fast")
        assert attrs == {"rate": "fast"}
        assert len(warnings) == 0

    def test_ipa_phonemes(self):
        """Test IPA phoneme values."""
        attrs, warnings = parse_attributes('ph="hɛˈloʊ wˈɝld"')
        assert attrs == {"ph": "hɛˈloʊ wˈɝld"}
        assert len(warnings) == 0

    def test_unicode_value(self):
        """Test unicode characters in values."""
        attrs, warnings = parse_attributes('ph="你好" lang="zh"')
        assert attrs == {"ph": "你好", "lang": "zh"}
        assert len(warnings) == 0

    def test_case_insensitive_keys(self):
        """Test that keys are case-folded."""
        attrs, warnings = parse_attributes('Ph="hello" LANG="fr"')
        assert attrs == {"ph": "hello", "lang": "fr"}
        assert len(warnings) == 0

    def test_malformed_no_equals(self):
        """Test malformed attribute without equals."""
        attrs, warnings = parse_attributes('ph"hello"')
        assert len(warnings) > 0
        assert "Expected '='" in warnings[0].message

    def test_malformed_no_value(self):
        """Test malformed attribute without value."""
        attrs, warnings = parse_attributes("ph=")
        assert len(warnings) > 0
        # Should warn about unclosed quote or missing value

    def test_malformed_unclosed_quote(self):
        """Test unclosed quote."""
        attrs, warnings = parse_attributes('ph="hello')
        assert attrs == {"ph": "hello"}  # Still parses the value
        assert len(warnings) > 0
        assert "Unclosed quote" in warnings[0].message

    def test_empty_string(self):
        """Test empty attribute string."""
        attrs, warnings = parse_attributes("")
        assert attrs == {}
        assert len(warnings) == 0

    def test_whitespace_only(self):
        """Test whitespace-only string."""
        attrs, warnings = parse_attributes("   ")
        assert attrs == {}
        assert len(warnings) == 0

    def test_complex_real_world_example(self):
        """Test real-world complex annotation."""
        attrs, warnings = parse_attributes(
            'ph="misˈɑki" lang="en-us" voice-name="Amy" xml:lang="en-US"'
        )
        assert attrs == {
            "ph": "misˈɑki",
            "lang": "en-us",
            "voice-name": "Amy",
            "xml:lang": "en-US",
        }
        assert len(warnings) == 0

    def test_preserve_special_ipa_characters(self):
        """Test that special IPA characters are preserved."""
        attrs, warnings = parse_attributes('ph="tʃɛk ðɪs ʃʊə"')
        assert attrs == {"ph": "tʃɛk ðɪs ʃʊə"}
        assert len(warnings) == 0
