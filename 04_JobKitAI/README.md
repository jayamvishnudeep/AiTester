# JobKitAI — Resume Tailoring Workspace

This folder documents an end-to-end pass of tailoring Vishnudeep Jayam's resume
against two batches of real job postings, using the `resume-tailor` skill.
Nothing here invents skills, employers, dates, or metrics — every tailored
resume only reorders, highlights, and reframes facts that already exist in
the source resume.

## What was done

1. **Read the base resume** (`Vishnudeep_Testing_Latest__Copy_.pdf`, supplied
   by the user) and extracted every role, date, tool, and claim into a single
   source of truth.
2. **Read two job batches**:
   - `naukri_jobs.csv` — 22 postings from Naukri (Indian job market).
   - `stepstone_jobs.csv` — 5 postings from Stepstone (German job market,
     descriptions in German).
3. **Extracted each JD's real requirements** — named tools, responsibilities,
   seniority signals, and domain — and cross-referenced them against the
   resume to see what's a genuine match vs. a real gap.
4. **Generated one tailored `.docx` resume per job posting** (27 total). For
   each one, only the following changed:
   - The target title line (matches the JD's job title)
   - The summary (proof points relevant to that JD)
   - Core Skills row order + which items are highlighted
   - The order of bullets within each role (JD-relevant ones float to the top)
   - A `[X]`-team-size placeholder was added *only* on postings whose title
     is Manager/Lead level, since the source resume never states headcount
     managed — flagged rather than invented.
5. **Flagged real gaps instead of papering over them** — e.g. no Tricentis
   TOSCA experience for the msg systems TOSCA role, no Pega experience for
   puntus GmbH, no finance/banking background for Wells Fargo, no healthcare
   EDI experience for kezan. These gaps are called out in the chat history
   for each batch, not hidden inside the documents.
6. **Wrote a reference copy of every JD** into Markdown (`naukri.md`,
   `stepstone.md`) so the original postings stay next to the tailored
   resumes without needing to reopen the CSVs.

## Folder layout

```
04_JobKitAI/
├── README.md                    ← this file
├── naukri_jobs.csv               source: 22 Naukri job postings
├── stepstone_jobs.csv            source: 5 Stepstone job postings (German)
├── naukri.md                     all 22 Naukri JDs, formatted by company
├── stepstone.md                  all 5 Stepstone JDs, formatted by company
├── output/
│   ├── naukri/                   22 tailored resumes (.docx), one per job
│   └── stepstone/                5 tailored resumes (.docx), one per job
└── resume-helper/
    └── resume-tailor/            the skill that drove all of this
        ├── SKILL.md               the skill's workflow definition
        ├── references/            writing rules + resume JSON schema
        ├── scripts/
        │   ├── build_resume.js     renders one spec.json -> one .docx
        │   └── generate_all.js     defines all 27 jobs + builds them all
        └── specs/                 the generated spec.json for every resume
                                    (kept for traceability / re-editing)
```

## File naming

Each resume is named `<Company>_<Short Job Title>_Vishnudeep_Jayam.docx`, so
the two batches can be dropped straight into a job-application tracker
without renaming.

## Regenerating or adding more jobs

All 27 resumes come from one script, so nothing needs to be hand-built again:

```bash
cd resume-helper/resume-tailor
node scripts/generate_all.js
```

To tailor against a new job, add an entry to the `JOBS` array in
`scripts/generate_all.js` (company, target title, output filename, which
existing resume terms to emphasise/highlight, which two proof points and
differentiator to use in the summary, and `subdir: 'naukri' | 'stepstone' | '<new>'`),
then re-run the script — it rebuilds every resume, including the ones
already generated, so results stay consistent.

## Non-negotiables carried over from the skill

- No skill, tool, employer, date, or metric is added that the base resume
  doesn't support.
- Outcome metrics the resume doesn't have are left out rather than invented
  — the resume only claims what's already true.
- Every resume is a working copy (highlights + `[X]` placeholders kept) so
  the candidate can see exactly what was emphasised before sending it out.
