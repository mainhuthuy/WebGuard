class ScoringEngine:
    # Điểm trừ cho mỗi severity (chấm điểm "nới tay": mục tiêu là học tập, không phải audit
    # khắt khe — một trang chỉ thiếu vài header vẫn nên đạt hạng B/C chứ không phải F).
    SEVERITY_SCORES = {
        "critical": 10,
        "high": 6,
        "medium": 3,
        "low": 1
    }
    # Cùng một vấn đề lặp lại (vd 8 cookie cùng thiếu SameSite) là MỘT quyết định cấu hình,
    # không phải 8 lỗi độc lập: lần đầu trừ đủ, các lần lặp sau chỉ trừ theo hệ số này.
    REPEAT_FACTOR = 0.5
    # Thang điểm grade
    GRADE_THRESHOLDS = [
        (95, "A+"),
        (85, "A"),
        (70, "B"),
        (50, "C"),
        (0, "F")
    ]
    def calculate(self, findings: list) -> dict:
        penalty = 0.0
        seen: set[tuple[str, str, str]] = set()
        for finding in findings:
            base = self.SEVERITY_SCORES.get(finding["severity"], 0)
            # Cùng module + severity + mô tả = cùng một loại vấn đề (tên khác nhau, vd tên cookie).
            key = (finding.get("module", ""), finding["severity"], finding.get("description", ""))
            penalty += base * (self.REPEAT_FACTOR if key in seen else 1)
            seen.add(key)
        total_score = max(0, round(100 - penalty))
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
