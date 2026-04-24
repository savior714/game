# dev.nu - Developer UX Layer

export def main [] {
    help dev
}

# Sync, Check, and Start Dev
export def dev [] {
    print "🚀 Starting Dev Workflow..."
    uv sync
    just ci
}

# Run specific test
export def t [name: string] {
    pytest -k $name
}

# Quick Verify
export def v [] {
    ./verify.sh
}
