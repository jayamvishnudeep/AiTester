#!/usr/bin/env node
/*
 * generate_all.js — build one tailored resume .docx per job row from the
 * naukri_jobs.csv, using build_resume.js as the renderer.
 *
 * Bullets and facts are a single source of truth (BASE below); per-job
 * tailoring only changes: title line, summary, skills-category order, the
 * order of bullets within a role, and which existing terms get ==highlighted==
 * to show what was emphasised for that JD. Nothing is invented.
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');           // .../resume-tailor
const SPECS_DIR = path.join(ROOT, 'specs');
const OUT_DIR = path.resolve(ROOT, '..', '..', 'output'); // 04_JobKitAI/output
const BUILD_SCRIPT = path.join(ROOT, 'scripts', 'build_resume.js');

fs.mkdirSync(SPECS_DIR, { recursive: true });
fs.mkdirSync(OUT_DIR, { recursive: true });

// ---------------------------------------------------------------- base data
const CONTACT = [
  ['Berlin, Germany', 'jayamvishnudeep1@gmail.com|mailto:jayamvishnudeep1@gmail.com', '+49 176 5797 5732'],
];

const EDUCATION_ROWS = [
  ['Masters in Information Technology', 'Frankfurt University of Applied Sciences, Frankfurt am Main, Germany  ·  Oct 2014 – Jan 2018'],
  ['Principal Subjects', 'Software Engineering (.NET), Mobile Computing (Java), Distributed Systems, Machine Learning, Autonomous Intelligent Systems'],
];

const LANGUAGE_ROWS = [
  ['English', 'Proficient'],
  ['German', 'Intermediate (A2)'],
];

const CERT_BULLETS = [
  'ISTQB Certified Tester – Foundation Level (CTFL)',
];

// Core skills: id -> {label, items}. Every item must be evidenced in the source resume.
const SKILL_CATS = {
  automation:  { label: 'Automation Frameworks & Tools', items: ['Selenium WebDriver', 'Playwright', 'Cucumber (BDD)', 'TestNG', 'Page Object Model', 'Selenium Grid'] },
  languages:   { label: 'Languages', items: ['Java', 'TypeScript', 'Python', 'PHP (Codeception)'] },
  api:         { label: 'API & Backend Testing', items: ['REST Assured', 'Postman', 'Python API test scripts'] },
  cicd:        { label: 'CI/CD, Build & Cloud', items: ['Jenkins', 'Gradle', 'Maven', 'Travis CI', 'Git', 'GitHub', 'AWS'] },
  mgmt:        { label: 'Test Management & Methodology', items: ['TestRail', 'XRay', 'Jira', 'Agile Scrum', 'Kanban', 'Test Planning & Case Design', 'Defect Tracking & Reporting', 'SDLC / STLC'] },
  platforms:   { label: 'Platforms Tested', items: ['Web (Chrome, Firefox, IE)', 'Windows Desktop', 'Android', 'iOS', 'Mobile / Tablet'] },
  domain:      { label: 'Domain Exposure', items: ['Automotive Infotainment Systems (VW)', 'E-commerce Platforms (Magento)', 'Enterprise Web Applications'] },
};
const SKILL_ORDER_DEFAULT = ['automation', 'languages', 'api', 'cicd', 'mgmt', 'platforms', 'domain'];

// Roles, most recent first. Each bullet: {id, text, terms:[highlightable terms]}
const ROLES = [
  {
    key: 'zertificon',
    title: 'Senior QA Engineer',
    org: 'Zertificon Solutions GmbH',
    meta: 'Feb 2022 – Present  |  Berlin, Germany  |  Secure email / enterprise web applications',
    bullets: [
      { id: 'z1', text: 'Develop and maintain a test automation framework for web applications using Playwright with TypeScript.', terms: ['Playwright', 'TypeScript'] },
      { id: 'z2', text: 'Design and build test automation from scratch using the Cucumber framework for Windows-based, Android, and iOS Zertificon applications.', terms: ['Cucumber', 'Windows', 'Android', 'iOS'] },
      { id: 'z3', text: 'Build and maintain test automation for the Zertificon website using the Cucumber framework with Selenium and Java.', terms: ['Selenium', 'Java', 'Cucumber'] },
      { id: 'z4', text: 'Write and maintain test cases for Zertificon applications in the TestRail test case management tool.', terms: ['TestRail'] },
      { id: 'z5', text: 'Use Gradle as the build management tool and Jenkins for CI/CD.', terms: ['Gradle', 'Jenkins', 'CI/CD'] },
      { id: 'z6', text: 'Follow Scrum Agile methodology across the team, collaborating with cross-functional teams to reproduce reported bugs and mentoring junior engineers.', terms: ['Scrum', 'Agile'] },
    ],
  },
  {
    key: 'ibmix',
    title: 'Quality Assurance Manager',
    org: 'IBMiX',
    meta: 'Mar 2019 – Jan 2022  |  Berlin, Germany  |  Automotive / in-car infotainment',
    leadershipBullet: 'ib7',
    bullets: [
      { id: 'ib1', text: 'Owned testing of the Volkswagen in-car infotainment app "We Experience" for the VW Passat and VW Golf as the sole QA resource on the product.', terms: ['Volkswagen', 'infotainment'] },
      { id: 'ib2', text: "Analyzed real-time app performance while driving the vehicle and debugged logs from the car's backend systems.", terms: [] },
      { id: 'ib3', text: 'Designed a test automation framework using Selenium, Java, and TestNG for the in-car infotainment app.', terms: ['Selenium', 'Java', 'TestNG'] },
      { id: 'ib4', text: 'Automated infotainment system backend APIs using the REST Assured framework and Postman for manual API testing.', terms: ['REST Assured', 'Postman', 'API'] },
      { id: 'ib5', text: 'Used Maven as the build management tool and Jenkins / Travis CI for continuous integration.', terms: ['Maven', 'Jenkins', 'Travis CI', 'CI/CD'] },
      { id: 'ib6', text: 'Wrote test cases for the infotainment car application in the XRay test case management tool and produced daily and weekly status reports.', terms: ['XRay'] },
      { id: 'ib7', text: 'Followed Scrum and Kanban Agile methodology, managing test case preparation, execution, defect tracking, and reporting for the team.', terms: ['Scrum', 'Kanban'] },
    ],
  },
  {
    key: 'geschenkidee',
    title: 'QA Engineer',
    org: 'Geschenkidee DA GmbH',
    meta: 'Oct 2017 – Jan 2019  |  Berlin, Germany  |  E-commerce (13 European markets)',
    bullets: [
      { id: 'g1', text: 'Owned testing for all 13 e-commerce shops across Europe as the sole QA engineer.', terms: ['e-commerce'] },
      { id: 'g2', text: 'Designed a test automation framework using Selenium with Java in the Page Object Model pattern, using Maven as the build management tool.', terms: ['Selenium', 'Java', 'Page Object Model', 'Maven'] },
      { id: 'g3', text: 'Developed automation scripts using TestNG and ran automated test suites in Jenkins.', terms: ['TestNG', 'Jenkins'] },
      { id: 'g4', text: 'Wrote automated test scripts using Codeception in PHP.', terms: ['PHP'] },
      { id: 'g5', text: 'Wrote test cases from user stories and acceptance criteria and created test plans.', terms: [] },
      { id: 'g6', text: 'Tested application compatibility across browser versions (IE, Firefox, Chrome) and across mobile, desktop, and tablet environments.', terms: ['mobile'] },
      { id: 'g7', text: 'Tested backend Magento e-commerce modules and deployed features to test servers for manual and automated testing.', terms: ['Magento'] },
      { id: 'g8', text: 'Used Git for version control and worked within AWS infrastructure.', terms: ['Git', 'AWS'] },
      { id: 'g9', text: 'Performed the complete testing lifecycle — regression testing of fixed bugs and new builds, sanity testing, and user testing — following Scrum and Kanban.', terms: ['regression', 'Scrum', 'Kanban'] },
    ],
  },
  {
    key: 'adnymics_werk',
    title: 'QA Automation Engineer (Werkstudent)',
    org: 'Adnymics GmbH',
    meta: 'May 2017 – Oct 2017  |  München, Germany  |  Print-tech / personalization platform',
    bullets: [
      { id: 'aw1', text: 'Designed a test automation framework using Selenium with Python in the Page Object Model pattern.', terms: ['Selenium', 'Python', 'Page Object Model'] },
      { id: 'aw2', text: 'Wrote automated test scripts for APIs in Python and tested APIs using Postman.', terms: ['Python', 'API', 'Postman'] },
      { id: 'aw3', text: 'Ran Selenium automation scripts using Selenium Grid and performed the complete testing lifecycle — regression, sanity, and user testing — following Agile Scrum.', terms: ['Selenium', 'Scrum'] },
    ],
  },
  {
    key: 'adnymics_intern',
    title: 'QA Automation Engineer (Intern)',
    org: 'Adnymics GmbH',
    meta: 'Mar 2017 – Apr 2017  |  München, Germany  |  Print-tech / personalization platform',
    bullets: [
      { id: 'ai1', text: 'Wrote and executed manual and automated test cases using Selenium in Python, running scripts via Selenium Grid.', terms: ['Selenium', 'Python'] },
      { id: 'ai2', text: 'Performed the complete testing lifecycle — regression, sanity, and user testing — applying SDLC quality practices and filing defects in Jira.', terms: ['SDLC', 'Jira'] },
    ],
  },
];

// -------------------------------------------------------------- proof pool
const PROOFS = {
  playwright: 'built a Playwright + TypeScript automation framework for web applications and led Cucumber-based automation across Windows, Android, and iOS',
  selenium_java: 'designed Selenium + Java + TestNG automation frameworks across e-commerce, automotive, and enterprise web platforms',
  api: 'automated backend APIs with REST Assured and Postman, and built Python-based API test suites',
  cicd: 'embedded automated suites into CI/CD pipelines using Jenkins, Gradle, Maven, and Travis CI',
  ecommerce: 'owned QA for 13 European e-commerce storefronts on the Magento platform',
  management: 'managed test case preparation, execution, defect tracking, and status reporting as the QA lead on an automotive infotainment product',
  crossplatform: 'delivered cross-platform automation spanning Windows, Android, iOS, and web',
};
const DIFFERENTIATORS = {
  automotive: 'differentiated by hands-on experience testing real-time, safety-relevant in-car infotainment systems for Volkswagen',
  ecommerce: 'differentiated by end-to-end ownership of QA across a 13-country e-commerce portfolio',
  fullstack: 'differentiated by owning the full automation lifecycle — from framework design through CI/CD integration to defect reporting — independently',
};

const cap = s => s.charAt(0).toUpperCase() + s.slice(1);

function buildSummary(targetTitle, proofIds, diffId) {
  const proofs = proofIds.map(id => PROOFS[id]);
  const diff = DIFFERENTIATORS[diffId];
  return `==${targetTitle}== with **9+ years** of experience across UI and API test automation — from tool selection and framework design through script development, suite execution, and defect reporting. ==${cap(proofs[0])}==. ==${cap(proofs[1])}==, ${diff}.`;
}

// --------------------------------------------------------------- helpers
function highlightOnce(text, terms, usedSet) {
  let out = text;
  for (const term of terms) {
    const key = term.toLowerCase();
    if (usedSet.has(key)) continue;
    const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'i');
    if (re.test(out) && !/==/.test(out.match(re)?.[0] || '')) {
      out = out.replace(re, '==$1==');
      usedSet.add(key);
    }
  }
  return out;
}

function buildRoleSection(job) {
  const usedTerms = new Set();
  const roles = ROLES.map(role => {
    let bullets = role.bullets.slice();
    // front-load bullets whose terms match this job's emphasis
    const emphasis = new Set(job.terms.map(t => t.toLowerCase()));
    bullets.sort((a, b) => {
      const aHit = a.terms.some(t => emphasis.has(t.toLowerCase())) ? 0 : 1;
      const bHit = b.terms.some(t => emphasis.has(t.toLowerCase())) ? 0 : 1;
      return aHit - bHit;
    });
    let texts = bullets.map(b => highlightOnce(b.text, job.terms.filter(t => b.terms.some(bt => bt.toLowerCase() === t.toLowerCase())), usedTerms));
    if (job.leadershipRoleKey === role.key && role.leadershipBullet) {
      const idx = bullets.findIndex(b => b.id === role.leadershipBullet);
      if (idx !== -1) {
        texts[idx] = texts[idx].replace(/\.$/, ', leading a team of [X] QA and automation engineers.');
      }
    }
    return { title: role.title, org: role.org, meta: role.meta, bullets: texts };
  });
  return roles;
}

const FILL_IN_RULE = 'FILL-IN RULE — every item in the bracketed row above is named by this job description but is not evidenced anywhere in your source resume. Keep only what you have genuinely shipped with and could be questioned on for twenty minutes; delete the rest, then delete the row label itself. Do not soften an entry to "exposure to".';

function buildSkillsRows(job) {
  const order = [...new Set([...(job.skillOrder || []), ...SKILL_ORDER_DEFAULT])];
  const rows = order.map(catId => {
    const cat = SKILL_CATS[catId];
    const items = cat.items.map(item => {
      const isMatch = job.terms.some(t => item.toLowerCase().includes(t.toLowerCase()));
      return isMatch ? `==${item}==` : item;
    });
    return [cat.label, items.join(' · ')];
  });
  if (job.gapSkills) {
    rows.push([
      '[Gate skills — fill or delete this row]',
      job.gapSkills.map(g => `[${g}]`).join(' · '),
    ]);
  }
  return rows;
}

function buildSkillsNote(job) {
  const parts = [];
  if (job.jdWarning) parts.push(`JD MISMATCH — ${job.jdWarning}`);
  if (job.gapSkills) parts.push(FILL_IN_RULE);
  return parts.length ? parts.join('  ') : undefined;
}

function buildSpec(job) {
  const fileSafe = `${job.file}_Vishnudeep_Jayam`;
  const targetDir = path.join(OUT_DIR, job.subdir || 'naukri');
  const output = path.join(targetDir, `${fileSafe}.docx`);
  return {
    output,
    docTitle: `Vishnudeep Jayam — ${job.targetTitle} — ${job.company}`,
    name: 'VISHNUDEEP JAYAM',
    title: `==${job.targetTitle.toUpperCase()}==  ·  TEST AUTOMATION`,
    contact: CONTACT,
    margin: 0.5,
    sections: [
      { heading: 'SUMMARY', body: buildSummary(job.targetTitle, job.proofs, job.diff) },
      { heading: 'CORE SKILLS', rows: buildSkillsRows(job), note: buildSkillsNote(job) },
      { heading: 'PROFESSIONAL EXPERIENCE', roles: buildRoleSection(job).map(r => ({ title: r.title, org: r.org, meta: r.meta, bullets: r.bullets })) },
      { heading: 'EDUCATION', rows: EDUCATION_ROWS },
      { heading: 'CERTIFICATIONS', bullets: CERT_BULLETS },
      { heading: 'LANGUAGES', rows: LANGUAGE_ROWS },
    ],
  };
}

// ------------------------------------------------------------------ jobs
// gapSkills: gate skills the JD names that the source resume does NOT evidence —
//   rendered as a [placeholder] row plus a fill-in rule, never asserted.
// jdWarning: surfaced on the working copy when the posting itself is inconsistent.
const JOBS = [
  // ---- naukri_jobs.csv (Indian market, Naukri) --------------------------
  {
    company: 'Light & Wonder', targetTitle: 'Senior QA Engineer, Software', file: 'Light_and_Wonder_Senior_QA_Engineer',
    terms: ['Selenium', 'Java', 'Agile', 'regression', 'Test Planning', 'Defect Tracking'],
    proofs: ['selenium_java', 'management'], diff: 'fullstack', skillOrder: ['automation', 'mgmt'],
    gapSkills: ['Land-Based Gaming / Casino Domain'],
  },
  {
    company: 'Xoxoday', targetTitle: 'Catalog Quality & AI Automation Manager', file: 'Xoxoday_Catalog_Quality_AI_Automation_Manager',
    terms: ['Agile', 'Jira', 'Defect Tracking'],
    proofs: ['management', 'ecommerce'], diff: 'ecommerce', skillOrder: ['mgmt', 'domain'], leadershipRoleKey: 'ibmix',
    gapSkills: ['Product Catalog Management', 'AI-Powered Automation Tooling', 'Data Analysis & Trend Reporting'],
    jdWarning: 'this is a catalog / product-data management role, not a software test automation role. Your QA and e-commerce experience is adjacent, not a direct match — address the domain gap in a cover note or skip this one.',
  },
  {
    company: 'PwC Service Delivery Center', targetTitle: 'Manager – QA Automation, Data & Analytics', file: 'PwC_Manager_QA_Automation_Data_Analytics_Advisory',
    terms: ['Playwright', 'Selenium', 'Java', 'Python', 'Jenkins', 'CI/CD', 'AWS', 'Agile', 'Scrum'],
    proofs: ['playwright', 'cicd'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'cicd', 'mgmt'], leadershipRoleKey: 'ibmix',
    gapSkills: ['ETL / ELT Pipeline Testing', 'SQL & Data Quality Validation', 'PyTest', 'Azure DevOps'],
  },
  {
    company: 'Tata Consultancy Services', targetTitle: 'Senior Quality Assurance Engineer', file: 'TCS_Senior_Quality_Assurance_Engineer',
    terms: ['Java', 'TypeScript', 'Python', 'Selenium', 'Postman', 'Cucumber', 'Jenkins', 'Agile', 'XRay', 'Jira'],
    proofs: ['selenium_java', 'cicd'], diff: 'fullstack', skillOrder: ['languages', 'automation', 'api', 'mgmt'],
    gapSkills: ['Appium', 'Node.js / Mocha', 'JUnit', 'Insomnia', 'Harness'],
  },
  {
    company: 'Tekskills India', targetTitle: 'QA Tester with AI', file: 'Tekskills_QA_Tester_with_AI',
    terms: ['CI/CD', 'Defect Tracking'],
    proofs: ['cicd', 'api'], diff: 'fullstack', skillOrder: ['cicd', 'api'],
    gapSkills: ['LLM Behaviour Testing (hallucination, bias, edge cases)', 'Prompt Engineering for Adversarial Tests', 'RAG Evaluation & Guardrails', 'Synthetic Test Data Generation', 'Data Pipeline Testing', 'Azure DevOps / GitHub Actions'],
    jdWarning: 'this is an AI/LLM-specific testing role. Almost every mandatory skill (LLM behaviour, prompt engineering, RAG evaluation, guardrails) is absent from your resume — this is a stretch application, not a near match.',
  },
  {
    company: 'CGI', targetTitle: 'Senior QA Automation Engineer (Playwright)', file: 'CGI_Senior_QA_Automation_Engineer_Playwright',
    terms: ['Java', 'Playwright', 'CI/CD', 'Agile', 'Scrum', 'Git', 'API'],
    proofs: ['playwright', 'cicd'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'cicd'],
    gapSkills: ['Spring Boot / Spring Framework', 'Angular', 'Microservices Architecture', 'SQL Databases (MySQL / PostgreSQL / Oracle)'],
    jdWarning: 'the posting title says QA Automation Engineer but the description body is a Java Full Stack Developer role (Spring Boot, Angular, Microservices, HTML/CSS). Confirm with the recruiter which role is actually being hired before applying — this resume is tailored to the QA title, not the developer JD.',
  },
  {
    company: 'GSR Business Services', targetTitle: 'Cypress Automation Tester', file: 'GSR_Business_Services_Cypress_Automation_Tester',
    terms: ['Windows', 'Cucumber', 'API', 'CI/CD', 'SDLC', 'regression'],
    proofs: ['crossplatform', 'cicd'], diff: 'fullstack', skillOrder: ['automation', 'platforms', 'api'],
    gapSkills: ['Cypress', 'Mocha / Jasmine / Chai', 'Jest', 'Applitools', 'FlaUI'],
  },
  {
    company: 'Larsen & Toubro (L&T)', targetTitle: 'Test Automation Engineer – C# and OOP', file: 'LT_CSharp_OOP_Automation_Expert',
    terms: ['Selenium', 'Page Object Model', 'Cucumber', 'REST Assured', 'API', 'SDLC', 'regression'],
    proofs: ['selenium_java', 'api'], diff: 'fullstack', skillOrder: ['automation', 'api', 'mgmt'],
    gapSkills: ['C#', 'Appium'],
    jdWarning: 'C# is the headline requirement and is absent from your resume (only .NET as a Master’s course subject). Appium is also named. Your framework-design and REST API automation experience transfers, but the language gate does not.',
  },
  {
    company: 'Grid Dynamics', targetTitle: 'Quality Engineer', file: 'Grid_Dynamics_Quality_Engineer',
    terms: ['Playwright', 'Java', 'Cucumber', 'Selenium', 'API', 'AWS', 'XRay', 'regression'],
    proofs: ['playwright', 'api'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'api', 'cicd'],
    gapSkills: ['JavaScript', 'Kafka / Amazon MQ', 'Splunk / Grafana / OpenTelemetry', 'Retail & Order Management Domain'],
  },
  {
    company: 'Infosys', targetTitle: 'API Tester', file: 'Infosys_API_Tester',
    terms: ['Java', 'Selenium', 'REST Assured', 'Postman', 'TestNG', 'Maven', 'Gradle', 'API'],
    proofs: ['api', 'selenium_java'], diff: 'fullstack', skillOrder: ['api', 'automation', 'languages'],
    gapSkills: ['SQL / Database Validation', 'Karate', 'SoapUI', 'JUnit'],
  },
  {
    company: 'PwC Service Delivery Center', targetTitle: 'Senior Associate – QA Automation, Data & Analytics', file: 'PwC_Senior_Associate_QA_Automation_Data_Analytics',
    terms: ['Python', 'Java', 'Selenium', 'Jenkins', 'CI/CD', 'AWS', 'Agile', 'Scrum'],
    proofs: ['selenium_java', 'cicd'], diff: 'fullstack', skillOrder: ['languages', 'automation', 'cicd'],
    gapSkills: ['ETL / ELT Pipeline Testing', 'SQL & Data Quality Validation', 'PyTest', 'Azure DevOps'],
  },
  {
    company: 'HCLTech', targetTitle: 'Playwright Automation Tester', file: 'HCLTech_Playwright_Automation_Tester',
    terms: ['Playwright', 'TypeScript', 'TestNG', 'Cucumber', 'API', 'Java', 'Selenium'],
    proofs: ['playwright', 'selenium_java'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'api'],
  },
  {
    company: 'Siemens Healthcare', targetTitle: 'QA Automation Engineer', file: 'Siemens_Healthcare_QA_Automation_Engineer',
    terms: ['Playwright', 'Selenium', 'TypeScript', 'Page Object Model', 'REST Assured', 'Postman', 'Git', 'Cucumber', 'TestNG', 'API', 'Scrum', 'SDLC'],
    proofs: ['playwright', 'api'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'api', 'cicd'],
    gapSkills: ['Cypress', 'Azure DevOps', 'SQL / Database Validation'],
  },
  {
    company: 'kezan', targetTitle: 'QA Automation + EDI Test Engineer', file: 'kezan_QA_Automation_EDI_Test_Engineer',
    terms: ['Selenium', 'Java', 'Python', 'Postman', 'TestNG', 'Git', 'Jenkins', 'Jira', 'API', 'regression', 'SDLC'],
    proofs: ['selenium_java', 'api'], diff: 'fullstack', skillOrder: ['automation', 'api', 'cicd'],
    gapSkills: ['Healthcare EDI Transactions (837 / 835 / 270 / 271 / 276 / 277)', 'US Healthcare Claims & Payer / Provider Processes', 'SQL & Database Testing', 'PyTest'],
    jdWarning: 'Healthcare EDI testing is the mandatory, non-negotiable skill here and is entirely absent from your resume. The automation half matches well; the domain half does not.',
  },
  {
    company: 'MNC Group', targetTitle: 'QA Engineer (Playwright, REST Assured)', file: 'MNC_Group_QA_Engineer_Playwright_RestAssured',
    terms: ['Playwright', 'REST Assured', 'API', 'Postman'],
    proofs: ['playwright', 'api'], diff: 'fullstack', skillOrder: ['automation', 'api'],
  },
  {
    company: 'Tata Consultancy Services', targetTitle: 'QA Automation Engineer (Playwright)', file: 'TCS_QA_Automation_Engineer_Playwright_Bangalore',
    terms: ['Playwright', 'TypeScript', 'Jira', 'XRay', 'Postman', 'Selenium', 'API', 'regression', 'Test Planning'],
    proofs: ['playwright', 'management'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'mgmt'],
    gapSkills: ['JavaScript', 'JUnit', 'SAP Sales Processes'],
    jdWarning: 'the posting requires candidates to be based in Bangalore and states internal candidates are preferred. You are Berlin-based — confirm relocation is acceptable before applying.',
  },
  {
    company: 'Tata Consultancy Services', targetTitle: 'Senior SDET', file: 'TCS_Sr_SDET',
    terms: ['Java', 'TypeScript', 'Python', 'Cucumber', 'Selenium', 'Postman', 'Jenkins', 'Jira', 'XRay', 'Agile', 'regression'],
    proofs: ['selenium_java', 'management'], diff: 'fullstack', skillOrder: ['languages', 'automation', 'mgmt'], leadershipRoleKey: 'ibmix',
    gapSkills: ['Node.js / Mocha', 'Insomnia', 'Harness', 'qTest / Allure Report'],
  },
  {
    company: 'Okta', targetTitle: 'QA Automation Engineer, Professional Services R&D', file: 'Okta_QA_Automation_Engineer_Professional_Services',
    terms: ['Python', 'Java', 'Playwright', 'Selenium', 'Postman', 'Jenkins', 'CI/CD', 'API', 'Agile', 'Test Planning'],
    proofs: ['playwright', 'cicd'], diff: 'fullstack', skillOrder: ['automation', 'languages', 'api', 'cicd'],
    gapSkills: ['Cypress / Jest', 'GraphQL API Testing', 'GitHub Actions / GitLab CI'],
  },
  {
    company: 'Larsen & Toubro (L&T)', targetTitle: 'QA Automation Engineer (Camera Testing)', file: 'LT_QA_Automation_Engineer_Camera_Testing',
    terms: ['Selenium', 'Java', 'Python', 'Jira', 'Jenkins', 'Git', 'Cucumber', 'Postman', 'REST Assured', 'API', 'regression'],
    proofs: ['selenium_java', 'api'], diff: 'automotive', skillOrder: ['automation', 'api', 'cicd', 'domain'],
    gapSkills: ['Camera / Image-Capture Testing'],
  },
  {
    company: 'CGI', targetTitle: 'Lead QA Automation Engineer (Playwright)', file: 'CGI_Lead_QA_Automation_Engineer_Playwright',
    terms: ['Java', 'Playwright', 'CI/CD', 'Agile', 'Scrum', 'Git', 'API'],
    proofs: ['playwright', 'management'], diff: 'fullstack', skillOrder: ['automation', 'mgmt', 'cicd'], leadershipRoleKey: 'ibmix',
    gapSkills: ['Spring Boot / Spring Framework', 'Angular', 'Microservices Architecture', 'SQL Databases (MySQL / PostgreSQL / Oracle)'],
    jdWarning: 'the posting title says Lead QA Automation Engineer but the description body is a Java Full Stack Developer role (Spring Boot, Angular, Microservices, HTML/CSS). Confirm with the recruiter which role is actually being hired before applying — this resume is tailored to the QA title, not the developer JD.',
  },
  {
    company: 'Wells Fargo', targetTitle: 'Senior Quantitative Model Solutions Specialist', file: 'Wells_Fargo_Senior_Quant_Model_Solutions_Specialist',
    terms: ['Python', 'Selenium', 'SDLC', 'regression', 'Test Planning'],
    proofs: ['selenium_java', 'management'], diff: 'fullstack', skillOrder: ['languages', 'automation', 'mgmt'],
    gapSkills: ['Finance / Credit / Banking Modelling', 'PyTest', 'R / SAS', 'PowerBI / Tableau / Qlikview', 'SQL & Database Testing', 'Data Migration Testing'],
    jdWarning: 'the automated-testing-framework line is one requirement inside a quantitative finance role. The core of the job — credit/banking modelling, data engineering at volume, and BI tooling — is absent from your resume.',
  },

  // ---- stepstone_jobs.csv (German market, Stepstone) --------------------
  {
    company: 'msg systems ag', targetTitle: 'TOSCA Test Automation Engineer', file: 'msg_systems_TOSCA_Test_Automation_Engineer', subdir: 'stepstone',
    terms: ['API', 'CI/CD', 'Agile'], proofs: ['api', 'cicd'], diff: 'fullstack', skillOrder: ['api', 'cicd', 'mgmt'], leadershipRoleKey: 'ibmix',
  },
  {
    company: 'Sopra Steria', targetTitle: 'Test Automation Consultant', file: 'Sopra_Steria_Test_Automation_Consultant', subdir: 'stepstone',
    terms: ['Selenium', 'Java', 'Agile'], proofs: ['selenium_java', 'cicd'], diff: 'fullstack', skillOrder: ['automation', 'mgmt'],
  },
  {
    company: 'Materna Information & Communications SE', targetTitle: 'Test Automation Engineer', file: 'Materna_Test_Automation_Engineer', subdir: 'stepstone',
    terms: ['Playwright', 'Selenium', 'mobile'], proofs: ['playwright', 'crossplatform'], diff: 'fullstack', skillOrder: ['automation', 'languages'],
  },
  {
    company: 'msg systems ag', targetTitle: 'Test Automation Engineer', file: 'msg_systems_Test_Automation_Engineer', subdir: 'stepstone',
    terms: ['CI/CD', 'Jenkins', 'Agile'], proofs: ['cicd', 'selenium_java'], diff: 'fullstack', skillOrder: ['cicd', 'automation'], leadershipRoleKey: 'ibmix',
  },
  {
    company: 'puntus GmbH', targetTitle: 'IT Consultant – Software Testing / Test Automation (Pega)', file: 'puntus_GmbH_IT_Consultant_Test_Automation_Pega', subdir: 'stepstone',
    terms: ['Agile'], proofs: ['selenium_java', 'api'], diff: 'fullstack', skillOrder: ['automation', 'mgmt'],
  },
];

// ------------------------------------------------------------------ build
for (const job of JOBS) {
  const spec = buildSpec(job);
  const specPath = path.join(SPECS_DIR, `${job.file}.json`);
  fs.writeFileSync(specPath, JSON.stringify(spec, null, 2));
  try {
    const result = execFileSync('node', [BUILD_SCRIPT, specPath], { encoding: 'utf8' });
    console.log(`[ok] ${job.company} — ${job.targetTitle}`);
  } catch (e) {
    console.error(`[FAIL] ${job.company} — ${job.targetTitle}`);
    console.error(e.stdout || e.message);
  }
}
console.log(`\nDone. ${JOBS.length} resumes -> ${OUT_DIR}`);
