# Third-party sources

- yaml-cpp 0.8.0 — `https://github.com/jbeder/yaml-cpp/tree/0.8.0`, MIT. Source archive SHA-256: `334e80ab7b52e14c23f94e041c74bab0742f2281aad55f66be2f19f4b7747071`. License: `vendor/yaml-cpp-0.8.0/LICENSE`.
- Notepad++ SDK headers v8.9.6 — `https://github.com/notepad-plus-plus/notepad-plus-plus/tree/v8.9.6`. `PluginInterface.h`, `Notepad_plus_msgs.h`, `menuCmdID.h`: GPL-3.0-or-later. Retrieved from the tagged upstream source (raw.githubusercontent.com / jsDelivr GitHub mirror).
- Scintilla headers from the same Notepad++ source tag — `Scintilla.h`, `Sci_Position.h`; license in `vendor/npp/Scintilla.License.txt`.
- LLVM-MinGW 20261104 UCRT x86_64 — build tool only, not shipped in the plugin package. `https://github.com/mstorsjo/llvm-mingw/releases/tag/20261104`. Its static runtime notices are retained in the release's third-party notices.

API references used: Notepad++ plugin communication and the tagged SDK headers, yaml-cpp's shipped source and documentation, Java `java.util.Properties` Javadoc. Java parser compatibility is verified with `tests/java_compat.py` when Java is installed.
