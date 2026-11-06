#!/bin/bash
# Deploy de PHP API van Pi naar Strato-server.
# Gebruik: ./scripts/deploy-api.sh

set -e

HOST="stu176966241@511575482.ssh.wl.strato.hosting"
REMOTE_API="prosperia/api"
LOCAL_API="/opt/ProsperiaV2/api"

echo "→ Deploy van $LOCAL_API naar $HOST:$REMOTE_API"

# Sync alle PHP-bestanden (behalve .htaccess, die staat al op de server)
rsync -avz --exclude='.htaccess' \
    "$LOCAL_API/" "$HOST:$REMOTE_API/"

echo "✓ Deploy klaar."
