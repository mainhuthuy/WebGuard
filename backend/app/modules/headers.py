import re

import httpx

from app.modules.base import HTTP_TIMEOUT, BaseModule


class HeadersModule(BaseModule):
    @property
    def name(self) -> str:
        return "headers"

    @property
    def description(self) -> str:
        return "Kiểm tra HTTP Security Headers"

    SECURITY_HEADERS = [
        {
            "name" : "Content-Security-Policy",
            "severity" : "high",
            "description" : "CSP giúp ngăn chặn tấn công XSS bằng cách chỉ cho phép load tài nguyên từ nguồn tin cậy",
            "remediation" : "Thêm header: Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self';"
        },
        {
            "name": "Strict-Transport-Security",
            "severity": "high",
            "description": "HSTS ép trình duyệt luôn dùng HTTPS, chống tấn công Man-in-the-Middle",
            "remediation": "Thêm header: Strict-Transport-Security: max-age=31536000; includeSubDomains"
        },
        {
            "name" : "X-Frame-Options",
            "severity" : "medium",
            "description" : "XFO ngăn chặn tấn công Clickjacking bằng cách hạn chế frame",
            "remediation" : "Thêm header: X-Frame-Options: DENY"
        },
        {
            "name" : "X-Content-Type-Options",
            "severity" : "medium",
            "description" : "Ngăn chặn trình duyệt đoán sai Content-Type",
            "remediation" : "Thêm header: X-Content-Type-Options: nosniff"
        },
        {
            "name" : "X-XSS-Protection",
            "severity" : "low",
            "description" : "Bảo vệ XSS lỗi thời, CSP tốt hơn",
            "remediation" : "X-XSS-Protection: 1; mode=block (cần khi không có CSP)"
        },
        {
            "name" : "Referrer-Policy",
            "severity" : "low",
            "description" : "Kiểm soát thông tin referrer",
            "remediation" : "Thêm header: Referrer-Policy: strict-origin-when-cross-origin"
        },
        {
            "name" : "Permissions-Policy",
            "severity" : "medium",
            "description" : "Kiểm soát tính năng trình duyệt (camera, microphone...)",
            "remediation" : "Thêm header: Permissions-Policy: geolocation=(); microphone=(); camera=()"
        },
        {
            "name": "Cross-Origin-Opener-Policy",
            "severity": "medium",
            "description": "Ngăn chặn tấn công Spectre và các lỗ hổng liên quan đến cùng nguồn gốc",
            "remediation": "Thêm header: Cross-Origin-Opener-Policy: same-origin"
        },
        {
            "name": "Cross-Origin-Embedder-Policy",
            "severity": "medium",
            "description": "Ngăn chặn tải tài nguyên từ nguồn gốc khác vào cùng một ngữ cảnh",
            "remediation": "Thêm header: Cross-Origin-Embedder-Policy: require-corp"
        },
        {
            "name": "Cross-Origin-Resource-Policy",
            "severity": "low",
            "description": "Ngăn website khác nhúng tài nguyên của bạn (chống rò rỉ dữ liệu qua side-channel)",
            "remediation": "Thêm header: Cross-Origin-Resource-Policy: same-origin"
        }
    ]

    # Header CÓ mặt nhưng giá trị yếu/sai — mỗi mục là một kiểm tra riêng (key = `name`)
    HEADER_WEAKNESSES = [
        {
            "name": "csp_unsafe_inline",
            "severity": "medium",
            "description": "CSP cho phép 'unsafe-inline' trong script-src/default-src nên script chèn vào (XSS) vẫn chạy được",
            "remediation": "Bỏ 'unsafe-inline'; dùng nonce hoặc hash cho script nội tuyến"
        },
        {
            "name": "csp_unsafe_eval",
            "severity": "medium",
            "description": "CSP cho phép 'unsafe-eval' nên eval()/new Function() vẫn được dùng để thực thi mã tùy ý",
            "remediation": "Bỏ 'unsafe-eval' và loại bỏ eval() khỏi mã nguồn"
        },
        {
            "name": "csp_wildcard_source",
            "severity": "medium",
            "description": "CSP cho phép nguồn script quá rộng (*, https:, http: hoặc data:) nên kẻ tấn công dễ nạp mã từ máy chủ của họ",
            "remediation": "Chỉ liệt kê đích danh các domain script tin cậy, không dùng ký tự đại diện"
        },
        {
            "name": "hsts_short_max_age",
            "severity": "medium",
            "description": "HSTS có max-age dưới 6 tháng nên trình duyệt chỉ được bảo vệ trong thời gian ngắn",
            "remediation": "Đặt max-age tối thiểu 31536000 (1 năm)"
        },
        {
            "name": "hsts_missing_include_subdomains",
            "severity": "low",
            "description": "HSTS không có includeSubDomains nên các subdomain vẫn có thể bị hạ cấp xuống HTTP",
            "remediation": "Thêm includeSubDomains vào Strict-Transport-Security"
        },
        {
            "name": "x_frame_options_invalid",
            "severity": "medium",
            "description": "X-Frame-Options có giá trị không hợp lệ hoặc đã lỗi thời (vd: ALLOW-FROM) nên trình duyệt bỏ qua",
            "remediation": "Dùng X-Frame-Options: DENY hoặc SAMEORIGIN (hoặc CSP frame-ancestors)"
        },
        {
            "name": "x_content_type_options_invalid",
            "severity": "medium",
            "description": "X-Content-Type-Options có giá trị khác 'nosniff' nên không có tác dụng",
            "remediation": "Đặt X-Content-Type-Options: nosniff"
        },
        {
            "name": "referrer_policy_unsafe",
            "severity": "low",
            "description": "Referrer-Policy luôn gửi URL đầy đủ sang website khác (unsafe-url / no-referrer-when-downgrade)",
            "remediation": "Dùng Referrer-Policy: strict-origin-when-cross-origin hoặc nghiêm ngặt hơn"
        }
    ]

    HSTS_MIN_MAX_AGE = 15_552_000  # 180 ngày
    UNSAFE_REFERRER_VALUES = {"unsafe-url", "no-referrer-when-downgrade"}
    VALID_XFO_VALUES = {"deny", "sameorigin"}
    WILDCARD_SOURCES = {"*", "https:", "http:", "data:"}

    @staticmethod
    def _parse_csp(value: str) -> dict[str, list[str]]:
        """Tách CSP thành {directive: [nguồn...]} (chỉ lấy directive xuất hiện đầu tiên)."""
        directives: dict[str, list[str]] = {}
        for part in value.split(";"):
            tokens = part.split()
            if tokens and tokens[0].lower() not in directives:
                directives[tokens[0].lower()] = [t.lower() for t in tokens[1:]]
        return directives

    def _weak_values(self, headers: httpx.Headers) -> set[str]:
        """Trả về tập khóa HEADER_WEAKNESSES mà các header hiện có đang vi phạm."""
        weak: set[str] = set()

        csp = headers.get("content-security-policy")
        if csp:
            directives = self._parse_csp(csp)
            script_src = directives.get("script-src", directives.get("default-src"))
            if script_src is not None:
                # nonce/hash/'strict-dynamic' khiến trình duyệt bỏ qua 'unsafe-inline'
                protected = any(
                    s.startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-"))
                    or s == "'strict-dynamic'"
                    for s in script_src
                )
                if "'unsafe-inline'" in script_src and not protected:
                    weak.add("csp_unsafe_inline")
                if "'unsafe-eval'" in script_src:
                    weak.add("csp_unsafe_eval")
                if self.WILDCARD_SOURCES & set(script_src):
                    weak.add("csp_wildcard_source")

        hsts = headers.get("strict-transport-security")
        if hsts:
            match = re.search(r"max-age\s*=\s*\"?(\d+)", hsts, re.IGNORECASE)
            if not match or int(match.group(1)) < self.HSTS_MIN_MAX_AGE:
                weak.add("hsts_short_max_age")
            if "includesubdomains" not in hsts.lower():
                weak.add("hsts_missing_include_subdomains")

        xfo = headers.get("x-frame-options")
        if xfo and xfo.strip().lower() not in self.VALID_XFO_VALUES:
            weak.add("x_frame_options_invalid")

        xcto = headers.get("x-content-type-options")
        if xcto and xcto.strip().lower() != "nosniff":
            weak.add("x_content_type_options_invalid")

        referrer = headers.get("referrer-policy")
        if referrer:
            # Giá trị cuối cùng hợp lệ mà trình duyệt hiểu sẽ được áp dụng
            last = referrer.split(",")[-1].strip().lower()
            if last in self.UNSAFE_REFERRER_VALUES:
                weak.add("referrer_policy_unsafe")
        return weak

    async def scan(self, url: str, **kwargs) -> list:
        findings = []
        # Bước 1: Gửi request
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url)
        # Bước 2: Lấy headers từ response
        headers = response.headers
        # Bước 3: Duyệt qua từng header cần check
        for header in self.SECURITY_HEADERS:
            header_name = header["name"].lower()
            if header_name not in headers:
                findings.append({
                    "module": self.name,
                    "name" : header_name,
                    "severity" : header["severity"],
                    "description" : header["description"],
                    "remediation" : header["remediation"],
                    "url": url
                })
        # Bước 4: Header có mặt nhưng giá trị yếu
        weak = self._weak_values(headers)
        for item in self.HEADER_WEAKNESSES:
            if item["name"] in weak:
                findings.append({
                    "module": self.name,
                    "name": item["name"],
                    "severity": item["severity"],
                    "description": item["description"],
                    "remediation": item["remediation"],
                    "url": url
                })
        # Bước 5: Trả về kết quả
        return findings
