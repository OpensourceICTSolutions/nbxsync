# Development flow

We use a simple GitFlow-lite:

- **Working branch:** `develop`
- **Release branch:** `main`
- **Feature branches:** branch off `develop`, merge back into `develop`
- **Releases:** done via a PR from `develop` → `main`, then a version tag on `main`

## Daily development

1. Branch from `develop` into a new branch:

    ```bash
    git checkout develop
    git pull origin develop
    git switch -c feature/my-change
    ```

2. Do the work (tests, docs, migrations as needed).
3. Open a PR from your feature branch into develop.
4. CI must pass (lint, tests, coverage ≥ 85%, migrations check).
5. Merge the PR into develop (squash or rebase merges preferred).

   >  Keep your feature branch rebased on develop to avoid drift.

## Preparing a release

1. Open a release PR from develop → main.
2. Ensure CI passes on that PR.
3. Merge the PR into main (squash merge recommended).
4. Tag the merge commit on main with the new version (see RELEASE.md).

   > Tagging triggers CI on the tag. The release workflow will run only after that CI succeeds and verifies the tag came from a merged PR to main.

## Hotfixes

For urgent production fixes:

1. Branch from main, implement fix, open PR → main.
2. After merge, tag and release (see RELEASE.md).
3. Back-merge or cherry-pick the fix into develop to keep branches in sync.

## Conventions

- Keep PR titles meaningful (Conventional Commits encouraged) for clean release notes.
- No direct pushes to develop or main (branch protections enforced).
