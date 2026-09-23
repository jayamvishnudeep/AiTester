"""Tests for the Attack Surface Mapper and the Security Test Plan Writer.

The failure this agent has to avoid is different from the others in this repo.
Nothing here asks a model to judge anything true or false, so there is no
"invented finding" to catch downstream - the catalog is fixed and every payload
in it is a published OWASP detection probe. The risk is upstream, in the
mapper: a check offered against a parameter that is not actually in the spec
sends a tester probing something that does not exist, and a security report
padded with checks-that-do-not-apply erodes trust in the ones that do.

So most of what follows is: does every emitted vector target a real, parsed
parameter; is each attack class only offered where it plausibly applies (SSRF
on a URL parameter, not on a display name); and does the catalog stay a
detection-probe catalog rather than acquiring anything destructive.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_security_test_generator.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from attack_surface_mapper import _ATTACKS, AttackSurfaceMapper  # noqa: E402
from security_plan_writer import SecurityPlanWriter  # noqa: E402

passed = failed = 0
HERE = Path(__file__).parent
SAMPLES = HERE / "sample_apis"


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def raises(name, fn, fragment):
    try:
        fn()
    except ValueError as exc:
        check(name, fragment.lower() in str(exc).lower(), f"message was: {exc}")
    except Exception as exc:  # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
    else:
        check(name, False, "no error raised")


def mapper(**kw):
    params = {"spec_path": "", "default_spec_path": "", "pasted_spec": "",
              "max_payloads": 5, "max_brief_endpoints": 20,
              "include_access_control": True, "output_dir": ""}
    params.update(kw)
    return AttackSurfaceMapper(**params)


def analyse(spec_text, **kw):
    return mapper(pasted_spec=spec_text, **kw).build_surface().data


def writer(**kw):
    params = {"priorities": "See above.", "output_dir": "", "report_name": "security_test_plan.md"}
    params.update(kw)
    return SecurityPlanWriter(**params)


MINI_OPENAPI = json.dumps({
    "openapi": "3.0.3",
    "info": {"title": "Mini API", "version": "1.0"},
    "servers": [{"url": "https://staging.example.com"}],
    "paths": {
        "/search": {"get": {"parameters": [
            {"name": "q", "in": "query", "schema": {"type": "string"}},
        ]}},
        "/users/{userId}": {"get": {"parameters": [
            {"name": "userId", "in": "path", "required": True, "schema": {"type": "integer"}},
        ]}},
        "/webhook": {"post": {"requestBody": {"content": {"application/json": {
            "schema": {"type": "object", "properties": {"url": {"type": "string"}}}}}}}},
        "/health": {"get": {}},
    },
})


def prepared(spec=MINI_OPENAPI, **kw):
    folder = Path(tempfile.mkdtemp())
    mapper(pasted_spec=spec, output_dir=str(folder), **kw).build_brief()
    return folder


# --------------------------------------------------------- format detection

print("\nFormat detection")
check("OpenAPI JSON is recognised", analyse(MINI_OPENAPI)["format"] == "openapi-json")

yaml_spec = """openapi: 3.0.3
info:
  title: Y
  version: "1"
paths:
  /a:
    get:
      parameters:
        - name: id
          in: query
          schema:
            type: string
"""
check("OpenAPI YAML is recognised", analyse(yaml_spec)["format"] == "openapi-yaml")

text_spec = "GET /api/search?q=\nPOST /api/feedback  body: name, message\n"
check("a plain endpoint list is recognised", analyse(text_spec)["format"] == "text")
check("text-list endpoints are found", analyse(text_spec)["endpoints_total"] == 2)

# ------------------------------------------------------ every check is real

print("\nEvery check targets a real, parsed parameter")
a = analyse(MINI_OPENAPI)
real_params = {(e["path"], p["name"]) for e in [
    {"path": "/search", "params": [{"name": "q"}]},
    {"path": "/users/{userId}", "params": [{"name": "userId"}]},
    {"path": "/webhook", "params": [{"name": "url"}]},
] for p in e["params"]}
for v in a["vectors"]:
    check(f"vector targets a real param: {v['endpoint']}/{v['param']}",
          (v["endpoint"], v["param"]) in real_params, str((v["endpoint"], v["param"])))

check("an endpoint with no parameters gets no checks",
      not any(v["endpoint"] == "/health" for v in a["vectors"]))
check("/health is listed as untested rather than silently skipped",
      "GET /health" in a["untested_endpoints"])
check("a parameter is never listed twice for the same attack",
      len(a["vectors"]) == len({(v["endpoint"], v["method"], v["param"], v["attack"]) for v in a["vectors"]}))

# ------------------------------------------------------- targeting sanity

print("\nAttack classes are offered only where they plausibly apply")
targeted = analyse(json.dumps({
    "openapi": "3.0.3", "info": {"title": "T", "version": "1"},
    "paths": {
        "/download": {"get": {"parameters": [
            {"name": "path", "in": "query", "schema": {"type": "string"}}]}},
        "/redirect": {"get": {"parameters": [
            {"name": "next", "in": "query", "schema": {"type": "string"}}]}},
        "/avatar": {"get": {"parameters": [
            {"name": "imageUrl", "in": "query", "schema": {"type": "string"}}]}},
        "/products/{id}": {"get": {"parameters": [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}]}},
        "/import": {"post": {"requestBody": {"content": {"application/xml": {
            "schema": {"type": "string"}}}}}},
        "/reviews": {"post": {"requestBody": {"content": {"application/json": {
            "schema": {"type": "object", "properties": {
                "displayName": {"type": "string"}}}}}}}},
    },
}))
by_param = {}
for v in targeted["vectors"]:
    by_param.setdefault(v["param"], set()).add(v["attack"])

check("path traversal is offered on a 'path' parameter", "path_traversal" in by_param.get("path", set()))
check("open redirect is offered on a 'next' parameter", "open_redirect" in by_param.get("next", set()))
check("SSRF is offered on an 'imageUrl' parameter", "ssrf" in by_param.get("imageUrl", set()))
check("BOLA is offered on a path-integer id", "bola" in by_param.get("id", set()))
check("XXE is offered on an XML body", "xxe" in by_param.get("<xml body>", set()))
check("SQL injection is offered broadly, including on displayName",
      "sqli" in by_param.get("displayName", set()))

check("path traversal is NOT offered on an unrelated string param",
      "path_traversal" not in by_param.get("imageUrl", set()))
check("SSRF is NOT offered on a path-traversal-shaped parameter",
      "ssrf" not in by_param.get("path", set()))
check("XXE is NOT offered on a JSON body field",
      "xxe" not in by_param.get("displayName", set()))
check("open redirect is NOT offered on an unrelated id",
      "open_redirect" not in by_param.get("id", set()))

print("\nAccess-control checks can be switched off")
without_ac = analyse(targeted_spec := json.dumps({
    "openapi": "3.0.3", "info": {"title": "T", "version": "1"},
    "paths": {"/products/{id}": {"get": {"parameters": [
        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}]}}},
}), include_access_control=False)
check("BOLA is excluded when access-control checks are off",
      not any(v["attack"] == "bola" for v in without_ac["vectors"]))
with_ac = analyse(targeted_spec, include_access_control=True)
check("BOLA is included when access-control checks are on",
      any(v["attack"] == "bola" for v in with_ac["vectors"]))

# --------------------------------------------------------------- the catalog

print("\nThe catalog itself")
check("every attack has at least one payload", all(a["payloads"] for a in _ATTACKS))
check("every attack names its OWASP reference", all(a["owasp"] for a in _ATTACKS))
check("every attack has a positive signal to look for", all(a["positive"] for a in _ATTACKS))
check("every attack has a remediation", all(a["remediation"] for a in _ATTACKS))
check("every severity is one of the four known levels",
      all(a["severity"] in ("critical", "high", "medium", "low") for a in _ATTACKS))

# No payload in the catalog performs a destructive action. This is a detection
# tool: every payload proves a class of bug exists without doing damage - a
# quoted string, a probe for a delay, a request to a metadata endpoint, never a
# write, a delete, or a payload that would corrupt data if it landed.
_DESTRUCTIVE = ["drop table", "delete from", "; rm ", "truncate", "shutdown",
                "format c:", "> /dev/", "del /", "insert into", "update ",
                "os.system", "eval(", "exec(", "subprocess"]
for a in _ATTACKS:
    for payload in a["payloads"]:
        low = payload.lower()
        check(f"detection-only: {a['id']}/{payload[:36]!r}",
              not any(bad in low for bad in _DESTRUCTIVE), f"looks destructive: {payload}")

check("max_payloads caps the list per check",
      max(len(v["payloads"]) for v in analyse(MINI_OPENAPI, max_payloads=2)["vectors"]) == 2)

# ------------------------------------------------------------------- guards

print("\nMapper guards")
raises("no spec is refused", lambda: mapper().build_surface(), "no api spec reached")
raises("a greeting in the path field is refused",
       lambda: mapper(spec_path="hello there").build_surface(), "no api spec reached")
raises("a spec with no endpoints is refused",
       lambda: analyse('{"openapi": "3.0.3", "paths": {}}'), "no endpoints")
raises("prose with no endpoints is refused",
       lambda: analyse("This API lets you search for products and check out."),
       "no endpoints")

print("\nReading from disk")
tmp = Path(tempfile.mkdtemp())
(tmp / "spec.json").write_text(MINI_OPENAPI, encoding="utf-8")
check("a path is read", mapper(spec_path=str(tmp / "spec.json")).build_surface().data["endpoints_total"] == 4)
check("a quoted path is read",
      mapper(spec_path=f'"{tmp / "spec.json"}"').build_surface().data["endpoints_total"] == 4)
check("a missing path falls back to the default",
      mapper(spec_path="C:/nope.json",
             default_spec_path=str(tmp / "spec.json")).build_surface().data["endpoints_total"] == 4)
check("a pasted spec beats the path",
      mapper(spec_path=str(tmp / "spec.json"), pasted_spec=text_spec
            ).build_surface().data["endpoints_total"] == 2)

# --------------------------------------------------------------- $ref and body

print("\n$ref resolution and request bodies")
ref_spec = json.dumps({
    "openapi": "3.0.3", "info": {"title": "R", "version": "1"},
    "paths": {"/thing": {"post": {"requestBody": {"content": {"application/json": {
        "schema": {"$ref": "#/components/schemas/Thing"}}}}}}},
    "components": {"schemas": {"Thing": {"type": "object", "properties": {
        "name": {"type": "string"}, "count": {"type": "integer"}}}}},
})
r = analyse(ref_spec)
check("a $ref body schema is resolved", r["params_total"] == 2, str(r["params_total"]))
check("fields from the resolved schema are named",
      {v["param"] for v in r["vectors"]} <= {"name", "count"})

raw_body_spec = json.dumps({
    "openapi": "3.0.3", "info": {"title": "B", "version": "1"},
    "paths": {"/raw": {"post": {"requestBody": {"content": {"application/json": {
        "schema": {"type": "string"}}}}}}},
})
r = analyse(raw_body_spec)
check("a raw string body is still a parameter", r["params_total"] == 1)

# ------------------------------------------------------------- writer guards

print("\nWriter guards")
raises("no reports folder is refused", lambda: writer().write_report(), "set a reports folder")
raises("a missing surface file is named",
       lambda: writer(output_dir=tempfile.mkdtemp()).write_report(), "attack_surface.json")
bad = Path(tempfile.mkdtemp())
(bad / "attack_surface.json").write_text("{nope", encoding="utf-8")
raises("a corrupt surface file is refused",
       lambda: writer(output_dir=str(bad)).write_report(), "not valid json")
wrong = Path(tempfile.mkdtemp())
(wrong / "attack_surface.json").write_text('{"api": "x"}', encoding="utf-8")
raises("a surface file with no vectors is refused",
       lambda: writer(output_dir=str(wrong)).write_report(), "no vectors")
folder = prepared()
raises("empty prioritisation is refused",
       lambda: writer(output_dir=str(folder), priorities="   ").write_report(), "no prioritisation")

# ------------------------------------------------------------ the report

print("\nThe report")
r = writer(output_dir=str(folder),
          priorities="Focus on GET /users/{userId} first for BOLA.").write_report()
report = (folder / "security_test_plan.md").read_text(encoding="utf-8")
check("the authorised-use disclaimer opens the report", report.index("Authorised testing only") < 200)
check("every attack class in the surface appears in the report",
      all(v["attack_name"] in report for v in json.loads(
          (folder / "attack_surface.json").read_text(encoding="utf-8"))["vectors"]))
check("payloads are printed in the report", "' OR '1'='1" in report)
check("a positive signal is given for each check", "look for:" in report)
check("a remediation is given for each check", "Fix if found:" in report)
check("the model's prioritisation is labelled as model-written", "written by a language model" in report)
check("the report states its own limits", "does not cover" in report)
check("untested endpoints are listed", "/health" in report or "No injectable parameters" in report)
check("the summary carries the disclaimer too", "Authorised testing only" in r.text)

fenced = writer(output_dir=str(folder),
               priorities="```markdown\nStart with the id checks.\n```").write_report()
fenced_report = (folder / "security_test_plan.md").read_text(encoding="utf-8")
check("a fenced reply is unwrapped", "Start with the id checks." in fenced_report and "```markdown" not in fenced_report)

vague = writer(output_dir=str(folder), priorities="Test everything carefully and be thorough.").write_report()
vague_report = (folder / "security_test_plan.md").read_text(encoding="utf-8")
check("a vague prioritisation naming no real endpoint is flagged",
      "does not name a specific endpoint" in vague_report)

named = writer(output_dir=str(folder),
               priorities="Start with GET /users/{userId} for the BOLA check.").write_report()
named_report = (folder / "security_test_plan.md").read_text(encoding="utf-8")
check("a prioritisation naming a real endpoint is not flagged",
      "does not name a specific endpoint" not in named_report)

writer(output_dir=str(folder), priorities="x", report_name="run-1").write_report()
check("a report name without an extension gets .md", (folder / "run-1.md").is_file())
check("the details output reports where it wrote",
      writer(output_dir=str(folder), priorities="x").write_details().data["report"].endswith("security_test_plan.md"))

# ---------------------------------------------------------------- the samples

print("\nThe sample APIs in this folder")
EXPECTED = {
    "shopfront_openapi.json": ("openapi-json", 11, 19),
    "support_desk_openapi.yaml": ("openapi-yaml", 4, 6),
    "endpoints.txt": ("text", 6, 10),
}
for name, (fmt, endpoints, params) in EXPECTED.items():
    path = SAMPLES / name
    if not path.is_file():
        check(f"{name} exists", False, str(path))
        continue
    a = mapper(spec_path=str(path)).build_surface().data
    check(f"{name}: parsed as {fmt}", a["format"] == fmt, a["format"])
    check(f"{name}: {endpoints} endpoints", a["endpoints_total"] == endpoints, str(a["endpoints_total"]))
    check(f"{name}: {params} parameters", a["params_total"] == params, str(a["params_total"]))

shopfront = mapper(spec_path=str(SAMPLES / "shopfront_openapi.json")).build_surface().data
check("shopfront: SSRF found on the webhook url",
      any(v["attack"] == "ssrf" and v["param"] == "url" for v in shopfront["vectors"]))
check("shopfront: path traversal found on the download path",
      any(v["attack"] == "path_traversal" and v["param"] == "path" for v in shopfront["vectors"]))
check("shopfront: XXE found on the XML import",
      any(v["attack"] == "xxe" for v in shopfront["vectors"]))
check("shopfront: BOLA found on all three id-bearing endpoints",
      {v["endpoint"] for v in shopfront["vectors"] if v["attack"] == "bola"}
      == {"/orders/{orderId}", "/products/{productId}", "/users/{userId}"})
check("shopfront: /status has no checks", "GET /status" in shopfront["untested_endpoints"])
check("shopfront: every vector traces to a real endpoint",
      {v["endpoint"] for v in shopfront["vectors"]} <=
      {e["path"] for e in shopfront["endpoints"]})

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
