#!/usr/bin/env sh
set -eu
# Executar no servidor. Manter backup e seus hashes FORA do repositório.
: "${BACKUP_DIR:?Informe BACKUP_DIR absoluto e protegido}"
mkdir -p "$BACKUP_DIR"
file="$BACKUP_DIR/transporte-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db pg_dump -U transporte -Fc transporte > "$file"
sha256sum "$file" > "$file.sha256"
printf '%s\n' 'Backup criado; realizar restauração de teste periodicamente.'
