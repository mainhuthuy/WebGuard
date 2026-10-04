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
    # 100 - 15 (crit) - 10 (high) - 5 (med) - 2 (low) = 68
    assert result["score"] == 68
    assert result["grade"] == "C"
    assert result["total_findings"] == 4

def test_scoring_floor_at_zero():
    """Điểm không bao giờ bị tụt xuống số âm kể cả khi dính quá nhiều lỗi nặng."""
    engine = ScoringEngine()
    findings = [{"severity": "critical"}] * 10  # Trừ 150 điểm
    result = engine.calculate(findings)
    assert result["score"] == 0
    assert result["grade"] == "F"
