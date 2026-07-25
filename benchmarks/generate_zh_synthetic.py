#!/usr/bin/env python3
"""Generate Chinese (Mandarin) synthetic benchmark dataset.

This script creates a comprehensive Chinese benchmark dataset with:
1. Hand-crafted sentences covering common words and phonetic patterns
2. All Zhuyin (Bopomofo) phoneme characters from ZH_VOCAB
3. Natural speech samples from CHILDES corpus

The phoneme representation uses Zhuyin (Bopomofo) notation as used by Kokoro TTS,
NOT standard IPA. This includes tone markers (1-5) and special Zhuyin characters.
"""

import json
from pathlib import Path

from kokorog2p.zh import ChineseG2P

# Initialize Chinese G2P
g2p = ChineseG2P(use_espeak_fallback=False, version="1.1")


def generate_phonemes(text: str) -> str:
    """Generate Zhuyin phonemes for Chinese text."""
    tokens = g2p(text)
    return "".join(t.phonemes for t in tokens)


def create_sentence(
    id: int,
    text: str,
    category: str,
    difficulty: str = "basic",
    notes: str = "",
) -> dict:
    """Create a sentence entry with phonemes."""
    phonemes = generate_phonemes(text)
    word_count = len(text.replace(" ", ""))  # Count Chinese characters

    return {
        "id": id,
        "text": text,
        "phonemes": phonemes,
        "category": category,
        "difficulty": difficulty,
        "word_count": word_count,
        "contains_oov": False,
        "notes": notes,
    }


def main():
    print("Generating Chinese synthetic benchmark dataset...")
    print("=" * 80)

    sentences = []
    sentence_id = 1

    # ==========================================================================
    # GREETINGS & POLITE PHRASES
    # ==========================================================================

    greetings = [
        ("你好", "Hello - most common greeting"),
        ("谢谢", "Thank you - with tone sandhi (xie4 xie5)"),
        ("再见", "Goodbye"),
        ("早上好", "Good morning"),
        ("晚安", "Good night"),
        ("对不起", "Sorry - apologizing"),
        ("没关系", "It's okay - responding to apology"),
        ("不客气", "You're welcome"),
    ]

    print(f"\n[1/9] Creating greetings ({len(greetings)} sentences)...")
    for text, notes in greetings:
        sentences.append(
            create_sentence(sentence_id, text, "greetings", "basic", notes)
        )
        sentence_id += 1

    # ==========================================================================
    # COMMON WORDS & PHRASES
    # ==========================================================================

    common_words = [
        ("爱", "Love - single character"),
        ("家", "Home/family"),
        ("朋友", "Friend"),
        ("工作", "Work"),
        ("学习", "Study"),
        ("时间", "Time"),
        ("名字", "Name"),
        ("世界", "World"),
        ("中国", "China"),
        ("北京", "Beijing"),
        ("上海", "Shanghai"),
        ("我爱你", "I love you - common phrase"),
        ("很高兴", "Very happy - word boundary marker /"),
        ("好吃", "Delicious"),
        ("好看", "Good-looking/pretty"),
        ("漂亮", "Beautiful"),
        ("美丽", "Beautiful (elegant form)"),
    ]

    print(f"[2/9] Creating common words ({len(common_words)} sentences)...")
    for text, notes in common_words:
        sentences.append(
            create_sentence(sentence_id, text, "common_words", "basic", notes)
        )
        sentence_id += 1

    # ==========================================================================
    # NUMBERS
    # ==========================================================================

    numbers = [
        ("一", "One - 1st tone"),
        ("二", "Two - 4th tone"),
        ("三", "Three - 1st tone"),
        ("四", "Four - 4th tone"),
        ("五", "Five - 3rd tone"),
        ("六", "Six - 4th tone"),
        ("七", "Seven - 1st tone"),
        ("八", "Eight - 1st tone"),
        ("九", "Nine - 3rd tone"),
        ("十", "Ten - 2nd tone"),
        ("百", "Hundred"),
        ("千", "Thousand"),
        ("万", "Ten thousand - special final"),
        ("一二三", "One two three - sequence"),
    ]

    print(f"[3/9] Creating numbers ({len(numbers)} sentences)...")
    for text, notes in numbers:
        sentences.append(create_sentence(sentence_id, text, "numbers", "basic", notes))
        sentence_id += 1

    # ==========================================================================
    # FOOD & DAILY ITEMS
    # ==========================================================================

    food = [
        ("饭", "Rice/meal"),
        ("茶", "Tea"),
        ("水", "Water"),
        ("面", "Noodles"),
        ("肉", "Meat"),
        ("鱼", "Fish"),
        ("菜", "Vegetable/dish"),
        ("果", "Fruit"),
        ("水果", "Fruit (compound word)"),
    ]

    print(f"[4/9] Creating food words ({len(food)} sentences)...")
    for text, notes in food:
        sentences.append(create_sentence(sentence_id, text, "food", "basic", notes))
        sentence_id += 1

    # ==========================================================================
    # QUESTIONS
    # ==========================================================================

    questions = [
        ("什么", "What - question word"),
        ("为什么", "Why"),
        ("怎么", "How"),
        ("哪里", "Where"),
        ("谁", "Who"),
        ("哪个", "Which one"),
        ("你叫什么名字", "What is your name?"),
        ("这是什么", "What is this?"),
    ]

    print(f"[5/9] Creating questions ({len(questions)} sentences)...")
    for text, notes in questions:
        sentences.append(
            create_sentence(sentence_id, text, "questions", "basic", notes)
        )
        sentence_id += 1

    # ==========================================================================
    # PHONEME COVERAGE - INITIALS (21 Zhuyin initials)
    # ==========================================================================

    initials = [
        ("爸爸", "Dad - ㄅ (b)"),
        ("妈妈", "Mom - ㄇ (m)"),
        ("爬", "Climb - ㄆ (p)"),
        ("发", "Send/emit - ㄈ (f)"),
        ("大", "Big - ㄉ (d)"),
        ("他", "He - ㄊ (t)"),
        ("那", "That - ㄋ (n)"),
        ("拉", "Pull - ㄌ (l)"),
        ("个", "Classifier - ㄍ (g)"),
        ("可", "Can - ㄎ (k)"),
        ("河", "River - ㄏ (h)"),
        ("姐", "Older sister - ㄐ (j)"),
        ("去", "Go - ㄑ (q)"),
        ("西", "West - ㄒ (x)"),
        ("知", "Know - ㄓ (zh)"),
        ("吃", "Eat - ㄔ (ch)"),
        ("是", "Is - ㄕ (sh)"),
        ("日", "Day/sun - ㄖ (r)"),
        ("字", "Character - ㄗ (z)"),
        ("次", "Time/occasion - ㄘ (c)"),
        ("思", "Think - ㄙ (s)"),
    ]

    print(f"[6/9] Creating phoneme coverage - initials ({len(initials)} sentences)...")
    for text, notes in initials:
        sentences.append(
            create_sentence(sentence_id, text, "phoneme_initials", "basic", notes)
        )
        sentence_id += 1

    # ==========================================================================
    # PHONEME COVERAGE - FINALS (16 basic Zhuyin finals)
    # ==========================================================================

    finals = [
        ("啊", "Ah - ㄚ (a)"),
        ("我", "I/me - 我 (uo special final)"),
        ("哥", "Older brother - ㄜ (e)"),
        ("衣", "Clothes - ㄧ (i)"),
        ("乌", "Crow - ㄨ (u)"),
        ("鱼", "Fish - ㄩ (ü)"),
        ("白", "White - ㄞ (ai)"),
        ("飞", "Fly - ㄟ (ei)"),
        ("高", "Tall/high - ㄠ (ao)"),
        ("走", "Walk - ㄡ (ou)"),
        ("安", "Peace - ㄢ (an)"),
        ("人", "Person - ㄣ (en)"),
        ("房", "House - ㄤ (ang)"),
        ("风", "Wind - ㄥ (eng)"),
        ("儿", "Child/diminutive - ㄦ (er)"),
    ]

    print(f"[7/9] Creating phoneme coverage - finals ({len(finals)} sentences)...")
    for text, notes in finals:
        sentences.append(
            create_sentence(sentence_id, text, "phoneme_finals", "basic", notes)
        )
        sentence_id += 1

    # ==========================================================================
    # TONE COVERAGE (All 5 tones with same syllable)
    # ==========================================================================

    tones = [
        ("妈", "Mom - 1st tone (high level)"),
        ("麻", "Hemp - 2nd tone (rising)"),
        ("马", "Horse - 3rd tone (dipping)"),
        ("骂", "Scold - 4th tone (falling)"),
        ("吗", "Question particle - 5th tone (neutral)"),
    ]

    print(f"[8/9] Creating tone coverage ({len(tones)} sentences)...")
    for text, notes in tones:
        sentences.append(
            create_sentence(sentence_id, text, "tone_coverage", "basic", notes)
        )
        sentence_id += 1

    # ==========================================================================
    # COMPLEX PHONEMES & SPECIAL CASES
    # ==========================================================================

    complex = [
        ("光", "Light - ㄍ王 (uang)"),
        ("窗", "Window - ㄔ王 (uang after ch)"),
        ("双", "Pair - ㄕ王 (uang after sh)"),
        ("想", "Think - ㄒ阳 (iang)"),
        ("强", "Strong - ㄑ阳 (iang after q)"),
        ("床", "Bed - ㄔ王 (uang)"),
        ("装", "Install/dress - ㄓ王 (uang after zh)"),
        ("花儿", "Flower - erhua (儿化音)"),
        ("玩儿", "Play - erhua with R marker"),
        ("聪明", "Clever - complex compound"),
        ("快乐", "Happy - ㄎ外 (uai)"),
        ("幸福", "Blessed/happy"),
        ("健康", "Healthy"),
    ]

    print(f"[9/9] Creating complex phonemes ({len(complex)} sentences)...")
    for text, notes in complex:
        sentences.append(
            create_sentence(
                sentence_id, text, "complex_phonemes", "intermediate", notes
            )
        )
        sentence_id += 1

    # ==========================================================================
    # SAVE TO FILE
    # ==========================================================================

    output_path = Path(__file__).parent / "data" / "zh_synthetic_handcrafted.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)

    # ==========================================================================
    # STATISTICS
    # ==========================================================================

    print("\n" + "=" * 80)
    print("DATASET STATISTICS")
    print("=" * 80)
    print(f"Total sentences: {len(sentences)}")
    print("\nBy category:")

    categories = {}
    for s in sentences:
        cat = s["category"]
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        print(f"  {cat:25s}: {count:3d} sentences")

    # Collect all unique phoneme characters
    all_chars = set()
    for s in sentences:
        all_chars.update(s["phonemes"])

    print(f"\nUnique phoneme characters: {len(all_chars)}")
    print(f"Characters: {''.join(sorted(all_chars))}")

    # Check against ZH_VOCAB
    from kokorog2p.phonemes import ZH_VOCAB

    missing_from_dataset = ZH_VOCAB - all_chars
    extra_in_dataset = all_chars - ZH_VOCAB

    coverage = len(all_chars & ZH_VOCAB) / len(ZH_VOCAB) * 100

    print(
        f"Phoneme coverage: {coverage:.1f}% "
        f"({len(all_chars & ZH_VOCAB)}/{len(ZH_VOCAB)})"
    )

    if missing_from_dataset:
        print(f"\nMissing from dataset ({len(missing_from_dataset)} chars):")
        print(f"  {''.join(sorted(missing_from_dataset))}")

    if extra_in_dataset:
        print(f"\nExtra in dataset (not in ZH_VOCAB): {len(extra_in_dataset)} chars")
        print(f"  {''.join(sorted(extra_in_dataset))}")

    print(f"\n✓ Dataset saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
