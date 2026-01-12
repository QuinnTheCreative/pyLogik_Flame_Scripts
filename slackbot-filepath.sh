#!/bin/bash -e
set -o pipefail

# I created this script as a means to quickly and simply 
# post a directory path and listing to a specific slack channel.
# Then taking the result of that data and formatting it as "code" in slack.
# The formatting was desired as it visually makes it distinguished from the 
# rest of any slack conversations.

# To do this, you need to create a basic slack app. This is very basic
# and involves only delcaring the app in your works space via api.slack.com/apps

# Once you have created the app, you need to authorize it in those settings.
# Specifically, OAuth & Permissions. It is here you will generate the Token to
# authorize the script to post to your app and thus post to your slack-channel.

# The script here was cobbled together via vibe conding with ChatGPT and referencing
#  (https://github.com/rockymadden/slack-cli)





# -------------------------------------------------
# CONFIG
# -------------------------------------------------
SLACK_CHANNEL="C08NT32SM7H"
SLACK_USERNAME="qbot"
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
