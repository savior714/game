from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN_HTML = ROOT / "domains/reward/guardian/index.html"


def test_guardian_loads_supabase_auth_and_sync_in_dependency_order() -> None:
    html = GUARDIAN_HTML.read_text(encoding="utf-8")
    scripts = re.findall(r'<script\s+src="([^"]+)"', html)

    supabase = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"
    auth = "../../../domains/auth/auth.js"
    sync = "../../../domains/sync/sync-engine.js"
    guardian = "guardian.js"

    assert scripts.count(supabase) == 1
    assert scripts.count(auth) == 1
    assert scripts.count(sync) == 1
    assert scripts.index(supabase) < scripts.index(auth) < scripts.index(sync)
    assert scripts.index(sync) < scripts.index(guardian)
    assert "../../../domains/reward/auth.js" not in scripts
    assert "../../../domains/reward/sync-engine.js" not in scripts
