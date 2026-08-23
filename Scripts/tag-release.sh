#!/bin/bash

set -euo pipefail

REMOTE="origin"
BUMP_KIND="patch"
TAG_MESSAGE=""
AUTO_CONFIRM="false"
ALLOW_DIRTY="false"
FETCH_TAGS="true"

usage() {
    cat <<'EOF'
Usage:
  Scripts/tag-release.sh [patch|minor|major] [options]

Options:
  -m, --message <message>   Annotated tag message. Default: "Release <tag>"
  -r, --remote <remote>     Remote to push to. Default: origin
  -y, --yes                 Skip confirmation prompt
      --allow-dirty         Allow tagging with uncommitted changes
      --no-fetch            Do not fetch remote tags before computing next tag
  -h, --help                Show this help

Examples:
  Scripts/tag-release.sh
  Scripts/tag-release.sh minor
  Scripts/tag-release.sh patch --message "Release 0.0.4"
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        patch|minor|major)
            BUMP_KIND="$1"
            shift
            ;;
        -m|--message)
            TAG_MESSAGE="${2:-}"
            shift 2
            ;;
        -r|--remote)
            REMOTE="${2:-}"
            shift 2
            ;;
        -y|--yes)
            AUTO_CONFIRM="true"
            shift
            ;;
        --allow-dirty)
            ALLOW_DIRTY="true"
            shift
            ;;
        --no-fetch)
            FETCH_TAGS="false"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: this script must be run inside a git repository." >&2
    exit 1
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
    echo "Error: remote '$REMOTE' does not exist." >&2
    exit 1
fi

if [[ "$ALLOW_DIRTY" != "true" ]] && [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree has uncommitted changes. Commit or stash them first, or pass --allow-dirty." >&2
    exit 1
fi

if [[ "$FETCH_TAGS" == "true" ]]; then
    echo "==> Fetching tags from $REMOTE..."
    git fetch "$REMOTE" --tags --prune
fi

LATEST_TAG=$(
    git tag --list '[0-9]*.[0-9]*.[0-9]*' \
    | sort -V \
    | tail -n 1
)

if [[ -z "$LATEST_TAG" ]]; then
    MAJOR=0
    MINOR=0
    PATCH=0
else
    IFS='.' read -r MAJOR MINOR PATCH <<< "$LATEST_TAG"
fi

case "$BUMP_KIND" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
esac

NEXT_TAG="${MAJOR}.${MINOR}.${PATCH}"

if git rev-parse -q --verify "refs/tags/$NEXT_TAG" >/dev/null 2>&1; then
    echo "Error: tag '$NEXT_TAG' already exists." >&2
    exit 1
fi

if [[ -z "$TAG_MESSAGE" ]]; then
    TAG_MESSAGE="Release $NEXT_TAG"
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse --short HEAD)

echo "==> Release plan"
echo "Remote:        $REMOTE"
echo "Branch:        $CURRENT_BRANCH"
echo "Commit:        $CURRENT_COMMIT"
echo "Latest tag:    ${LATEST_TAG:-<none>}"
echo "Bump:          $BUMP_KIND"
echo "Next tag:      $NEXT_TAG"
echo "Tag message:   $TAG_MESSAGE"
echo

if [[ "$AUTO_CONFIRM" != "true" ]]; then
    read -r -p "Create and push tag '$NEXT_TAG'? [y/N] " RESPONSE
    case "$RESPONSE" in
        y|Y|yes|YES)
            ;;
        *)
            echo "Cancelled."
            exit 0
            ;;
    esac
fi

echo "==> Creating annotated tag $NEXT_TAG"
git tag -a "$NEXT_TAG" -m "$TAG_MESSAGE"

echo "==> Pushing tag to $REMOTE"
git push "$REMOTE" "$NEXT_TAG"

echo "Done: pushed tag $NEXT_TAG to $REMOTE"
