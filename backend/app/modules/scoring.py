class ScoringEngine:
    # Điểm trừ cho mỗi severity
    SEVERITY_SCORES = {
        "critical": 15,
        "high": 10,
        "medium": 5,
        "low": 2
    }
    # Thang điểm grade
    GRADE_THRESHOLDS = [
        (95, "A+"),
        (85, "A"),
        (70, "B"),
        (50, "C"),
        (0, "F")
    ]
    def calculate(self, findings: list) -> dict:
        total_score = 100
        for finding in findings:
            total_score -= self.SEVERITY_SCORES.get(finding["severity"], 0)
        total_score = max(0, total_score)
        grade = "A+"
        for threshold, grade_letter in self.GRADE_THRESHOLDS:
            if total_score >= threshold:
                grade = grade_letter
                break
        return {
            "score": total_score,
            "grade": grade,
            "total_findings": len(findings)
        }
