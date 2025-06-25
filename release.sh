#!/bin/bash
set -e

# 获取版本号
VERSION=$(grep '^version *= *' pyproject.toml | sed -E 's/version *= *"([^"]+)"/\1/')
TAG="v$VERSION"

echo "\ud83c\udff7\ufe0f  当前版本为: $VERSION"
echo "\ud83c\udff7\ufe0f  准备打 tag: $TAG"

# 确保 tag 不存在
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "\u274c Tag $TAG 已存在，发布失败"
  exit 1
fi

# 检查是否为 main 分支
CURRENT_BRANCH=$(git symbolic-ref --short HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "\u26a0\ufe0f 当前不在 main 分支，而是 $CURRENT_BRANCH，建议切换后再发布"
fi

# 添加更改并提交（如果有）
git add -A
git commit -m "release: $TAG" || echo "\u26a0\ufe0f 无需提交"

# 打 tag 并推送
git tag $TAG
git push origin main
git push origin $TAG

echo "\u2705 发布成功，tag: $TAG"
