from agent.collectors.jvm_collector import _parse_jstat


def test_parse_jstat_gc_metrics():
    values = _parse_jstat("S0C S1C EC EU OC OU YGC YGCT FGC FGCT GCT\n0 1024 4096 2048 8192 4096 4 0.2 1 0.1 0.3")

    assert values["EU"] == 2048
    assert values["FGC"] == 1


def test_parse_jstat_handles_missing_output():
    assert _parse_jstat("") == {}
