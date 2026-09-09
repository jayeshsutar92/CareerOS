# CareerOS — Discovery Engine Architecture Review & Production Pipeline Design

## 1. Root-Cause Analysis

Every bottleneck listed in Section 6 of your context — wrong websites, wrong social profiles, unreliable emails, rate-limiting — traces back to **one structural mistake repeated at every stage**: the pipeline treats "the first plausible search result" as "the verified answer." There is no separation between *finding candidates* and *confirming identity*, and no scoring layer in between. This single pattern explains nearly all observed failures:

- **"Official website = top search result"** — the top result for a company name is frequently a directory (Crunchbase, LinkedIn company page, Glassdoor, a news article) or a same-named company in a different city/industry. Search ranking optimizes for relevance-to-query, not identity-match-to-entity — these are different problems.
- **"Social profiles via keyword search"** — `"Company Name LinkedIn"` returns the same category of noise: employee personal profiles, similarly-named companies, fan pages. Nothing cross-checks the result against known facts about the actual company (location, domain, industry).
- **"Regex email extraction"** — regex finds *any* email-shaped string on a page; it can't tell a real recruiter's email from a stale example, a support alias, or a competitor's email quoted in a blog comment. There's no verification that the mailbox is real or belongs to a person with a relevant role.
- **Rate limiting (403/429)** — a direct consequence of having no caching/dedup discipline between candidate generation calls; every discovery run re-queries search engines from scratch even for companies seen before.

The fix is the same architectural pattern in every domain (websites, socials, emails): **generate multiple candidates deterministically → score them against structured evidence → only then let AI adjudicate the top few → apply a final confidence gate that can output "not found" instead of guessing.** Below is that pipeline applied end-to-end to your specific workflow.

---

## 2. Proposed Pipeline — High-Level Flow

```
┌──────────────┐    ┌───────────────────┐    ┌────────────────────┐    ┌──────────────────┐
│ 1. Company      │   │ 2. Company Entity   │   │ 3. Website           │   │ 4. Social Profile   │
│    Discovery     │→ │    Resolution        │→ │    Resolution         │→ │    Resolution        │
│  (search, as-is) │   │ (dedup + core facts) │   │ (candidates+scoring) │   │ (per-platform,       │
│                  │   │                     │   │    +AI adjudication) │   │  candidates+scoring) │
└──────────────┘    └───────────────────┘    └────────────────────┘    └──────────────────┘
                                                                                    │
        ┌───────────────────────────────────────────────────────────────────────────┘
        ▼
┌──────────────┐    ┌───────────────────┐    ┌────────────────────┐    ┌──────────────────┐
│ 5. Careers Page  │   │ 6. Contact           │   │ 7. Email             │   │ 8. Structured        │
│    Location       │→ │    Discovery          │→ │    Discovery &        │→ │    Output +           │
│ (site crawl,       │   │ (page parse + role   │   │    Verification       │   │    Confidence Scores  │
│  deterministic)    │   │  classification)     │   │ (pattern + SMTP check)│   │                       │
└──────────────┘    └───────────────────┘    └────────────────────┘    └──────────────────┘
```

Every arrow above represents a **hard contract**: a stage only receives a scored, structured object from the previous one — never raw HTML, never a raw search-result list. This is what your current pipeline is missing.

---

## 3. Stage-by-Stage Design

### Stage 1 — Company Discovery (mostly unchanged)
**Keep your existing search-based discovery.** The input is Job Role + City + Work Mode; this stage's job is recall, not precision — casting a reasonably wide net is fine here since the accuracy problem lives downstream.

Additions (deterministic, cheap):
- Normalize company names at ingestion: strip legal suffixes (`Inc.`, `Pvt Ltd`, `LLC`), lowercase, collapse whitespace — store both the raw and normalized name. This single step prevents a large fraction of duplicate-entity bugs later (e.g. "Acme Corp" vs "Acme Corporation" being treated as different companies).
- Deduplicate against existing `Companies` table using normalized-name + city before creating a new row, to avoid re-running the entire downstream pipeline for a company you've already resolved. Cache the "already resolved" check as a fast Postgres lookup — no new infra needed.

### Stage 2 — Company Entity Resolution (NEW, deterministic, no AI)
This stage doesn't exist in your current pipeline and is the most important addition. Before searching for a website, establish a **structured identity record** for the company from what you already know:
- Name (raw + normalized), City, industry/domain hints from the job posting itself (job description text often names the industry, tech stack, or parent company — cheap free signal, already in hand from Stage 1).
- If two discovered "companies" normalize to the same name + city, merge them at this point (canonical resolution) rather than letting duplicates flow downstream and get resolved twice, wasting AI calls later.

This identity record — not the raw company name string — is what every later stage will score candidates against. This is the anchor that fixes "similarly named entity" confusion: a same-named company in a different city or industry will score poorly against *this specific* identity record, even though it would win a plain keyword search.

### Stage 3 — Website Resolution (candidate generation → deterministic scoring → single AI adjudication call)

**3a. Candidate generation (deterministic):**
Run a small fixed set of search query variants — not one:
- `"{company_name}" {city} official site`
- `"{company_name}" careers`
- `{company_name_slug}.com` / `.in` / common regional TLDs as direct probes (cheap HTTP HEAD requests, no AI, no search engine call)

Collect top-K (e.g. 5) results. Discard known non-candidates via a static blocklist — directories, aggregators (Crunchbase, ZoomInfo, Glassdoor, LinkedIn company pages, Indeed, Google Maps listings) are *never* the official website and should never reach scoring, let alone AI. This blocklist is free to build and maintain and eliminates a large share of your "wrong domain" failures immediately.

**3b. Deterministic scoring (no AI):**
For each surviving candidate domain, compute a structured evidence object:
- `name_token_match`: fuzzy match between company name tokens and domain name / page `<title>`.
- `city_mentioned`: does the homepage or About/Contact page mention the target city or a matching address?
- `industry_keyword_overlap`: does page content overlap with industry/domain hints from Stage 2?
- `careers_link_present`: does the site have an internal careers/jobs link? (a positive signal it's a real operating company site, not a placeholder or parked domain)

**3c. AI adjudication (single gpt-oss/Groq call, only if needed):**
- If the top candidate's score clears a high threshold with a clear margin over the second — auto-accept, skip AI entirely (this is your primary cost-saver, since most well-known companies will resolve deterministically).
- Otherwise, send the **top 2–3 scored candidates** (structured evidence, not raw HTML) to gpt-oss with an explicit instruction: pick exactly one, or return `NONE` if ambiguous — never force a guess. Require a short justification field referencing the evidence, for auditability.
- **Trade-off:** this two-tier design (deterministic-first, AI-only-on-ambiguity) trades a small amount of AI reasoning power for a large reduction in call volume and — more importantly — removes AI from the easy cases where it's most likely to be lazily overconfident. AI is reserved for genuinely hard disambiguation, which is what it's actually good at.

### Stage 4 — Social Profile Resolution (per-platform, same pattern as Stage 3)

This directly targets your "Failed Social Identity Resolution" bottleneck.

**4a. Candidate generation:** per platform (LinkedIn, Facebook, Instagram, X, YouTube), generate multiple query variants using the *now-known official website domain* from Stage 3 as an anchor:
- `site:linkedin.com/company "{company_name}"`
- Cross-check: many company websites link to their own social profiles in the footer/header — **crawl the verified website's footer and header links first**, before falling back to search. This is a free, high-precision signal that's currently unused, and it directly solves the "employee personal profile vs. official page" confusion, since a link *from the verified official site* is far stronger evidence than a keyword search hit.
- Only fall back to platform-specific search queries if the website doesn't expose the social links directly.

**4b. Deterministic scoring:**
- `linked_from_official_site`: boolean, highest-weight signal — if the verified website itself links to this profile, that's near-certain confirmation.
- `name_similarity`: profile display-name vs. company name.
- `location/industry match`: if the platform snippet exposes an "About"/location field.
- `account_type_signal`: LinkedIn/Facebook expose "Company Page" vs. personal profile in metadata/snippets — filter personal profiles out deterministically, never send them to AI.

**4c. AI adjudication:** same pattern as website resolution — only invoked when no candidate has an outright dominant score (e.g. no `linked_from_official_site` hit and multiple ambiguous keyword-search candidates). Batch all platforms for one company into a single Groq call when several are ambiguous simultaneously, to reduce round-trips.

**Trade-off:** relying primarily on "linked from official website" as the strongest signal means companies with a poorly maintained website (no footer social links) will fall back to weaker search-based candidates more often. This is acceptable and consistent with your stated priority — those cases should more often resolve to `UNVERIFIED` rather than guessed, not get a lower-quality forced answer.

### Stage 5 — Careers/Jobs Page Location (mostly unchanged, deterministic)
Keep your existing crawl-for-keywords approach — it's already appropriately deterministic and doesn't need AI. One addition: once found, verify the careers page is *reachable from* the verified official domain (Stage 3 output), not from an unrelated domain that happened to match a keyword search — this prevents rare cases where a directory site with a "/careers" URL gets mistaken for the actual company's careers page.

### Stage 6 — Contact Discovery (HR/Recruiter/TA identification)
This stage should crawl **only pages reachable from the verified website/careers page** — never independent web search for "person name at company," which is where most hallucination risk lives.

- Parse team/about/careers pages for name + role text pairs (existing approach, keep it).
- Add a **deterministic role classifier** (no AI needed): a maintained keyword list mapping title text to role categories — `"Talent Acquisition"`, `"Recruiter"`, `"HR"`, `"People Ops"`, `"Hiring Manager"` vs. exclude obviously irrelevant titles. This is a static dictionary/regex job, not something to spend an LLM call on.
- Only when title text is genuinely ambiguous (doesn't match any keyword pattern but appears near hiring-related content) escalate to a single batched AI call classifying a *list* of ambiguous title strings at once — batch, don't call per-contact.

### Stage 7 — Email Discovery & Verification
This is where "hallucinates or extracts invalid contacts" needs the most structural fix. Split into two sub-steps that your current pipeline conflates:

**7a. Candidate generation (pattern-based, deterministic — free):**
- If a real email is found directly on a page (regex, as today) — that's a direct-evidence candidate, highest confidence tier.
- If no direct email is found for a named contact but the verified domain is known, generate **pattern-guess candidates** using common corporate conventions (`first.last@domain`, `firstlast@domain`, `flast@domain`, etc.) — but these must be clearly tagged as *inferred*, never presented with the same confidence as a directly-scraped email.

**7b. Verification (deterministic, free, no paid API required):**
- **MX record check** on the domain (free DNS lookup) — confirms the domain accepts mail at all; instantly discard candidates for domains with no MX record.
- **SMTP RCPT-TO probe** (connect to the mail server, issue `MAIL FROM`/`RCPT TO`, read the server's accept/reject response, then disconnect without sending) — this is a long-standing, free, no-API-key technique for checking mailbox existence without sending an email. **Caveat/trade-off:** many mail providers (notably Gmail/Google Workspace, Outlook/Microsoft 365) intentionally return ambiguous "accept-all" responses to this probe as an anti-enumeration measure, so it works reliably for smaller companies on standalone mail servers but degrades to "inconclusive" for large orgs on major providers. Treat SMTP verification as a *confidence booster when conclusive*, not a hard requirement — a directly-scraped email with a valid MX record but an inconclusive SMTP check should still rank higher than a pattern-guessed email, and should be labeled accordingly in the confidence score rather than silently upgraded.
- Never present a **pattern-guessed** email as "verified" — only directly-scraped emails that additionally pass MX+SMTP checks should carry the highest confidence tier; pattern-guessed emails, even if SMTP-plausible, should be labeled as a lower tier ("plausible, unconfirmed") so outreach users can make an informed choice, consistent with your "accuracy over quantity" priority.

### Stage 8 — Structured Output & Confidence Scoring
Every entity (website, each social platform, each contact, each email) carries forward its full evidence trail and final confidence tier, e.g.:
`VERIFIED_HIGH | VERIFIED_MEDIUM | PLAUSIBLE_UNCONFIRMED | UNVERIFIED | REJECTED`
with the source URLs and scoring rationale stored alongside — this satisfies transparency requirements and gives users (and future tuning work) a concrete audit trail instead of an opaque boolean.

---

## 4. Fallback Strategy (per stage)

| Stage | Preferred Source | Fallback 1 | Fallback 2 | Final Fallback |
|---|---|---|---|---|
| Website | Direct TLD probe + search candidates, scored | AI adjudication on ambiguous top candidates | — | `UNVERIFIED`, retry later via worker queue |
| Social | Verified website's own footer/header links | Platform-specific search candidates, scored | AI adjudication on ambiguous candidates | `UNVERIFIED` per platform |
| Careers page | Crawl verified website for keyword links | Search `site:{domain} careers` | — | `UNVERIFIED`, contact discovery skipped for this company |
| Contacts | Parse team/careers pages, deterministic role classifier | Batched AI classification for ambiguous titles only | — | Company flagged "no contacts found" |
| Emails | Directly scraped + MX/SMTP verified | Directly scraped + MX-only (SMTP inconclusive) | Pattern-guessed + MX/SMTP plausible | Pattern-guessed, unconfirmed — clearly labeled, never silently upgraded |

Each fallback tier is a **lower confidence label**, never a silent substitution — this is the core discipline that turns "sometimes wrong" into "honestly ranked."

---

## 5. Caching, Dedup & Rate-Limit Handling (Redis — reuse existing infra)

Your existing Redis worker/task system already has retries, dead-letter queuing, and delayed scheduling — reuse it directly for all of the above; no new task infrastructure needed. Add these cache key patterns:

| Key | Content | Scope | TTL | Purpose |
|---|---|---|---|---|
| `company:resolved:{normalized_name}:{city}` | Canonical company ID | Global | 90d | Avoid re-resolving identity for companies seen before |
| `website:candidates:{company_hash}` | Raw Stage 3a candidate list | Global | 14d | Avoid repeat search-engine calls |
| `website:decision:{company_hash}` | Final website resolution + evidence | Global | 90d | Reuse across users targeting the same company |
| `social:candidates:{platform}:{company_hash}` | Raw Stage 4a candidates | Global | 14d | Same as above, per platform |
| `ai_decision:{evidence_hash}` | Cached AI adjudication JSON | Global | 30d | Skip Groq call for identical evidence sets |
| `mx_check:{domain}` | MX record result | Global | 7d | Avoid repeat DNS lookups |

**Multi-tenant note:** all of the above key on *company identity evidence*, which is not user-owned — many users will independently discover the same real companies (e.g. two users both job-hunting in the same city/role), so global caching here is both safe (no cross-tenant data leakage — only *which contacts a user chose to email* is tenant-scoped, and that stays in your existing per-`user_id` tables untouched) and a major cost/rate-limit reducer, since the second user's discovery run for an already-resolved company hits cache instead of search engines or AI.

**Rate-limit handling:** because candidate generation and website/social probing are now deduplicated via cache and gated by scoring (many resolve without ever reaching AI or without needing a full fresh search), overall external call volume drops substantially versus today's "search from scratch every time" pattern — this is your primary fix for the 403/429 issue, more so than any single retry/backoff tweak. Layer standard exponential backoff + your existing worker retry/dead-letter mechanism on top for the calls that do go out, exactly as you likely already do elsewhere in the worker system.

---

## 6. Data Model Changes (additive, no rewrite)

- Add a confidence/status enum (as in Section 8) to Website, SocialProfile, Contact, and Email records, replacing implicit null/boolean handling.
- Add an `evidence_log` JSONB column (or related table) to each of those, storing candidate list, scores, and AI justification when applicable — this is your audit trail and future tuning dataset.
- Add `evidence_hash` columns for AI-decision cache keys as described above.
- Everything else — Users, Companies (core columns), Templates, Resumes, Portfolios, the outreach queue, and all existing multi-tenant `user_id` scoping — **stays untouched.**

---

## 7. What Stays Untouched vs. What Changes

**Untouched:**
- FastAPI, PostgreSQL (schema is extended, not restructured), Redis, the custom worker/task system (retries, dead-letter, scheduling, progress polling).
- Frontend, dashboards, state management.
- Bulk email queuing/processing mechanism.
- AI context aggregation for personalized outreach content generation.
- gpt-oss via GroqCloud as the sole AI provider — AI's *role* changes (adjudication over pre-scored evidence instead of raw judgment calls), but the provider/model does not.

**Changes (additive refactor of discovery flow only):**
- Insertion of an explicit Entity Resolution stage (Stage 2) that doesn't currently exist.
- Website/social resolution split into candidate-generation → deterministic-scoring → conditional-AI-adjudication, instead of "top search result = answer."
- New deterministic role classifier for contacts (mostly removing reliance on ad hoc parsing).
- New MX/SMTP verification step for emails, with a formal confidence tiering instead of a flat "found it" boolean.
- New Redis cache key patterns layered onto your existing Redis usage (no new Redis instance, no new broker).
- Schema additions: status enums + evidence_log columns.

---

## 8. Trade-offs Summary

- **Two-tier deterministic-then-AI scoring** (websites/socials): reduces AI calls and false positives, at the cost of needing to build and maintain blocklists, scoring weight tables, and query-variant templates — genuine engineering work, but all free/open-source and one-time.
- **"Linked from official website" as primary social signal**: very high precision when available, but leaves companies with sparse websites more often `UNVERIFIED` rather than guessed — intentional, aligned with your stated priority.
- **SMTP verification**: free and useful as a confidence booster, but inconclusive against major mail providers' anti-enumeration behavior — must be treated as one signal among several, not a hard pass/fail gate, or you'll systematically underrate legitimate contacts at large companies.
- **Global (cross-tenant) caching of company evidence**: substantial cost/rate-limit win, but requires discipline to ensure no user-specific data (which contacts a user emailed, template choices, etc.) ever enters these cache keys — worth stating explicitly in code review guidelines when this is implemented.
- **Optional/paid alternatives** (mentioned only as opt-in, not required): a paid email-verification API (e.g. a bulk SMTP-verification service) could replace the free MX/SMTP probe for higher throughput at scale, and a paid company-data API could serve as an additional evidence source for Stage 2/3 scoring — both are **strictly optional enhancements**, not required for the design above to work, and the free approach should remain the default/fallback either way.

---

## 9. Suggested Implementation Phasing (design-only)

1. **Phase A:** Add status enums + evidence_log schema; introduce Stage 2 (Entity Resolution) and the deterministic blocklist for websites. Immediate reduction in wrong-domain matches without touching AI.
2. **Phase B:** Rebuild website candidate generation (multi-query + TLD probing) and deterministic scoring (Stage 3a/3b); wire AI adjudication (3c) only for ambiguous cases.
3. **Phase C:** Rebuild social resolution using verified-website-link-crawling as the primary signal (Stage 4), with search-based candidates as fallback.
4. **Phase D:** Add deterministic role classifier for contacts; restrict contact/email crawling to pages reachable from the verified website only.
5. **Phase E:** Add MX/SMTP email verification and confidence tiering for emails.
6. **Phase F:** Layer in the Redis caching patterns and cross-tenant dedup once the above stages are stable and evidence_log has real data to validate scoring weights against.

This order front-loads the changes with the highest accuracy impact per unit of effort (killing obviously-wrong domains and directory matches) before moving to the more nuanced signal-engineering work (socials, emails), and defers the caching/performance layer until the scoring logic itself is proven correct.
