"""Inactivity Filter - a Langflow custom component.

Reads a tool-login activity export (CSV or JSON) and works out which seats are
being paid for and not used.

This is the highest-stakes guard in the repository. Every other agent here is
wrong in a way that gets skimmed and ignored; this one is wrong in a way that
can get a real person's tool access revoked. So the tier that decides whether
an account is safe to cut - "revoke now" versus "confirm first" - is computed
in code from a fixed rule, never left to a model's judgement, and an account
on the exceptions list is never silently dropped: the suppression is reported
alongside the finding it suppressed, so a QA Lead can see exactly what was
held back and why.

Money follows the same rule. The seat cost is in the log; the saving is
arithmetic on it. The model is handed the totals and never asked to add up a
column, because a wrong sum here is a wrong budget number in someone's
planning meeting.
"""

import csv
import io
import json
from datetime import date
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_REQUIRED_CSV_COLUMNS = {"tool", "user_email", "user_name", "account_created", "last_login", "seat_cost_month"}


class LicenseActivityFilter(Component):
    display_name = "Inactivity Filter"
    description = "Classifies every seat in a tool activity log as active, dormant, or never used."
    documentation = "https://www.saastr.com/saas-metrics-2-0-a-guide-to-measuring-and-improving-what-matters/"
    icon = "user-x"
    name = "LicenseActivityFilter"

    inputs = [
        MessageTextInput(
            name="log_path",
            display_name="Activity log path",
            info="Path to a CSV or JSON activity export. Leave empty to use the pasted log below.",
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="default_log_path",
            display_name="Default log path",
            info="Used whenever the path above is empty or does not exist.",
            value="",
        ),
        MultilineInput(
            name="pasted_log",
            display_name="Pasted log",
            info="Paste a CSV or JSON activity export here to use it instead of reading from disk.",
            value="",
            advanced=True,
        ),
        IntInput(
            name="dormant_after_days",
            display_name="Dormant after (days)",
            info="A seat with no login in at least this many days is dormant.",
            value=60,
        ),
        IntInput(
            name="new_account_grace_days",
            display_name="New-account grace period (days)",
            info=(
                "An account created more recently than this that has never logged in is just "
                "new, not dormant - it has not had time to be used yet."
            ),
            value=14,
            advanced=True,
        ),
        MultilineInput(
            name="exceptions",
            display_name="Exceptions",
            info=(
                "One account per line that must never be flagged - approved leave, a service "
                "account, whatever the business reason. Each line is an email address, or "
                "'email - reason', or 'email: reason'. Matching is case-insensitive. A "
                "suppressed finding is still reported, just marked as excepted rather than "
                "dropped."
            ),
            value="",
            advanced=True,
        ),
        MessageTextInput(
            name="reference_date",
            display_name="Reference date",
            info="ISO date (YYYY-MM-DD) to measure inactivity against. Empty means today.",
            value="",
            advanced=True,
        ),
        IntInput(
            name="max_listed",
            display_name="Max rows in the brief",
            info="Caps how many flagged accounts are listed in the prompt brief, by savings.",
            value=15,
            advanced=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where license_findings.json is written. The report writer reads it back from "
                "here, so both nodes must point at the same folder."
            ),
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Brief", name="brief", method="build_brief"),
        Output(display_name="Findings", name="findings", method="build_findings"),
    ]

    # ------------------------------------------------------------- loading

    def _source(self) -> tuple:
        """(text, origin) - the pasted log if there is one, otherwise the file on disk."""
        pasted = (self.pasted_log or "").strip()
        if pasted:
            return pasted, "pasted log"

        for candidate in (self.log_path, self.default_log_path):
            cleaned = (candidate or "").strip().strip('"').strip("'")
            if cleaned and Path(cleaned).is_file():
                try:
                    return Path(cleaned).read_text(encoding="utf-8-sig"), cleaned
                except OSError as exc:
                    msg = f"Could not read {cleaned} - {exc}"
                    raise ValueError(msg) from exc

        msg = (
            "No activity log reached this component, so anything reported from it would be "
            "invented - and an invented revoke list can name a real person. Set 'Default log "
            "path' to a CSV or JSON export, or paste one into 'Pasted log'."
        )
        raise ValueError(msg)

    # ------------------------------------------------------------- parsing

    @staticmethod
    def _parse_date(raw: str, context: str):
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            msg = f"{context}: '{raw}' is not a valid date (expected YYYY-MM-DD)."
            raise ValueError(msg) from exc

    @staticmethod
    def _parse_cost(raw, context: str) -> float:
        try:
            cost = float(raw)
        except (TypeError, ValueError) as exc:
            msg = f"{context}: '{raw}' is not a valid seat cost."
            raise ValueError(msg) from exc
        if cost < 0:
            msg = f"{context}: seat cost cannot be negative ({cost})."
            raise ValueError(msg)
        return cost

    def _parse_csv(self, text: str) -> list:
        reader = csv.DictReader(io.StringIO(text))
        header = set(reader.fieldnames or [])
        missing = _REQUIRED_CSV_COLUMNS - header
        if missing:
            msg = f"CSV log is missing column(s): {', '.join(sorted(missing))}."
            raise ValueError(msg)

        rows = []
        for i, raw in enumerate(reader, start=2):  # header is line 1
            tool = (raw.get("tool") or "").strip()
            email = (raw.get("user_email") or "").strip()
            if not tool:
                msg = f"CSV line {i}: missing 'tool'."
                raise ValueError(msg)
            if not email:
                msg = f"CSV line {i}: missing 'user_email'."
                raise ValueError(msg)
            created = self._parse_date(raw.get("account_created"), f"CSV line {i} ('account_created')")
            if created is None:
                msg = f"CSV line {i}: missing 'account_created'."
                raise ValueError(msg)
            rows.append({
                "tool": tool,
                "plan": (raw.get("plan") or "").strip(),
                "user_email": email,
                "user_name": (raw.get("user_name") or "").strip() or email,
                "account_created": created,
                "last_login": self._parse_date(raw.get("last_login"), f"CSV line {i} ('last_login')"),
                "seat_cost_month": self._parse_cost(raw.get("seat_cost_month"), f"CSV line {i} ('seat_cost_month')"),
            })
        return rows

    def _parse_json(self, text: str) -> list:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"Log is not valid JSON - {exc}"
            raise ValueError(msg) from exc

        tools = payload.get("tools") if isinstance(payload, dict) else None
        if not isinstance(tools, list):
            msg = 'JSON log has no "tools" list at the top level.'
            raise ValueError(msg)

        rows = []
        for t, tool in enumerate(tools, start=1):
            name = (tool.get("name") or "").strip() if isinstance(tool, dict) else ""
            if not name:
                msg = f"JSON tool entry {t}: missing 'name'."
                raise ValueError(msg)
            cost = self._parse_cost(tool.get("seat_cost_month"), f"JSON tool '{name}' ('seat_cost_month')")
            plan = (tool.get("plan") or "").strip()
            users = tool.get("users")
            if not isinstance(users, list):
                msg = f"JSON tool '{name}': missing a 'users' list."
                raise ValueError(msg)
            for u, user in enumerate(users, start=1):
                email = (user.get("email") or "").strip() if isinstance(user, dict) else ""
                if not email:
                    msg = f"JSON tool '{name}', user {u}: missing 'email'."
                    raise ValueError(msg)
                created = self._parse_date(user.get("account_created"), f"JSON tool '{name}' user '{email}' ('account_created')")
                if created is None:
                    msg = f"JSON tool '{name}', user '{email}': missing 'account_created'."
                    raise ValueError(msg)
                rows.append({
                    "tool": name,
                    "plan": plan,
                    "user_email": email,
                    "user_name": (user.get("name") or "").strip() or email,
                    "account_created": created,
                    "last_login": self._parse_date(user.get("last_login"), f"JSON tool '{name}' user '{email}' ('last_login')"),
                    "seat_cost_month": cost,
                })
        return rows

    def _rows(self) -> list:
        text, origin = self._source()
        # A CSV export never parses as JSON, so "it parsed" is the format test. Anything
        # that parsed but is the wrong shape gets a JSON error, not a confusing CSV one.
        try:
            json.loads(text)
            is_json = True
        except json.JSONDecodeError:
            is_json = False

        rows = self._parse_json(text) if is_json else self._parse_csv(text)
        if not rows:
            msg = f"No user rows found in the log ({origin}). Nothing to classify."
            raise ValueError(msg)
        return rows

    # -------------------------------------------------------- exceptions

    @staticmethod
    def _exceptions_map(raw: str) -> dict:
        out = {}
        for line in (raw or "").splitlines():
            line = line.strip()
            if not line:
                continue
            email, reason = line, ""
            if ":" in line:
                email, reason = line.split(":", 1)
            elif " - " in line:
                email, reason = line.split(" - ", 1)
            out[email.strip().lower()] = reason.strip()
        return out

    # ----------------------------------------------------------- classify

    def _reference_date(self) -> date:
        raw = (self.reference_date or "").strip()
        if not raw:
            return date.today()
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            msg = f"Reference date: '{raw}' is not a valid date (expected YYYY-MM-DD)."
            raise ValueError(msg) from exc

    def _classify(self, row: dict, today: date, dormant_after: int, grace: int, exceptions: dict) -> dict:
        created, last_login = row["account_created"], row["last_login"]

        if last_login is None:
            age = (today - created).days
            if age <= grace:
                base_status, tier, days, days_kind = "too_new", None, age, "since_created"
            else:
                base_status, tier, days, days_kind = "never_activated", "revoke_now", age, "since_created"
        else:
            inactive = (today - last_login).days
            if inactive <= dormant_after:
                base_status, tier, days, days_kind = "active", None, inactive, "since_last_login"
            else:
                tier = "revoke_now" if inactive >= dormant_after * 2 else "confirm_first"
                base_status, days, days_kind = "dormant", inactive, "since_last_login"

        email_lower = row["user_email"].lower()
        excepted = email_lower in exceptions
        annual_cost = round(row["seat_cost_month"] * 12, 2)

        return {
            "tool": row["tool"],
            "plan": row["plan"],
            "user_name": row["user_name"],
            "user_email": row["user_email"],
            "account_created": row["account_created"].isoformat(),
            "last_login": row["last_login"].isoformat() if row["last_login"] else None,
            "base_status": base_status,
            "tier": tier,
            "days": days,
            "days_kind": days_kind,
            "excepted": excepted,
            "exception_reason": exceptions.get(email_lower) if excepted else None,
            "monthly_cost": round(row["seat_cost_month"], 2),
            "annual_cost": annual_cost,
        }

    # ------------------------------------------------------------- results

    def _analysis(self) -> dict:
        rows = self._rows()
        today = self._reference_date()
        dormant_after = max(int(self.dormant_after_days or 60), 1)
        grace = max(int(self.new_account_grace_days or 14), 0)
        exceptions = self._exceptions_map(self.exceptions)

        accounts = [self._classify(r, today, dormant_after, grace, exceptions) for r in rows]

        flagged = [a for a in accounts if a["tier"] and not a["excepted"]]
        revoke_now = sorted((a for a in flagged if a["tier"] == "revoke_now"),
                             key=lambda a: (-a["annual_cost"], a["tool"], a["user_email"]))
        confirm_first = sorted((a for a in flagged if a["tier"] == "confirm_first"),
                                key=lambda a: (-a["annual_cost"], a["tool"], a["user_email"]))
        exceptions_applied = sorted(
            (a for a in accounts if a["excepted"] and a["tier"]),
            key=lambda a: (a["tool"], a["user_email"]),
        )
        too_new = sorted((a for a in accounts if a["base_status"] == "too_new"),
                          key=lambda a: (a["tool"], a["user_email"]))

        by_tool = {}
        for a in accounts:
            slot = by_tool.setdefault(a["tool"], {
                "tool": a["tool"], "seats": 0, "evaluated_seats": 0, "flagged": 0,
                "monthly_recoverable": 0.0, "annual_recoverable": 0.0,
            })
            slot["seats"] += 1
            if a["excepted"]:
                continue
            slot["evaluated_seats"] += 1
            if a["tier"]:
                slot["flagged"] += 1
                slot["monthly_recoverable"] += a["monthly_cost"]
                slot["annual_recoverable"] += a["annual_cost"]

        per_tool = []
        for slot in by_tool.values():
            frac = slot["flagged"] / slot["evaluated_seats"] if slot["evaluated_seats"] else 0.0
            per_tool.append({
                **slot,
                "monthly_recoverable": round(slot["monthly_recoverable"], 2),
                "annual_recoverable": round(slot["annual_recoverable"], 2),
                "dormant_fraction": round(frac, 2),
            })
        per_tool.sort(key=lambda t: -t["annual_recoverable"])

        return {
            "reference_date": today.isoformat(),
            "dormant_after_days": dormant_after,
            "new_account_grace_days": grace,
            "accounts_total": len(accounts),
            "status_counts": {
                s: sum(1 for a in accounts if a["base_status"] == s)
                for s in ("active", "dormant", "never_activated", "too_new")
            },
            "exceptions_defined": len(exceptions),
            "revoke_now": revoke_now,
            "confirm_first": confirm_first,
            "exceptions_applied": exceptions_applied,
            "too_new": too_new,
            "per_tool": per_tool,
            "totals": {
                "revoke_now_count": len(revoke_now),
                "revoke_now_monthly": round(sum(a["monthly_cost"] for a in revoke_now), 2),
                "revoke_now_annual": round(sum(a["annual_cost"] for a in revoke_now), 2),
                "confirm_first_count": len(confirm_first),
                "confirm_first_monthly": round(sum(a["monthly_cost"] for a in confirm_first), 2),
                "confirm_first_annual": round(sum(a["annual_cost"] for a in confirm_first), 2),
            },
            "accounts": accounts,
        }

    # -------------------------------------------------------------- disk

    FINDINGS_FILE = "license_findings.json"

    def _persist(self, analysis: dict) -> None:
        """Hand the findings to the report writer through a file, not a second edge.

        Langflow lets a component expose only one output on the canvas - a second
        wired edge is silently dropped the moment the flow is opened in the UI.
        The file is the hand-off, and it is a deliverable in its own right: a
        number in a document is a claim, a number in a file someone can
        re-generate is a fact.
        """
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / self.FINDINGS_FILE
        path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------- outputs

    def build_brief(self) -> Message:
        a = self._analysis()
        cap = max(int(self.max_listed or 15), 1)
        t = a["totals"]
        sc = a["status_counts"]

        lines = [
            "# Vendor license activity", "",
            f"Reference date: {a['reference_date']}  "
            f"(dormant after {a['dormant_after_days']} days, "
            f"{a['new_account_grace_days']}-day grace for new accounts)",
            f"Accounts: {a['accounts_total']} "
            f"({sc['active']} active, {sc['dormant']} dormant, "
            f"{sc['never_activated']} never activated, {sc['too_new']} too new)",
            f"Revoke now: {t['revoke_now_count']} seats, "
            f"${t['revoke_now_monthly']:.2f}/mo (${t['revoke_now_annual']:.2f}/yr) recoverable",
            f"Confirm first: {t['confirm_first_count']} seats, "
            f"${t['confirm_first_monthly']:.2f}/mo (${t['confirm_first_annual']:.2f}/yr) at risk",
            "", "## Per tool",
        ]
        for tool in a["per_tool"]:
            lines.append(
                f"- {tool['tool']}: {tool['flagged']}/{tool['evaluated_seats']} seats flagged "
                f"(dormant fraction {tool['dormant_fraction']:.2f}), "
                f"${tool['annual_recoverable']:.2f}/yr recoverable"
            )

        if a["revoke_now"]:
            lines.extend(["", f"## Revoke now, top {min(cap, len(a['revoke_now']))} by annual savings"])
            for acc in a["revoke_now"][:cap]:
                lines.append(
                    f"- {acc['tool']} / {acc['user_name']} ({acc['user_email']}) - "
                    f"{acc['base_status']}, {acc['days']} days {acc['days_kind'].replace('_', ' ')}, "
                    f"${acc['annual_cost']:.2f}/yr"
                )
            if len(a["revoke_now"]) > cap:
                lines.append(f"  ... and {len(a['revoke_now']) - cap} more")

        # The prompt asks the model to write about this tier by name, so the names have
        # to be here. Given only a count, a model reports the tier as empty.
        if a["confirm_first"]:
            lines.extend(["", f"## Confirm first, all {len(a['confirm_first'])}"])
            for acc in a["confirm_first"]:
                lines.append(
                    f"- {acc['tool']} / {acc['user_name']} ({acc['user_email']}) - "
                    f"{acc['days']} days {acc['days_kind'].replace('_', ' ')}, "
                    f"${acc['annual_cost']:.2f}/yr"
                )

        if a["exceptions_applied"]:
            lines.extend(["", "## Exceptions applied"])
            for acc in a["exceptions_applied"]:
                lines.append(f"- {acc['tool']} / {acc['user_email']} - {acc['exception_reason'] or 'no reason given'}")

        if a["too_new"]:
            lines.extend(["", "## Too new to judge"])
            for acc in a["too_new"]:
                lines.append(f"- {acc['tool']} / {acc['user_email']} - account created {acc['days']} days ago")

        self._persist(a)
        self.status = f"{t['revoke_now_count']} revoke now, {t['confirm_first_count']} confirm first"
        return Message(text="\n".join(lines))

    def build_findings(self) -> Data:
        a = self._analysis()
        self._persist(a)
        t = a["totals"]
        self.status = f"{t['revoke_now_count']} revoke now, {t['confirm_first_count']} confirm first"
        return Data(data=a)
