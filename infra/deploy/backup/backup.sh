#!/bin/sh
# pg_dump backup loop for the meal-ordering DB.
#
# Environment variables (all optional — shown with defaults):
#   PGHOST                 db
#   PGUSER                 (required — no default)
#   PGPASSWORD             (required — no default)
#   PGDATABASE             meal_ordering
#   BACKUP_DIR             /backups        (override for local testing)
#   BACKUP_KEEP            7               (number of newest dumps to keep)
#   BACKUP_INTERVAL_SECONDS  86400         (seconds between runs; daily default)
#   BACKUP_ONCE            ""              (set to 1 to run once then exit)
#
# Usage (normal, in container):
#   entrypoint: ["sh", "/backup.sh"]
#
# Usage (one-shot local test):
#   PGHOST=localhost PGUSER=meal_user PGPASSWORD=... PGDATABASE=meal_ordering \
#   BACKUP_DIR=/tmp/test-backups BACKUP_KEEP=2 BACKUP_ONCE=1 sh backup.sh

set -e

PGHOST="${PGHOST:-db}"
PGDATABASE="${PGDATABASE:-meal_ordering}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_ONCE="${BACKUP_ONCE:-}"

log() {
    printf '[backup] %s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

do_backup() {
    mkdir -p "$BACKUP_DIR"
    STAMP="$(date -u '+%Y%m%d-%H%M%S')"
    OUTFILE="$BACKUP_DIR/mealorder-${STAMP}.sql.gz"

    log "Starting pg_dump → $OUTFILE (host=$PGHOST db=$PGDATABASE user=$PGUSER)"

    # pg_dump failure is fatal — do NOT swallow errors.
    # We cannot rely on the pipe exit code in POSIX sh (no pipefail), so we dump
    # to a raw temp file first, check the exit code explicitly, then gzip it.
    TMPFILE="${OUTFILE%.gz}.tmp"
    if ! pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" > "$TMPFILE"; then
        log "ERROR: pg_dump failed — removing partial file"
        rm -f "$TMPFILE" "$OUTFILE"
        exit 1
    fi
    gzip -c "$TMPFILE" > "$OUTFILE"
    rm -f "$TMPFILE"

    SIZE="$(du -sh "$OUTFILE" 2>/dev/null | cut -f1)"
    log "Dump complete: $OUTFILE ($SIZE)"

    # Prune: keep only newest BACKUP_KEEP files.
    # `ls -1t` sorts newest-first; tail skips the first BACKUP_KEEP lines;
    # the remainder are the oldest and get deleted.
    TO_DELETE="$(ls -1t "$BACKUP_DIR"/mealorder-*.sql.gz 2>/dev/null \
        | tail -n "+$((BACKUP_KEEP + 1))")"

    if [ -n "$TO_DELETE" ]; then
        COUNT="$(printf '%s\n' "$TO_DELETE" | wc -l | tr -d ' ')"
        log "Pruning $COUNT old dump(s) (keeping newest $BACKUP_KEEP):"
        printf '%s\n' "$TO_DELETE" | while IFS= read -r f; do
            log "  removing $f"
            rm -f "$f"
        done
    else
        log "Retention OK — no pruning needed (kept $BACKUP_KEEP or fewer)"
    fi

    REMAINING="$(ls -1 "$BACKUP_DIR"/mealorder-*.sql.gz 2>/dev/null | wc -l | tr -d ' ')"
    log "Backups on disk: $REMAINING"
}

log "Backup sidecar started (BACKUP_KEEP=$BACKUP_KEEP, BACKUP_INTERVAL_SECONDS=$BACKUP_INTERVAL_SECONDS, BACKUP_ONCE=${BACKUP_ONCE:-0})"

while true; do
    do_backup

    if [ "${BACKUP_ONCE}" = "1" ] || [ -n "$BACKUP_ONCE" ]; then
        log "BACKUP_ONCE set — exiting after single run"
        exit 0
    fi

    log "Sleeping ${BACKUP_INTERVAL_SECONDS}s until next backup…"
    sleep "$BACKUP_INTERVAL_SECONDS"
done
