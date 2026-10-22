# Per-Plugin Semantic Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate per-plugin versioning in `mpilhlt/pte-plugins` so that a Conventional Commit scoped to a plugin id (e.g. `fix(archival-edition): ...`) automatically bumps that plugin's version, commits the bump, and pushes a `<plugin-id>-v<version>` tag — which the existing `.github/workflows/release.yml` already turns into a wheel + GitHub release.

**Architecture:** A new `.github/workflows/semantic-release.yml` runs on every push to `main`. In one job it loops sequentially over every plugin listed in `pte-plugins.json` and runs `npx semantic-release` once per plugin (env `PLUGIN_ID`/`PLUGIN_PATH` select the plugin). A single `release.config.js` reads those env vars to set `tagFormat` and wires in a new local plugin, `scripts/release/scoped-release-plugin.js`, which filters commits to only those whose Conventional-Commits `scope` equals `PLUGIN_ID` before delegating to the real `@semantic-release/commit-analyzer` / `@semantic-release/release-notes-generator`. `@semantic-release/exec` bumps the plugin's `pte-plugin.json` version (via a new `scripts/bump_plugin_version.py`) and regenerates `pte-plugins.json`; `@semantic-release/git` commits both files; semantic-release's core then tags and pushes. No `@semantic-release/github` plugin is used, so `release.yml` remains the sole creator of GitHub releases/wheels.

**Tech Stack:** Node 24 / ESM (`package.json` already has `"type": "module"`), `semantic-release` + official plugins (`commit-analyzer`, `release-notes-generator`, `exec`, `git`), `conventional-commits-parser` (already a transitive dep of the above; added directly for the scope filter), Python 3 stdlib (`tomllib`, `json`) for the version-bump script, GitHub Actions.

**Spec:** This document (the design was agreed in conversation; no separate spec file exists). Key agreed facts carried from that conversation:
- Standard Angular mapping: `fix` → patch, `feat` → minor, `BREAKING CHANGE:` footer → major.
- Fully automatic on every push to `main`, no manual approval gate.
- A one-time tag backfill was planned and approved, but turned out to be already done: every plugin in `pte-plugins.json` already has a `<plugin-id>-v<version>` tag (and GitHub release) matching its current manifest version — verified via `git ls-remote --tags origin` and `gh release list`. Task 5 below only confirms this invariant; it does not push anything.

## Global Constraints

- Node: `>=24` (per `package.json` `engines`).
- Do not modify `.github/workflows/release.yml` or `scripts/release_plugin.py` — they are unchanged consumers of the tags this work produces.
- The plugin loop must iterate over the plugins listed in `pte-plugins.json` (18 entries today), **not** over `plugins/*/` directories — `plugins/inference-endpoints` has no `pyproject.toml` and is intentionally excluded from the index/build.
- `pte-plugin.json` is the single source of a plugin's version (consumed by `hatchling` via `pyproject.toml`'s `[tool.hatch.version]`); any version bump must go through this file.
- Version-bump commits must include `[skip ci]` so they do not re-trigger this workflow (GitHub Actions natively skips workflow runs for pushes whose head commit message contains `[skip ci]`).
- `python3` is used directly (no `uv`) for `scripts/bump_plugin_version.py`, matching the existing `release.yml` pattern of calling `scripts/release_plugin.py` with plain `python3` — this script only needs the stdlib.

## Review Focus

- An unscoped commit (e.g. `chore: update deps`, `docs: fix typo`) must not trigger a release for any plugin. (Task 2 test: commit with `scope: null`.)
- A commit scoped to one plugin must never be attributed to a different plugin, including one whose id is a prefix/suffix of another (e.g. a hypothetical `grobid` vs `grobid-extra`). (Task 2 test: exact-match / no-substring-match assertions.)
- Bumping a plugin's version must not corrupt or drop other fields already in its `pte-plugin.json` (e.g. `readme`, `engines`), and must preserve the trailing-newline, 2-space-indent formatting the rest of the repo uses. (Task 1 test.)
- A plugin with zero qualifying commits since its last tag must produce no release (no commit, no tag, no error) when its `semantic-release` invocation runs in the loop — this is standard `semantic-release` behavior, verified via the dry-run smoke check in Task 3 rather than a new unit test.
- Before the new workflow is live, every currently-indexed plugin must have a backfilled tag matching its current manifest version exactly, or its first real release could compute the wrong next version. (Task 5 verification step checks tag-vs-manifest-version equality for all 18 plugins.)

---

### Task 1: Plugin version bump script

**Files:**
- Create: `scripts/bump_plugin_version.py`
- Test: `tests/test_bump_plugin_version.py`

**Interfaces:**
- Produces: `manifest_path(plugin_dir: Path) -> Path` and `bump_version(plugin_dir: Path, version: str) -> None` in `scripts/bump_plugin_version.py`; CLI `python3 scripts/bump_plugin_version.py <plugin-path> <version>` (mirrors the usage-docstring style of `scripts/release_plugin.py`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_bump_plugin_version.py
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bump_plugin_version", REPO_ROOT / "scripts" / "bump_plugin_version.py")
assert spec is not None and spec.loader is not None
bump_plugin_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bump_plugin_version)


class TestBumpPluginVersion(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin_dir = Path(self.tmp.name) / "plugins" / "demo"
        module_dir = self.plugin_dir / "src" / "pte_plugin_demo"
        module_dir.mkdir(parents=True)
        (self.plugin_dir / "pyproject.toml").write_text(
            '[project]\nname = "pte-plugin-demo"\n'
            '[project.entry-points."pte.plugins"]\ndemo = "pte_plugin_demo"\n',
            encoding="utf-8",
        )
        (module_dir / "pte-plugin.json").write_text(
            json.dumps({"version": "1.0.0", "readme": "https://example.com", "engines": {"pte": ">=0.76.0"}}, indent=2) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_bump_version_updates_version_field(self):
        bump_plugin_version.bump_version(self.plugin_dir, "1.1.0")
        manifest = json.loads((self.plugin_dir / "src" / "pte_plugin_demo" / "pte-plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "1.1.0")

    def test_bump_version_preserves_other_fields_and_formatting(self):
        bump_plugin_version.bump_version(self.plugin_dir, "1.1.0")
        text = (self.plugin_dir / "src" / "pte_plugin_demo" / "pte-plugin.json").read_text(encoding="utf-8")
        manifest = json.loads(text)
        self.assertEqual(manifest["readme"], "https://example.com")
        self.assertEqual(manifest["engines"], {"pte": ">=0.76.0"})
        self.assertTrue(text.endswith("}\n"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/test_bump_plugin_version.py -v`
Expected: FAIL (`scripts/bump_plugin_version.py` does not exist / has no `bump_version`)

- [ ] **Step 3: Implement `scripts/bump_plugin_version.py`**

Mirror the docstring/CLI style of `scripts/release_plugin.py`: a module docstring explaining purpose and usage, `manifest_path()` reads `pyproject.toml` with `tomllib`, pulls the single `[project.entry-points."pte.plugins"]` value as the module name, and returns `plugin_dir / "src" / module / "pte-plugin.json"`. `bump_version()` loads that file as JSON, sets `manifest["version"] = version`, and writes it back with `json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"`. A `main()` parses `sys.argv` (`plugin_dir`, `version`), calls `bump_version`, and the usual `if __name__ == "__main__": sys.exit(main())` footer.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run python -m pytest tests/test_bump_plugin_version.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/bump_plugin_version.py tests/test_bump_plugin_version.py
git commit -m "feat: add script to bump a plugin's manifest version"
```

---

### Task 2: Scope-filtering semantic-release plugin

**Files:**
- Create: `scripts/release/scoped-release-plugin.js`
- Create: `scripts/release/tests/scoped-release-plugin.test.js`
- Modify: `package.json:7` (the `"test"` script glob)

**Interfaces:**
- Consumes: none from Task 1.
- Produces: named exports `filterByScope(commits: {message: string}[], pluginId: string) -> {message: string}[]`, `analyzeCommits(pluginConfig, context)`, `generateNotes(pluginConfig, context)` from `scripts/release/scoped-release-plugin.js`. `analyzeCommits`/`generateNotes` read `process.env.PLUGIN_ID`, filter `context.commits` with `filterByScope`, and delegate to `@semantic-release/commit-analyzer`'s `analyzeCommits` / `@semantic-release/release-notes-generator`'s `generateNotes` respectively with the filtered commits spliced into `context`.

- [ ] **Step 1: Install the new devDependencies**

Run: `npm install -D @semantic-release/commit-analyzer @semantic-release/release-notes-generator conventional-commits-parser`

- [ ] **Step 2: Write the failing test for `filterByScope`**

```javascript
// scripts/release/tests/scoped-release-plugin.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterByScope } from '../scoped-release-plugin.js';

test('keeps only commits whose scope matches the plugin id', () => {
  const commits = [
    { message: 'fix(archival-edition): handle broken pb sync' },
    { message: 'feat(grobid): add retry' },
  ];
  assert.deepEqual(filterByScope(commits, 'archival-edition'), [commits[0]]);
});

test('drops unscoped commits', () => {
  const commits = [{ message: 'chore: update deps' }];
  assert.deepEqual(filterByScope(commits, 'archival-edition'), []);
});

test('does not match on scope substrings', () => {
  const commits = [
    { message: 'fix(grobid-extra): tweak' },
    { message: 'fix(grobid): tweak' },
  ];
  assert.deepEqual(filterByScope(commits, 'grobid'), [commits[1]]);
});

test('returns an empty array when nothing matches', () => {
  assert.deepEqual(filterByScope([{ message: 'fix(other): x' }], 'archival-edition'), []);
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `node --test --experimental-test-module-mocks --disable-warning=ExperimentalWarning "scripts/release/tests/*.test.js"`
Expected: FAIL (`scoped-release-plugin.js` does not exist)

- [ ] **Step 4: Implement `scripts/release/scoped-release-plugin.js`**

```javascript
import { CommitParser } from 'conventional-commits-parser';
import * as commitAnalyzer from '@semantic-release/commit-analyzer';
import * as releaseNotesGenerator from '@semantic-release/release-notes-generator';

const parser = new CommitParser();

export function filterByScope(commits, pluginId) {
  return commits.filter((commit) => parser.parse(commit.message).scope === pluginId);
}

function requirePluginId() {
  const pluginId = process.env.PLUGIN_ID;
  if (!pluginId) throw new Error('PLUGIN_ID environment variable is required');
  return pluginId;
}

export async function analyzeCommits(pluginConfig, context) {
  const commits = filterByScope(context.commits, requirePluginId());
  return commitAnalyzer.analyzeCommits(pluginConfig, { ...context, commits });
}

export async function generateNotes(pluginConfig, context) {
  const commits = filterByScope(context.commits, requirePluginId());
  return releaseNotesGenerator.generateNotes(pluginConfig, { ...context, commits });
}
```

(Signature and behavior are fixed by the test and by the `Interfaces` block above; this is a direct transcription, not a design choice.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `node --test --experimental-test-module-mocks --disable-warning=ExperimentalWarning "scripts/release/tests/*.test.js"`
Expected: PASS

- [ ] **Step 6: Add the new test glob to `package.json`**

In `package.json`, change the `"test"` script to also run `"scripts/release/tests/*.test.js"` alongside the existing two globs, so `npm test` covers this file.

- [ ] **Step 7: Run the full JS suite to confirm nothing broke**

Run: `npm test`
Expected: PASS (including the existing plugin tests and the new ones)

- [ ] **Step 8: Commit**

```bash
git add package.json package-lock.json scripts/release/scoped-release-plugin.js scripts/release/tests/scoped-release-plugin.test.js
git commit -m "feat: add commit-scope filter for per-plugin semantic-release"
```

---

### Task 3: `release.config.js`

**Files:**
- Create: `release.config.js`

**Interfaces:**
- Consumes: `scripts/release/scoped-release-plugin.js`'s `analyzeCommits`/`generateNotes` exports (Task 2); `scripts/bump_plugin_version.py`'s CLI (Task 1); `scripts/build_index.py`'s existing CLI (unchanged).
- Produces: a semantic-release config read via `process.env.PLUGIN_ID` / `process.env.PLUGIN_PATH`, consumed by `npx semantic-release` in Task 4's workflow loop.

- [ ] **Step 1: Install the new devDependencies**

Run: `npm install -D semantic-release @semantic-release/exec @semantic-release/git`

- [ ] **Step 2: Write `release.config.js`**

```javascript
import scopedReleasePlugin from './scripts/release/scoped-release-plugin.js';

const pluginId = process.env.PLUGIN_ID;
const pluginPath = process.env.PLUGIN_PATH;
if (!pluginId || !pluginPath) {
  throw new Error('PLUGIN_ID and PLUGIN_PATH environment variables are required');
}

export default {
  branches: ['main'],
  tagFormat: `${pluginId}-v\${version}`,
  plugins: [
    [scopedReleasePlugin, { preset: 'angular' }],
    [
      '@semantic-release/exec',
      {
        prepareCmd: `python3 scripts/bump_plugin_version.py ${pluginPath} \${nextRelease.version} && python3 scripts/build_index.py`,
      },
    ],
    [
      '@semantic-release/git',
      {
        assets: ['pte-plugins.json', `${pluginPath}/src/**/pte-plugin.json`],
        message: `chore(release): ${pluginId} \${nextRelease.version} [skip ci]\n\n\${nextRelease.notes}`,
      },
    ],
  ],
};
```

Note the `\${version}`, `\${nextRelease.version}` and `\${nextRelease.notes}` are deliberately escaped inside the JS template literals: they must remain literal in the generated config strings so `semantic-release` (for `tagFormat`) and the `@semantic-release/exec`/`@semantic-release/git` plugins (which apply their own Lodash-template substitution at release time) can fill them in, rather than being evaluated now by this script's own template-literal interpolation.

- [ ] **Step 3: Smoke-test the config against a real plugin, without making changes**

Run: `PLUGIN_ID=grobid PLUGIN_PATH=plugins/grobid npx semantic-release --dry-run --no-ci`
Expected: exits 0 and logs either "no release" (if `grobid` has no qualifying commits since its last tag — expected before Task 5's backfill exists) or a computed next version; no stack trace about `PLUGIN_ID`/`PLUGIN_PATH`/missing plugin.

- [ ] **Step 4: Commit**

```bash
git add package.json package-lock.json release.config.js
git commit -m "feat: add semantic-release config parameterized per plugin"
```

---

### Task 4: Per-plugin release workflow

**Files:**
- Create: `.github/workflows/semantic-release.yml`

**Interfaces:**
- Consumes: `release.config.js` (Task 3, loaded implicitly by `npx semantic-release`); the existing `.github/workflows/release.yml` (consumes the `<plugin-id>-v<version>` tags this workflow pushes — unchanged).

- [ ] **Step 1: Write `.github/workflows/semantic-release.yml`**

```yaml
name: Release plugins

# On every push to main, runs semantic-release once per plugin listed in pte-plugins.json,
# scoped to that plugin's own Conventional Commits (scope must equal the plugin id, e.g.
# "fix(grobid): ..."). A qualifying plugin gets its pte-plugin.json version bumped, a commit,
# and a <plugin-id>-v<version> tag — which release.yml turns into a wheel + GitHub release.

on:
  push:
    branches: [main]

concurrency:
  group: release-plugins
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
          fetch-tags: true
          persist-credentials: true

      - uses: actions/setup-node@v7
        with:
          node-version: '24'

      - run: npm ci

      - name: Configure git identity
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - name: Release each plugin with qualifying commits
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -e
          for id in $(jq -r '.plugins[].id' pte-plugins.json); do
            echo "::group::$id"
            path=$(jq -r --arg id "$id" '.plugins[] | select(.id==$id) | .path' pte-plugins.json)
            PLUGIN_ID="$id" PLUGIN_PATH="$path" npx semantic-release
            echo "::endgroup::"
          done
```

- [ ] **Step 2: Validate the YAML**

Run: `uv run python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/semantic-release.yml').read_text())"`
Expected: no error

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/semantic-release.yml
git commit -m "feat: automate per-plugin releases from scoped conventional commits"
```

---

### Task 5: Verify the tag backfill invariant

**Files:** none (verification only — no code or repository change)

As recorded under **Spec** above, this turned out to already be true for all 18 currently-indexed plugins (confirmed via `git ls-remote --tags origin` and `gh release list --repo mpilhlt/pte-plugins`, which show a `<plugin-id>-v<version>` tag and release for every plugin matching its current `pte-plugins.json` version, all created the same day this plan was written). This task just re-checks it right before Task 4's workflow is merged, in case versions drift between planning and merge.

**Interfaces:**
- Consumes: `pte-plugins.json`'s current `id`/`version` pairs; local git tags (run `git fetch --tags` first if the local checkout is stale).

- [ ] **Step 1: Confirm every indexed plugin has a matching tag**

```bash
git fetch --tags -q
for tag in $(jq -r '.plugins[] | "\(.id)-v\(.version)"' pte-plugins.json); do
  git rev-parse "$tag" >/dev/null 2>&1 || echo "MISSING $tag"
done
echo done
```

Expected: only `done` is printed — no `MISSING` lines. If any plugin *is* missing a tag at merge time, create and push just that one tag (`git tag <id>-v<version> && git push origin <id>-v<version>`) before merging Task 4's workflow, so its first automated run has a correct baseline.
