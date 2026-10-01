#!/bin/sh
# Build the review bundle: ../os9-dev-skills.zip
#
# The bundle is the tracked tree minus the maintainer-side tooling, wrapped in
# one top-level directory so it expands tidily. `git archive` is what makes it
# trustworthy: only committed files can appear, so an uncommitted experiment or
# an untracked scratch file cannot ride along. maintainer/ is gitignored and
# therefore excluded by construction rather than by a rule that could rot.
#
# One edition serves every assistant: README.md's install table covers Claude
# Code, other skill loaders, any agent pointed at AGENTS.md, and attachment-only
# chat. There is nothing to vary.
#
# Usage: tools/make-bundle.sh [output.zip]

set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-$root/../os9-dev-skills.zip}
name=os9-dev-skills

cd "$root"

if ! git diff --quiet HEAD -- . 2>/dev/null; then
    echo "refusing: working tree has uncommitted changes -- the bundle would not" >&2
    echo "match any commit. Commit or stash first." >&2
    exit 1
fi

echo "checker + tests"
python3 tools/check_doc_consistency.py --no-inventory >/dev/null
python3 tools/tests/test_check.py >/dev/null 2>&1

staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
mkdir "$staging/$name"

# Committed files only, then drop what the reader has no use for.
git archive HEAD | tar -x -C "$staging/$name"
# tools/ stays in the repo for contributors but has no use inside a bundle.
rm -rf "$staging/$name/tools" "$staging/$name/.gitignore"

# A bundle that leaked maintainer notes would be worse than no bundle.
if find "$staging/$name" -name 'maintainer' -o -name '*.pyc' | grep -q .; then
    echo "refusing: maintainer material reached the staging tree" >&2
    exit 1
fi

rm -f "$out"
(cd "$staging" && zip -q -r "$out" "$name")

echo "built $out"
unzip -l "$out" | tail -3
