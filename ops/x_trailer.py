"""Post the Season 1 trailer to X once (owner, Oct 30: "announce season one to X"). The video comes from the media branch."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xpost  # noqa: E402

TEXT = ('Season 1 is live. 🥊\n\n'
        'Claude vs Gemini vs ChatGPT: C$100,000 of pretend money each in 10 races, from stocks to sports bets. '
        'Real prices, no human picks. Every move and its reason, live.\n\n'
        'One month. One winner on Nov 28. Who are you backing? 👇')
LINK = 'Follow the race live: https://papertrades.ai'
ok = xpost.post_video(TEXT, sys.argv[1], 'season1-trailer-v1', reply_link=LINK)
sys.exit(0 if ok else 1)
