"""Tests for launchd install helpers (orphan menubar, not STT)."""
from service import is_orphan_menubar_cmdline, kill_orphan_menubar


def test_orphan_menubar_matches_main_py():
    assert is_orphan_menubar_cmdline(
        ["/usr/bin/python", "src/vtt2/main.py"]
    )


def test_orphan_menubar_skips_stt_server():
    assert not is_orphan_menubar_cmdline(
        ["/usr/bin/python", "src/vtt2/main.py", "--serve-stt"]
    )


def test_orphan_menubar_skips_install_and_status():
    assert not is_orphan_menubar_cmdline(
        ["/usr/bin/python", "src/vtt2/main.py", "--install"]
    )
    assert not is_orphan_menubar_cmdline(
        ["/usr/bin/python", "src/vtt2/main.py", "--status"]
    )
    assert not is_orphan_menubar_cmdline(
        ["/usr/bin/python", "src/vtt2/main.py", "--health"]
    )


def test_orphan_menubar_skips_empty_and_unrelated():
    assert not is_orphan_menubar_cmdline(None)
    assert not is_orphan_menubar_cmdline([])
    assert not is_orphan_menubar_cmdline(["/usr/bin/python", "other.py"])


def test_kill_orphan_menubar_skips_current_and_stt(monkeypatch):
    class FakeProc:
        def __init__(self, pid, cmdline):
            self.info = {"pid": pid, "cmdline": cmdline}
            self.terminated = False

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=3):
            return None

        def kill(self):
            pass

    stt = FakeProc(11, ["python", "src/vtt2/main.py", "--serve-stt"])
    ui = FakeProc(22, ["python", "src/vtt2/main.py"])
    self_ui = FakeProc(99, ["python", "src/vtt2/main.py"])

    monkeypatch.setattr(
        "service.psutil.process_iter",
        lambda attrs: [stt, ui, self_ui],
    )
    killed = kill_orphan_menubar(current_pid=99)
    assert killed == [22]
    assert ui.terminated
    assert not stt.terminated
    assert not self_ui.terminated
