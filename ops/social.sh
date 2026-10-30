#!/usr/bin/env bash
# Instagram: draw what is due, publish the pictures on papertrades.ai, post them, record them. Used by rivals.yml and social.yml.
set -u
[ -n "${INSTAGRAM_ACCESS_TOKEN:-}" ] || { echo "no Instagram key; skipped"; exit 0; }
pip install -q matplotlib pillow >/dev/null 2>&1 || true
git config user.name "paper-trades-bot"
git config user.email "paper-trades-bot@users.noreply.github.com"
push() {   # commit the given files and push, retrying on top of newer commits
  msg="$1"; shift
  for i in 1 2 3 4 5; do
    git add "$@" 2>/dev/null
    git diff --cached --quiet && return 0
    git commit -qm "$msg"
    git push -q origin HEAD:main && return 0
    git reset -q --soft HEAD~1; git stash -q; git fetch -q origin main && git reset -q --hard origin/main; git stash pop -q || true
    sleep $((i * 5))
  done
  return 1
}
highlights() {   # sort every story into its highlight and keep the owner's to-do issue current (ops/highlights.py)
  python3 ops/highlights.py sync && push "Instagram: highlights to-do" ops/src/social.json || echo "highlights to-do not updated"
}
git fetch -q origin main && git reset -q --hard origin/main
python3 ops/social.py prepare || { highlights; exit 0; }
[ "$(python3 -c 'import json;print(len(json.load(open("social/pending.json"))))')" = 0 ] && { echo "nothing due"; highlights; exit 0; }
push "Instagram: pictures for the next posts" social || { echo "could not push the pictures"; exit 0; }
gh api -X POST repos/${GITHUB_REPOSITORY}/pages/builds >/dev/null 2>&1 || true
python3 ops/social.py publish
push "Instagram: record what was posted" ops/src/social.json || echo "could not record the posts (they will be skipped by id next time only if recorded)"
highlights
exit 0
