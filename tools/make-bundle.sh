#!/bin/sh
# Build the review bundle: ../os9-dev-skills.zip
#
# The bundle is the tracked tree minus the maintainer-side tooling, wrapped in
# one top-level directory so it expands tidily. `git archive` is what makes it
# trustworthy: only committed files can appear, so an uncommitted experiment or
# an untracked scratch file cannot ride along. maintainer/ is gitignored and
# therefore excluded by construction rather than by a rule that could rot.
#
# Two editions ship from the same corpus; only the wrapper documents differ.
#   (default)     for Microware review -- README installs it as a Claude skill
#   --variant sol for any other agent -- adds START-HERE.md and drops the
#                 Claude-specific install steps, since a reader who cannot use
#                 the skill runtime should not be told to symlink into it.
# Variant wrappers live in packaging/<name>/ and overlay the bundle root.
# packaging/ itself never ships in either edition.
#
# Usage: tools/make-bundle.sh [--variant sol] [output.zip]

set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
variant=
if [ "${1:-}" = "--variant" ]; then
    variant=$2
    shift 2
    [ -d "$root/packaging/$variant" ] || { echo "no such variant: $variant" >&2; exit 1; }
fi
default_out="$root/../os9-dev-skills.zip"
[ -n "$variant" ] && default_out="$root/../os9-dev-skills-for-agents.zip"
out=${1:-$default_out}
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
rm -rf "$staging/$name/tools" "$staging/$name/.gitignore" "$staging/$name/packaging"

if [ -n "$variant" ]; then
    cp "$root/packaging/$variant/"* "$staging/$name/"
fi

# A bundle that leaked maintainer notes would be worse than no bundle.
if find "$staging/$name" -name 'maintainer' -o -name '*.pyc' | grep -q .; then
    echo "refusing: maintainer material reached the staging tree" >&2
    exit 1
fi

rm -f "$out"
(cd "$staging" && zip -q -r "$out" "$name")

echo "built $out"
unzip -l "$out" | tail -3
