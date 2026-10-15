# Resume helper

The `resume-tailor` skill that produced every resume in [`../output/`](../output/), plus a zip of it for
installing elsewhere.

| Path | What it is |
|---|---|
| [resume-tailor/SKILL.md](resume-tailor/SKILL.md) | The skill: turn a resume plus a job description into a tailored, ATS-safe, honest resume, with every change visible |
| [resume-tailor/references/](resume-tailor/references/) | `writing-rules.md` and `resume-json.md`, the resume JSON schema |
| [resume-tailor/scripts/build_resume.js](resume-tailor/scripts/build_resume.js) | Renders one spec JSON into one `.docx` |
| [resume-tailor/scripts/generate_all.js](resume-tailor/scripts/generate_all.js) | Defines all 26 jobs and builds every resume |
| [resume-tailor/specs/](resume-tailor/specs/) | The generated spec for each resume, kept for traceability and re-editing |
| [resume-tailor.zip](resume-tailor.zip) | The same skill zipped, to install in Claude |

## Rebuild the resumes

```bash
cd 04_JobKitAI/resume-helper/resume-tailor
npm install
node scripts/generate_all.js
```

The script rebuilds all 26 into `../output/naukri/` and `../output/stepstone/`. To add a job, add an entry to the
`JOBS` array in `generate_all.js`; the fields are explained in the [JobKitAI README](../README.md#regenerating-or-adding-more-jobs).
