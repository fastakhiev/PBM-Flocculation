#!/bin/bash
set -e  # Stop execution on error

# Connect to the “postgres” system database and create a database if it does not exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO "$POSTGRES_USER";
EOSQL

echo "База данных $POSTGRES_DB проверена/создана!"
