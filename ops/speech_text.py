"""Spoken words, written one way, so a script ("twenty-eight thousand dollars") and a transcript ("$28,000") can be compared word for
word: numbers become words, $ becomes "dollars", % becomes "percent", hyphens and punctuation go. Used by ops/voice.py (did the voice
say the script?) and ops/yt_short.py (when is each word said?)."""
import re

ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
        'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']


def words_of(n):
    n = int(n)
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], 'hundred'] + (words_of(n % 100) if n % 100 else [])
    for size, name in ((10 ** 9, 'billion'), (10 ** 6, 'million'), (1000, 'thousand')):
        if n >= size:
            return words_of(n // size) + [name] + (words_of(n % size) if n % size else [])
    return [str(n)]


def tokens(text, drop_and=True):
    """The words as they are said: '$28,085' -> twenty eight thousand eighty five dollars; '2%' -> two percent."""
    t = text.lower().replace('&', ' and ').replace('’', "'")
    t = re.sub(r'(\d)\s+([,.]\d{3})', r'\1\2', t)                  # "28 ,000" (split by the transcript) -> "28,000"
    t = re.sub(r'(\d),(?=\d{3})', r'\1', t)                       # 28,085 -> 28085
    t = re.sub(r'\$\s*(\d+(?:\.\d+)?)', r' \1 dollars ', t)        # $28085 -> 28085 dollars
    t = re.sub(r'(\d+(?:\.\d+)?)\s*%', r' \1 percent ', t)
    t = re.sub(r'[-–—]', ' ', t)
    out = []
    for w in re.sub(r"[^a-z0-9. ]", ' ', t).split():
        w = w.strip('.')
        if not w:
            continue
        if re.fullmatch(r'\d+', w):
            out += words_of(w)
        elif re.fullmatch(r'\d+\.\d+', w):
            a, b = w.split('.'); out += words_of(a) + ['point'] + [ONES[int(c)] for c in b]
        else:
            out.append(w.replace('.', ''))
    return [w for w in out if w != 'and'] if drop_and else out     # "thousand and eighty" = "thousand eighty"


def merge_words(words):
    """Whisper can split "$28,000" into "$28" and ",000": put such pieces back together (keeping the time span)."""
    out = []
    for w, s, e in words:
        if out and re.match(r'^[,.]?\d', w.strip()) and re.search(r'\d$', out[-1][0].strip()) and w.strip()[:1] in ',.':
            out[-1] = [out[-1][0].strip() + w.strip(), out[-1][1], e]
        else:
            out.append([w, s, e])
    return out


def similarity(script, heard):
    """0..1: how closely the heard words match the script, letter by letter (spacing and hyphens do not count)."""
    import difflib
    a = ''.join(tokens(script)); b = ''.join(tokens(heard))
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
