# Vendor license review

*Generated 2026-09-18 by the Vendor License Monitor, measured against 2026-09-19. Every count and every dollar below is computed from the activity log - re-run the filter to reproduce it.*

## At a glance

| | |
|---|---|
| Accounts reviewed | 24 |
| Active | 10 |
| Dormant | 10 |
| Never activated | 2 |
| Inside grace period | 2 |
| **Revoke now** | **9 seats — $259.00/mo, $3108.00/yr** |
| Confirm first | 2 seats — $17.00/mo, $204.00/yr |

Dormant means no login in 60 days. An account is **revoke now** when it has never been used at all, or has been idle for at least twice that. Anything between the two is **confirm first** — idle enough to cost money, not idle enough to cut without asking.

## By tool

| Tool | Seats | Flagged | Dormant fraction | Monthly | Annual |
|---|---:|---:|---:|---:|---:|
| BrowserStack | 6 | 4 | 67% | $168.00 | $2016.00 |
| TestRail | 4 | 2 | 50% | $68.00 | $816.00 |
| Jira | 10 | 4 | 44% | $34.00 | $408.00 |
| Confluence | 4 | 1 | 25% | $6.00 | $72.00 |

## Revoke now (9)

Never used, or idle for at least twice the dormancy threshold.

| Tool | Person | Account | Last login | Days | Monthly | Annual |
|---|---|---|---|---:|---:|---:|
| BrowserStack | Noor Hassan | `noor@shopfront.example.com` | never | 383 (since created) | $42.00 | **$504.00** |
| BrowserStack | Oliver Bennett | `oliver@shopfront.example.com` | 2025-06-15 | 461 (since last login) | $42.00 | **$504.00** |
| BrowserStack | Priya Sharma | `priya@shopfront.example.com` | 2025-12-20 | 273 (since last login) | $42.00 | **$504.00** |
| BrowserStack | Sam Okafor | `sam@shopfront.example.com` | 2026-01-08 | 254 (since last login) | $42.00 | **$504.00** |
| TestRail | Noor Hassan | `noor@shopfront.example.com` | 2025-08-25 | 390 (since last login) | $34.00 | **$408.00** |
| TestRail | Zara Ahmed | `zara@shopfront.example.com` | 2026-02-14 | 217 (since last login) | $34.00 | **$408.00** |
| Jira | Sam Okafor | `sam@shopfront.example.com` | 2025-10-02 | 352 (since last login) | $8.50 | **$102.00** |
| Jira | Zara Ahmed | `zara@shopfront.example.com` | never | 901 (since created) | $8.50 | **$102.00** |
| Confluence | Raj Patel | `raj@shopfront.example.com` | 2026-03-01 | 202 (since last login) | $6.00 | **$72.00** |

## Confirm first (2)

Dormant, but not long enough to cut without asking the seat holder.

| Tool | Person | Account | Last login | Days | Monthly | Annual |
|---|---|---|---|---:|---:|---:|
| Jira | Noor Hassan | `noor@shopfront.example.com` | 2026-07-01 | 80 (since last login) | $8.50 | **$102.00** |
| Jira | Priya Sharma | `priya@shopfront.example.com` | 2026-06-01 | 110 (since last login) | $8.50 | **$102.00** |

## Exceptions applied (1)

These met the criteria above and were held back by the exceptions list.

| Tool | Account | Would have been | Reason given |
|---|---|---|---|
| Jira | `kai@shopfront.example.com` | revoke now | approved leave, back in October |

## Inside the grace period (2)

Created within the last 14 days and not used yet. New, not dormant.

- Confluence — `tom@shopfront.example.com`, created 9 days ago
- Jira — `tom@shopfront.example.com`, created 9 days ago

---

## Recommendations

*This section is written by a language model from the evidence above. The counts are not its work; the priorities are.*

The largest single drain on the budget is BrowserStack, where four out of six seats are flagged as unused. This tool accounts for $2016.00/yr in recoverable waste, driven by a 0.67 dormant fraction. While other tools show some inactivity, BrowserStack’s high concentration of idle licenses makes it the primary target for immediate cost reduction.

Do this first
1. Revoke the four BrowserStack seats for Noor Hassan, Oliver Bennett, Priya Sharma, and Sam Okafor. This action saves $2016.00/yr.
2. Revoke the two TestRail seats for Noor Hassan and Zara Ahmed. This action saves $816.00/yr.
3. Revoke the Jira seat for Sam Okafor and the Confluence seat for Raj Patel. This action saves $174.00/yr.

Worth renegotiating
BrowserStack’s dormant fraction of 0.67 indicates a structural mismatch between the contract size and actual usage patterns, suggesting the vendor agreement itself needs review rather than just individual seat management.

Before you revoke
Check with Noor Hassan and Priya Sharma regarding their Jira access. Both accounts are currently in the "confirm first" category with 80 and 110 days since last login, respectively. Verify if they are on extended leave or have pending projects before proceeding, as these seats represent $204.00/yr in potential savings.

If every revoke-now seat is actioned, the total annual saving is $3108.00/yr.
