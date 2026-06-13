"""Emit bash `export` lines for verify DB isolation from DATABASE_URL (SSOT).

Reads ``DATABASE_URL`` (``postgresql+asyncpg://...``). If unset, uses the same
docker-first default as ``.env.example`` / ``settings._default_database_url``.

Usage::

    eval "$(python3 scripts/verify/resolve_verify_database_env.py <isolation_db_name>)"
"""

from __future__ import annotations

import os
import shlex
import sys
from urllib.parse import quote, unquote, urlparse

# SSOT with ``.env.example`` and docker-compose.dev.yml published Postgres.
_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/emr"


def parse_asyncpg_database_url(url: str) -> tuple[str, int, str, str | None, str]:
    s = (url or "").strip()
    if not s.startswith("postgresql+asyncpg://"):
        msg = "DATABASE_URL must start with postgresql+asyncpg://"
        raise ValueError(msg)
    rest = s.removeprefix("postgresql+asyncpg://")
    parsed = urlparse("postgresql://" + rest)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    user = unquote(parsed.username) if parsed.username else "postgres"
    password = unquote(parsed.password) if parsed.password else None
    path = (parsed.path or "/").lstrip("/")
    source_db = path or "postgres"
    return host, port, user, password, source_db


def build_asyncpg_url(
    *,
    host: str,
    port: int,
    user: str,
    password: str | None,
    database: str,
) -> str:
    u = quote(user, safe="")
    if password:
        p = quote(password, safe="")
        auth = f"{u}:{p}"
    else:
        auth = u
    return f"postgresql+asyncpg://{auth}@{host}:{port}/{database}"


def emit_shell_exports(*, isolation_db: str, base_url: str | None) -> str:
    raw = (base_url or "").strip() or _DEFAULT_DATABASE_URL
    host, port, user, password, _src = parse_asyncpg_database_url(raw)
    isolation_url = build_asyncpg_url(
        host=host,
        port=port,
        user=user,
        password=password,
        database=isolation_db,
    )
    pwd = password if password is not None else ""
    lines = [
        f"export VERIFY_PG_HOST={shlex.quote(host)}",
        f"export VERIFY_PG_PORT={shlex.quote(str(port))}",
        f"export VERIFY_PG_USER={shlex.quote(user)}",
        f"export VERIFY_PG_PASSWORD={shlex.quote(pwd)}",
        f"export DATABASE_URL={shlex.quote(isolation_url)}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    isolation = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("VERIFY_PG_DATABASE", "")
    ).strip()
    if not isolation:
        sys.stderr.write(
            "resolve_verify_database_env.py: missing isolation DB name "
            "(argv or VERIFY_PG_DATABASE).\n",
        )
        return 2
    base = os.environ.get("DATABASE_URL")
    try:
        sys.stdout.write(emit_shell_exports(isolation_db=isolation, base_url=base))
    except ValueError as e:
        sys.stderr.write(f"resolve_verify_database_env.py: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
