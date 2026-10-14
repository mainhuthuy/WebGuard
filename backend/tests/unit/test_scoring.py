from app.modules.scoring import ScoringEngine


def test_scoring_perfect():
    """Trang web không có lỗi nào phải đạt điểm 100 và Grade A+."""
    engine = ScoringEngine()
    result = engine.calculate([])
    assert result["score"] == 100
    assert result["grade"] == "A+"
    assert result["total_findings"] == 0

def test_scoring_with_sample_findings(sample_findings):
    """Kiểm tra trừ điểm chính xác theo từng severity từ fixture."""
    engine = ScoringEngine()
    result = engine.calculate(sample_findings)
    # 100 - 10 (crit) - 6 (high) - 3 (med) - 1 (low) = 80
    assert result["score"] == 80
    assert result["grade"] == "B"
    assert result["total_findings"] == 4

def test_scoring_floor_at_zero():
    """Điểm không bao giờ bị tụt xuống số âm kể cả khi dính quá nhiều lỗi nặng."""
    engine = ScoringEngine()
    findings = [{"severity": "critical", "description": str(i)} for i in range(15)]  # Trừ 150 điểm
    result = engine.calculate(findings)
    assert result["score"] == 0
    assert result["grade"] == "F"


def test_repeated_issue_counts_in_full_once_then_at_half():
    """8 cookie cùng lỗi SameSite = 1 quyết định cấu hình: 3 + 7 × 1.5 = 13.5 điểm, không phải 24."""
    cookie = {"module": "cookies", "severity": "medium", "description": "SameSite=None"}
    findings = [{**cookie, "name": f"cookie_{i}"} for i in range(8)]
    result = ScoringEngine().calculate(findings)
    assert result["score"] == 86  # round(100 - 13.5)
    assert result["total_findings"] == 8


def test_same_description_in_different_severity_or_module_is_not_a_repeat():
    findings = [
        {"module": "headers", "severity": "medium", "description": "x"},
        {"module": "cookies", "severity": "medium", "description": "x"},
        {"module": "headers", "severity": "low", "description": "x"},
    ]
    assert ScoringEngine().calculate(findings)["score"] == 100 - 3 - 3 - 1


def test_example_com_style_site_with_no_security_headers_lands_in_c():
    """Hồi quy: trang trống kiểu example.com (3 high, 5 medium, 3 low) từng bị F (39), giờ là C."""
    findings = [
        [{"module": "headers", "severity": sev, "description": f"{sev}-{i}"} for i in range(n)]
        for sev, n in (("high", 3), ("medium", 5), ("low", 3))
    ]
    result = ScoringEngine().calculate([f for group in findings for f in group])
    assert result["score"] == 100 - 18 - 15 - 3
    assert result["grade"] == "C"
