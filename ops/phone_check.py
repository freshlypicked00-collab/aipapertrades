"""Phone pass (Nov 20): a guard for whoever edits ops/phone.css or ops/phone.js next. NOT part of the race runner's tests: it can never
stop a race run. Run it by hand from the repo root after an edit:  python3 ops/phone_check.py   (exit 1 when something is wrong).

It checks the promise the owner was given ("the computer layout stays exactly as it is"):
  1. every rule in ops/phone.css sits inside an "@media (max-width: N px)" block with N of 700 or less; the only thing allowed outside is
     the one line that hides the phone-only parts at 701 px and wider;
  2. ops/phone.js still tests the screen width before it draws anything, and still takes away what it added on a wider screen."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def top_level_blocks(css):
    """Yield (prelude, body) for every top-level block of a stylesheet (comments removed)."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    i, n = 0, len(css)
    while i < n:
        j = css.find('{', i)
        if j < 0:
            if css[i:].strip():
                yield css[i:].strip(), None
            return
        depth, k = 1, j + 1
        while k < n and depth:
            depth += css[k] == '{'
            depth -= css[k] == '}'
            k += 1
        yield css[i:j].strip(), css[j + 1:k - 1]
        i = k


def check():
    problems = []
    css = open(os.path.join(HERE, 'phone.css')).read()
    blocks = list(top_level_blocks(css))
    if not blocks:
        problems.append('ops/phone.css has no rules')
    for prelude, body in blocks:
        if body is None:
            problems.append('text outside any block: ' + prelude[:60])
            continue
        m = re.fullmatch(r'@media\s*\(\s*max-width:\s*(\d+)px\s*\)', prelude)
        if m and int(m.group(1)) <= 700:
            continue
        if re.fullmatch(r'@media\s*\(\s*min-width:\s*701px\s*\)', prelude) and re.fullmatch(r'\s*[^{}]+\{\s*display:\s*none\s*!important;\s*\}\s*', body):
            continue   # the one line that keeps the phone-only parts out of sight on wider screens
        problems.append('a rule that also reaches computers: "' + prelude[:80] + '"')
    js = open(os.path.join(HERE, 'phone.js')).read()
    if "matchMedia('(max-width: 700px)')" not in js:
        problems.append('ops/phone.js no longer tests for a screen 700 px wide or less')
    for name in ('dropFront', 'dropRaces', 'dropBar'):
        if not re.search(r'if \(!ON\.\w+ \|\| !PH\.matches\) \{ ' + name + r'\(\); return; \}', js):
            problems.append('ops/phone.js: ' + name + '() is no longer called when the screen is wider than a phone')
    return problems


if __name__ == '__main__':
    bad = check()
    for b in bad:
        print('PROBLEM:', b)
    print('phone pass guard: ' + ('OK, computers are untouched by ops/phone.css and ops/phone.js' if not bad else str(len(bad)) + ' problem(s)'))
    sys.exit(1 if bad else 0)
