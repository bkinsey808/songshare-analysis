from songshare_analysis.genre import panns


def test__import_panns_returns_a_class():
    cls = panns._import_panns()
    assert callable(cls)
    assert getattr(cls, "__name__", "").lower() in {"soundtagging", "audiotagging"}
