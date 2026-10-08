# Third-Party Notices

NAVA's proprietary notice applies only to original materials owned by its
copyright holder. It does not replace, restrict, or relicense third-party
software, fonts, icons, or other assets bundled with or used by the project.

## Bundled font

The Vazirmatn font is copyright 2015 The Vazirmatn Project Authors and is
licensed under the SIL Open Font License 1.1. The full license is included at
[app/assets/fonts/LICENSE.txt](app/assets/fonts/LICENSE.txt). The font may be
redistributed only under its own license and required notices must accompany
redistributions. The npm Fontsource package used by the frontend is also
subject to its upstream license and notices.

## Dependencies

- `requirements.txt` and `requirements-dev.txt` pin the Python dependency set.
  Each Python distribution retains its own license.
- `frontend/package.json` declares direct JavaScript dependencies and
  `frontend/package-lock.json` records the resolved dependency tree and the
  license metadata supplied by npm packages.
- Do not assume that every dependency is permissively licensed or that the
  metadata in a package manifest is a complete legal review. Check the exact
  versions shipped, transitive dependencies, optional packages, and required
  attribution/notice text before redistribution or commercial transfer.

## Release and transfer review

For each release or sale, generate and retain a software bill of materials
(SBOM) and a license report for the exact production artifacts. Review source
and binary distributions, fonts, icons, images, datasets, generated assets,
AI-provider terms, and any customer-provided material separately. Preserve the
licenses and notices required by each component. A dependency's presence in a
lockfile does not by itself establish that all redistribution obligations have
been met.
