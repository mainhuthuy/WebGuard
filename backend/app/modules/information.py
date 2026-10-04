import asyncio
import re
import uuid

import httpx

from app.modules.base import HTTP_TIMEOUT, BaseModule

REDIRECT_STATUSES = (301, 302, 303, 307, 308)
EXPOSED_STATUSES = (200, 206)
# Chỉ đọc phần đầu của nội dung (xin Range để server khỏi gửi cả file backup nặng)
MAX_BODY_BYTES = 65536
MAX_CONCURRENCY = 8

# Thư mục hay bị bật liệt kê nội dung ("" = trang chủ)
DIRECTORY_PATHS = ("", "/uploads/", "/backup/", "/backups/", "/logs/", "/files/", "/images/", "/assets/", "/static/")
DIRECTORY_LISTING = re.compile(rb"<title>\s*Index of /|<h1>\s*Index of /|Directory listing for /", re.IGNORECASE)

# Dấu hiệu server in lỗi chi tiết (stack trace, lỗi SQL...) ra cho người dùng
ERROR_SIGNATURES = re.compile(
    rb"Traceback \(most recent call last\)"
    rb"|Fatal error:.{0,200} on line \d+"
    rb"|Warning:.{0,200} on line \d+"
    rb"|You have an error in your SQL syntax"
    rb"|ORA-\d{5}"
    rb"|SQLSTATE\["
    rb"|psycopg2\.|PG::\w+Error"
    rb"|Server Error in '/' Application"
    rb"|Stack trace:"
    rb"|at [\w.$]+\([\w$]+\.java:\d+\)",
    re.IGNORECASE | re.DOTALL,
)

# IP mạng nội bộ lộ trong HTML (10.x, 192.168.x, 172.16-31.x)
INTERNAL_IP = re.compile(
    rb"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
)


class InformationModule(BaseModule):
    @property
    def name(self) -> str:
        return "information"

    @property
    def description(self) -> str:
        return "Rà soát lộ file và thông tin nhạy cảm"

    # Mục có "signature" (regex bytes) chỉ tính là lộ khi nội dung KHỚP chữ ký đó,
    # nên không bị báo sai khi site trả 200 cho mọi đường dẫn (SPA / catch-all).
    SENSITIVE_PATHS = [
        {
            "path" : "/.env",
            "severity" : "critical",
            "description": "File .env chứa biến môi trường nhạy cảm (mật khẩu, API keys)",
            "remediation": "Chặn truy cập file .env trong cấu hình web server"
        },
        {
            "path" : "/.git/HEAD",
            "severity" : "critical",
            "description" : "Lộ thông tin về git repository",
            "remediation" : "Xóa file .git/HEAD hoặc chặn truy cập"
        },
        {
            "path" : "/robots.txt",
            "severity" : "low",
            "description" : "File robots.txt chỉ dẫn cho bot biết nên crawl vào đâu, tránh đâu",
            "remediation" : "Nếu có những đường dẫn nhạy cảm cần che giấu thì hãy thêm vào file robots.txt"
        },
        {
            "path" : "/wp-admin",
            # /wp-admin thường trả 301/302 chuyển tới wp-login.php thay vì 200
            "redirect_markers" : ("wp-login.php", "/wp-admin/"),
            "severity" : "medium",
            "description" : "Cổng quản trị website",
            "remediation" : "Tăng cường bảo mật cho cổng quản trị"
        },
        # --- Lộ mã nguồn / khóa / dữ liệu (critical) ---
        {
            "path": "/.git/config",
            "signature": rb"\[core\]",
            "severity": "critical",
            "description": "File cấu hình git bị lộ, có thể chứa URL remote kèm token và cho phép tải lại toàn bộ mã nguồn",
            "remediation": "Chặn truy cập thư mục .git trong web server hoặc không triển khai nó lên production"
        },
        {
            "path": "/.svn/wc.db",
            "signature": rb"SQLite format 3",
            "severity": "critical",
            "description": "Cơ sở dữ liệu Subversion bị lộ, cho phép khôi phục mã nguồn",
            "remediation": "Xóa thư mục .svn khỏi production hoặc chặn truy cập"
        },
        {
            "path": "/.aws/credentials",
            "signature": rb"aws_access_key_id",
            "severity": "critical",
            "description": "File khóa truy cập AWS bị lộ công khai",
            "remediation": "Thu hồi và tạo lại khóa AWS ngay, không để thư mục .aws trong webroot"
        },
        {
            "path": "/id_rsa",
            "signature": rb"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY",
            "severity": "critical",
            "description": "Khóa riêng SSH bị lộ công khai",
            "remediation": "Thu hồi khóa, tạo khóa mới và xóa file khỏi webroot"
        },
        {
            "path": "/.htpasswd",
            "signature": rb"^[^:\s<]+:(?:\$|\{SHA\}|[A-Za-z0-9./]{13})",
            "severity": "critical",
            "description": "File mật khẩu .htpasswd bị lộ, có thể bị dò mật khẩu offline",
            "remediation": "Chuyển .htpasswd ra ngoài webroot và chặn truy cập"
        },
        {
            "path": "/wp-config.php.bak",
            "signature": rb"DB_PASSWORD|DB_NAME|AUTH_KEY",
            "severity": "critical",
            "description": "Bản sao lưu wp-config.php hiển thị dạng văn bản, lộ mật khẩu database và khóa bí mật",
            "remediation": "Xóa file sao lưu khỏi webroot và đổi mật khẩu/khóa đã lộ"
        },
        {
            "path": "/backup.sql",
            "signature": rb"CREATE TABLE|INSERT INTO|DROP TABLE|MySQL dump|PostgreSQL database dump",
            "severity": "critical",
            "description": "Bản sao lưu database có thể tải về công khai",
            "remediation": "Xóa file sao lưu khỏi webroot, lưu backup ở nơi không public"
        },
        {
            "path": "/dump.sql",
            "signature": rb"CREATE TABLE|INSERT INTO|DROP TABLE|MySQL dump|PostgreSQL database dump",
            "severity": "critical",
            "description": "Bản dump database có thể tải về công khai",
            "remediation": "Xóa file dump khỏi webroot, lưu backup ở nơi không public"
        },
        {
            "path": "/database.sql",
            "signature": rb"CREATE TABLE|INSERT INTO|DROP TABLE|MySQL dump|PostgreSQL database dump",
            "severity": "critical",
            "description": "File SQL của database có thể tải về công khai",
            "remediation": "Xóa file khỏi webroot, lưu backup ở nơi không public"
        },
        {
            "path": "/backup.zip",
            "signature": rb"^PK\x03\x04",
            "severity": "critical",
            "description": "Bản nén sao lưu website có thể tải về, chứa mã nguồn và cấu hình",
            "remediation": "Xóa file nén khỏi webroot, lưu backup ở nơi không public"
        },
        {
            "path": "/console",
            "signature": rb"Werkzeug|Interactive Console",
            "severity": "critical",
            "description": "Debug console (Werkzeug/Flask) đang mở, cho phép thực thi mã tùy ý trên server",
            "remediation": "Tắt chế độ debug ở production và chặn đường dẫn /console"
        },
        # --- Lộ cấu hình / công cụ debug (high) ---
        {
            "path": "/.npmrc",
            "signature": rb"_authToken|_auth=|registry\s*=",
            "severity": "high",
            "description": "File .npmrc bị lộ, có thể chứa token đăng nhập npm",
            "remediation": "Xóa khỏi webroot và thu hồi token đã lộ"
        },
        {
            "path": "/actuator/env",
            "signature": rb"propertySources|activeProfiles",
            "severity": "high",
            "description": "Spring Boot Actuator /env mở công khai, lộ biến môi trường và cấu hình",
            "remediation": "Tắt hoặc yêu cầu xác thực cho các endpoint Actuator nhạy cảm"
        },
        {
            "path": "/docker-compose.yml",
            "signature": rb"(?m)^\s*services\s*:",
            "severity": "high",
            "description": "File docker-compose.yml bị lộ, tiết lộ kiến trúc hạ tầng và thường kèm mật khẩu",
            "remediation": "Không đặt file cấu hình triển khai trong webroot"
        },
        {
            "path": "/elmah.axd",
            "signature": rb"Error Log for",
            "severity": "high",
            "description": "ELMAH error log mở công khai, lộ stack trace và dữ liệu phiên",
            "remediation": "Yêu cầu xác thực hoặc vô hiệu hóa elmah.axd"
        },
        {
            "path": "/_profiler/",
            "signature": rb"Symfony Profiler|sf-toolbar",
            "severity": "high",
            "description": "Symfony Profiler đang bật trên production, lộ request, cấu hình và biến môi trường",
            "remediation": "Tắt profiler ở môi trường production"
        },
        {
            "path": "/telescope",
            "signature": rb"Laravel Telescope",
            "severity": "high",
            "description": "Laravel Telescope mở công khai, lộ request, truy vấn và dữ liệu người dùng",
            "remediation": "Giới hạn Telescope bằng gate xác thực hoặc tắt ở production"
        },
        # --- Lộ thông tin / bề mặt tấn công (medium) ---
        {
            "path": "/phpinfo.php",
            "signature": rb"phpinfo\(\)|PHP Version",
            "severity": "medium",
            "description": "Trang phpinfo() lộ phiên bản PHP, module, đường dẫn và biến môi trường",
            "remediation": "Xóa file phpinfo khỏi production"
        },
        {
            "path": "/info.php",
            "signature": rb"phpinfo\(\)|PHP Version",
            "severity": "medium",
            "description": "Trang phpinfo() lộ phiên bản PHP, module, đường dẫn và biến môi trường",
            "remediation": "Xóa file phpinfo khỏi production"
        },
        {
            "path": "/server-status",
            "signature": rb"Apache Server Status",
            "severity": "medium",
            "description": "Trang trạng thái Apache mở công khai, lộ URL đang được truy cập và IP khách",
            "remediation": "Giới hạn /server-status cho IP nội bộ"
        },
        {
            "path": "/server-info",
            "signature": rb"Apache Server Information",
            "severity": "medium",
            "description": "Trang thông tin Apache mở công khai, lộ module và cấu hình",
            "remediation": "Tắt mod_info hoặc giới hạn cho IP nội bộ"
        },
        {
            "path": "/phpmyadmin/",
            "signature": rb"phpMyAdmin",
            "severity": "medium",
            "description": "Giao diện quản trị database phpMyAdmin mở ra Internet, là mục tiêu dò mật khẩu và khai thác",
            "remediation": "Giới hạn theo IP/VPN hoặc xóa khỏi server public"
        },
        {
            "path": "/adminer.php",
            "signature": rb"Adminer",
            "severity": "medium",
            "description": "Công cụ quản trị database Adminer mở ra Internet",
            "remediation": "Xóa Adminer khỏi server public hoặc giới hạn theo IP/VPN"
        },
        {
            "path": "/.DS_Store",
            "signature": rb"\x00\x00\x00\x01Bud1",
            "severity": "medium",
            "description": "File .DS_Store của macOS bị lộ, tiết lộ danh sách file/thư mục trong webroot",
            "remediation": "Xóa các file .DS_Store và chặn truy cập chúng"
        },
        {
            "path": "/.htaccess",
            "signature": rb"RewriteEngine|AuthType|AuthUserFile|<IfModule|Require ",
            "severity": "medium",
            "description": "File cấu hình .htaccess có thể đọc được, lộ luật rewrite và đường dẫn nội bộ",
            "remediation": "Chặn truy cập các file bắt đầu bằng dấu chấm trong web server"
        },
        {
            "path": "/web.config",
            "signature": rb"<configuration",
            "severity": "medium",
            "description": "File web.config (IIS/ASP.NET) có thể đọc được, có thể chứa chuỗi kết nối và khóa",
            "remediation": "Chặn truy cập web.config (IIS mặc định đã chặn, kiểm tra lại cấu hình)"
        },
        {
            "path": "/Dockerfile",
            "signature": rb"(?m)^\s*FROM\s+\S+",
            "severity": "medium",
            "description": "Dockerfile bị lộ, tiết lộ image nền, phiên bản và cách triển khai",
            "remediation": "Không đặt Dockerfile trong webroot"
        },
        {
            "path": "/.idea/workspace.xml",
            "signature": rb"<project",
            "severity": "medium",
            "description": "File dự án IDE (JetBrains) bị lộ, tiết lộ cấu trúc dự án và đường dẫn máy dev",
            "remediation": "Không triển khai thư mục .idea lên production"
        },
        {
            "path": "/xmlrpc.php",
            "signature": rb"XML-RPC server accepts POST requests only",
            "severity": "medium",
            "description": "WordPress xmlrpc.php bật, thường bị lạm dụng để brute-force và DDoS qua pingback",
            "remediation": "Vô hiệu hóa XML-RPC nếu không dùng"
        },
        {
            "path": "/wp-json/wp/v2/users",
            "signature": rb"\"slug\"\s*:",
            "severity": "medium",
            "description": "REST API WordPress liệt kê tên người dùng, giúp kẻ tấn công dò mật khẩu có mục tiêu",
            "remediation": "Chặn truy cập danh sách user cho người chưa đăng nhập"
        },
        {
            "path": "/crossdomain.xml",
            "signature": rb"allow-access-from\s+domain=\"\*\"",
            "severity": "medium",
            "description": "crossdomain.xml cho phép mọi domain truy cập qua Flash/Silverlight",
            "remediation": "Giới hạn domain được phép hoặc xóa file này"
        },
        # --- Thông tin phụ (low) ---
        {
            "path": "/composer.json",
            "signature": rb"\"require\"",
            "severity": "low",
            "description": "composer.json lộ danh sách thư viện PHP và phiên bản đang dùng",
            "remediation": "Chặn truy cập file quản lý phụ thuộc trong webroot"
        },
        {
            "path": "/package.json",
            "signature": rb"\"(?:dependencies|devDependencies|scripts)\"",
            "severity": "low",
            "description": "package.json lộ danh sách thư viện Node.js và phiên bản đang dùng",
            "remediation": "Chặn truy cập file quản lý phụ thuộc trong webroot"
        },
        {
            "path": "/swagger-ui.html",
            "signature": rb"Swagger UI|swagger-ui",
            "severity": "low",
            "description": "Tài liệu API Swagger UI mở công khai, phơi bày toàn bộ endpoint",
            "remediation": "Yêu cầu xác thực hoặc tắt tài liệu API ở production"
        },
        {
            "path": "/swagger.json",
            "signature": rb"\"swagger\"\s*:|\"openapi\"\s*:",
            "severity": "low",
            "description": "Đặc tả API (Swagger) mở công khai, phơi bày toàn bộ endpoint",
            "remediation": "Yêu cầu xác thực hoặc tắt tài liệu API ở production"
        },
        {
            "path": "/openapi.json",
            "signature": rb"\"openapi\"\s*:|\"swagger\"\s*:",
            "severity": "low",
            "description": "Đặc tả OpenAPI mở công khai, phơi bày toàn bộ endpoint",
            "remediation": "Yêu cầu xác thực hoặc tắt tài liệu API ở production"
        },
        {
            "path": "/v2/api-docs",
            "signature": rb"\"swagger\"\s*:|\"openapi\"\s*:",
            "severity": "low",
            "description": "Đặc tả API (Springfox) mở công khai, phơi bày toàn bộ endpoint",
            "remediation": "Yêu cầu xác thực hoặc tắt tài liệu API ở production"
        },
    ]

    # Header tiết lộ công nghệ/phiên bản (ngoài Server và X-Powered-By xử lý riêng)
    VERSION_HEADERS = [
        {
            "header": "X-AspNet-Version",
            "name": "X-AspNet-Version header",
            "severity": "medium",
            "description": "Lộ phiên bản ASP.NET đang chạy",
            "remediation": "Đặt <httpRuntime enableVersionHeader=\"false\" /> trong web.config"
        },
        {
            "header": "X-AspNetMvc-Version",
            "name": "X-AspNetMvc-Version header",
            "severity": "medium",
            "description": "Lộ phiên bản ASP.NET MVC đang chạy",
            "remediation": "Gọi MvcHandler.DisableMvcResponseHeader = true khi khởi động ứng dụng"
        },
        {
            "header": "X-Generator",
            "name": "X-Generator header",
            "severity": "low",
            "description": "Lộ CMS/công cụ tạo website và phiên bản",
            "remediation": "Xóa header X-Generator"
        },
    ]

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
    def _body(response: httpx.Response) -> bytes:
        return response.content[:MAX_BODY_BYTES]

    async def _get(self, client: httpx.AsyncClient, target: str, gate: asyncio.Semaphore) -> httpx.Response | None:
        """GET có giới hạn đồng thời; lỗi mạng → None (bỏ qua mục này)."""
        async with gate:
            try:
                return await client.get(target, headers={"Range": f"bytes=0-{MAX_BODY_BYTES - 1}"})
            except httpx.HTTPError:
                return None

    async def _check_path(
        self, client: httpx.AsyncClient, url: str, item: dict, catch_all: bool, gate: asyncio.Semaphore
    ) -> dict | None:
        signature = item.get("signature")
        # Site trả 200 cho mọi đường dẫn: không có chữ ký thì không thể tin status 200
        if catch_all and not signature:
            return None
        target = url.rstrip("/") + item["path"]
        response = await self._get(client, target, gate)
        if response is None:
            return None
        exposed = response.status_code in EXPOSED_STATUSES
        if exposed and signature:
            exposed = re.search(signature, self._body(response)) is not None
        if not exposed and "redirect_markers" in item:
            # Không theo redirect (tránh SSRF) nên tự đọc header Location
            location = response.headers.get("location", "").lower()
            exposed = (
                response.status_code in REDIRECT_STATUSES
                and any(m in location for m in item["redirect_markers"])
            )
        if not exposed:
            return None
        return self._finding(item["path"], item["severity"], item["description"], item["remediation"], target)

    async def _check_directory(
        self, client: httpx.AsyncClient, url: str, path: str, gate: asyncio.Semaphore
    ) -> dict | None:
        target = url.rstrip("/") + path if path else url
        response = await self._get(client, target, gate)
        if (
            response is None
            or response.status_code != 200
            or not DIRECTORY_LISTING.search(self._body(response))
        ):
            return None
        return self._finding(
            "directory_listing",
            "medium",
            "Server liệt kê toàn bộ file trong thư mục, giúp kẻ tấn công tìm file nhạy cảm",
            "Tắt autoindex/Options -Indexes trong cấu hình web server",
            target,
        )

    async def scan(self, url: str, **kwargs) -> list:
        findings = []
        gate = asyncio.Semaphore(MAX_CONCURRENCY)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # Dò "soft 404": đường dẫn ngẫu nhiên không tồn tại mà vẫn trả 200 → catch-all.
            # Cùng request này gửi kèm ký tự lạ trong query để xem server có in lỗi chi tiết không.
            probe = f"{url.rstrip('/')}/webguard-{uuid.uuid4().hex[:12]}?id=%27%22%5C"
            baseline = await self._get(client, probe, gate)
            catch_all = baseline is not None and baseline.status_code == 200

            # Duyệt qua từng path / thư mục song song (kết quả giữ nguyên thứ tự khai báo)
            results = await asyncio.gather(
                *[self._check_path(client, url, item, catch_all, gate) for item in self.SENSITIVE_PATHS],
                *[self._check_directory(client, url, path, gate) for path in DIRECTORY_PATHS],
            )
            findings.extend(r for r in results if r)

            if baseline is not None and ERROR_SIGNATURES.search(self._body(baseline)):
                findings.append(self._finding(
                    "verbose_error_messages",
                    "medium",
                    "Server hiển thị lỗi chi tiết (stack trace / lỗi SQL) cho người dùng, lộ đường dẫn và cấu trúc nội bộ",
                    "Tắt chế độ debug, hiển thị trang lỗi chung và ghi lỗi chi tiết vào log",
                    probe,
                ))

            try:
                response = await client.get(url)
                server = response.headers.get("Server")
                if server:
                    findings.append({
                        "module" : self.name,
                        "name" : "Server header",
                        "severity" : "medium",
                        "description" : "Lộ thông tin về framework/công nghệ được sử dụng",
                        "remediation" : "Xóa header Server hoặc sử dụng Reverse Proxy để che giấu",
                        "url" : url
                    })
                # Check X-Powered-By header
                xpb = response.headers.get("X-Powered-By")
                if xpb:
                    findings.append({
                        "module": self.name,
                        "name": "X-Powered-By header",
                        "severity": "medium",
                        "description": f"Lộ thông tin framework: {xpb}",
                        "remediation": "Xóa header X-Powered-By",
                        "url": url
                    })
                for item in self.VERSION_HEADERS:
                    value = response.headers.get(item["header"])
                    if value:
                        findings.append(self._finding(
                            item["name"], item["severity"],
                            f"{item['description']}: {value}", item["remediation"], url,
                        ))
                if INTERNAL_IP.search(self._body(response)):
                    findings.append(self._finding(
                        "internal_ip_disclosure",
                        "low",
                        "Trang web để lộ địa chỉ IP mạng nội bộ trong nội dung HTML",
                        "Xóa địa chỉ IP nội bộ khỏi HTML, comment và cấu hình client",
                        url,
                    ))
            except httpx.HTTPError:
                pass
        return findings
