#!/usr/bin/env python3
"""Readability scorer for translations.

North Star: текст должен быть безумно понятным для носителя.
Uses language-specific readability metrics:
- RU: Flesch-Kincaid adapted (sentence length, word length, syllable count)
- EN: Flesch Reading Ease + Flesch-Kincaid Grade Level
- ES: Fernández Huerta (adapted Flesch for Spanish)
"""

import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def count_syllables_ru(word):
    """Count vowel clusters in Russian word."""
    vowels = set("аеёиоуыэюя")
    word = word.lower()
    count = 0
    prev_vowel = False
    for ch in word:
        if ch in vowels:
            if not prev_vowel:
                count += 1
            prev_vowel = True
        else:
            prev_vowel = False
    return max(count, 1)


def count_syllables_en(word):
    """Approximate English syllable count."""
    word = word.lower().strip(".,:;!?\"'()")
    if not word:
        return 1
    vowels = set("aeiouy")
    count = 0
    prev_vowel = False
    for ch in word:
        if ch in vowels:
            if not prev_vowel:
                count += 1
            prev_vowel = True
        else:
            prev_vowel = False
    # Silent -e
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def count_syllables_es(word):
    """Spanish syllable count — straightforward vowel counting."""
    word = word.lower().strip(".,:;!?\"'()")
    if not word:
        return 1
    vowels = set("aeiouáéíóúü")
    count = 0
    prev_vowel = False
    for ch in word:
        if ch in vowels:
            if not prev_vowel:
                count += 1
            prev_vowel = True
        else:
            prev_vowel = False
    return max(count, 1)


def split_sentences(text):
    """Split text into sentences (language-agnostic)."""
    # Split on .!? followed by space + capital, or newline
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZА-ЯЁ])', text)
    return [s.strip() for s in sentences if len(s.strip().split()) >= 3]


def split_words(text):
    """Split text into words (language-agnostic)."""
    return [w for w in re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿА-Яа-яЁё]+', text)]


def flesch_ru(text):
    """Adapted Flesch for Russian: lower = harder."""
    sentences = split_sentences(text)
    words = split_words(text)
    if not sentences or not words:
        return {"score": 100, "grade": "N/A", "sentences": 0, "words": 0}

    n_sents = len(sentences)
    n_words = len(words)
    n_syllables = sum(count_syllables_ru(w) for w in words)

    asl = n_words / n_sents  # average sentence length
    asw = n_syllables / n_words  # average syllables per word

    # Flesch-Kincaid adapted for Russian
    score = 206.835 - (1.3 * asl) - (60.1 * asw)
    score = max(0, min(100, score))

    if score >= 80:
        grade = "очень легко (5 класс)"
    elif score >= 60:
        grade = "легко (7 класс)"
    elif score >= 40:
        grade = "средне (9 класс)"
    elif score >= 20:
        grade = "сложно (студент)"
    else:
        grade = "очень сложно (специалист)"

    return {
        "score": round(score, 1),
        "grade": grade,
        "sentences": n_sents,
        "words": n_words,
        "avg_sentence_len": round(asl, 1),
        "avg_syllables": round(asw, 2),
    }


def flesch_en(text):
    """Flesch Reading Ease for English."""
    sentences = split_sentences(text)
    words = split_words(text)
    if not sentences or not words:
        return {"score": 100, "grade": "N/A", "sentences": 0, "words": 0}

    n_sents = len(sentences)
    n_words = len(words)
    n_syllables = sum(count_syllables_en(w) for w in words)

    asl = n_words / n_sents
    asw = n_syllables / n_words

    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    score = max(0, min(100, score))

    if score >= 90:
        grade = "5th grade (very easy)"
    elif score >= 80:
        grade = "6th grade (easy)"
    elif score >= 70:
        grade = "7th grade (fairly easy)"
    elif score >= 60:
        grade = "8th-9th grade (plain English)"
    elif score >= 50:
        grade = "10th-12th grade (fairly difficult)"
    elif score >= 30:
        grade = "college (difficult)"
    else:
        grade = "college graduate (very difficult)"

    return {
        "score": round(score, 1),
        "grade": grade,
        "sentences": n_sents,
        "words": n_words,
        "avg_sentence_len": round(asl, 1),
        "avg_syllables": round(asw, 2),
    }


def flesch_es(text):
    """Fernández Huerta (adapted Flesch for Spanish)."""
    sentences = split_sentences(text)
    words = split_words(text)
    if not sentences or not words:
        return {"score": 100, "grade": "N/A", "sentences": 0, "words": 0}

    n_sents = len(sentences)
    n_words = len(words)
    n_syllables = sum(count_syllables_es(w) for w in words)

    asl = n_words / n_sents
    asw = n_syllables / n_words

    score = 206.84 - (1.02 * asl) - (60 * asw)
    score = max(0, min(100, score))

    if score >= 80:
        grade = "muy fácil"
    elif score >= 60:
        grade = "fácil"
    elif score >= 40:
        grade = "normal"
    elif score >= 20:
        grade = "algo difícil"
    else:
        grade = "muy difícil"

    return {
        "score": round(score, 1),
        "grade": grade,
        "sentences": n_sents,
        "words": n_words,
        "avg_sentence_len": round(asl, 1),
        "avg_syllables": round(asw, 2),
    }


SCORERS = {"ru": flesch_ru, "en": flesch_en, "es": flesch_es}


def score_file(path, lang):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    scorer = SCORERS.get(lang, flesch_en)
    result = scorer(text)
    result["path"] = os.path.relpath(path, ROOT)
    result["file"] = os.path.basename(path)
    return result


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Readability scorer")
    ap.add_argument("lang", nargs="?", default="ru",
                    help="Target language (ru/en/es)")
    ap.add_argument("--dir", default=None,
                    help="Directory (default: book/LANG/)")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    ap.add_argument("--desc", action="store_true", help="Sort by score ascending (hardest first)")
    args = ap.parse_args()

    scan_dir = args.dir or os.path.join(ROOT, "book", args.lang)
    if not os.path.isdir(scan_dir):
        print(f"Directory not found: {scan_dir}", file=sys.stderr)
        sys.exit(1)

    results = []
    for fn in sorted(os.listdir(scan_dir)):
        if not fn.endswith(".md"):
            continue
        results.append(score_file(os.path.join(scan_dir, fn), args.lang))

    if args.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        return

    if args.desc:
        results.sort(key=lambda r: r["score"])

    print(f"{'File':<40} {'Score':>6} {'Words':>6} {'Grade'}")
    print("-" * 75)
    for r in results:
        print(f"{r['file']:<40} {r['score']:>6.0f} {r['words']:>6} {r['grade']}")

    avg_score = sum(r["score"] for r in results) / len(results)
    total_words = sum(r["words"] for r in results)
    print("-" * 75)
    print(f"{'AVERAGE':<40} {avg_score:>6.1f} {total_words:>6}")
    print(f"\nTarget: score ≥ 60 (легко / easy / fácil) for native speaker clarity.")

    below = [r for r in results if r["score"] < 60]
    if below:
        print(f"\n⚠ {len(below)} file(s) below target:")
        for r in below:
            print(f"  {r['file']}: {r['score']:.0f} — {r['grade']}")

    sys.exit(1 if below else 0)


if __name__ == "__main__":
    main()