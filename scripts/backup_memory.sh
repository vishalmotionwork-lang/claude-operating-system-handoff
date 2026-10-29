#!/bin/bash
# Daily backup of Qdrant memory and Redis state
# Run via cron: 0 3 * * * bash ~/.claude/scripts/backup_memory.sh
#
# Self-healing: verifies backup integrity BEFORE rotating old ones.
# Keeps 7 daily snapshots, auto-rotates old ones.

# Cron doesn't load shell profile — ensure Homebrew tools are available
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$HOME/.local/bin:$PATH"

BACKUP_DIR="$HOME/.claude/backups"
QDRANT_DIR="$HOME/.qdrant-memory"
TIMESTAMP=$(date +%Y-%m-%d)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
MAX_BACKUPS=7
LOG="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

echo "" >> "$LOG"
echo "[backup] ═══ $TIMESTAMP ═══" >> "$LOG"

BACKUP_OK=true

# 1. Backup Qdrant data (skip .lock file)
if [ -d "$QDRANT_DIR" ]; then
    mkdir -p "$BACKUP_PATH/qdrant"
    rsync -a --exclude='.lock' "$QDRANT_DIR/" "$BACKUP_PATH/qdrant/"
    # Verify: check that collection dir was copied
    if [ -d "$BACKUP_PATH/qdrant/collection" ]; then
        QDRANT_SIZE=$(du -sh "$BACKUP_PATH/qdrant" 2>/dev/null | cut -f1)
        echo "[backup] Qdrant → $BACKUP_PATH/qdrant/ ($QDRANT_SIZE)" >> "$LOG"
    else
        echo "[backup] WARNING: Qdrant backup may be incomplete (no collection dir)" >> "$LOG"
        BACKUP_OK=false
    fi
else
    echo "[backup] SKIP: Qdrant dir not found" >> "$LOG"
fi

# 2. Backup Redis hot memory state
if command -v redis-cli &>/dev/null && redis-cli ping &>/dev/null; then
    mkdir -p "$BACKUP_PATH/redis"
    redis-cli --no-auth-warning keys "claude:*" > "$BACKUP_PATH/redis-keys.txt"
    KEY_COUNT=$(wc -l < "$BACKUP_PATH/redis-keys.txt" | tr -d ' ')
    while IFS= read -r key; do
        [ -z "$key" ] && continue
        safe_name=$(echo "$key" | tr ':/' '__')
        redis-cli --no-auth-warning get "$key" > "$BACKUP_PATH/redis/$safe_name.txt" 2>/dev/null
    done < "$BACKUP_PATH/redis-keys.txt"
    # Verify: check that we backed up all keys
    BACKED_UP=$(ls "$BACKUP_PATH/redis/"*.txt 2>/dev/null | wc -l | tr -d ' ')
    echo "[backup] Redis → $BACKUP_PATH/redis/ ($BACKED_UP/$KEY_COUNT keys)" >> "$LOG"
    if [ "$BACKED_UP" -lt "$KEY_COUNT" ]; then
        echo "[backup] WARNING: Redis backup incomplete ($BACKED_UP of $KEY_COUNT)" >> "$LOG"
        BACKUP_OK=false
    fi
else
    echo "[backup] SKIP: Redis not available" >> "$LOG"
fi

# 3. Backup context files
if [ -d "$HOME/.claude/context" ]; then
    mkdir -p "$BACKUP_PATH/context"
    cp "$HOME/.claude/context/"*.md "$BACKUP_PATH/context/" 2>/dev/null
    CTX_COUNT=$(ls "$BACKUP_PATH/context/"*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "[backup] Context → $BACKUP_PATH/context/ ($CTX_COUNT files)" >> "$LOG"
fi

# 4. Backup memory files (cold tier)
if [ -d "$HOME/.claude/projects/-Users-YOUR-USER/memory" ]; then
    mkdir -p "$BACKUP_PATH/memory"
    rsync -a "$HOME/.claude/projects/-Users-YOUR-USER/memory/" "$BACKUP_PATH/memory/"
    MEM_COUNT=$(find "$BACKUP_PATH/memory" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    echo "[backup] Memory → $BACKUP_PATH/memory/ ($MEM_COUNT files)" >> "$LOG"
fi

# 5. VERIFY before rotating — only delete old backups if today's succeeded
TOTAL_SIZE=$(du -sh "$BACKUP_PATH" 2>/dev/null | cut -f1)

if [ "$BACKUP_OK" = true ]; then
    echo "[backup] Verification: PASSED ($TOTAL_SIZE)" >> "$LOG"

    # Rotate old backups (keep MAX_BACKUPS)
    BACKUP_COUNT=$(ls -d "$BACKUP_DIR"/????-??-?? 2>/dev/null | wc -l | tr -d ' ')
    if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
        EXCESS=$((BACKUP_COUNT - MAX_BACKUPS))
        ls -d "$BACKUP_DIR"/????-??-?? | head -n "$EXCESS" | while read -r old; do
            rm -rf "$old"
            echo "[rotate] Removed $old" >> "$LOG"
        done
    fi
else
    echo "[backup] Verification: FAILED — skipping rotation to preserve older backups" >> "$LOG"
fi

echo "[backup] Done — $TOTAL_SIZE at $BACKUP_PATH" >> "$LOG"

# 6. Rotate backup log (keep last 200 lines)
if [ -f "$LOG" ]; then
    LINE_COUNT=$(wc -l < "$LOG" | tr -d ' ')
    if [ "$LINE_COUNT" -gt 200 ]; then
        tail -100 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi
fi
