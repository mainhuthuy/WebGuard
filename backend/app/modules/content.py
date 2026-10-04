import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.modules.base import HTTP_TIMEOUT, BaseModule

MAX_HTML_CHARS = 1_000_000
CSRF_FIELD = re.compile(r"csrf|xsrf|token|nonce|authenticity", re.IGNORECASE)
GENERATOR_VERSION = re.compile(r"\d+\.\d+")

# --- Dò username enumeration qua form đăng nhập (chủ động, rủi ro thấp) ---
# Chỉ 2 lượt POST với mật khẩu SAI cố định — không phải brute-force, không thể đăng nhập thành công.
USERNAME_FIELD_TYPES = ("text", "email")
PROBE_NONEXISTENT_USERNAME = "webguard-probe-9f1c2b"
PROBE_COMMON_USERNAME = "admin"
PROBE_PASSWORD = "WebGuard-Probe-Pw1!"  # noqa: S105 — not a credential, a known-wrong probe value
ENUMERATION_PHRASES = (
    "no account", "doesn't exist", "does not exist", "not found",
    "unknown user", "no such user", "user does not exist", "invalid username",
)

# Thư viện JS có lỗ hổng đã biết: (nhãn, regex bắt phiên bản trong URL script, phiên bản an toàn tối thiểu)
# min_safe=None nghĩa là mọi phiên bản bắt được đều đã hết hỗ trợ (vd: AngularJS 1.x)
VULNERABLE_LIBRARIES = [
    ("jQuery", re.compile(r"jquery[-.@/]v?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE), (3, 5, 0), "XSS (CVE-2020-11022/11023)"),
    ("Bootstrap", re.compile(r"bootstrap[-.@/]v?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE), (4, 3, 1), "XSS trong tooltip/popover (CVE-2019-8331)"),
    ("AngularJS", re.compile(r"angular(?:js)?(?:\.js)?[-.@/]v?(1\.\d+(?:\.\d+)?)", re.IGNORECASE), None, "đã hết hỗ trợ, tồn tại nhiều lỗ hổng XSS/sandbox"),
    ("Lodash", re.compile(r"lodash[-.@/]v?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE), (4, 17, 21), "prototype pollution / command injection (CVE-2021-23337)"),
    ("Moment.js", re.compile(r"moment[-.@/]v?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE), (2, 29, 4), "ReDoS (CVE-2022-31129)"),
]


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in text.split("."))


class _PageParser(HTMLParser):
    """Gom các thẻ liên quan bảo mật từ HTML (không chạy JS, chỉ phân tích tĩnh)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[dict[str, str]] = []       # <script src>
        self.styles: list[dict[str, str]] = []        # <link rel=stylesheet>
        self.active_resources: list[str] = []         # iframe/object/embed src
        self.passive_resources: list[str] = []        # img/audio/video/source src
        self.forms: list[dict] = []
        self.generator: str | None = None
        self._form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and a.get("src"):
            self.scripts.append(a)
        elif tag == "link" and "stylesheet" in a.get("rel", "").lower() and a.get("href"):
            self.styles.append(a)
        elif tag in ("iframe", "object", "embed") and (a.get("src") or a.get("data")):
            self.active_resources.append(a.get("src") or a.get("data", ""))
        elif tag in ("img", "audio", "video", "source") and a.get("src"):
            self.passive_resources.append(a["src"])
        elif tag == "meta" and a.get("name", "").lower() == "generator":
            self.generator = a.get("content", "")
        elif tag == "form":
            self._form = {"method": a.get("method", "get").lower(), "action": a.get("action", ""), "inputs": []}
            self.forms.append(self._form)
        elif tag == "input" and self._form is not None:
            self._form["inputs"].append({
                "type": a.get("type", "text").lower(),
                "name": a.get("name", ""),
                "value": a.get("value", ""),
            })

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._form = None


class ContentModule(BaseModule):
    @property
    def name(self) -> str:
        return "content"

    @property
    def description(self) -> str:
        return "Phân tích nội dung HTML của trang chủ"

    def _finding(self, name: str, severity: str, description: str, remediation: str, url: str) -> dict:
        return {
            "module": self.name,
            "name": name,
            "severity": severity,
            "description": description,
            "remediation": remediation,
            "url": url,
        }

    @staticmethod
    def _is_third_party(src: str, base: str) -> bool:
        host = (urlparse(urljoin(base, src)).hostname or "").lower()
        page_host = (urlparse(base).hostname or "").lower()
        return bool(host) and host != page_host and not host.endswith("." + page_host)

    def _mixed_content(self, page: _PageParser, base: str) -> list[dict]:
        def insecure(sources: list[str]) -> list[str]:
            absolute = (urljoin(base, s) for s in sources)
            return [s for s in absolute if s.lower().startswith("http://")]

        active = insecure(
            [s["src"] for s in page.scripts] + [s["href"] for s in page.styles] + page.active_resources
        )
        passive = insecure(page.passive_resources)
        findings = []
        if active:
            findings.append(self._finding(
                "mixed_content_active", "high",
                f"Trang HTTPS nạp {len(active)} script/CSS/iframe qua HTTP (vd: {active[0]}) — kẻ tấn công trên đường truyền có thể thay mã chạy trên trang",
                "Đổi mọi tài nguyên sang https:// hoặc dùng upgrade-insecure-requests trong CSP",
                base,
            ))
        if passive:
            findings.append(self._finding(
                "mixed_content_passive", "low",
                f"Trang HTTPS nạp {len(passive)} ảnh/media qua HTTP (vd: {passive[0]}), trình duyệt cảnh báo và nội dung có thể bị thay đổi",
                "Đổi mọi tài nguyên sang https://",
                base,
            ))
        return findings

    def _missing_sri(self, page: _PageParser, base: str) -> dict | None:
        missing = [
            urljoin(base, tag.get("src") or tag.get("href", ""))
            for tag in page.scripts + page.styles
            if not tag.get("integrity") and self._is_third_party(tag.get("src") or tag.get("href", ""), base)
        ]
        if not missing:
            return None
        hosts = sorted({urlparse(m).hostname or m for m in missing})
        return self._finding(
            "missing_sri", "medium",
            f"{len(missing)} script/CSS từ bên thứ ba không có thuộc tính integrity (SRI): {', '.join(hosts[:3])}. "
            "Nếu CDN bị xâm nhập, mã độc sẽ chạy trên trang của bạn",
            "Thêm integrity=\"sha384-...\" và crossorigin=\"anonymous\" cho tài nguyên bên thứ ba, hoặc tự host",
            missing[0],
        )

    def _forms(self, page: _PageParser, base: str) -> list[dict]:
        findings: list[dict] = []
        page_is_https = base.lower().startswith("https://")
        has_password = any(i["type"] == "password" for f in page.forms for i in f["inputs"])
        if has_password and not page_is_https:
            findings.append(self._finding(
                "password_form_http", "critical",
                "Trang có ô nhập mật khẩu nhưng được phục vụ qua HTTP — mật khẩu được gửi dạng văn bản thuần",
                "Chỉ phục vụ trang đăng nhập qua HTTPS và chuyển hướng toàn bộ HTTP sang HTTPS",
                base,
            ))
        insecure_actions = [
            urljoin(base, f["action"]) for f in page.forms
            if f["action"] and urljoin(base, f["action"]).lower().startswith("http://") and page_is_https
        ]
        if insecure_actions:
            findings.append(self._finding(
                "insecure_form_action", "high",
                f"Form trên trang HTTPS gửi dữ liệu tới địa chỉ HTTP: {insecure_actions[0]}",
                "Đổi thuộc tính action của form sang https://",
                insecure_actions[0],
            ))
        unprotected = [
            f for f in page.forms
            if f["method"] == "post" and not any(
                i["type"] == "hidden" and CSRF_FIELD.search(i["name"]) for i in f["inputs"]
            )
        ]
        if unprotected:
            findings.append(self._finding(
                "form_without_csrf_token", "low",
                f"{len(unprotected)} form POST không có trường token chống CSRF (kiểm tra heuristic; "
                "có thể đã được bảo vệ bằng SameSite cookie hoặc header)",
                "Thêm token CSRF ngẫu nhiên theo phiên cho mọi form thay đổi dữ liệu",
                base,
            ))
        return findings

    @staticmethod
    def _login_form(page: _PageParser) -> dict | None:
        """Form POST đầu tiên có cả ô username (text/email) lẫn ô password — coi là form đăng nhập."""
        for form in page.forms:
            if form["method"] != "post":
                continue
            username_field = next(
                (i["name"] for i in form["inputs"] if i["type"] in USERNAME_FIELD_TYPES and i["name"]),
                None,
            )
            password_field = next(
                (i["name"] for i in form["inputs"] if i["type"] == "password" and i["name"]),
                None,
            )
            if username_field and password_field:
                return {"form": form, "username_field": username_field, "password_field": password_field}
        return None

    @staticmethod
    def _responses_reveal_enumeration(resp_a: httpx.Response, resp_b: httpx.Response) -> bool:
        """So sánh heuristic 2 phản hồi đăng nhập sai: khác mã trạng thái, khác cụm từ, hoặc độ dài
        nội dung lệch đáng kể (sau khi bỏ số, vì nhiều trang chèn số ngẫu nhiên/timestamp)."""
        if resp_a.status_code != resp_b.status_code:
            return True
        text_a, text_b = resp_a.text[:20000].lower(), resp_b.text[:20000].lower()
        has_a = any(p in text_a for p in ENUMERATION_PHRASES)
        has_b = any(p in text_b for p in ENUMERATION_PHRASES)
        if has_a != has_b:
            return True
        norm_a, norm_b = re.sub(r"\d+", "", text_a), re.sub(r"\d+", "", text_b)
        longer = max(len(norm_a), len(norm_b), 1)
        diff = abs(len(norm_a) - len(norm_b))
        return diff > 20 and diff / longer > 0.15

    async def _check_username_enumeration(
        self, client: httpx.AsyncClient, page: _PageParser, base: str
    ) -> dict | None:
        """Gửi 2 lượt đăng nhập sai (username khác nhau, cùng mật khẩu sai cố định) và so sánh phản hồi.

        Không phải brute-force: đúng 2 request, mật khẩu không có thật nên không thể đăng nhập thành công.
        """
        login = self._login_form(page)
        if not login:
            return None
        form, username_field, password_field = login["form"], login["username_field"], login["password_field"]
        hidden_fields = {i["name"]: i["value"] for i in form["inputs"] if i["type"] == "hidden" and i["name"]}
        action = urljoin(base, form["action"] or base)

        def payload(username: str) -> dict[str, str]:
            return {**hidden_fields, username_field: username, password_field: PROBE_PASSWORD}

        try:
            resp_a = await client.post(action, data=payload(PROBE_NONEXISTENT_USERNAME))
            resp_b = await client.post(action, data=payload(PROBE_COMMON_USERNAME))
        except httpx.HTTPError:
            return None

        if not self._responses_reveal_enumeration(resp_a, resp_b):
            return None
        return self._finding(
            "username_enumeration", "low",
            "Form đăng nhập trả về phản hồi khác nhau giữa một username không tồn tại và một username "
            "phổ biến (kiểm tra heuristic bằng 2 lượt đăng nhập với mật khẩu sai cố định), cho phép dò "
            "ra danh sách tài khoản hợp lệ để tấn công tiếp",
            "Trả về cùng một thông báo lỗi và cùng mã trạng thái cho mọi lần đăng nhập sai, bất kể "
            "username có tồn tại hay không; cân nhắc thêm rate-limit/CAPTCHA cho form đăng nhập",
            action,
        )

    def _outdated_libraries(self, page: _PageParser, base: str) -> list[dict]:
        findings: list[dict] = []
        seen: set[str] = set()
        for tag in page.scripts:
            src = urljoin(base, tag["src"])
            for label, pattern, min_safe, risk in VULNERABLE_LIBRARIES:
                match = pattern.search(src)
                if not match:
                    continue
                version = match.group(1)
                outdated = min_safe is None or _version_tuple(version) < min_safe
                if outdated and f"{label}{version}" not in seen:
                    seen.add(f"{label}{version}")
                    findings.append(self._finding(
                        "outdated_js_library", "medium",
                        f"{label} {version} có lỗ hổng đã biết: {risk}",
                        f"Nâng cấp {label} lên bản mới nhất còn được hỗ trợ",
                        src,
                    ))
        return findings

    async def scan(self, url: str, **kwargs) -> list:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url)
        content_type = response.headers.get("content-type", "").lower()
        text = response.text[:MAX_HTML_CHARS]
        if "html" not in content_type and not text.lstrip().lower().startswith(("<!doctype html", "<html")):
            return []
        base = url  # không theo redirect nên response luôn ứng với đúng URL đã quét
        page = _PageParser()
        page.feed(text)

        findings: list[dict] = []
        if base.lower().startswith("https://"):
            findings.extend(self._mixed_content(page, base))
        sri = self._missing_sri(page, base)
        if sri:
            findings.append(sri)
        findings.extend(self._forms(page, base))
        enum_finding = await self._check_username_enumeration(client, page, base)
        if enum_finding:
            findings.append(enum_finding)
        findings.extend(self._outdated_libraries(page, base))
        if page.generator and GENERATOR_VERSION.search(page.generator):
            findings.append(self._finding(
                "generator_version_disclosure", "low",
                f"Thẻ meta generator tiết lộ công nghệ và phiên bản: {page.generator}",
                "Xóa thẻ <meta name=\"generator\"> hoặc ẩn phiên bản",
                base,
            ))
        return findings
