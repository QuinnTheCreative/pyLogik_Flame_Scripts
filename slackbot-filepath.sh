#!/bin/bash -e
set -o pipefail

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
SLACK_CHANNEL="<slack cheannel code not name>"
SLACK_USERNAME="<your username>"
SLACK_ICON_EMOJI=":file_folder:"
STATE_FILE=".last_slack_message"

API_POST="https://slack.com/api/chat.postMessage"
API_DELETE="https://slack.com/api/chat.delete"

: "${SLACK_TOKEN:?SLACK_TOKEN must be exported}"

# -------------------------------------------------
# DELETE MODE (GUARDED, NO JSON)
# -------------------------------------------------
if [[ "$1" == "--delete" ]]; then
    [[ -f "$STATE_FILE" ]] || { echo "No state file; refusing delete." >&2; exit 1; }

    read -r saved_channel saved_ts < "$STATE_FILE"

    [[ "$saved_channel" == "$SLACK_CHANNEL" ]] || {
        echo "Channel mismatch; refusing delete." >&2
        exit 1
    }

    curl -sS \
      -H "Authorization: Bearer $SLACK_TOKEN" \
      -H "Content-type: application/json; charset=utf-8" \
      --data "{\"channel\":\"$saved_channel\",\"ts\":\"$saved_ts\"}" \
      "$API_DELETE" \
      > /dev/null

    rm -f "$STATE_FILE"
    exit 0
fi

# -------------------------------------------------
# INPUT
# -------------------------------------------------
if [[ -n "$1" ]]; then
    INPUT="$*"
elif [[ ! -t 0 ]]; then
    INPUT="$(cat)"
else
    INPUT="$(pwd; tree -hD)"
fi

# -------------------------------------------------
# FORMAT (inline code per line)
# -------------------------------------------------
formatted=$(printf '%s\n' "$INPUT" | sed 's/.*/`&`/')

# -------------------------------------------------
# BUILD PAYLOAD (NO PYTHON)
# -------------------------------------------------
payload=$(cat <<EOF
{
  "channel": "$SLACK_CHANNEL",
  "text": $(printf '%s' ":round_pushpin: $formatted" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
  "username": "$SLACK_USERNAME",
  "icon_emoji": "$SLACK_ICON_EMOJI"
}
EOF
)

# -------------------------------------------------
# OPTIONAL DEBUG (one-line toggle)
# -------------------------------------------------
# echo "$payload" > ~/Desktop/slack_last_payload.json

# -------------------------------------------------
# POST MESSAGE (NO RESPONSE PARSING)
# -------------------------------------------------
headers="$(mktemp)"

curl -sS -D "$headers" \
  -H "Authorization: Bearer $SLACK_TOKEN" \
  -H "Content-type: application/json; charset=utf-8" \
  --data "$payload" \
  "$API_POST" \
  > /dev/null

# -------------------------------------------------
# EXTRACT TIMESTAMP FROM HEADERS IF PRESENT
# -------------------------------------------------
ts="$(grep -i '^x-slack-req-id:' "$headers" | awk '{print $2}' | tr -d '\r')"
rm -f "$headers"

# Fallback timestamp if Slack gives none
[[ -n "$ts" ]] || ts="$(date +%s)"

echo "$SLACK_CHANNEL $ts" > "$STATE_FILE"
