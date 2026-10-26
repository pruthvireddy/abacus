# GitHub preparation and first push

This guide prepares Abacus for source control while preserving the research
record. The [README](../README.md) is the public entry point; the
[contribution guide](../CONTRIBUTING.md) covers development. The live selected
research collection is [Narada on Vercel](https://abacus-narada.vercel.app/).

Preparation on October 24, 2026 was local only. On October 25, the owner
authorized replacing the existing public repository
[pruthvireddy/abacus](https://github.com/pruthvireddy/abacus) with this workspace.
The existing repository visibility and independent Vercel release workflow are
preserved. No blanket reuse license is introduced.

## Repository and recovery

The source remote is `git@github.com:pruthvireddy/abacus.git`, with `main` as the
default branch. The previous main commit was
`a00ae95545c1c752292e5b75e128d1339d480201`; its unrelated Pine scripts and notebook
are retained on the recovery branch
[`codex/backup-before-publication-20261025`](https://github.com/pruthvireddy/abacus/tree/codex/backup-before-publication-20261025).
Only main is replaced; its update uses an explicit lease against that old commit.

A complete local recovery bundle is retained at
`work/github-publish-20261025/old-github-main.bundle`. This ignored local bundle
is separate from the branch kept on GitHub. Inspect the old source without
changing main by fetching and creating a separate worktree:

```sh
git fetch origin codex/backup-before-publication-20261025
git worktree add --detach ../abacus-before-publication FETCH_HEAD
```

The [repository checks](https://github.com/pruthvireddy/abacus/actions/workflows/ci.yml)
run for the published main branch. Repository hosting does not restore ignored
data or deploy the Vercel site.

## Preparation results

The October 24 audit reduced Git-eligible working content from approximately
1.08 GiB to 718 MiB by excluding 89 manifest-pinned bulk tables and private
report-cell maps (391 MiB). This is an uncompressed file inventory, not a future
Git pack or clone-size estimate. The retained public app bundles remain included.

The working-tree/index/`HEAD` audit found no blocking size, credential-pattern,
or symlink issues. One legacy manifest link needs separately restored data.
The existing `HEAD` history contains approximately 12.25 MiB of blobs and needs
no large-file history rewrite. Pattern checks remain bounded.

Hash comparison confirmed 6,559 previously eligible run, presentation-export,
catalog and legacy files unchanged. A clean source-only snapshot passes all
95 documentation guides, 214 utility tests, and metadata checks. Narada
verification, 168 tests, lint and static build
pass with the existing installed dependencies. An offline clean install could
not finish because a dependency tarball was absent from npm's cache; hosted CI
installation was not part of those local preparation results. Published workflow
outcomes are available from the repository checks linked above.

The full local compatibility gate is not passing: Bhishma's 957-test run reports
two configured-data errors (missing volume-rank symbology and an unavailable
point-in-time definition pair). Its four later checks remain unexecuted after
fail-fast. This preparation does not rebuild data to repair those prerequisites.
Raw local audit/verification records live under
`work/github-readiness-20261024/` and are excluded from the upload.

## What belongs in Git

| Include | Retain separately |
|---|---|
| Package, study and app source with focused tests | Market-data deliveries and feature partitions |
| Protocols, settings, input locks and catalog manifests | Private/local configuration and credentials |
| Small saved evidence, reports and provenance records | Event ledgers, bulk tables and retained historical working evidence |
| Selected Narada public bundles and its npm lockfile | Dependency directories, build caches and static release payloads |
| Documentation, workspace check registry and CI | Ignored dirty-source reconstruction snapshots needed for release recovery |

The existing [ignore rules](../.gitignore) implement the storage boundary.
Additional bulk exclusions are recorded in the additive
[artifact inventory](github-bulk-artifacts.json), including original paths,
byte sizes, SHA-256 hashes, and the sealed manifest that already pins each file.
Those original files remain at their existing local paths. No sealed run,
catalog snapshot, historical report, or completed presentation revision is
rewritten for GitHub preparation.

An ignored file is not backed up by Git. Retain an approved separate backup of
`data/`, bulk run/export artifacts, and kept Narada release payload/source
snapshots. Restore exact bytes to the recorded paths and verify their hashes
before data-backed work. The inventory records local identity; it does not
certify an off-device backup or provide a hosted download. See
[storage guidance](../data/README.md) and the
[release reconstruction guide](../apps/narada/releases/README.md#prepare-locally).

Compatibility links under `legacy/` may point to ignored local data. A source
clone can contain these links without their targets. Retain their layout and
restore the correct data rather than replacing them with external machine paths.
Historical absolute paths inside preserved provenance describe the original
execution; current path resolution uses [configuration](../config/paths.example.toml).

## Repeat the upload audit

Run from the workspace root with system Python and Git:

```sh
python3 scripts/check-github-readiness.py
python3 scripts/check-github-readiness.py --json > work/github-readiness.json
```

The equivalent explicit harness selection is
`./scripts/check-workspace --profile github-readiness`. It is outside the default
and source-only CI gates. Use repeatable `--ref <branch-or-tag>` arguments on the
direct command when the intended push includes additional refs; the default
history scope is `HEAD`.

The read-only audit examines tracked and nonignored untracked candidates,
symlinks, suspicious credential filenames/patterns, file sizes, and the selected
Git history. It never prints matched credential values. Its output states scan
scope, findings and limitations. Pattern matching cannot prove an absence of
secrets, certify redistribution rights, or approve making research public.
Inspect findings and the actual staged diff before a push.

GitHub warns above 50 MiB per file and blocks files above 100 MiB. Ignore rules
only affect untracked additions: they do not remove existing tracked files or
history. The [GitHub large-file guide](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
explains the limits. Abacus keeps bulk research bytes outside ordinary Git
history using retained locators and checksums; this preparation does not convert
sealed evidence to Git LFS pointers.

Review the upload candidates and staging explicitly:

```sh
git status --short
git diff --stat
git ls-files --others --exclude-standard
git diff --cached --stat
git diff --cached --check
```

Keep the existing local work visible. Stage only paths intended for the first
upload after review; no commit or index changes are required just to inspect
readiness. Do not force-add ignored data, authentication state, or release
snapshots. Select the intended branch explicitly when pushing: local agent refs
and other internal snapshots are outside this upload, so do not use a mirror
push or indiscriminate ref export.

## Verify a source-only checkout

The [GitHub Actions workflow](../.github/workflows/ci.yml) has two independent jobs:

- System Python checks maintained documentation, synthetic workspace utility
  tests, and navigation metadata. It does not install the research environment.
- Node 24 installs Narada's npm lockfile and runs `verify`, `test`, `lint`, and
  `build`, including the static-export verifier. It reads app-owned inputs.

Both jobs use read-only repository permissions. They do not restore private
inputs, execute research, audit private publication sources, publish reports,
or deploy. The default local six-step compatibility gate is unchanged.

From a source-only checkout, run:

```sh
./scripts/check-workspace --profile documentation --profile tooling --profile metadata
```

Then follow the [Narada setup/checks](../apps/narada/README.md#setup-and-checks).
Some package/study suites require retained market data, Ruby, or a compiler.
The [verification reference](verification.md) documents these prerequisites.
Index freshness remains a full-workspace check because the generator includes
optional local artifact links. Its failure in a source-only checkout is not
permission to regenerate or overwrite the saved index. Hosted CI execution is
only established after a future GitHub push; local commands test the same scope.

## Choose publication scope

A private repository can hold source intended only for collaborators. A public
repository makes every included file and reachable commit available to readers,
including older research reports, source extracts, screenshots and provenance.
The live website is a separately selected subset. Review the complete candidate
scope and third-party material before choosing public visibility.
For example, the study 17 run retains chart screenshots from its identified
external video source; existing publication of selected figures does not settle
permission to redistribute the broader repository.

No repository-wide license has been selected. Choose one deliberately before
advertising reuse permissions; source, market data, third-party material and
selected public reports can have different ownership or redistribution terms.
No blanket license is inferred from Vercel hosting or GitHub visibility.

## Publishing to another repository

The current destination is already identified above. The following is a general
reference for a future separately authorized destination; it is not an instruction
to recreate or replace the existing GitHub repository.

Choose the owner, repository name, and visibility after the local diff is ready.
Commit the reviewed source/evidence selection, then create an empty GitHub
repository without an extra README, license, or `.gitignore`. Authenticate with
GitHub through the normal credential manager or CLI; keep tokens out of URLs
and repository files. The
[official import guide](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
covers authentication and importing an existing local Git repository.

After creating that empty repository, replace the example destination below
with the actual chosen owner/name:

```sh
git remote add origin git@github.com:OWNER/REPOSITORY.git
git remote -v
git push -u origin main
```

Alternatively, after authentication, use the
[GitHub CLI create command](https://cli.github.com/manual/gh_repo_create) with
an explicit visibility flag. Do not run both creation paths:

```sh
gh repo create OWNER/REPOSITORY --private --source=. --remote=origin --push
```

Once pushed, verify both workflow jobs, set the repository About website to
`https://abacus-narada.vercel.app/`, and use a description such as
“Market-data pipelines, reproducible research studies, and selected evidence reports.”
The README already uses stable Vercel study routes and needs no repository-name
substitution.

## Keep hosting independent

The existing Vercel project uses verified static uploads under the
[Narada release workflow](../apps/narada/releases/README.md). GitHub source
hosting does not change that boundary. Keep it disconnected from automatic Git
builds unless a later deployment task explicitly changes the release design.
Only the isolated prepared deployment directory is uploaded; the workspace,
private source audit locators and full research library are not website inputs.
