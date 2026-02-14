#!/bin/bash
# Deploy ProjectA to ai-builders.space
# Requires AI_BUILDER_TOKEN in environment or .env

set -e
source .env 2>/dev/null || true
TOKEN="${AI_BUILDER_TOKEN:-$SUPER_MIND_API_KEY}"

if [ -z "$TOKEN" ]; then
  echo "Error: AI_BUILDER_TOKEN or SUPER_MIND_API_KEY not set. Add to .env or export."
  exit 1
fi

curl -s -X POST "https://space.ai-builders.com/backend/v1/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/zpx223/CalligraphySignature",
    "service_name": "projecta-chat",
    "branch": "projecta-chat",
    "port": 8000
  }' | python3 -m json.tool
