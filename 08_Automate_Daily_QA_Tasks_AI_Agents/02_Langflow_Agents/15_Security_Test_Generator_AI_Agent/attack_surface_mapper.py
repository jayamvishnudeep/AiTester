"""Attack Surface Mapper - a Langflow custom component.

Reads an API description and works out, for every real parameter, which OWASP
injection checks are worth running against it and what to send.

This is a security tool for a functional QA testing an API they are authorized
to test - their own staging instance. So two things are true of it by design.
The payloads are **detection probes**, not weaponised exploits: the canonical
strings a scanner sends to see whether an endpoint is vulnerable, straight from
the OWASP testing guide. And the attack surface is **parsed, never invented**:
every probe targets a parameter that actually appears in the spec, because a
security report that sends a QA chasing parameters an endpoint does not have is
worse than useless - it wastes the time and it builds false confidence.

Nothing here asks a model anything. The same spec always produces the same
vectors. The model downstream only decides what to test first and explains what
a hit looks like; it never chooses a payload and never names a parameter that
was not found here.
"""

import json
import re
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _matches(pattern):
    compiled = re.compile(pattern, re.I)
    return lambda name: bool(compiled.search(name or ""))


# --------------------------------------------------------------- the catalog
# Each attack class: (id, name, category, owasp, severity, applies, payloads,
# positive_signal, remediation). "applies" takes a parameter context dict and
# returns True when the class is worth trying against that parameter. Payloads
# are detection probes - the standard published strings a scanner uses to reveal
# a vulnerability, not to exploit one.
_ATTACKS = [
    {
        "id": "sqli", "name": "SQL injection", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-05", "severity": "critical",
        "applies": lambda p: p["type"] in ("string", "integer") and p["in"] in ("query", "path", "body"),
        "payloads": ["'", "' OR '1'='1", "' OR '1'='1' -- ", "1 OR 1=1",
                     "' UNION SELECT NULL-- ", "admin'-- ", "1'; WAITFOR DELAY '0:0:5'-- ",
                     "' AND SLEEP(5)-- "],
        "positive": "A database error in the response, a 500, results that change between "
                    "' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.",
        "remediation": "Use parameterised queries; never build SQL by string concatenation.",
    },
    {
        "id": "nosqli", "name": "NoSQL injection", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-05", "severity": "high",
        "applies": lambda p: p["in"] == "body" and p["type"] == "string"
        and (p["auth_context"] or _matches(r"user|pass|email|filter|query|id")(p["name"])),
        "payloads": ['{"$ne": null}', '{"$gt": ""}', '{"$regex": ".*"}', "' || '1'=='1"],
        "positive": "Authentication bypassed, or records returned that a plain value would not match.",
        "remediation": "Validate types server-side; reject objects where a scalar is expected.",
    },
    {
        "id": "xss", "name": "Reflected cross-site scripting", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-01", "severity": "high",
        "applies": lambda p: p["type"] == "string" and p["in"] in ("query", "body"),
        "payloads": ["<script>alert(1)</script>", "\"><script>alert(1)</script>",
                     "<img src=x onerror=alert(1)>", "'\"><svg onload=alert(1)>",
                     "javascript:alert(1)"],
        "positive": "The payload comes back in the response body unencoded - the < and > are "
                    "still angle brackets, not &lt; and &gt;.",
        "remediation": "Context-encode on output; set a Content-Security-Policy.",
    },
    {
        "id": "cmdi", "name": "OS command injection", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-12", "severity": "critical",
        "applies": lambda p: _matches(r"host|ip|domain|ping|cmd|command|exec|dns|lookup|shell|trace")(p["name"]),
        "payloads": ["; id", "| id", "& whoami", "$(id)", "`id`", "; sleep 5", "| ping -c 1 127.0.0.1"],
        "positive": "Command output (a uid=, a hostname) in the response, or a ~5s delay on the sleep probe.",
        "remediation": "Never pass input to a shell; use an argument array and an allow-list.",
    },
    {
        "id": "path_traversal", "name": "Path traversal", "category": "injection",
        "owasp": "A01:2021 Broken Access Control / WSTG-ATHZ-01", "severity": "high",
        "applies": lambda p: _matches(r"file|path|dir|folder|filename|template|include|download|attachment|doc")(p["name"]),
        "payloads": ["../../../../etc/passwd", "..\\..\\..\\..\\windows\\win.ini",
                     "....//....//....//etc/passwd", "%2e%2e%2f%2e%2e%2fetc%2fpasswd", "/etc/passwd"],
        "positive": "File contents that are not the intended file - root:x:0:0 from /etc/passwd, "
                    "or the [fonts] section of win.ini.",
        "remediation": "Resolve to a canonical path and confirm it stays inside the allowed root.",
    },
    {
        "id": "ssrf", "name": "Server-side request forgery", "category": "ssrf",
        "owasp": "A10:2021 SSRF / WSTG-INPV-19", "severity": "high",
        "applies": lambda p: _matches(r"url|uri|link|callback|webhook|target|dest|host|endpoint|image|avatar|proxy|fetch|feed|remote|load")(p["name"]),
        "payloads": ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:22",
                     "http://localhost/", "file:///etc/passwd", "http://[::1]/"],
        "positive": "Cloud metadata, an internal service banner, or a timing difference between a "
                    "reachable internal host and an unreachable one.",
        "remediation": "Allow-list destinations; block link-local, loopback and private ranges.",
    },
    {
        "id": "open_redirect", "name": "Open redirect", "category": "validation",
        "owasp": "A01:2021 Broken Access Control / WSTG-CLNT-04", "severity": "medium",
        "applies": lambda p: _matches(r"redirect|next|return|continue|goto|forward|dest|url|callback")(p["name"]),
        "payloads": ["//evil.example.com", "https://evil.example.com", "/\\evil.example.com",
                     "https:evil.example.com", "javascript:alert(1)"],
        "positive": "A 3xx response whose Location header points at evil.example.com.",
        "remediation": "Redirect only to a relative path or an allow-listed host.",
    },
    {
        "id": "ssti", "name": "Server-side template injection", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-18", "severity": "high",
        "applies": lambda p: p["type"] == "string" and p["in"] in ("query", "body")
        and _matches(r"template|name|subject|message|greeting|title|comment|body|display|content")(p["name"]),
        "payloads": ["${7*7}", "{{7*7}}", "#{7*7}", "<%= 7*7 %>", "${{7*7}}", "*{7*7}"],
        "positive": "The number 49 appears in the response where 7*7 was evaluated.",
        "remediation": "Never build a template from user input; pass it as data to a fixed template.",
    },
    {
        "id": "header_crlf", "name": "HTTP header / CRLF injection", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-16", "severity": "medium",
        "applies": lambda p: p["in"] == "header"
        or _matches(r"redirect|next|lang|locale|host|referer|location|url")(p["name"]),
        "payloads": ["%0d%0aX-Injected:%201", "%0d%0aSet-Cookie:%20injected=1", "\r\nX-Injected: 1"],
        "positive": "The injected header (X-Injected, Set-Cookie) appears in the response headers.",
        "remediation": "Strip CR and LF from anything written into a header.",
    },
    {
        "id": "ldap", "name": "LDAP injection", "category": "injection",
        "owasp": "A03:2021 Injection / WSTG-INPV-06", "severity": "high",
        "applies": lambda p: p["auth_context"] and _matches(r"user|uid|cn|login|account|mail|email")(p["name"]),
        "payloads": ["*", "*)(uid=*", "admin)(&)", "*)(|(uid=*", "*))%00"],
        "positive": "Authentication bypassed, or more directory entries returned than a real value matches.",
        "remediation": "Escape LDAP special characters; use a parameterised directory query.",
    },
    {
        "id": "xxe", "name": "XML external entity", "category": "injection",
        "owasp": "A05:2021 Security Misconfiguration / WSTG-INPV-07", "severity": "high",
        "applies": lambda p: p["in"] == "body" and p["type"] == "xml",
        "payloads": ['<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>',
                     '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "http://169.254.169.254/">]><r>&x;</r>'],
        "positive": "File contents (root:x:0:0) or an internal response reflected back inside the parsed XML.",
        "remediation": "Disable external entity and DTD processing in the XML parser.",
    },
    {
        "id": "bola", "name": "Broken object-level authorization (IDOR)", "category": "access_control",
        "owasp": "A01:2021 Broken Access Control / API1:2023 / WSTG-ATHZ-04", "severity": "critical",
        "applies": lambda p: p["in"] in ("path", "query")
        and (_matches(r"(^|_)id$|.+id$|uuid|user|account|order|ticket|doc|invoice|customer")(p["name"])
             or (p["type"] == "integer" and p["in"] == "path")),
        "payloads": ["<the id of an object belonging to another user>", "1", "0", "-1",
                     "<a valid id you were not given>"],
        "positive": "You receive an object that belongs to a different user or account than yours.",
        "remediation": "Check on every request that the authenticated user owns the object.",
        "note": "This is an access-control check, not an injection - do not send injection strings, "
                "change the identifier to one you should not be able to see.",
    },
]
_ATTACK_BY_ID = {a["id"]: a for a in _ATTACKS}

# Names of parameters that carry a JSON/XML body rather than a scalar.
_AUTH_PATHS = _matches(r"login|auth|signin|session|token|register|account")

# ------------------------------------------------------------ fallback text
_FALLBACK_LINE = re.compile(r"^\s*(GET|POST|PUT|PATCH|DELETE)\s+(\S+)(.*)$", re.I)
_QUERY_PARAM = re.compile(r"[?&]([A-Za-z_][\w-]*)=")
_PATH_PARAM = re.compile(r"\{([A-Za-z_][\w-]*)\}")
_BODY_FIELDS = re.compile(r"body:\s*(.+)$", re.I)


class AttackSurfaceMapper(Component):
    display_name = "Attack Surface Mapper"
    description = "Finds every real parameter in an API spec and the OWASP checks worth running on it."
    documentation = "https://owasp.org/www-project-web-security-testing-guide/"
    icon = "shield-alert"
    name = "AttackSurfaceMapper"

    inputs = [
        MessageTextInput(
            name="spec_path",
            display_name="API spec path",
            info="An OpenAPI/Swagger file (.json/.yaml), or a plain endpoint list. Empty uses the pasted spec.",
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="default_spec_path",
            display_name="Default API spec path",
            info="Used whenever the path above is empty or does not exist.",
            value="",
        ),
        MultilineInput(
            name="pasted_spec",
            display_name="Pasted spec",
            info="Paste an OpenAPI spec or an endpoint list here instead of reading from disk.",
            value="",
            advanced=True,
        ),
        IntInput(
            name="max_payloads",
            display_name="Payloads per check",
            info="How many probes to list for each attack class.",
            value=5,
            advanced=True,
        ),
        IntInput(
            name="max_brief_endpoints",
            display_name="Endpoints in the brief",
            info="Caps how many endpoints are described to the model, most exposed first.",
            value=20,
            advanced=True,
        ),
        BoolInput(
            name="include_access_control",
            display_name="Include access-control checks",
            info="IDOR/BOLA is not injection but is the top API risk. Off restricts output to injection only.",
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where attack_surface.json is written. The plan writer reads it back to verify "
                "the model targeted only real parameters, so both nodes must point at the same folder."
            ),
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Brief", name="brief", method="build_brief"),
        Output(display_name="Surface", name="surface", method="build_surface"),
    ]

    # ------------------------------------------------------------- loading

    def _source(self) -> tuple:
        pasted = (self.pasted_spec or "").strip()
        if pasted:
            return pasted, "pasted spec"
        for candidate in (self.spec_path, self.default_spec_path):
            cleaned = (candidate or "").strip().strip('"').strip("'")
            if cleaned and Path(cleaned).is_file():
                try:
                    return Path(cleaned).read_text(encoding="utf-8", errors="replace"), cleaned
                except OSError as exc:
                    msg = f"Could not read {cleaned} - {exc}"
                    raise ValueError(msg) from exc
        msg = (
            "No API spec reached this component. A model asked to security-test an API it "
            "cannot see will invent endpoints and parameters, and a security report full of "
            "parameters that do not exist wastes a tester's time and hides the ones that do. "
            "Set 'Default API spec path', or paste a spec."
        )
        raise ValueError(msg)

    @staticmethod
    def _load(text: str) -> tuple:
        """(structured_spec_or_None, format). None means parse it as a text list."""
        stripped = text.lstrip()
        if stripped.startswith(("{", "[")):
            try:
                return json.loads(text), "openapi-json"
            except json.JSONDecodeError:
                return None, "text"
        if "openapi:" in text[:200] or "swagger:" in text[:200] or "paths:" in text[:400]:
            try:
                import yaml
                data = yaml.safe_load(text)
                if isinstance(data, dict) and "paths" in data:
                    return data, "openapi-yaml"
            except Exception:  # noqa: BLE001 - fall back to the text parser
                pass
        return None, "text"

    # ------------------------------------------------------------- parsing

    @staticmethod
    def _resolve_ref(spec: dict, node):
        seen = 0
        while isinstance(node, dict) and "$ref" in node and seen < 10:
            ref = node["$ref"]
            seen += 1
            if not ref.startswith("#/"):
                return {}
            target = spec
            for part in ref[2:].split("/"):
                if not isinstance(target, dict) or part not in target:
                    return {}
                target = target[part]
            node = target
        return node if isinstance(node, dict) else {}

    def _params_from_openapi(self, spec: dict) -> list:
        endpoints = []
        paths = spec.get("paths") or {}
        for path, item in paths.items():
            if not isinstance(item, dict):
                continue
            shared = item.get("parameters") or []
            for method, op in item.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete") or not isinstance(op, dict):
                    continue
                auth = _AUTH_PATHS(path)
                params = []
                for raw in list(shared) + list(op.get("parameters") or []):
                    p = self._resolve_ref(spec, raw)
                    name = p.get("name")
                    if not name:
                        continue
                    schema = self._resolve_ref(spec, p.get("schema") or {})
                    params.append(self._param(name, p.get("in", "query"),
                                              schema.get("type", "string"), bool(p.get("required")), auth))

                body = self._resolve_ref(spec, op.get("requestBody") or {})
                for ctype, media in (body.get("content") or {}).items():
                    schema = self._resolve_ref(spec, (media or {}).get("schema") or {})
                    if "xml" in ctype:
                        params.append(self._param("<xml body>", "body", "xml", True, auth))
                        continue
                    props = schema.get("properties") or {}
                    if not props and schema.get("type") == "string":
                        params.append(self._param("<body>", "body", "string", True, auth))
                    for field, fschema in props.items():
                        fschema = self._resolve_ref(spec, fschema)
                        params.append(self._param(field, "body", fschema.get("type", "string"),
                                                  field in (schema.get("required") or []), auth))

                endpoints.append({"path": path, "method": method.upper(), "params": params})
        return endpoints

    def _params_from_text(self, text: str) -> list:
        endpoints = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _FALLBACK_LINE.match(line)
            if not m:
                continue
            method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
            auth = _AUTH_PATHS(path)
            params = []
            for name in _QUERY_PARAM.findall(path):
                params.append(self._param(name, "query", "string", False, auth))
            for name in _PATH_PARAM.findall(path):
                params.append(self._param(name, "path", "string", True, auth))
            body = _BODY_FIELDS.search(rest)
            if body:
                for field in re.split(r"[,\s]+", body.group(1).strip()):
                    if field:
                        params.append(self._param(field, "body", "string", False, auth))
            clean_path = path.split("?")[0]
            endpoints.append({"path": clean_path, "method": method, "params": params})
        return endpoints

    @staticmethod
    def _param(name, where, ptype, required, auth) -> dict:
        return {"name": name, "in": where, "type": (ptype or "string").lower(),
                "required": bool(required), "auth_context": bool(auth)}

    # ----------------------------------------------------------- analysing

    def _analyse(self) -> dict:
        text, origin = self._source()
        spec, fmt = self._load(text)
        if spec is not None:
            endpoints = self._params_from_openapi(spec)
            title = (spec.get("info") or {}).get("title") or Path(origin).stem
            base = (spec.get("servers") or [{}])[0].get("url", "")
        else:
            endpoints = self._params_from_text(text)
            title = Path(origin).stem.replace("_", " ")
            base = ""

        if not endpoints:
            msg = (f"No endpoints were found in {origin}. This reads an OpenAPI/Swagger file "
                   "(JSON or YAML) or a plain 'METHOD /path?param=' list. Without endpoints there "
                   "is no attack surface to map.")
            raise ValueError(msg)

        cap = max(int(self.max_payloads or 5), 1)
        include_ac = bool(self.include_access_control)
        mapped, vectors = [], []
        for ep in endpoints:
            ep_vectors = []
            for p in ep["params"]:
                for attack in _ATTACKS:
                    if attack["category"] == "access_control" and not include_ac:
                        continue
                    try:
                        if not attack["applies"](p):
                            continue
                    except Exception:  # noqa: BLE001 - a matcher error is not a match
                        continue
                    vector = {
                        "endpoint": ep["path"], "method": ep["method"],
                        "param": p["name"], "param_in": p["in"], "param_type": p["type"],
                        "attack": attack["id"], "attack_name": attack["name"],
                        "category": attack["category"], "owasp": attack["owasp"],
                        "severity": attack["severity"],
                        "payloads": attack["payloads"][:cap],
                        "positive_signal": attack["positive"],
                        "remediation": attack["remediation"],
                    }
                    if attack.get("note"):
                        vector["note"] = attack["note"]
                    ep_vectors.append(vector)
                    vectors.append(vector)
            mapped.append({**ep, "vector_count": len(ep_vectors),
                           "params_count": len(ep["params"])})

        by_severity = {s: sum(1 for v in vectors if v["severity"] == s)
                       for s in ("critical", "high", "medium", "low")}
        by_category = {}
        for v in vectors:
            by_category[v["category"]] = by_category.get(v["category"], 0) + 1
        by_attack = {}
        for v in vectors:
            by_attack[v["attack_name"]] = by_attack.get(v["attack_name"], 0) + 1

        ranked = sorted(mapped, key=lambda e: -e["vector_count"])
        return {
            "api": title,
            "base_url": base,
            "source": origin,
            "format": fmt,
            "endpoints_total": len(endpoints),
            "params_total": sum(len(e["params"]) for e in endpoints),
            "untested_endpoints": [f"{e['method']} {e['path']}" for e in mapped if e["vector_count"] == 0],
            "vectors_total": len(vectors),
            "severity_counts": by_severity,
            "category_counts": by_category,
            "attack_counts": dict(sorted(by_attack.items(), key=lambda kv: -kv[1])),
            "endpoints": ranked,
            "vectors": vectors,
        }

    # -------------------------------------------------------------- disk

    SURFACE_FILE = "attack_surface.json"

    def _persist(self, analysis: dict) -> None:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / self.SURFACE_FILE).write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ outputs

    def _brief_text(self, a: dict) -> str:
        sv = a["severity_counts"]
        lines = [
            f"# Attack surface — {a['api']}", "",
            "**Test only an environment you are authorised to test.** These are detection probes "
            "for your own API, not exploits to run against anyone else's.", "",
            f"Base URL: {a['base_url'] or 'not stated'}",
            f"Endpoints: {a['endpoints_total']}   Parameters: {a['params_total']}",
            f"Checks to run: {a['vectors_total']} "
            f"({sv['critical']} critical, {sv['high']} high, {sv['medium']} medium)",
            "",
            "## Attack surface by endpoint, most exposed first",
            "",
        ]
        cap = max(int(self.max_brief_endpoints or 20), 1)
        for ep in a["endpoints"][:cap]:
            if not ep["vector_count"]:
                continue
            lines.append(f"### {ep['method']} {ep['path']}  ({ep['vector_count']} checks)")
            grouped = {}
            for p in ep["params"]:
                grouped.setdefault(p["name"], [])
            for v in a["vectors"]:
                if v["endpoint"] == ep["path"] and v["method"] == ep["method"]:
                    grouped.setdefault(v["param"], []).append(f"{v['attack_name']} [{v['severity']}]")
            for name, attacks in grouped.items():
                if attacks:
                    lines.append(f"- `{name}` ({next((p['in'] for p in ep['params'] if p['name'] == name), '?')}): "
                                 + ", ".join(sorted(set(attacks))))
            lines.append("")

        if a["untested_endpoints"]:
            lines.append("## No injectable parameters found")
            lines.append(", ".join(a["untested_endpoints"]))
            lines.append("")
        return "\n".join(lines)

    def build_brief(self) -> Message:
        a = self._analyse()
        self._persist(a)
        self.status = self._status(a)
        return Message(text=self._brief_text(a))

    def build_surface(self) -> Data:
        a = self._analyse()
        self._persist(a)
        self.status = self._status(a)
        return Data(data=a)

    @staticmethod
    def _status(a: dict) -> str:
        sv = a["severity_counts"]
        return f"{a['vectors_total']} checks, {sv['critical']} critical, {sv['high']} high"
