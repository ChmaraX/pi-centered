# pi-centered

[![CI](https://github.com/ChmaraX/pi-centered/actions/workflows/ci.yml/badge.svg)](https://github.com/ChmaraX/pi-centered/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/pi-centered)](https://www.npmjs.com/package/pi-centered)
[![License](https://img.shields.io/github/license/ChmaraX/pi-centered)](LICENSE)

<p align="center">
  <a href="#install">install</a> · <a href="#usage">usage</a> · <a href="#how-it-works">how it works</a> · <a href="#limitations">limitations</a> · <a href="CHANGELOG.md">changelog</a>
</p>

On a wide terminal, [Pi](https://pi.dev) stretches every line from edge to
edge. pi-centered keeps the chat, editor and footer in a centered column that
is comfortable to read. Wide Mermaid diagrams still break out of the column,
so they render in full.

<!-- TODO: screenshot / demo -->
<p align="center"><img src="assets/screenshot.png" alt="pi-centered: centered chat column with a wide Mermaid diagram breaking out" width="900"></p>

## Install

```bash
pi install npm:pi-centered
```

Or straight from GitHub:

```bash
pi install git:github.com/ChmaraX/pi-centered
```

Restart Pi. The column is 110 cells wide by default.

## Usage

| Command | Effect |
| --- | --- |
| `/maxwidth 100` | Set the column width (whole number, 20 or more). Saved. |
| `/maxwidth off` | Full width. Saved. |
| `/maxwidth` | Show the current width. |

The width is saved to `~/.pi/agent/pi-centered.json` and applies right away.
To override it for one launch, set `PI_CENTERED_WIDTH`:

```bash
PI_CENTERED_WIDTH=90 pi
```

## How it works

- The transcript, editor and footer render at the column width and are padded
  to the center. Terminals narrower than the column are left alone.
- A Mermaid diagram wider than the column gets its own width, up to the full
  terminal. The text around it stays in the column.
- Only diagrams Pi would draw break out: top-level Mermaid blocks, with Pi's
  Mermaid setting on. Diagrams in lists, quotes or example code blocks stay
  as source, as in plain Pi.

## Limitations

- **Uses Pi internals.** Pi has no layout API, so pi-centered wraps Pi's own
  components. A Pi update can break it. If that happens, remove the package
  and Pi goes back to full width.
- **Diagrams wider than the terminal** still show as source, as in plain Pi.

## Development

```bash
git clone https://github.com/ChmaraX/pi-centered
cd pi-centered
npm install
pi install "$PWD"   # load your checkout
```

`npm run check` type-checks. `npm run e2e` runs the pinned Pi in a virtual
terminal against a fixed reply (no model calls) and checks where every line
lands; screens are saved to `e2e/artifacts/`. Needs Python 3.

Commits and PR titles follow [Conventional Commits](https://www.conventionalcommits.org/);
release-please writes the changelog and publishes to npm.

## License

[MIT](LICENSE)
