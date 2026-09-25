# pi-centered

[![CI](https://github.com/ChmaraX/pi-centered/actions/workflows/ci.yml/badge.svg)](https://github.com/ChmaraX/pi-centered/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ChmaraX/pi-centered)](https://github.com/ChmaraX/pi-centered/releases/latest)
[![License](https://img.shields.io/github/license/ChmaraX/pi-centered)](LICENSE)

<p align="center">
  <a href="#install">install</a> · <a href="#usage">usage</a> · <a href="#wide-diagrams">wide diagrams</a> · <a href="CHANGELOG.md">changelog</a>
</p>

**[Pi](https://pi.dev), centered.** A readable chat column on wide terminals.

<!-- TODO: screenshot -->
<p align="center"><img src="assets/screenshot.png" alt="Pi chat in a centered column on a wide terminal" width="900"></p>

## Install

```bash
pi install git:github.com/ChmaraX/pi-centered
```

Restart Pi. Pi shows a notice when a new version lands; update with
`pi update --extensions`.

## Usage

| Command | Effect |
| --- | --- |
| `/maxwidth 100` | Set the column width (20 or more). Saved. |
| `/maxwidth off` | Full width. Saved. |
| `/maxwidth` | Show the current width. |

Default is 110. The width is saved to `~/.pi/agent/pi-centered.json`. Override
it for one launch with `PI_CENTERED_WIDTH=90 pi`.

## Wide diagrams

<!-- TODO: screenshot -->
<p align="center"><img src="assets/wide-diagram.png" alt="A wide Mermaid diagram breaking out of the centered column" width="900"></p>

Mermaid diagrams wider than the column break out to their full width, so Pi
can still draw them. The text around them stays in the column.

## Development

```bash
git clone https://github.com/ChmaraX/pi-centered && cd pi-centered
npm install
pi install "$PWD"
```

`npm run check` type-checks. `npm run e2e` runs real Pi in a virtual terminal
and checks where every line lands (needs Python 3; screens go to
`e2e/artifacts/`). PR titles follow
[Conventional Commits](https://www.conventionalcommits.org/); release-please
writes the changelog and tags releases.

## License

[MIT](LICENSE)
