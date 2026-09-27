#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="aiden-test-pg"
DB_USER="test"
DB_NAME="aiden_test"
PORT="54329"

echo "=== AidenGame Disposable Test PostgreSQL Setup ==="

# Check docker availability
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker is not installed or not in PATH."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker daemon is not running."
  exit 1
fi

# Check if container is running
if [ "$(docker ps -q -f name=^/${CONTAINER_NAME}$)" ]; then
  echo "✓ Container ${CONTAINER_NAME} is already running."
elif [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
  echo "Starting existing container ${CONTAINER_NAME}..."
  docker start "${CONTAINER_NAME}" >/dev/null
else
  echo "Starting new container ${CONTAINER_NAME} on port ${PORT}..."
  docker run -d \
    --name "${CONTAINER_NAME}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_USER}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -p "${PORT}:5432" \
    postgres:17-alpine >/dev/null
fi

# Wait for PostgreSQL to become ready
echo "Waiting for PostgreSQL to accept connections..."
for i in {1..30}; do
  if docker exec -i "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# Initialize Supabase compatibility environment
echo "Configuring Supabase compatibility schema & roles..."
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -q << 'EOF'
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid;
$$;
DO $$ BEGIN CREATE ROLE anon NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE authenticated NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE service_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT ALL ON SCHEMA public TO anon, authenticated, service_role, test;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role, test;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated, service_role, test;
EOF

# Apply repository migrations in canonical order
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Applying migrations..."
for migration in \
  "${REPO_ROOT}/supabase/migrations/001_create_user_data.sql" \
  "${REPO_ROOT}/supabase/migrations/002_create_merge_game_stats_function.sql" \
  "${REPO_ROOT}/supabase/migrations/003_create_weekly_english_ingestion.sql" \
  "${REPO_ROOT}/supabase/migrations/004_weekly_ingestion_closure.sql" \
  "${REPO_ROOT}/supabase/migrations/005_weekly_ingestion_authority_and_confirmation_closure.sql"
do
  echo "  Applying $(basename "${migration}")..."
  docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -q < "${migration}"
done

echo "Applying RLS policies..."
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -q < "${REPO_ROOT}/supabase/policies/user_data_rls.sql"
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -q < "${REPO_ROOT}/supabase/policies/weekly_english_ingestion_rls.sql"

echo "✓ Supabase test PostgreSQL environment ready."
