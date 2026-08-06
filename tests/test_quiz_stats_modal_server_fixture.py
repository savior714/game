from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = (
    "test_quiz_stats_modal_focus.py",
    "test_quiz_stats_modal_focus_containment.py",
    "test_quiz_stats_modal_escape.py",
)


def test_stats_modal_server_fixtures_use_ephemeral_ports_and_close_sockets() -> None:
    for name in TARGETS:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "PORT =" not in text, f"{name} still hard-codes a server port"
        assert 'TCPServer(("127.0.0.1", 0), QuietHandler)' in text
        assert "self.server.server_address[1]" in text
        assert "self.server.server_close()" in text
