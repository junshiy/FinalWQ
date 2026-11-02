"""诊断引擎单元测试（pytest）。"""
from faultdiag.services import MIN_CONFIDENCE, diagnose


def test_disk_full_is_matched():
    """磁盘满的典型报错应命中 disk_full，且置信度过阈值。"""
    result = diagnose("cp: cannot create regular file '/var/log/a.log': No space left on device")
    assert result["matches"], "应至少命中一条规则"
    assert result["matches"][0]["rule_id"] == "disk_full"
    assert result["matches"][0]["confidence"] >= MIN_CONFIDENCE
    assert result["need_human"] is False


def test_port_conflict_is_matched():
    """端口占用应命中 port_in_use。"""
    result = diagnose("nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)")
    assert result["matches"][0]["rule_id"] == "port_in_use"


def test_hostname_hosts_mismatch():
    """sudo unable to resolve host 应命中 hostname 同步问题。"""
    result = diagnose("sudo: unable to resolve host wangqi: Name or service not known")
    assert result["matches"][0]["rule_id"] in {"sudo_unable_resolve_host", "dns_resolve"}


def test_empty_input_needs_human():
    """空输入不产生结论，直接提示补全信息。"""
    result = diagnose("   ")
    assert result["matches"] == []
    assert result["need_human"] is True


def test_unknown_error_needs_human():
    """知识库未覆盖的文本应转人工，不得硬凑结论。"""
    result = diagnose("hello world, this is a totally unrelated sentence")
    assert result["matches"] == []
    assert result["need_human"] is True


def test_matches_sorted_by_confidence():
    """多个候选结论必须按置信度降序，便于学生先看最可能的一条。"""
    result = diagnose("curl: (7) Failed to connect to 127.0.0.1 port 8000: Connection refused")
    confidence = [item["confidence"] for item in result["matches"]]
    assert confidence == sorted(confidence, reverse=True)


def test_top_k_limit():
    """top_k 限制返回条数，默认 3 条。"""
    text = "No space left on device; Address already in use; connection refused"
    result = diagnose(text, top_k=2)
    assert len(result["matches"]) <= 2


def test_result_always_has_source_and_verify():
    """每条结论必须带引用来源与验证命令（防幻觉的硬约束）。"""
    result = diagnose("502 Bad Gateway")
    for item in result["matches"]:
        assert item["source"]
        assert item["verify"]
