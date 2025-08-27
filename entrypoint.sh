#!/bin/bash
set -e  # Остановить выполнение при ошибке

# Подключаемся к системной базе данных "postgres" и создаем БД, если её нет
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO "$POSTGRES_USER";
EOSQL

echo "База данных $POSTGRES_DB проверена/создана!"
