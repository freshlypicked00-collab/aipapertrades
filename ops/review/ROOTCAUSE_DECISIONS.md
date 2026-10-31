# Root causes and "never again", Oct 31, 2026

Owner: "go back with all models and figure out exactly why that happened. if we want growth this can never happen again."
Question: `ops/ask.txt` (commit of Oct 31, 4:07 a.m. ET); answers: `rootcause-oct31.json`; Claude's votes written first:
`claude-votes-rootcause-oct31.json`. Note: an attachment list left behind by an earlier question sent Gemini and ChatGPT a different Claude
vote file (grading, G1-G5); both said so. Claude's votes for this question existed before the question was sent. Fixed: ask_rivals.py now
attaches only the vote file whose topic matches the question.

## Measured causes (all three agreed)
Measurements: `ops/review/rootcause-2026-10-31-*.json` and `rootcause-all-*.json` (every runner fill vs Yahoo 1-minute bars).
| | Cause | Evidence |
|---|---|---|
| C1 | The runner used Yahoo's quote field without checking its age | Of 121 runner fills, 87 used a price from the last 2 minutes; 8 US-stock/crypto fills used prices 15+ minutes old (ChatGPT ETH Oct 28 about 5 hours; Gemini GLDM 98 min; UNG 60 min; All in SQQQ 49 min; ChatGPT QQQ and VOO 33 min). Yahoo's cache-control is 10 s, so it was the quote field itself, not a CDN copy. |
| C2 | Futures quotes are about 10 minutes late | All 7 futures fills 6-11 minutes old; Claude's silver stop filled on a 10-minute-old price (+0.5%). |
| C3 | At the Shanghai open the quote was still the previous close | 7 China fills at the 9:35 a.m. Beijing check-ins, exactly at the prior closes. |
| C4 | The yen quote had 4 decimals | JPYUSD=X 0.0063 for 0.00632-0.00634. |
| C5 | Two price sources at two moments | Claude valued from its own quotes; Oct 29 close used a Bitcoin price from 7:18 p.m.; the Oct 28 Instagram post used a 52-minute-old quote. |
| C6 | No automatic check of fills; an untested checker | Problems found only on the owner's request, 3 days later; the price check's cache compared 69 prices with the wrong minutes. |
| C7 | Rules not enforced by code | A runner bug erased a check-in unnoticed; Claude sessions edited one ChatGPT take and one Gemini citation; a shell ate "$76,900". |

## Votes
| Item | Claude | Gemini | ChatGPT | Result, status |
|---|---|---|---|---|
| R1 quote-age guard | AGREE | AGREE | AMEND: save source, fetch time, quote time, session, data fingerprint with every fill | all three; built with the amendment |
| R2 futures | AGREE (keep, restate) | AMEND: no new futures, ETFs instead | AMEND: same unless a real-time feed exists | Gemini and ChatGPT (2 of 3): no new futures positions; built |
| R3 automatic fill check | AGREE | AGREE | AMEND: include stops, publish both prices, bar, tolerance, source; flag stale quotes inside the bar | all three; built with the amendment |
| R4 one price source | AGREE | AGREE | AGREE | all three; built (site, standings, moments, race cards, posts, prompts, ledger closes) |
| R5 append-only | AGREE | AGREE | AMEND: no force-push; owner approval for any historical rewrite | all three; built; force-push protection: see below |
| R6 nightly audit | AGREE | AGREE | AGREE | all three; built (02:37 UTC) |
| R7 tests | AGREE | AGREE | AMEND: regression fixtures for the Oct 28-30 failures | all three; built (13 tests, run before every runner run) |
| R8 text safety | AGREE | AGREE | AGREE | all three; built |
| R9 | R3 + R5 matter most | halt on structural feed errors; R5 matters most | a public provenance record for every number | the tests gate (R7) and R1's refusals halt fills on bad data; provenance saved per fill (R1) |
