"""Reviewed station benchmark corpora and deterministic scaling helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

LANGUAGES: dict[str, dict[str, Any]] = {
    "en-us": {
        "label": "English US",
        "slug": "en_us",
        "sentences": (
            "The quick brown fox jumps over the lazy dog.",
            "Please bring fresh coffee and warm bread to the table.",
            "Every language needs a fast and predictable pronunciation frontend.",
            (
                "Kokoro reads clear prepared text while the benchmark "
                "watches every station."
            ),
        ),
    },
    "en-gb": {
        "label": "English GB",
        "slug": "en_gb",
        "sentences": (
            "The colour of the theatre curtain is dark blue.",
            "Please bring fresh tea and warm bread to the table.",
            "A careful speaker keeps every syllable clear and steady.",
            (
                "Kokoro reads prepared British English while the benchmark "
                "watches every station."
            ),
        ),
    },
    "de": {
        "label": "German",
        "slug": "de",
        "sentences": (
            "Der schnelle braune Fuchs springt über den faulen Hund.",
            "Bitte bring frischen Kaffee und warmes Brot an den Tisch.",
            "Eine klare Aussprache macht lange Sätze leichter verständlich.",
            (
                "Kokoro liest vorbereiteten deutschen Text und der Benchmark "
                "misst jede Station."
            ),
        ),
    },
    "fr": {
        "label": "French",
        "slug": "fr",
        "sentences": (
            "Le renard brun rapide saute par dessus le chien paresseux.",
            "Veuillez apporter du café frais et du pain chaud à la table.",
            "Une prononciation claire rend chaque phrase plus facile à comprendre.",
            (
                "Kokoro lit un texte français préparé pendant que le benchmark "
                "mesure chaque étape."
            ),
        ),
    },
    "es": {
        "label": "Spanish",
        "slug": "es",
        "sentences": (
            "El zorro marrón rápido salta sobre el perro perezoso.",
            "Trae café fresco y pan caliente a la mesa, por favor.",
            "Una pronunciación clara hace que cada frase sea fácil de entender.",
            "Kokoro lee texto español preparado mientras el benchmark mide cada etapa.",
        ),
    },
    "it": {
        "label": "Italian",
        "slug": "it",
        "sentences": (
            "La volpe marrone veloce salta sopra il cane pigro.",
            "Porta caffè fresco e pane caldo al tavolo, per favore.",
            "Una pronuncia chiara rende ogni frase facile da capire.",
            (
                "Kokoro legge testo italiano preparato mentre il benchmark "
                "misura ogni fase."
            ),
        ),
    },
    "pt-br": {
        "label": "Portuguese BR",
        "slug": "pt_br",
        "sentences": (
            "A rápida raposa marrom salta sobre o cachorro preguiçoso.",
            "Por favor, traga café fresco e pão quente para a mesa.",
            "Uma pronúncia clara deixa cada frase mais fácil de entender.",
            (
                "Kokoro lê texto brasileiro preparado enquanto o benchmark "
                "mede cada etapa."
            ),
        ),
    },
    "pt-pt": {
        "label": "Portuguese PT",
        "slug": "pt_pt",
        "sentences": (
            "A rápida raposa castanha salta sobre o cão preguiçoso.",
            "Por favor, traga café fresco e pão quente para a mesa.",
            "Uma pronúncia clara torna cada frase mais fácil de compreender.",
            "Kokoro lê texto europeu preparado enquanto o benchmark mede cada etapa.",
        ),
    },
    "cs": {
        "label": "Czech",
        "slug": "cs",
        "sentences": (
            "Rychlá hnědá liška skáče přes líného psa.",
            "Prosím přines čerstvou kávu a teplý chléb na stůl.",
            "Jasná výslovnost usnadňuje porozumění každé větě.",
            "Kokoro čte připravený český text a benchmark měří každou část.",
        ),
    },
    "vi": {
        "label": "Vietnamese",
        "slug": "vi",
        "sentences": (
            "Con cáo nâu nhanh nhảy qua con chó lười.",
            "Xin mang cà phê mới và bánh mì nóng đến bàn.",
            "Phát âm rõ ràng giúp mọi câu dễ hiểu hơn.",
            "Kokoro đọc văn bản tiếng Việt đã chuẩn bị và phép đo theo dõi từng bước.",
        ),
    },
    "sv-se": {
        "label": "Swedish",
        "slug": "sv",
        "sentences": (
            "Den snabba bruna räven hoppar över den lata hunden.",
            "Ta med färskt kaffe och varmt bröd till bordet.",
            "Ett tydligt uttal gör varje mening lättare att förstå.",
            "Kokoro läser förberedd svensk text medan mätningen följer varje steg.",
        ),
    },
    "ru": {
        "label": "Russian",
        "slug": "ru",
        "sentences": (
            "Быстрая коричневая лиса прыгает через ленивую собаку.",
            "Пожалуйста, принеси свежий кофе и тёплый хлеб к столу.",
            "Чёткое произношение помогает легче понимать каждую фразу.",
            "Кокоро читает подготовленный русский текст, а тест измеряет каждый этап.",
        ),
    },
    "kk": {
        "label": "Kazakh",
        "slug": "kk",
        "sentences": (
            "Жылдам қоңыр түлкі жалқау иттің үстінен секіреді.",
            "Үстелге жаңа кофе мен жылы нан әкеліңіз.",
            "Анық айтылым әр сөйлемді түсінуді жеңілдетеді.",
            "Кокоро дайын қазақ мәтінін оқиды, ал сынақ әр кезеңді өлшейді.",
        ),
    },
    "he": {
        "label": "Hebrew",
        "slug": "he",
        "sentences": (
            "השועל החום המהיר קופץ מעל הכלב העצלן.",
            "בבקשה הבא קפה טרי ולחם חם אל השולחן.",
            "הגייה ברורה מקלה על ההבנה של כל משפט.",
            "קוקורו קורא טקסט עברי מוכן והבדיקה מודדת כל שלב.",
        ),
    },
    "ar": {
        "label": "Arabic",
        "slug": "ar",
        "sentences": (
            "يقفز الثعلب البني السريع فوق الكلب الكسول.",
            "من فضلك أحضر قهوة طازجة وخبزا دافئا إلى الطاولة.",
            "يساعد النطق الواضح على فهم كل جملة بسهولة.",
            "يقرأ كوكورو نصا عربيا جاهزا بينما يقيس الاختبار كل مرحلة.",
        ),
    },
    "zh": {
        "label": "Chinese",
        "slug": "zh",
        "sentences": (
            "敏捷的棕色狐狸跳过懒狗。",
            "请把新鲜咖啡和热面包带到桌上。",
            "清楚的发音让每句话都更容易理解。",
            "可可罗读取准备好的中文文本，基准测试记录每个阶段。",
        ),
    },
    "ja": {
        "label": "Japanese",
        "slug": "ja",
        "sentences": (
            "素早い茶色の狐が怠けた犬を飛び越えます。",
            "新鮮なコーヒーと温かいパンをテーブルに持ってきてください。",
            "明瞭な発音はすべての文を理解しやすくします。",
            "ココロは準備された日本語の文章を読み、ベンチマークが各段階を測ります。",
        ),
    },
    "ko": {
        "label": "Korean",
        "slug": "ko",
        "sentences": (
            "빠른 갈색 여우가 게으른 개를 뛰어넘습니다.",
            "신선한 커피와 따뜻한 빵을 식탁으로 가져오세요.",
            "명확한 발음은 모든 문장을 이해하기 쉽게 만듭니다.",
            "코코로는 준비된 한국어 문장을 읽고 벤치마크는 각 단계를 측정합니다.",
        ),
    },
    "th": {
        "label": "Thai",
        "slug": "th",
        "sentences": (
            "สุนัขจิ้งจอกสีน้ำตาลที่ว่องไวกระโดดข้ามสุนัขขี้เกียจ",
            "กรุณานำกาแฟสดและขนมปังอุ่นมาที่โต๊ะ",
            "การออกเสียงที่ชัดเจนทำให้ทุกประโยคเข้าใจง่ายขึ้น",
            "โคโคโระอ่านข้อความภาษาไทยที่เตรียมไว้และการทดสอบวัดทุกขั้นตอน",
        ),
    },
}


@dataclass(frozen=True)
class Corpus:
    name: str
    sentences: tuple[str, ...]
    base_sentence_count: int

    @property
    def text(self) -> str:
        return " ".join(self.sentences)

    @property
    def input_chars(self) -> int:
        return len(self.text)

    @property
    def input_utf8_bytes(self) -> int:
        return len(self.text.encode("utf-8"))


def scale_sentences(
    sentences: Sequence[str],
    *,
    target_chars: int,
) -> tuple[str, ...]:
    """Repeat reviewed sentences until the target is reached without truncation."""
    if target_chars < 1:
        raise ValueError("target_chars must be positive")
    if not sentences:
        raise ValueError("sentences must not be empty")
    result: list[str] = []
    total = 0
    index = 0
    while total < target_chars:
        sentence = sentences[index % len(sentences)]
        result.append(sentence)
        total += len(sentence) + (1 if len(result) > 1 else 0)
        index += 1
    return tuple(result)


def get_corpus(
    language: str,
    *,
    profile: str = "smoke",
    target_chars: int = 2000,
) -> Corpus:
    """Build a named corpus from one language's reviewed smoke sentences."""
    try:
        spec = LANGUAGES[language]
    except KeyError as exc:
        raise ValueError(f"unknown language: {language}") from exc
    base = tuple(spec["sentences"])
    if profile == "smoke":
        sentences = base
    elif profile == "scaled":
        sentences = scale_sentences(base, target_chars=target_chars)
    else:
        raise ValueError(f"unknown corpus profile: {profile}")
    return Corpus(profile, sentences, len(base))


__all__ = ["LANGUAGES", "Corpus", "get_corpus", "scale_sentences"]
