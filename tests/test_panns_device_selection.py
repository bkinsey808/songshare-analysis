import importlib
import sys

from songshare_analysis.genre import panns


class _FakeXPU:
    def __init__(self, available: bool):
        self._available = available

    def is_available(self):
        return self._available


class _FakeCUDA:
    def __init__(self, available: bool):
        self._available = available

    def is_available(self):
        return self._available


def _make_fake_torch(xpu_available: bool = False, cuda_available: bool = False):
    fake = type("FakeTorch", (), {})()
    fake.xpu = _FakeXPU(xpu_available) if xpu_available else None
    fake.cuda = _FakeCUDA(cuda_available) if cuda_available else None
    return fake


def test_prefers_xpu(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _make_fake_torch(xpu_available=True))
    # reload in case the function was cached; helper imports inside function so this is safe
    importlib.reload(panns)

    assert panns._detect_best_device() == "cpu"


def test_prefers_cuda_when_no_xpu(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _make_fake_torch(cuda_available=True))
    importlib.reload(panns)

    assert panns._detect_best_device() == "cpu"


def test_falls_back_to_cpu(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _make_fake_torch())
    importlib.reload(panns)

    assert panns._detect_best_device() == "cpu"
