from pathlib import Path

from scripts import agent_checks as ac


def make_file(path: Path, lines: int, body: str = "# empty\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8") as f:
        for _ in range(lines):
            f.write(body)


def test_long_file_detection(tmp_path: Path) -> None:
    src = tmp_path / "src"
    p = src / "mod.py"
    make_file(p, lines=500, body="x = 1\n")
    long = ac.find_long_files([p], threshold=400)
    assert long and long[0][0].name == "mod.py"


def test_ignore_detection(tmp_path: Path) -> None:
    src = tmp_path / "src"
    p = src / "m.py"
    make_file(p, 2, body="# type: ignore\n")
    ignored = ac.find_ignored_types([p])
    assert ignored and ignored[0][1] >= 1


def test_uncovered_detects_missing_tests(tmp_path: Path) -> None:
    src = tmp_path / "src"
    tests = tmp_path / "tests"
    m1 = src / "alpha.py"
    m2 = src / "beta.py"
    make_file(m1, 2, body="x=1\n")
    make_file(m2, 2, body="x=2\n")
    t = tests / "test_alpha.py"
    make_file(t, 2, body="import alpha\n")
    uncovered = ac.find_uncovered_modules([m1, m2], [t])
    assert any(p.name == "beta.py" for p in uncovered)
