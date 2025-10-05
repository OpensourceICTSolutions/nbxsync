# Release flow

Releases are created from **`main`** after merging the **release PR** from `develop`.
The release workflow is triggered by a successful run of the **CI** workflow (`workflow_run`) for a **tag**. CI also runs on every commit and on tags.

> The release will only proceed if:
>
> 1) CI for the tag finished with **success**, and  
> 2) The tagged commit is on `main` **and** is associated with a **merged PR into `main`** (enforced by the `gate` job).

---

## 1) Create the release PR

1. Open a PR from **`develop` → `main`**.
2. Ensure CI passes.
3. Merge the PR into `main`.

> This guarantees the release contains exactly what was reviewed and tested on `develop`.

---

## 2) Tag the release on `main`

From a clean working tree, tag the **merge commit on `main`**:

```bash
git checkout main
git pull origin main

# Create an annotated tag
# Stable:
git tag -a 1.4.0 -m "Release 1.4.0"

# Pre-releases:
git tag -a 1.4.0a1 -m "Alpha 1 for 1.4.0"
git tag -a 1.4.0b1 -m "Beta 1 for 1.4.0"
git tag -a 1.4.0rc1 -m "RC 1 for 1.4.0"

git push origin 1.4.0
# or: git push origin 1.4.0rc1
```

### Notes

> Tag formats accepted by the workflow:
>
> X.Y.Z, X.Y.ZaN, X.Y.ZbN, X.Y.ZrcN (e.g., 1.2.3, 1.2.3a1, 1.2.3b2,
> 1.2.3rc1)
>
> Do not prefix with v (i.e., v1.2.3 will not trigger).

## 3) What happens automatically

1. CI runs on the tag (tests, lint, coverage, migrations).
2. After CI completes successfully, the release workflow starts (workflow_run):

   - Gate: verifies the tag’s commit is contained in main and came from a merged PR → main.
   - Details: extracts the version from the tag.
   - PyPI check: ensures the new version is greater than the latest on PyPI.
   - Build: sets Poetry project version from the tag, installs deps, builds sdist and wheel.
   - Publish: uploads to PyPI (Trusted Publishing/OIDC).
   - GitHub Release: creates a release for the tag, attaches artifacts, auto-generates notes.

Poetry version is set by the pipeline; you don’t change pyproject.toml manually.

## 4) Verifying the release

1) PyPI: new version of nbxsync is visible.
2) GitHub → Releases: new release exists with artifacts and generated notes.

## 5) Hotfix releases

1) Branch from main, implement fix, PR → main.
2) Merge after CI passes.
3) Tag a new patch version (e.g., 1.4.1) on main and push.
4) Release runs automatically as above.
5) Back-merge/cherry-pick into develop.

## 6) When a release is skipped

- Tag wasn’t on main or wasn’t from a merged PR → main.
- CI for the tag didn’t finish successfully.
- The tagged version isn’t greater than the latest on PyPI.
- Tag format doesn’t match the accepted patterns.
