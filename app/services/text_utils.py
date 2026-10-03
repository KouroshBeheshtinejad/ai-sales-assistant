"""Text utilities shared by retrieval, intent detection and the offline assistant.

Everything here is deterministic, dependency-free and safe to call on untrusted
input.  The helpers understand Persian (Farsi) and English: character variants
(Arabic yeh/kaf), ZWNJ, Persian/Arabic digits, light stemming, number words
("سه میلیون"), budgets ("زیر ۳ میلیون") and fuzzy token matching.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache

# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

_CHAR_MAP = str.maketrans(
    {
        "ي": "ی", "ى": "ی", "ێ": "ی", "ك": "ک", "ڪ": "ک", "ة": "ه", "ۀ": "ه",
        "ؤ": "و", "أ": "ا", "إ": "ا", "ٱ": "ا", "ـ": "",
        "\u200c": " ", "\u200d": "", "\u200e": " ", "\u200f": " ", "\u00a0": " ",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        "٬": ",", "،": ",", "؛": ";", "؟": "?", "٫": ".",
    }
)
_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670]")
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_ARABIC_SCRIPT = re.compile(r"[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]")
_LATIN = re.compile(r"[A-Za-z]")


def normalize_text(value: str | None) -> str:
    """Comparison-only normal form: unified letters/digits, casefolded, single spaced."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(_CHAR_MAP)
    text = _DIACRITICS.sub("", text)
    return " ".join(text.casefold().split())


def has_arabic_script(text: str) -> bool:
    return bool(_ARABIC_SCRIPT.search(text or ""))


def detect_language(text: str, default: str = "fa") -> str:
    """Return ``fa`` or ``en`` for the dominant script of *text*."""
    arabic = len(_ARABIC_SCRIPT.findall(text or ""))
    latin = len(_LATIN.findall(text or ""))
    if arabic == 0 and latin == 0:
        return default
    return "fa" if arabic >= latin else "en"


def conversation_language(question: str, history=None, default: str = "fa") -> str:
    """Language of the reply: the question's, unless it is a bare Latin keyword
    ("checkout", "ok") inside an otherwise Persian conversation."""
    language = detect_language(question, default)
    if language == "en" and len(_LATIN_WORD.findall(question or "")) <= 2:
        for message in reversed(list(history or [])[-6:]):
            if message.get("role") == "user" and has_arabic_script(message.get("content", "")):
                return "fa"
    return language


_LATIN_WORD = re.compile(r"[A-Za-z]+")


def split_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize_text(text))


# --------------------------------------------------------------------------
# Stop words, light stemming, token forms
# --------------------------------------------------------------------------

STOP_WORDS_FA = frozenset(
    """
    و یا یه یک این آن اون همین همون که را رو از به با در بر برای تا هم نیز هر
    من ما شما تو او ایشان آیا چه چی چرا کی کجا کدام کدوم چطور چگونه چقدر چنده چند
    است هست هستش هستن هستند بود باشه باشد بود بوده شد شود میشه می شود میشود
    دارم داری دارد داره داریم دارید دارین دارند دارن ندارم ندارد
    بگو بگید بگین بده بدید بدین بدهید لطفا لطفاً ممنون مرسی سلام
    می نمی خواهم میخوام خوام خواهد خواد توانم میتونم میتونید میتوانم
    بنده اینجا اونجا آنجا هستید هستین
    درباره مورد سمت طرف اطلاعات توضیح توضیحات بیشتر
    خیلی کمی فقط هم‌چنین همچنین ولی اما اگر اگه پس هنوز الان امروز
    چیست چیه کدامه کدومه
    تو توی روی زیر بالای بین
    ها های هایی تر ترین ای ی
    """.split()
)
STOP_WORDS_EN = frozenset(
    """
    a an and are about am at be been by can could do does did for from get give got
    have has had how i if in is it its me my of on or please show tell that the there
    these this those to us was we were what when where which who why will with would
    you your yours hello hi hey thanks thank any some
    """.split()
)
STOP_WORDS = STOP_WORDS_FA | STOP_WORDS_EN

_FA_SUFFIXES = (
    "هایی", "های", "ها", "ترین", "تری", "تر", "ات", "ام", "اش", "مان", "تان", "شان",
    "ان", "ی", "ش",
)
_EN_SUFFIXES = (("ies", "y"), ("sses", "ss"), ("es", ""), ("s", ""), ("ing", ""), ("ed", ""))


def stem_token(token: str) -> str:
    """Very light, conservative stemmer for Persian and English tokens."""
    if not token or token.isdigit():
        return token
    if _ARABIC_SCRIPT.search(token):
        for suffix in _FA_SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                return token[: -len(suffix)]
        return token
    if len(token) <= 3:
        return token
    for suffix, replacement in _EN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            if suffix == "s" and token.endswith(("ss", "us", "is")):
                continue
            return token[: -len(suffix)] + replacement
    return token


def token_forms(token: str) -> set[str]:
    forms = {token}
    stem = stem_token(token)
    if stem:
        forms.add(stem)
    return forms


def content_tokens(text: str, *, keep_stop: bool = False) -> list[str]:
    """Normalised tokens, stop words removed, each expanded to its stem form."""
    result: list[str] = []
    for token in split_tokens(text):
        if not keep_stop and token in STOP_WORDS:
            continue
        stem = stem_token(token)
        if not keep_stop and stem in STOP_WORDS:
            continue
        if len(stem) < 2 and not stem.isdigit():
            continue
        result.append(stem)
    return result


# --------------------------------------------------------------------------
# Fuzzy matching
# --------------------------------------------------------------------------


@lru_cache(maxsize=8192)
def trigrams(token: str) -> frozenset[str]:
    padded = f"^{token}$"
    if len(padded) < 3:
        return frozenset({padded})
    return frozenset(padded[i : i + 3] for i in range(len(padded) - 2))


def dice_similarity(first: str, second: str) -> float:
    a, b = trigrams(first), trigrams(second)
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def edit_ratio(first: str, second: str) -> float:
    return SequenceMatcher(None, first, second).ratio()


def fuzzy_match(token: str, vocabulary, *, min_ratio: float = 0.78) -> str | None:
    """Return the closest vocabulary token for a (possibly misspelled) token."""
    if len(token) < 4 or token.isdigit():
        return None
    best, best_score = None, 0.0
    for candidate in vocabulary:
        if abs(len(candidate) - len(token)) > 2 or candidate == token:
            continue
        if dice_similarity(token, candidate) < 0.45:
            continue
        score = edit_ratio(token, candidate)
        if score > best_score:
            best, best_score = candidate, score
    return best if best_score >= min_ratio else None


# --------------------------------------------------------------------------
# Sentences / passages
# --------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟۔;؛])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(text or "")]
    return [part for part in parts if part]


def chunk_text(text: str, *, target_chars: int = 420, overlap_sentences: int = 1) -> list[str]:
    """Split long text into overlapping passages made of whole sentences."""
    sentences = split_sentences(text)
    if not sentences:
        return []
    if len(text) <= target_chars * 1.4:
        return [" ".join(sentences)]
    passages: list[str] = []
    current: list[str] = []
    size = 0
    for sentence in sentences:
        if current and size + len(sentence) > target_chars:
            passages.append(" ".join(current))
            current = current[-overlap_sentences:] if overlap_sentences else []
            size = sum(len(item) for item in current)
        current.append(sentence)
        size += len(sentence)
    if current:
        tail = " ".join(current)
        if not passages or tail != passages[-1]:
            passages.append(tail)
    return passages


# --------------------------------------------------------------------------
# Numbers: digits, number words, money amounts and budgets
# --------------------------------------------------------------------------

_UNITS = {
    "صفر": 0, "یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6,
    "شیش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10, "یازده": 11, "دوازده": 12,
    "سیزده": 13, "چهارده": 14, "پانزده": 15, "شانزده": 16, "هفده": 17, "هجده": 18,
    "نوزده": 19, "بیست": 20, "سی": 30, "چهل": 40, "پنجاه": 50, "شصت": 60,
    "هفتاد": 70, "هشتاد": 80, "نود": 90, "صد": 100, "یکصد": 100, "دویست": 200,
    "سیصد": 300, "چهارصد": 400, "پانصد": 500, "ششصد": 600, "هفتصد": 700,
    "هشتصد": 800, "نهصد": 900,
}
_EN_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "hundred": 100,
}
_MULTIPLIERS = {
    "هزار": 1_000, "میلیون": 1_000_000, "ملیون": 1_000_000, "میلیارد": 1_000_000_000,
    "thousand": 1_000, "k": 1_000, "million": 1_000_000, "m": 1_000_000,
    "billion": 1_000_000_000,
}
NUMBER_WORD_TOKENS = frozenset(_UNITS) | frozenset(_EN_UNITS) | frozenset(_MULTIPLIERS)


def parse_number_words(tokens: list[str]) -> int | None:
    """Parse a run of tokens such as ["دو", "میلیون", "و", "پانصد", "هزار"]."""
    total, current, seen = 0, 0, False
    for token in tokens:
        if token == "و":
            continue
        if token in _UNITS:
            current += _UNITS[token]
            seen = True
        elif token in _EN_UNITS:
            current += _EN_UNITS[token]
            seen = True
        elif token in _MULTIPLIERS and seen:
            total += (current or 1) * _MULTIPLIERS[token]
            current = 0
        else:
            return None
    return total + current if seen else None


_NUM_UNIT_RE = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)*)\s*(میلیارد|میلیون|ملیون|هزار|billion|million|thousand|k|m)?(?![\w])"
)


def _digits_to_number(raw: str) -> float | None:
    cleaned = raw
    if re.fullmatch(r"\d{1,3}(,\d{3})+", cleaned):
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_amounts(text: str) -> list[int]:
    """Extract money-like integers: ``3 میلیون`` → 3000000, ``2,500,000`` → 2500000."""
    normalized = normalize_text(text)
    amounts: list[int] = []
    consumed: list[tuple[int, int]] = []
    for match in _NUM_UNIT_RE.finditer(normalized):
        number = _digits_to_number(match.group(1))
        if number is None:
            continue
        multiplier = _MULTIPLIERS.get(match.group(2) or "", 1)
        amounts.append(int(round(number * multiplier)))
        consumed.append(match.span())
    tokens = split_tokens(normalized)
    run: list[str] = []

    def flush() -> None:
        nonlocal run
        if run and any(token in _MULTIPLIERS for token in run):
            value = parse_number_words(run)
            if value:
                amounts.append(value)
        run = []

    for token in tokens:
        if token in _UNITS or token in _EN_UNITS or token in _MULTIPLIERS or (run and token == "و"):
            run.append(token)
        else:
            flush()
    flush()
    return amounts


_MAX_WORDS = ("زیر", "کمتر از", "کمتر", "حداکثر", "تا سقف", "تا", "under", "below", "less than", "up to", "at most", "max", "cheaper than")
_MIN_WORDS = ("بالای", "بیشتر از", "بیشتر", "حداقل", "بالاتر از", "over", "above", "more than", "at least", "min")
_BETWEEN_RE = re.compile(r"(?:بین|between)\s+(.+?)\s+(?:تا|و|and|to)\s+(.+)")


def _has_phrase(padded: str, phrase: str) -> bool:
    return f" {phrase} " in padded


def extract_budget(text: str) -> tuple[int | None, int | None]:
    """Return ``(minimum, maximum)`` price constraints found in a question."""
    normalized = normalize_text(text)
    between = _BETWEEN_RE.search(normalized)
    if between:
        low = parse_amounts(between.group(1))
        high = parse_amounts(between.group(2))
        if low and high:
            lo, hi = sorted((low[0], high[0]))
            return lo, hi
    amounts = parse_amounts(normalized)
    if not amounts:
        return None, None
    amount = amounts[0]
    padded = f" {normalized} "
    if any(_has_phrase(padded, word) for word in _MAX_WORDS):
        return None, amount
    if any(_has_phrase(padded, word) for word in _MIN_WORDS):
        return amount, None
    if re.search(r"(?:بودجه|budget)", normalized):
        return None, amount
    return None, None


def format_price(value) -> str:
    """Human price: ``18990000.00`` → ``18,990,000`` (keeps real decimals)."""
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def numbers_in(text: str) -> set[int]:
    """All integers (digit-normalised, separators removed) appearing in *text*."""
    found: set[int] = set()
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", normalize_text(text)):
        cleaned = raw.replace(",", "")
        try:
            found.add(int(float(cleaned)))
        except ValueError:
            continue
    return found


def fa_digits(text: str) -> str:
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
