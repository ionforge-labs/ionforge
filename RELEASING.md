# Releasing

`ionforge` is published to [PyPI](https://pypi.org/project/ionforge/). Releases are
automated: publishing a GitHub Release builds the distributions, runs the full
test suite, and uploads to PyPI via
[trusted publishing](https://docs.pypi.org/trusted-publishers/) (no API tokens
stored in the repo).

## Cutting a release

1. Bump the version in `pyproject.toml` (`[project].version`).
2. Refresh the lockfile so it records the new version:

   ```bash
   uv lock
   ```

3. Commit the changes, tag the release, and push:

   ```bash
   git commit -am "chore: bump version to X.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

4. Draft and publish a [GitHub Release](https://github.com/ionforge-labs/ionforge/releases/new)
   for the `vX.Y.Z` tag.

Publishing the Release triggers `.github/workflows/release.yml`, which:

- runs lint, `ruff format --check`, typecheck, and the full test suite,
- verifies the release tag matches the version in `pyproject.toml`
  (tag and version are normalized with `packaging.version` so the check
  is PEP 440-aware, and the build fails loudly on a mismatch),
- builds the sdist and wheel with `uv build`, and
- publishes to PyPI through the `pypi` environment.

Publishing uses `skip-existing`, so re-firing a release event (or replaying a
run) is idempotent: any distribution already present on PyPI is left untouched
instead of failing the job on a 409.

To validate the build without publishing, trigger the workflow manually
(`workflow_dispatch`) from the Actions tab. Manual runs build and test only;
the publish job is skipped.

## One-time PyPI setup

Trusted publishing must be registered once on PyPI before the first automated
release. On the project's
[publishing settings](https://pypi.org/manage/project/ionforge/settings/publishing/),
add a GitHub Actions publisher with:

| Field             | Value          |
| ----------------- | -------------- |
| Owner             | `ionforge-labs` |
| Repository        | `ionforge`     |
| Workflow name     | `release.yml`  |
| Environment name  | `pypi`         |

The matching `pypi` environment should also exist in the GitHub repository
settings, where manual approval reviewers can be added to gate publishes.
