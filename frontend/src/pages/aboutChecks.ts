/* ============================================================
   Catalogue of everything WebGuard checks, shown on the About page.
   Keep in sync with backend/app/modules/* (names and severities).
   ============================================================ */

import type { ModuleName, ScanMode } from '../types'

export type CheckSeverity = 'critical' | 'high' | 'medium' | 'low'

export interface CheckInfo {
  /** Name as it appears in scan results */
  name: string
  severity: CheckSeverity
  /** What the scanner looks for */
  what: string
  /** Why it matters when the check fails */
  risk: string
}

export interface CheckModule {
  id: ModuleName
  title: string
  summary: string
  /** Scan modes that include this module */
  modes: ScanMode[]
  checks: CheckInfo[]
}

export const SEVERITY_GUIDE: { severity: CheckSeverity; label: string; meaning: string; penalty: number }[] = [
  {
    severity: 'critical',
    label: 'Critical',
    meaning: 'Immediate danger: secrets are exposed, or traffic and accounts can be taken over. Fix these first.',
    penalty: 15,
  },
  {
    severity: 'high',
    label: 'High',
    meaning: 'A serious weakness that makes real attacks easy (script injection, interception). Fix soon.',
    penalty: 10,
  },
  {
    severity: 'medium',
    label: 'Medium',
    meaning: 'A missing layer of defence, or information that helps an attacker. Plan a fix.',
    penalty: 5,
  },
  {
    severity: 'low',
    label: 'Low',
    meaning: 'Minor hardening or informational. Fix when convenient.',
    penalty: 2,
  },
]

export const CHECK_MODULES: CheckModule[] = [
  {
    id: 'headers',
    title: 'Security Headers',
    summary:
      'HTTP response headers that tell the browser how to protect visitors. A finding is reported for every header that is missing.',
    modes: ['quick', 'full'],
    checks: [
      {
        name: 'Content-Security-Policy',
        severity: 'high',
        what: 'Restricts where scripts, styles and images may be loaded from.',
        risk: 'Without it, an injected script (XSS) runs freely and can steal sessions or rewrite the page.',
      },
      {
        name: 'Strict-Transport-Security (HSTS)',
        severity: 'high',
        what: 'Tells browsers to always use HTTPS for this site.',
        risk: 'Visitors on hostile networks can be downgraded to plain HTTP, exposing logins and cookies.',
      },
      {
        name: 'X-Frame-Options',
        severity: 'medium',
        what: 'Controls whether other sites may embed the page in a frame.',
        risk: 'Clickjacking: a malicious page overlays an invisible frame to trick users into clicking.',
      },
      {
        name: 'X-Content-Type-Options',
        severity: 'medium',
        what: 'Stops the browser from guessing a file’s type (MIME sniffing).',
        risk: 'An uploaded text or image file could be treated as a script and executed.',
      },
      {
        name: 'Permissions-Policy',
        severity: 'medium',
        what: 'Restricts browser features such as camera, microphone and location.',
        risk: 'Injected or third-party scripts may request sensitive device features.',
      },
      {
        name: 'Cross-Origin-Opener-Policy',
        severity: 'medium',
        what: 'Isolates the page from windows opened by other origins.',
        risk: 'Weakens protection against cross-window and side-channel attacks such as Spectre.',
      },
      {
        name: 'Cross-Origin-Embedder-Policy',
        severity: 'medium',
        what: 'Requires cross-origin resources to opt in before they can be loaded.',
        risk: 'Cross-origin content loads without consent, which blocks strong browser isolation.',
      },
      {
        name: 'X-XSS-Protection',
        severity: 'low',
        what: 'Legacy switch for the old built-in browser XSS filter.',
        risk: 'Obsolete in modern browsers (CSP replaces it); only matters for very old ones.',
      },
      {
        name: 'Referrer-Policy',
        severity: 'low',
        what: 'Limits how much of the page URL is sent to other sites when a link is followed.',
        risk: 'URLs that contain tokens or IDs can leak to third parties.',
      },
      {
        name: 'Cross-Origin-Resource-Policy',
        severity: 'low',
        what: 'Stops other sites from embedding this site’s resources (images, scripts, data).',
        risk: 'Other origins can load your resources, which enables side-channel data leaks.',
      },
      {
        name: 'csp_unsafe_inline',
        severity: 'medium',
        what: 'The CSP allows \'unsafe-inline\' scripts without a nonce or hash.',
        risk: 'The policy no longer blocks injected inline scripts, so XSS runs as if there were no CSP.',
      },
      {
        name: 'csp_unsafe_eval',
        severity: 'medium',
        what: 'The CSP allows \'unsafe-eval\' (eval() and new Function()).',
        risk: 'Attackers can turn strings into running code, bypassing much of the CSP’s protection.',
      },
      {
        name: 'csp_wildcard_source',
        severity: 'medium',
        what: 'The CSP allows scripts from any host (*, https:, http: or data:).',
        risk: 'An attacker only needs to host a script anywhere to have it accepted by the page.',
      },
      {
        name: 'hsts_short_max_age',
        severity: 'medium',
        what: 'The HSTS max-age is shorter than six months (or missing).',
        risk: 'Browsers forget the HTTPS-only rule quickly, leaving repeat visitors exposed to downgrade attacks.',
      },
      {
        name: 'hsts_missing_include_subdomains',
        severity: 'low',
        what: 'HSTS does not include includeSubDomains.',
        risk: 'Subdomains can still be downgraded to HTTP, and cookies set for the parent domain can leak.',
      },
      {
        name: 'x_frame_options_invalid',
        severity: 'medium',
        what: 'X-Frame-Options has an invalid or obsolete value such as ALLOW-FROM.',
        risk: 'Browsers ignore the header, so the page can be framed and clickjacked.',
      },
      {
        name: 'x_content_type_options_invalid',
        severity: 'medium',
        what: 'X-Content-Type-Options is present but its value is not “nosniff”.',
        risk: 'The header has no effect, so MIME sniffing stays enabled.',
      },
      {
        name: 'referrer_policy_unsafe',
        severity: 'low',
        what: 'Referrer-Policy sends the full URL to other sites (unsafe-url or no-referrer-when-downgrade).',
        risk: 'Paths and query strings, which may hold tokens or IDs, leak to third parties.',
      },
    ],
  },
  {
    id: 'cookies',
    title: 'Cookie Flags',
    summary:
      'Security flags on the cookies the server sets when the page is requested. Each missing flag is reported per cookie.',
    modes: ['full'],
    checks: [
      {
        name: 'Secure',
        severity: 'high',
        what: 'The cookie is only sent over encrypted HTTPS connections.',
        risk: 'The cookie can travel in plain text on an insecure network, where anyone can read it and hijack the session.',
      },
      {
        name: 'HttpOnly',
        severity: 'high',
        what: 'JavaScript on the page cannot read the cookie.',
        risk: 'A single XSS bug lets an attacker steal the session cookie and log in as the victim.',
      },
      {
        name: 'SameSite',
        severity: 'medium',
        what: 'The browser does not attach the cookie to requests started by other sites.',
        risk: 'Cross-site request forgery (CSRF): another site can trigger actions using the visitor’s logged-in session.',
      },
      {
        name: 'SameSite=None',
        severity: 'medium',
        what: 'The cookie explicitly opts in to being sent on cross-site requests.',
        risk: 'Other sites can make requests that carry the visitor’s cookie, which enables CSRF.',
      },
      {
        name: 'cookie_prefix_violation',
        severity: 'low',
        what: 'A cookie named __Host- or __Secure- lacks the attributes the prefix requires.',
        risk: 'Browsers reject the cookie, and the intended protection against cookie overwriting is not in place.',
      },
      {
        name: 'cookie_broad_domain',
        severity: 'low',
        what: 'A session-like cookie sets the Domain attribute, so every subdomain receives it.',
        risk: 'One vulnerable or hijacked subdomain can read or overwrite the session.',
      },
      {
        name: 'cookie_long_lived',
        severity: 'low',
        what: 'A session-like cookie lives longer than 30 days.',
        risk: 'A stolen cookie stays useful to an attacker for a long time.',
      },
    ],
  },
  {
    id: 'ssl_tls',
    title: 'SSL / TLS',
    summary:
      'The encrypted connection and its certificate. The scanner also tries TLS 1.0 and 1.1 separately to see whether the server still accepts them.',
    modes: ['quick', 'full'],
    checks: [
      {
        name: 'ssl_connection_failed',
        severity: 'critical',
        what: 'A secure connection could not be established (no HTTPS, invalid or self-signed certificate, wrong hostname).',
        risk: 'Traffic cannot be trusted or is unencrypted; browsers warn users and attackers can intercept it.',
      },
      {
        name: 'cert_expired',
        severity: 'critical',
        what: 'The certificate is past its expiry date.',
        risk: 'Browsers block or warn; users learn to click through warnings, which attackers exploit.',
      },
      {
        name: 'outdated_tls_version',
        severity: 'high',
        what: 'The server still accepts TLS 1.0 or TLS 1.1 (checked by trying each version).',
        risk: 'These old protocols have known weaknesses that allow traffic to be downgraded or decrypted.',
      },
      {
        name: 'cert_expiring_soon',
        severity: 'medium',
        what: 'The certificate expires in less than 30 days.',
        risk: 'An unnoticed expiry causes an outage and browser warnings.',
      },
      {
        name: 'cert_hostname_mismatch',
        severity: 'critical',
        what: 'The certificate was issued for a different domain than the one being served.',
        risk: 'Browsers block the page; users who click through can no longer tell a real server from an impostor.',
      },
      {
        name: 'cert_self_signed',
        severity: 'critical',
        what: 'The certificate is self-signed rather than issued by a trusted authority.',
        risk: 'Anyone can present a certificate like this, so a man-in-the-middle cannot be detected.',
      },
      {
        name: 'cert_untrusted_chain',
        severity: 'critical',
        what: 'The certificate chain is incomplete or issued by an untrusted authority.',
        risk: 'Many clients and APIs reject the connection, and browsers may show warnings.',
      },
      {
        name: 'weak_cipher_suite',
        severity: 'high',
        what: 'The server still accepts RC4, 3DES, or NULL/anonymous cipher suites (checked by offering each).',
        risk: 'These ciphers are broken or offer no protection, so traffic can be decrypted or tampered with.',
      },
      {
        name: 'tls13_unsupported',
        severity: 'low',
        what: 'The best protocol the server negotiates is TLS 1.2.',
        risk: 'Missing the faster, safer TLS 1.3 handshake; a hardening and performance gap rather than an immediate hole.',
      },
    ],
  },
  {
    id: 'information',
    title: 'Information Disclosure',
    summary:
      'Files, folders, error pages and response headers that reveal secrets or details about the technology behind the site. File checks verify the content, so sites that answer 200 for every URL do not cause false alarms.',
    modes: ['full'],
    checks: [
      {
        name: '/.env',
        severity: 'critical',
        what: 'A publicly readable environment file.',
        risk: 'It often holds database passwords and API keys, which can lead to a full compromise.',
      },
      {
        name: '/.git/HEAD',
        severity: 'critical',
        what: 'Exposed git repository metadata.',
        risk: 'Attackers can download the whole source code and history, including old secrets.',
      },
      {
        name: '/wp-admin',
        severity: 'medium',
        what: 'A WordPress admin entry point is reachable (directly or via a redirect to the login page).',
        risk: 'Reveals the CMS and invites password-guessing and plugin-exploit attempts.',
      },
      {
        name: 'Server header',
        severity: 'medium',
        what: 'The response names the web server software and version.',
        risk: 'Attackers can look up known vulnerabilities for that exact version.',
      },
      {
        name: 'X-Powered-By header',
        severity: 'medium',
        what: 'The response names the framework or language in use.',
        risk: 'Same as above: it narrows down which known exploits to try.',
      },
      {
        name: '/robots.txt',
        severity: 'low',
        what: 'A robots.txt file exists.',
        risk: 'Informational: it can reveal hidden paths (such as /admin) that crawlers are told to skip.',
      },
      {
        name: '/.git/config',
        severity: 'critical',
        what: 'Readable git configuration (content is verified, not just the status code).',
        risk: 'Reveals remote URLs that may embed tokens and confirms the full repository can be downloaded.',
      },
      {
        name: '/.svn/wc.db',
        severity: 'critical',
        what: 'An exposed Subversion working-copy database.',
        risk: 'Lets attackers rebuild the source code from the stored file list.',
      },
      {
        name: '/.aws/credentials',
        severity: 'critical',
        what: 'A readable AWS credentials file.',
        risk: 'Gives direct access to cloud resources, often with broad permissions.',
      },
      {
        name: '/id_rsa',
        severity: 'critical',
        what: 'A readable SSH private key.',
        risk: 'Anyone can log in to servers that trust this key.',
      },
      {
        name: '/.htpasswd',
        severity: 'critical',
        what: 'A readable password file for HTTP basic auth.',
        risk: 'Password hashes can be cracked offline to reach protected areas.',
      },
      {
        name: '/wp-config.php.bak',
        severity: 'critical',
        what: 'A backup of the WordPress config served as plain text.',
        risk: 'Exposes database credentials and secret keys.',
      },
      {
        name: '/backup.sql',
        severity: 'critical',
        what: 'A downloadable SQL backup (content is verified).',
        risk: 'The whole database, including user data and password hashes, can be taken.',
      },
      {
        name: '/dump.sql',
        severity: 'critical',
        what: 'A downloadable SQL dump (content is verified).',
        risk: 'The whole database, including user data and password hashes, can be taken.',
      },
      {
        name: '/database.sql',
        severity: 'critical',
        what: 'A downloadable SQL file (content is verified).',
        risk: 'The whole database, including user data and password hashes, can be taken.',
      },
      {
        name: '/backup.zip',
        severity: 'critical',
        what: 'A downloadable zip archive (file signature is verified).',
        risk: 'Typically contains source code and configuration with secrets.',
      },
      {
        name: '/console',
        severity: 'critical',
        what: 'An open Werkzeug / Flask debug console.',
        risk: 'Allows arbitrary code execution on the server.',
      },
      {
        name: '/.npmrc',
        severity: 'high',
        what: 'A readable npm configuration file.',
        risk: 'May contain registry auth tokens that allow publishing or reading private packages.',
      },
      {
        name: '/actuator/env',
        severity: 'high',
        what: 'A public Spring Boot Actuator environment endpoint.',
        risk: 'Reveals configuration and sometimes secrets or connection strings.',
      },
      {
        name: '/docker-compose.yml',
        severity: 'high',
        what: 'A readable docker-compose file.',
        risk: 'Maps out the infrastructure and frequently contains passwords in environment variables.',
      },
      {
        name: '/elmah.axd',
        severity: 'high',
        what: 'An open ELMAH error log.',
        risk: 'Stack traces and request data, including session identifiers, are exposed.',
      },
      {
        name: '/_profiler/',
        severity: 'high',
        what: 'The Symfony profiler is reachable.',
        risk: 'Exposes requests, configuration and environment values.',
      },
      {
        name: '/telescope',
        severity: 'high',
        what: 'Laravel Telescope is reachable.',
        risk: 'Exposes requests, queries and user data to anyone.',
      },
      {
        name: '/phpinfo.php',
        severity: 'medium',
        what: 'A phpinfo() page.',
        risk: 'Reveals PHP version, modules, file paths and environment variables.',
      },
      {
        name: '/info.php',
        severity: 'medium',
        what: 'A phpinfo() page at a common alternate path.',
        risk: 'Reveals PHP version, modules, file paths and environment variables.',
      },
      {
        name: '/server-status',
        severity: 'medium',
        what: 'The Apache status page is public.',
        risk: 'Shows live request URLs and client IP addresses.',
      },
      {
        name: '/server-info',
        severity: 'medium',
        what: 'The Apache server-info page is public.',
        risk: 'Reveals loaded modules and configuration.',
      },
      {
        name: '/phpmyadmin/',
        severity: 'medium',
        what: 'A phpMyAdmin login is open to the internet.',
        risk: 'A constant target for password guessing and known exploits.',
      },
      {
        name: '/adminer.php',
        severity: 'medium',
        what: 'An Adminer database tool is open to the internet.',
        risk: 'A direct route to the database if credentials are guessed or leaked.',
      },
      {
        name: '/.DS_Store',
        severity: 'medium',
        what: 'A macOS .DS_Store file was left on the server.',
        risk: 'Lists file and folder names in the web root, including hidden ones.',
      },
      {
        name: '/.htaccess',
        severity: 'medium',
        what: 'A readable .htaccess file.',
        risk: 'Reveals rewrite rules and internal paths.',
      },
      {
        name: '/web.config',
        severity: 'medium',
        what: 'A readable web.config file.',
        risk: 'May contain connection strings and machine keys.',
      },
      {
        name: '/Dockerfile',
        severity: 'medium',
        what: 'A readable Dockerfile.',
        risk: 'Discloses base images, versions and how the app is built.',
      },
      {
        name: '/.idea/workspace.xml',
        severity: 'medium',
        what: 'A JetBrains IDE project file.',
        risk: 'Leaks project structure and developer machine paths.',
      },
      {
        name: '/xmlrpc.php',
        severity: 'medium',
        what: 'WordPress XML-RPC is enabled.',
        risk: 'Commonly abused for brute-force login attempts and pingback DDoS.',
      },
      {
        name: '/wp-json/wp/v2/users',
        severity: 'medium',
        what: 'The WordPress REST API lists user accounts.',
        risk: 'Gives attackers valid usernames for targeted password attacks.',
      },
      {
        name: '/crossdomain.xml',
        severity: 'medium',
        what: 'A cross-domain policy that allows every domain.',
        risk: 'Flash/Silverlight clients on any site can read responses from this site.',
      },
      {
        name: '/composer.json',
        severity: 'low',
        what: 'A readable composer.json.',
        risk: 'Lists PHP dependencies and versions to look up known vulnerabilities.',
      },
      {
        name: '/package.json',
        severity: 'low',
        what: 'A readable package.json.',
        risk: 'Lists Node.js dependencies and versions to look up known vulnerabilities.',
      },
      {
        name: '/swagger-ui.html',
        severity: 'low',
        what: 'A public Swagger UI.',
        risk: 'Documents every API endpoint, making attacks easier to plan.',
      },
      {
        name: '/swagger.json',
        severity: 'low',
        what: 'A public Swagger API specification.',
        risk: 'Documents every API endpoint, making attacks easier to plan.',
      },
      {
        name: '/openapi.json',
        severity: 'low',
        what: 'A public OpenAPI specification.',
        risk: 'Documents every API endpoint, making attacks easier to plan.',
      },
      {
        name: '/v2/api-docs',
        severity: 'low',
        what: 'A public Springfox API specification.',
        risk: 'Documents every API endpoint, making attacks easier to plan.',
      },
      {
        name: 'X-AspNet-Version header',
        severity: 'medium',
        what: 'The response names the ASP.NET version.',
        risk: 'Narrows down which known .NET exploits to try.',
      },
      {
        name: 'X-AspNetMvc-Version header',
        severity: 'medium',
        what: 'The response names the ASP.NET MVC version.',
        risk: 'Narrows down which known exploits to try.',
      },
      {
        name: 'X-Generator header',
        severity: 'low',
        what: 'The response names the CMS or site generator.',
        risk: 'Helps attackers target known vulnerabilities in that product.',
      },
      {
        name: 'directory_listing',
        severity: 'medium',
        what: 'A folder (home page, /uploads/, /backup/, /logs/ and similar) lists its files.',
        risk: 'Attackers can browse and download files that were never meant to be linked.',
      },
      {
        name: 'verbose_error_messages',
        severity: 'medium',
        what: 'A request with odd characters triggers a stack trace or SQL error in the response.',
        risk: 'Reveals file paths, code and database details, and often marks an injectable spot.',
      },
      {
        name: 'internal_ip_disclosure',
        severity: 'low',
        what: 'The home page contains private network addresses (10.x, 172.16–31.x, 192.168.x).',
        risk: 'Maps the internal network for follow-up attacks such as SSRF.',
      },
    ],
  },
  {
    id: 'cors',
    title: 'CORS Configuration',
    summary:
      'Which other websites may read responses from this site. The scanner sends a request with a fake origin to see how the server reacts.',
    modes: ['full'],
    checks: [
      {
        name: 'cors_origin_reflection',
        severity: 'critical',
        what: 'The server echoes back whatever origin it receives (tested with a fake origin).',
        risk: 'Every website is effectively trusted, so any site can read this site’s responses.',
      },
      {
        name: 'cors_credentials_exposed',
        severity: 'critical',
        what: 'A reflected origin combined with Access-Control-Allow-Credentials: true.',
        risk: 'A malicious site can make requests as the logged-in visitor and read private data (account takeover).',
      },
      {
        name: 'cors_wildcard',
        severity: 'high',
        what: 'Access-Control-Allow-Origin is “*”, so any website may read responses.',
        risk: 'Unsafe if the responses are not meant to be public; harmless for genuinely public data.',
      },
      {
        name: 'cors_null_origin',
        severity: 'high',
        what: 'The server accepts the special origin “null”.',
        risk: 'Sandboxed iframes and local files send “null”, so an attacker page can pose as a trusted origin.',
      },
      {
        name: 'cors_weak_origin_validation',
        severity: 'high',
        what: 'The origin allow-list only matches part of the domain (tested with example.com.evil.com and evilexample.com).',
        risk: 'An attacker registers a look-alike domain and is trusted, so they can read private responses.',
      },
    ],
  },
  {
    id: 'content',
    title: 'Page Content',
    summary:
      'Static analysis of the home page HTML — what it loads, what its forms do and which libraries it ships — plus one active, low-risk check: two failed login attempts to compare error responses.',
    modes: ['full'],
    checks: [
      {
        name: 'password_form_http',
        severity: 'critical',
        what: 'A password field is served over plain HTTP.',
        risk: 'Passwords travel unencrypted and can be read by anyone on the network path.',
      },
      {
        name: 'mixed_content_active',
        severity: 'high',
        what: 'An HTTPS page loads scripts, stylesheets or frames over HTTP.',
        risk: 'An attacker on the network can swap those files and run code in the page.',
      },
      {
        name: 'insecure_form_action',
        severity: 'high',
        what: 'A form on an HTTPS page submits to an http:// address.',
        risk: 'Submitted data, possibly credentials, is sent without encryption.',
      },
      {
        name: 'missing_sri',
        severity: 'medium',
        what: 'Third-party scripts or stylesheets are loaded without a Subresource Integrity hash.',
        risk: 'If the CDN or vendor is compromised, malicious code runs on your page with full access.',
      },
      {
        name: 'outdated_js_library',
        severity: 'medium',
        what: 'A script URL reveals a library version with known vulnerabilities (jQuery, Bootstrap, AngularJS, Lodash, Moment.js).',
        risk: 'Public exploits exist for those versions, such as XSS or prototype pollution.',
      },
      {
        name: 'mixed_content_passive',
        severity: 'low',
        what: 'An HTTPS page loads images or media over HTTP.',
        risk: 'Browsers warn, and an attacker could replace or observe the content.',
      },
      {
        name: 'form_without_csrf_token',
        severity: 'low',
        what: 'A POST form has no hidden anti-CSRF token field (heuristic).',
        risk: 'Without another defence such as SameSite cookies, other sites could submit the form for the visitor.',
      },
      {
        name: 'generator_version_disclosure',
        severity: 'low',
        what: 'A meta generator tag names the CMS and its version.',
        risk: 'Attackers look up known vulnerabilities for that exact version.',
      },
      {
        name: 'username_enumeration',
        severity: 'low',
        what: 'A login form replies differently to a non-existent username than to a common one (checked with two failed login attempts using a fixed wrong password — not a brute force).',
        risk: 'Attackers can compile a list of valid accounts to target with password-guessing or credential-stuffing attacks.',
      },
    ],
  },
  {
    id: 'http_config',
    title: 'HTTP Configuration',
    summary:
      'How the server behaves over plain HTTP and which request methods it accepts. The scanner contacts port 80, sends TRACE and OPTIONS requests, and probes common redirect parameters with a harmless, non-resolving test URL.',
    modes: ['full'],
    checks: [
      {
        name: 'https_not_enforced',
        severity: 'high',
        what: 'Plain HTTP is served, or redirects somewhere other than HTTPS.',
        risk: 'Visitors who type the bare domain can be intercepted or downgraded before reaching HTTPS.',
      },
      {
        name: 'open_redirect',
        severity: 'medium',
        what: 'A common redirect parameter (next, return, url, continue...) sends visitors to an arbitrary address without validation (checked with a harmless, non-resolving test domain).',
        risk: 'Attackers craft links that look like your domain but redirect to a phishing site, often used to steal credentials or bypass link filters.',
      },
      {
        name: 'http_trace_enabled',
        severity: 'medium',
        what: 'The TRACE method is enabled and echoes the request back.',
        risk: 'Cross-site tracing can expose headers and cookies that scripts should not see.',
      },
      {
        name: 'risky_http_methods',
        severity: 'medium',
        what: 'OPTIONS advertises PUT, DELETE or CONNECT.',
        risk: 'If these are not properly restricted, attackers may upload, delete or tunnel through the server.',
      },
      {
        name: 'security_txt_missing',
        severity: 'low',
        what: 'No /.well-known/security.txt with a Contact line was found.',
        risk: 'Researchers who find a vulnerability have no obvious way to report it to you.',
      },
    ],
  },
]

/** Total number of distinct checks across all modules */
export const TOTAL_CHECKS = CHECK_MODULES.reduce((sum, m) => sum + m.checks.length, 0)
