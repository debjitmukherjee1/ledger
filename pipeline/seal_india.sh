#!/bin/sh
# Seal Ledger's Indian-market calls into an encrypted file the daily Action can open.
#
#   sh pipeline/seal_india.sh /path/to/ledger-india-calls.json /path/to/.vault-key
#
# Indian calls stay private for 12 months, so they are not kept in plain text in this
# public repository. The plain list lives outside the repo (PRIVATE/ledger-india-calls.json
# on the author's machine). This script encrypts it to pipeline/calls.india.json.enc with
# AES-256, using the same key as the repository secret INDIA_VAULT_KEY. The daily workflow
# decrypts it into pipeline/calls.india.json (git-ignored, never committed), and publish.py
# still decides which calls are old enough to appear on the site.
#
# Run this whenever you add or change an Indian call, then commit pipeline/calls.india.json.enc.
set -eu
SRC="${1:?path to ledger-india-calls.json}"
KEY="${2:?path to the vault key}"
cd "$(dirname "$0")"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert isinstance(d,list); print(len(d),'Indian calls')" "$SRC"
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -salt \
  -in "$SRC" -out calls.india.json.enc -pass file:"$KEY"
# check it opens again before declaring success
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 \
  -in calls.india.json.enc -pass file:"$KEY" | cmp -s - "$SRC"
echo "Sealed into pipeline/calls.india.json.enc"
