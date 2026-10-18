# Vrtulka23 Tap

## How do I install these formulae?

`brew install vrtulka23/tap/<formula>`

Or `brew tap vrtulka23/tap` and then `brew install <formula>`.

Or, in a `brew bundle` `Brewfile`:

```ruby
tap "vrtulka23/tap"
brew "<formula>"
```

## Documentation

`brew help`, `man brew` or check [Homebrew's documentation](https://docs.brew.sh).

## Automatic snt3 updates

The [Update scinumtools3](.github/workflows/update-scinumtools3.yml) GitHub Actions
workflow checks `scinumtools/snt3` for a newer stable release every six hours
(at minute 23, UTC). It can also be run manually from the Actions tab on the
default branch.

For a newer release, it updates the source URL and SHA-256, synchronizes all four
resource commits with the release's submodules, and calculates their SHA-256s.
It removes any old bottle block and formula revision, builds from source on
Apple Silicon macOS, and runs the formula's tests. This runner can use Homebrew's
prebuilt dependency bottles, avoiding lengthy GCC builds on Intel macOS.
Only a successful build and test is
committed directly to the default branch. No change is made for the same or an
older version, drafts, or prereleases. Changes to the set of submodules or their
repositories fail the run for manual review.

The workflow uses the built-in `GITHUB_TOKEN` with `contents: write`; no extra
secret is needed. Repository rules must allow that token to push to the default
branch. A concurrent branch update causes the push to fail safely; the next
scheduled run retries from the latest branch state. Because
[pushes using `GITHUB_TOKEN` do not trigger other workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow),
the build and tests run inside the update workflow. This path does not publish
bottles; the existing pull-request workflows remain available for bottle builds.
