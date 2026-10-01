#!/bin/sh
# Publish the zip and its release page together, so the page can never lag the
# zip it describes.
#
# The page text is tools/release-notes.md; review it before every run. The tag
# and title come from `version` in .claude-plugin/plugin.json. If a release for
# that version already exists, its zip is replaced and its page rewritten;
# otherwise a new release is created. Either way, zip and page go out together.
#
# Publishing is outward-facing: run it only on the maintainer's word.
#
# Usage: tools/publish-release.sh

set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"

version=$(python3 -c 'import json; print(json.load(open(".claude-plugin/plugin.json"))["version"])')
tag="v$version"
title="OS-9 skills for AI coding assistants $version"
notes=tools/release-notes.md

# The release must describe what is on GitHub, not a local commit.
git fetch -q origin main
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    echo "refusing: HEAD is not origin/main -- push first." >&2
    exit 1
fi

staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
zip="$staging/os9-dev-skills.zip"
tools/make-bundle.sh "$zip"

if gh release view "$tag" >/dev/null 2>&1; then
    gh release upload "$tag" "$zip" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes"
else
    gh release create "$tag" "$zip" --target main --title "$title" --notes-file "$notes"
fi

echo "published $tag"
