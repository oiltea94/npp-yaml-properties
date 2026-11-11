# Changelog

## Unreleased

- Preserve complete logger names beneath `logging.level` when converting Properties to YAML, so package and class log levels coexist without a path conflict.

## 0.3.1 — 2026-11-11

- Make the default README English and add a linked Simplified Chinese README.
- Include both README languages in manual installation and source packages.
- Add Windows DLL version information, generated from the single `VERSION` file.
- Provide a separate ZIP with the DLL at its root for Notepad++ Plugins Admin.
- Exclude local diagnostics, toolchains and test environments from source releases.
- Add Windows CI, release-artifact checks and an official plugin-list entry generator.
- Document GitHub publication and the official plugin-list submission process.

## 0.3.0

- Add a persistent option to open conversion output in a new tab (enabled by default).
- Support in-place selection/document replacement with one-step text undo.
- Preserve document encoding and detect unrepresentable legacy-encoding output.

## 0.2.0

- Accept dotted and special YAML keys, including `logging.level.com.example`.
- Add optional automatic format detection and conversion.

## 0.1.0

- Initial native x64 YAML ↔ Properties converter with selection support.
- Add persistent literal-key mode and isolated editor/Java compatibility tests.
