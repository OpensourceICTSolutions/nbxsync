# Development flow

We use a simple GitFlow-lite:

- **Working branch:** `development`
- **Release branch:** `main`
- **Feature branches:** branch off `development`, merge back into `development`
- **Releases:** done via a PR from `development` → `main`, then a version tag on `main`

## Daily development

1. Branch from `development` into a new branch:

    ```bash
    git checkout development
    git pull origin development
    git switch -c feature/my-change
    ```

2. Do the work (tests, docs, migrations as needed).
3. Open a PR from your feature branch into development.
4. CI must pass (lint, tests, coverage ≥ 85%, migrations check).
5. Merge the PR into development (squash or rebase merges preferred).

   >  Keep your feature branch rebased on development to avoid drift.

## Preparing a release

1. Open a release PR from development → main.
2. Ensure CI passes on that PR.
3. Merge the PR into main (squash merge recommended).
4. Tag the merge commit on main with the new version (see RELEASE.md).

   > Tagging triggers CI on the tag. The release workflow will run only after that CI succeeds and verifies the tag came from a merged PR to main.

## Hotfixes

For urgent production fixes:

1. Branch from main, implement fix, open PR → main.
2. After merge, tag and release (see RELEASE.md).
3. Back-merge or cherry-pick the fix into development to keep branches in sync.

## Conventions

- Keep PR titles meaningful (Conventional Commits encouraged) for clean release notes.
- No direct pushes to development or main (branch protections enforced).
