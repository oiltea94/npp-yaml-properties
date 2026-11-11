# YamlProperties 0.3.1

## Objective and accepted behavior
Native Windows x86, x64 and ARM64 Notepad++ plugin with YAML → Properties, Properties → YAML and optional automatic conversion menu commands. Convert a single selection when present, otherwise the active document. By default, open the result in a new UTF-8 tab and preserve the source document. A persistent checked menu item controls this behavior; when unchecked, replace only the selected range or the whole document in place, with one undo action and no automatic save. Dotted keys and zero-based bracket indices always form nested mappings and sequences, except for complete logger names beneath logging.level. YAML output retains existing Properties quotes as syntax without adding new quotes. This behavior is fixed and has no configuration toggle.

## Conversion contract
- UTF-8 text, Unicode escapes, Java Properties separators, escaped keys and continued lines.
- Preserve insertion order and parsed Properties text. Emit existing quote characters directly as YAML syntax and never add protective quotes, including for numbers, booleans, dates, empty values or syntax-sensitive text. No extra output-syntax validation or repair is performed. String types and exact round-trip values are not guaranteed during conversion; YAML readers interpret the resulting syntax. Existing Java Properties unescaping and continuation handling still apply.
- Reject duplicate input keys, conflicting paths and sparse arrays. YAML input additionally rejects multiple documents, null values, non-scalar keys, custom tags, recursive aliases and empty nested containers.
- Accept dotted YAML keys (including `logging.level.com.example`) and special characters; escape Java Properties delimiters. Ordinary textual brackets belong to keys; numeric suffixes remain array indices. Detect duplicate flattened keys. Dotted paths normalize on conversion back to YAML rather than recreating original grouping.
- YAML → Properties retains double-quoted value syntax, including original single-line escape spelling, before Java Properties escaping. Normalize physically multiline double-quoted values to a single-line double-quoted representation of the decoded value. Tags and anchors before values and alias references use the original scalar style. Plain, single-quoted and block scalars retain their existing decoded-text behavior; mapping key quote styles are not preserved. Both manual and auto conversion share this fixed rule.
- In hierarchical Properties → YAML conversion, the exact `logging.level.` prefix creates `logging` / `level` mappings and treats the entire nonempty suffix as a literal logger name. Package and class logger levels coexist in either input order. Other prefixes retain normal path rules; namespace scalar/map conflicts still fail.
- Optional auto conversion uses recognized filename extensions first, then content. Unknown-name `key: value` defaults to YAML; `key=value` to Properties. Invalid detected YAML reports an error, with no silent fallback. Empty/comment-only input without a recognized extension requests a manual direction.
- Comments, scalar types, anchor names and source formatting are not retained. Ordinary nonrecursive aliases may expand to their values.
- Explain conversion errors and their source line where available. No output tab on failure.
- `NewTab=1` and `SortKeys=0` are the defaults, including when absent in older configuration. Legacy quoting and literal-key preferences are ignored. Both active preferences are saved together, atomically; failed persistence leaves the active options and menu checks unchanged.
- Optional key sorting applies at conversion time in both directions, including automatic conversion and either output destination. Order sibling mapping keys lexicographically by Unicode character order, case-sensitive and independent of locale; do not use natural-number or pinyin collation. Preserve array element positions and numeric index order. Compare parsed key text before Properties escaping and retain current value/quote handling. Keep hierarchical groups together rather than sorting flattened output lines globally. Default-off output retains existing insertion order. The CLI continues using default-off behavior; the core API accepts a `sort_keys` parameter.
- In-place output preserves the buffer identity, filename, encoding and EOL style. Preserve all text outside a selection; select the replacement. Change syntax highlighting only for whole-document conversion. Undo/redo applies to text, not language selection. Reject read-only output and unrepresentable legacy-encoding characters before editing. The filename-first auto detection contract still applies after in-place conversion.
- Maximum input 8 MiB, depth 64, 100,000 visited nodes, array index 9,999 and output 16 MiB.

## Implementation
C++17, Win32/Notepad++ plugin API, yaml-cpp 0.8.0 (MIT). Architecture-specific binaries and build directories prevent mixing target objects. A portable LLVM-MinGW toolchain is confined to `.tools/`. No runtime dependency on Python, Java or an external converter. Static C++ runtime and yaml-cpp.

## Commands
Build and test: `powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1`
Plugin smoke test: `python tests\smoke_plugin.py`
Install: `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1`
Uninstall/restore: `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Restore`

## Publication
The root VERSION file is the single executable version source. Embed a Windows VERSIONINFO resource in the DLL. Keep the manual installer ZIP and create a distinct Plugins Admin ZIP with YamlProperties.dll at its root. Source archives include build inputs and fixed dependencies, and exclude machine-specific evidence, runtime directories and caches. Official list metadata uses the final ZIP hash and explicit tested compatibility. GitHub publication, hosted CI and official Plugins Admin Debug testing remain external acceptance steps; see docs/RELEASING.md.

## Structure and style
`src/` conversion core and DLL adapter; `tests/` semantic and real Notepad++ checks; `vendor/` pinned dependency sources and SDK headers; `dist/` installable plugin; `evidence/` verification records. Use small named functions, RAII, explicit errors and `snake_case` functions. Example public call: `to_yaml(input)`.

## Testing and acceptance
Test sorting on/off in both directions, nested mappings and sequence objects, numeric indices above nine, case/Unicode ordering, aliases, logger names and quote round trips. Verify default-off migration, independent output/sort preferences, failed settings writes and restart persistence in the real editor.
Test source-quote output against exact expected text, including original single/double quotes, numeric/boolean values, log patterns and nested arrays. Compare direct YAML emission for single-segment keys against Java-parsed ordered key/value text; independently check YAML decoding through Java Properties. Verify removed menus and CLI flags are absent and old quoting/literal-key preferences have no effect. Empty keys have no hierarchical path and must fail in both directions. Cover escaping, Unicode, arrays of objects, ambiguity, invalid input and resource bounds. Build each target DLL, inspect its exports/dependencies, load it into an isolated copy of installed Notepad++, and invoke menu actions with source preservation checks. Verify new-tab defaults, selection/full-document replacement, undo/redo, encoding preservation, read-only/error handling, settings-save failure and restart persistence.

## Boundaries
Validate input and path structure before creating output; source-quote emission deliberately does not repair emitted YAML scalar syntax. Preserve original documents by default; explicit in-place preference permits undoable editor changes. Never save source files automatically. Back up an existing plugin before installation. Ask before remote publishing. Do not overwrite unrelated files or restart a user's editor. Build/test artifacts stay inside this project directory.
