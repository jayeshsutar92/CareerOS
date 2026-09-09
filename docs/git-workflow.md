# Git Workflow & Branching Strategy

This project adheres to a strict feature-branch workflow designed to protect the `main` branch and ensure modular, trackable development. 

## Branch Naming Conventions

All new work must occur on an isolated branch created from `main`.

1.  **Feature Branches**
    -   **Format:** `feature/<feature-name>`
    -   **When to use:** Use this for any net-new functionality, enhancements to existing systems, database schema additions, or new API endpoints.
    -   **Examples:** `feature/social-resolution`, `feature/bulk-email-queue`

2.  **Bugfix Branches**
    -   **Format:** `bugfix/<bug-name>`
    -   **When to use:** Use this for resolving errors, fixing type mismatches, repairing broken API contracts, addressing performance regressions, or fixing failing tests.
    -   **Examples:** `bugfix/queue-progress-types`, `bugfix/duckduckgo-import-error`

## Development Workflow

Follow these steps for all code modifications:

1.  **Checkout `main` & Sync:** Ensure you have the latest code.
    ```bash
    git checkout main
    git pull origin main
    ```
2.  **Create Branch:** Branch off `main` using the appropriate prefix.
    ```bash
    git checkout -b feature/your-feature-name
    ```
3.  **Implement & Commit:** Write your code. Commit frequently and logically with descriptive messages.
    ```bash
    git commit -m "feat: descriptive message"
    ```
4.  **Review:** Open a Pull Request (or equivalent review process).
5.  **Merge & Delete:** Once approved, merge the branch into `main`. The branch should be deleted after a successful merge to keep the repository clean.

---

## Historical Commit Classification

*The following is a classification of past commits for historical reference only. No Git history has been altered or rewritten.*

### 🚀 Features & Enhancements
- `b18135c` feat(discovery): phase 2 - implement website and social resolution
- `be504ab` feat(discovery): phase 1 - implement deterministic entity resolution
- `d168942` Phase 3: Bulk Email Queue implementation
- `4792ad8` Phase 2: Recipient Selection Implementation
- `6c3441f` Phase 1: Template System implementation
- `a5bdf5c` Add hard execution limits to contact discovery: workflow timeout (90s)...
- `aa60aa2` feat: complete administration and data management module
- `6deb1cd` feat: complete workflow with ranked contacts and automated email drafts
- `b712470` feat: user-isolated active lead discovery task tracker

### 🐛 Bug Fixes & Chores
- `d376d2d` Fix : Page.tsx fixed for eslint errors
- `faa7bb1` fix(frontend): resolve import and typescript errors in queue-progress component
- `b73d931` Fix runtime bugs: AttributeError on decode() and incorrect duckduckgo_search import
- `3b9a76f` Other : removed the unwanted files
- `9d8e6aa` Fix Phase E: Improve contact discovery - stop filtering HR emails...
- `ec429a6` Fix Phase D: Ensure email drafts persist with proper logging and rollback
- `878bb40` Phase C: Remove SMTP verification from contact discovery
- `e85d5cf` Fix Phase B: Implement strict user isolation for CompanyIntelligence
- `904f156` refactor: fix company discovery pipeline and missing job_role in request schema
- `1fdfb0e` chore: ignore .agents directory for AI rules
- `1ae651f` fix: dataclass field order in TaskResult
