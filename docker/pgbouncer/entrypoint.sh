#!/bin/sh
# Generates /etc/pgbouncer/userlist.txt from env vars at runtime.
# Called by the pgbouncer container entrypoint before starting pgbouncer.
set -e

USERLIST=/etc/pgbouncer/userlist.txt

echo "Generating PgBouncer userlist..."
cat > "$USERLIST" <<EOF
"${PGBOUNCER_DB_USER}" "${PGBOUNCER_DB_PASSWORD}"
EOF

echo "Starting PgBouncer..."
exec pgbouncer /etc/pgbouncer/pgbouncer.ini
