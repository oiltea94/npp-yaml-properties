# YamlProperties 0.3.1

## Objective and accepted behavior
Native Windows x64 Notepad++ plugin with YAML → Properties, Properties → YAML and optional automatic conversion menu commands. Convert a single selection when present, otherwise the active document. By default, open the result in a new UTF-8 tab and preserve the source document. A persistent checked menu item controls this behavior; when unchecked, replace only the selected range or the whole document in place, with one undo action and no automatic save. Default dotted keys and zero-based bracket indices form nested mappings and sequences. A separate persistent menu toggle preserves complete keys instead. All emitted YAML values are quoted strings.

## Conversion contract
- UTF-8 text, Unicode escapes, Java Properties separators, escaped keys and continued lines.
- Preserve insertion order and scalar text, including leading zeros and boolean-looking strings.
- Reject duplicate keys, conflicting paths, sparse arrays, multi-document YAML, null values, non-scalar keys, custom tags, recursive aliases and empty nested containers.
- Accept dotted YAML keys (including `logging.level.com.example`) and special characters; escape Java Properties delimiters. Ordinary textual brackets belong to keys; numeric suffixes remain array indices. Detect duplicate flattened keys. Dotted paths normalize on conversion back to YAML rather than recreating original grouping. Literal-key mode accepts flat scalar mappings.
- Optional auto conversion uses recognized filename extensions first, then content. Unknown-name `key: value` defaults to YAML; `key=value` to Properties. Invalid detected YAML reports an error, with no silent fallback. Empty/comment-only input without a recognized extension requests a manual direction.
- Comments, scalar types, anchor names and source formatting are not retained. Ordinary nonrecursive aliases may expand to their values.
- Explain conversion errors and their source line where available. No output tab on failure.
- `NewTab=1` is the default, including when the key is absent in older configuration. Both preference keys are saved atomically together; failed persistence leaves the active option and menu check unchanged.
- In-place output preserves the buffer identity, filename, encoding and EOL style. Preserve all text outside a selection; select the replacement. Change syntax highlighting only for whole-document conversion. Undo/redo applies to text, not language selection. Reject read-only output and unrepresentable legacy-encoding characters before editing. The filename-first auto detection contract still applies after in-place conversion.
- Maximum input 8 MiB, depth 64, 100,000 visited nodes, array index 9,999 and output 16 MiB.

## Implementation
C++17, Win32/Notepad++ plugin API, yaml-cpp 0.8.0 (MIT). A portable LLVM-MinGW toolchain is confined to `.tools/`. No runtime dependency on Python, Java or an external converter. Static C++ runtime and yaml-cpp.

## Commands
Build and test: `powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1`
Plugin smoke test: `python tests\smoke_plugin.py`
Install: `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1`
Uninstall/restore: `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Restore`

## Publication
The root VERSION file is the single executable version source. Embed a Windows VERSIONINFO resource in the DLL. Keep the manual installer ZIP and create a distinct Plugins Admin ZIP with YamlProperties.dll at its root. Source archives include build inputs and fixed dependencies, and exclude machine-specific evidence, runtime directories and caches. Official list metadata uses the final ZIP hash and explicit tested compatibility. GitHub publication, hosted CI and official Plugins Admin Debug testing remain external acceptance steps; see docs/RELEASING.md.

## Structure and style
`src/` conversion core and DLL adapter; `tests/` semantic and real Notepad++ checks; `vendor/` pinned dependency sources and SDK headers; `dist/` installable plugin; `evidence/` verification records. Use small named functions, RAII, explicit errors and `snake_case` functions. Example public call: `to_yaml(input, KeyMode::Hierarchical)`.

## Testing and acceptance
Test conversion semantics against independently expected values, not text formatting. Cover escaping, Unicode, arrays of objects, ambiguity, invalid input and resource bounds. Build the DLL, inspect its exports/dependencies, load it into an isolated copy of installed Notepad++, and invoke menu actions with source preservation checks. Verify new-tab defaults, selection/full-document replacement, undo/redo, encoding preservation, read-only/error handling, settings-save failure and restart persistence. Round-trip tests validate values, not YAML types/comments.

## Boundaries
Always validate before creating output. Preserve original documents by default; explicit in-place preference permits undoable editor changes. Never save source files automatically. Back up an existing plugin before installation. Ask before remote publishing. Do not overwrite unrelated files or restart a user's editor. Build/test artifacts stay inside this project directory.
