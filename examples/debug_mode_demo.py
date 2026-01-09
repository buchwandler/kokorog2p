"""Demonstration of the EnglishG2P debug mode.

This example shows how to use the process_with_debug() method to get detailed
information about text normalization, tokenization, and phonemization.
"""

from kokorog2p.en.g2p import EnglishG2P


def main():
    # Create a G2P instance with fallback enabled
    g2p = EnglishG2P(use_spacy=True, use_espeak_fallback=True)

    # Example 1: Simple text with quotes and contractions
    print("=" * 80)
    print("Example 1: Quotes and Contractions")
    print("=" * 80)

    text1 = "\"I don't think they'll come,\" she said."
    result1 = g2p.process_with_debug(text1)
    print(result1.render_debug())
    print()

    # Example 2: Text with normalization (curly quotes, ellipsis, em-dash)
    print("\n" + "=" * 80)
    print("Example 2: Text Normalization")
    print("=" * 80)

    text2 = 'Wait...she said--"really?"'
    result2 = g2p.process_with_debug(text2)
    print(result2.render_debug())
    print()

    # Example 3: Unknown words with fallback
    print("\n" + "=" * 80)
    print("Example 3: Unknown Words with Fallback")
    print("=" * 80)

    text3 = "The xylophone player learned a new fictionary word"
    result3 = g2p.process_with_debug(text3)
    print(result3.render_debug())
    print()

    # Example 4: Accessing individual token information
    print("\n" + "=" * 80)
    print("Example 4: Token-Level Information")
    print("=" * 80)

    text4 = "Hello world"
    result4 = g2p.process_with_debug(text4)

    print(f"Original text: {result4.original!r}")
    print(f"Normalized text: {result4.normalized!r}")
    print(f"Number of tokens: {len(result4.tokens)}")
    print()

    print("Token details:")
    for i, token in enumerate(result4.tokens):
        print(f"  Token {i + 1}:")
        print(f"    Text: {token.text!r}")
        print(f"    Position: {token.char_start}-{token.char_end}")
        print(f"    Phonemes: {token.phoneme}")
        source_val = token.phoneme_source.value if token.phoneme_source else "None"
        print(f"    Source: {source_val}")
        print(f"    Rating: {token.phoneme_rating}")
        if token.pos_tag:
            print(f"    POS tag: {token.pos_tag}")
        print()

    # Example 5: Comparing with regular mode
    print("\n" + "=" * 80)
    print("Example 5: Debug vs Regular Mode")
    print("=" * 80)

    text5 = "Testing mode comparison"

    # Regular mode
    regular_tokens = g2p(text5)
    print("Regular mode output:")
    for token in regular_tokens:
        print(f"  {token.text:15} → {token.phonemes}")
    print()

    # Debug mode
    debug_result = g2p.process_with_debug(text5)
    print("Debug mode output:")
    for token in debug_result.tokens:
        source_str = (
            f"[{token.phoneme_source.value}]" if token.phoneme_source else "[none]"
        )
        print(f"  {token.text:15} → {token.phoneme:15} {source_str}")
    print()

    # Example 6: Nested quotes and depth tracking
    print("\n" + "=" * 80)
    print("Example 6: Quote Nesting Depth")
    print("=" * 80)

    text6 = '"She said "hello world" to me"'
    result6 = g2p.process_with_debug(text6)

    print(f"Input: {text6}")
    print("\nTokens with quote depth:")
    for token in result6.tokens:
        depth_str = f"(depth={token.quote_depth})" if token.quote_depth > 0 else ""
        print(f"  {token.text:15} {depth_str}")
    print()


if __name__ == "__main__":
    main()
