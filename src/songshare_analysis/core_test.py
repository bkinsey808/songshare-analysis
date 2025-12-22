from songshare_analysis.core import dataframe_summary, sample_dataframe


def test_sample_dataframe() -> None:
    df = sample_dataframe()
    assert "song" in df.columns
    assert "plays" in df.columns
    assert df.plays.sum() == 30


def test_dataframe_summary() -> None:
    df = sample_dataframe()
    s = dataframe_summary(df)
    assert s["rows"] == 2
    assert s["total_plays"] == 30
