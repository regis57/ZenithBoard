#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copy docs/wiki/*.md to the GitHub wiki of this repository.
#
# The wiki is a separate git repository, so it has no pull request and no CI:
# the pages are kept here, reviewed here, and copied over by this script.
#
#   bash tools/publish-wiki.sh
#
# If the clone fails with "repository not found", the wiki has never been
# created: open https://github.com/regis57/ZenithBoard/wiki in a browser,
# save any page once, then run this again.
set -euo pipefail

REPO="${ZB_WIKI_REPO:-https://github.com/regis57/ZenithBoard.wiki.git}"
NAME="${ZB_GIT_NAME:-regis57}"
MAIL="${ZB_GIT_EMAIL:-regis.hennequin@gmail.com}"

here=$(cd "$(dirname "$0")/.." && pwd)
src="$here/docs/wiki"
[ -d "$src" ] || { echo "no $src"; exit 1; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Cloning the wiki..."
git clone --quiet "$REPO" "$tmp/wiki"

cp "$src"/*.md "$tmp/wiki/"

cd "$tmp/wiki"
if git diff --quiet && [ -z "$(git status --porcelain)" ]; then
  echo "The wiki is already up to date."
  exit 0
fi

git add -A
git -c "user.name=$NAME" -c "user.email=$MAIL" \
    commit --quiet -m "Wiki: roadmap, status and software documentation"
git push --quiet

echo "Published. See https://github.com/regis57/ZenithBoard/wiki"
git --no-pager log -1 --format='%h  %an <%ae>  %s'
