#include <windows.h>
#include "PluginInterface.h"
#include "menuCmdID.h"
#include "converter.h"
#include "version.h"
#include <array>
#include <string>
#include <vector>

namespace {
constexpr wchar_t plugin_name[] = L"YamlProperties";
constexpr std::size_t input_limit = 8 * 1024 * 1024;
NppData npp;
std::array<FuncItem, 7> commands;
constexpr std::size_t literal_command = 3;
constexpr std::size_t new_tab_command = 4;
bool literal_keys = false;
bool new_tab = true;
std::wstring settings_path;
unsigned output_number = 0;

std::wstring wide(const std::string& text) {
    if (text.empty()) return {};
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()), nullptr, 0);
    if (!count) return L"Conversion failed: invalid UTF-8 error text.";
    std::wstring result(count, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()), result.data(), count);
    return result;
}
void report(const std::string& message) {
    auto text = wide(message);
    MessageBoxW(npp._nppHandle, text.c_str(), plugin_name, MB_OK | MB_ICONERROR);
}
HWND editor() {
    int view = 0;
    SendMessageW(npp._nppHandle, NPPM_GETCURRENTSCINTILLA, 0, reinterpret_cast<LPARAM>(&view));
    return view == 0 ? npp._scintillaMainHandle : npp._scintillaSecondHandle;
}
std::string utf8_from_editor(const std::string& bytes, UINT codepage) {
    if (codepage == SC_CP_UTF8 || bytes.empty()) return bytes;
    if (!codepage) codepage = GetACP();
    int count = MultiByteToWideChar(codepage, MB_ERR_INVALID_CHARS, bytes.data(), static_cast<int>(bytes.size()), nullptr, 0);
    if (!count) throw yp::ConversionError("Text is invalid for the current document encoding. Convert the source to UTF-8 first.");
    std::wstring text(count, L'\0');
    MultiByteToWideChar(codepage, MB_ERR_INVALID_CHARS, bytes.data(), static_cast<int>(bytes.size()), text.data(), count);
    int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(), count, nullptr, 0, nullptr, nullptr);
    if (!size) throw yp::ConversionError("Could not convert the document encoding to UTF-8.");
    std::string result(size, '\0');
    WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(), count, result.data(), size, nullptr, nullptr);
    return result;
}
std::string read_input(HWND sci) {
    auto start = SendMessageW(sci, SCI_GETSELECTIONSTART, 0, 0);
    auto end = SendMessageW(sci, SCI_GETSELECTIONEND, 0, 0);
    bool selected = end != start;
    if (SendMessageW(sci, SCI_GETSELECTIONS, 0, 0) > 1 ||
        (selected && SendMessageW(sci, SCI_GETSELECTIONMODE, 0, 0) != SC_SEL_STREAM))
        throw yp::ConversionError("Select one continuous text range, or clear the selection to convert the whole document.");
    auto length = selected ? end-start : SendMessageW(sci, SCI_GETLENGTH, 0, 0);
    if (length < 0 || static_cast<std::size_t>(length) > input_limit) throw yp::ConversionError("Input exceeds 8 MiB.");
    std::string bytes(static_cast<std::size_t>(length)+1, '\0');
    if (selected) SendMessageW(sci, SCI_GETSELTEXT, 0, reinterpret_cast<LPARAM>(bytes.data()));
    else SendMessageW(sci, SCI_GETTEXT, bytes.size(), reinterpret_cast<LPARAM>(bytes.data()));
    bytes.resize(static_cast<std::size_t>(length));
    return utf8_from_editor(bytes, static_cast<UINT>(SendMessageW(sci, SCI_GETCODEPAGE, 0, 0)));
}
std::optional<yp::Format> filename_format() {
    wchar_t extension[64] = {};
    SendMessageW(npp._nppHandle, NPPM_GETEXTPART, 64, reinterpret_cast<LPARAM>(extension));
    if (lstrcmpiW(extension, L".yaml") == 0 || lstrcmpiW(extension, L".yml") == 0) return yp::Format::Yaml;
    if (lstrcmpiW(extension, L".properties") == 0) return yp::Format::Properties;
    return std::nullopt;
}
std::string bytes_for_editor(const std::string& utf8, UINT codepage) {
    if (!codepage) codepage = GetACP();
    if (codepage == CP_UTF8 || utf8.empty()) return utf8;
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8.data(), static_cast<int>(utf8.size()), nullptr, 0);
    if (!count) throw yp::ConversionError("Could not encode the conversion result. Source text was preserved.");
    std::wstring text(count, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8.data(), static_cast<int>(utf8.size()), text.data(), count);
    BOOL substituted = FALSE;
    int size = WideCharToMultiByte(codepage, WC_NO_BEST_FIT_CHARS, text.data(), count, nullptr, 0, nullptr, &substituted);
    if (!size || substituted)
        throw yp::ConversionError("The result contains characters outside the document encoding. Enable new-tab output or convert the source to UTF-8 first. Source text was preserved.");
    std::string bytes(size, '\0');
    int written = WideCharToMultiByte(codepage, WC_NO_BEST_FIT_CHARS, text.data(), count, bytes.data(), size, nullptr, &substituted);
    if (written != size || substituted || utf8_from_editor(bytes, codepage) != utf8)
        throw yp::ConversionError("The result cannot be represented exactly in the document encoding. Enable new-tab output or convert the source to UTF-8 first. Source text was preserved.");
    return bytes;
}
UINT document_codepage() {
    HMENU menu = GetMenu(npp._nppHandle);
    auto checked = [menu](UINT command) {
        UINT state = GetMenuState(menu, command, MF_BYCOMMAND);
        return state != static_cast<UINT>(-1) && (state & MF_CHECKED);
    };
    // Notepad++ keeps named legacy encodings in a UTF-8 Scintilla buffer.
    // Its Encoding menu exposes the save encoding; SCI_GETCODEPAGE alone does not.
    if (checked(IDM_FORMAT_ANSI)) return GetACP();
    struct Charset { UINT command; UINT codepage; };
    constexpr Charset charsets[] = {
        {IDM_FORMAT_WIN_1250, 1250}, {IDM_FORMAT_WIN_1251, 1251}, {IDM_FORMAT_WIN_1252, 1252},
        {IDM_FORMAT_WIN_1253, 1253}, {IDM_FORMAT_WIN_1254, 1254}, {IDM_FORMAT_WIN_1255, 1255},
        {IDM_FORMAT_WIN_1256, 1256}, {IDM_FORMAT_WIN_1257, 1257}, {IDM_FORMAT_WIN_1258, 1258},
        {IDM_FORMAT_ISO_8859_1, 28591}, {IDM_FORMAT_ISO_8859_2, 28592}, {IDM_FORMAT_ISO_8859_3, 28593},
        {IDM_FORMAT_ISO_8859_4, 28594}, {IDM_FORMAT_ISO_8859_5, 28595}, {IDM_FORMAT_ISO_8859_6, 28596},
        {IDM_FORMAT_ISO_8859_7, 28597}, {IDM_FORMAT_ISO_8859_8, 28598}, {IDM_FORMAT_ISO_8859_9, 28599},
        {IDM_FORMAT_ISO_8859_13, 28603}, {IDM_FORMAT_ISO_8859_14, 28604}, {IDM_FORMAT_ISO_8859_15, 28605},
        {IDM_FORMAT_DOS_437, 437}, {IDM_FORMAT_DOS_720, 720}, {IDM_FORMAT_DOS_737, 737},
        {IDM_FORMAT_DOS_775, 775}, {IDM_FORMAT_DOS_850, 850}, {IDM_FORMAT_DOS_852, 852},
        {IDM_FORMAT_DOS_855, 855}, {IDM_FORMAT_DOS_857, 857}, {IDM_FORMAT_DOS_858, 858},
        {IDM_FORMAT_DOS_860, 860}, {IDM_FORMAT_DOS_861, 861}, {IDM_FORMAT_DOS_862, 862},
        {IDM_FORMAT_DOS_863, 863}, {IDM_FORMAT_DOS_865, 865}, {IDM_FORMAT_DOS_866, 866},
        {IDM_FORMAT_DOS_869, 869}, {IDM_FORMAT_BIG5, 950}, {IDM_FORMAT_GB2312, 936},
        {IDM_FORMAT_SHIFT_JIS, 932}, {IDM_FORMAT_KOREAN_WIN, 949}, {IDM_FORMAT_EUC_KR, 51949},
        {IDM_FORMAT_TIS_620, 874}, {IDM_FORMAT_MAC_CYRILLIC, 10007},
        {IDM_FORMAT_KOI8U_CYRILLIC, 21866}, {IDM_FORMAT_KOI8R_CYRILLIC, 20866},
    };
    for (const auto& charset : charsets)
        if (checked(charset.command)) return charset.codepage;
    return CP_UTF8; // UTF-8 and UTF-16 files can represent every emitted Unicode scalar.
}
void replace_in_place(HWND source, const std::string& output, bool yaml_output) {
    if (SendMessageW(source, SCI_GETREADONLY, 0, 0))
        throw yp::ConversionError("The document is read-only. Enable new-tab output or make the document writable first. Source text was preserved.");
    UINT editor_codepage = static_cast<UINT>(SendMessageW(source, SCI_GETCODEPAGE, 0, 0));
    UINT file_codepage = document_codepage();
    if (file_codepage != CP_UTF8 && file_codepage != editor_codepage)
        bytes_for_editor(output, file_codepage); // Validate saving before changing any text.
    auto bytes = bytes_for_editor(output, editor_codepage);
    auto start = SendMessageW(source, SCI_GETSELECTIONSTART, 0, 0);
    auto end = SendMessageW(source, SCI_GETSELECTIONEND, 0, 0);
    bool selected = start != end;
    if (!selected) {
        start = 0;
        end = SendMessageW(source, SCI_GETLENGTH, 0, 0);
    }
    SendMessageW(source, SCI_BEGINUNDOACTION, 0, 0);
    SendMessageW(source, SCI_SETTARGETSTART, start, 0);
    SendMessageW(source, SCI_SETTARGETEND, end, 0);
    SendMessageW(source, SCI_REPLACETARGET, bytes.size(), reinterpret_cast<LPARAM>(bytes.data()));
    SendMessageW(source, SCI_ENDUNDOACTION, 0, 0);
    if (selected) {
        SendMessageW(source, SCI_SETSEL, start, start + static_cast<LPARAM>(bytes.size()));
    } else {
        SendMessageW(source, SCI_GOTOPOS, 0, 0);
        SendMessageW(npp._nppHandle, NPPM_SETCURRENTLANGTYPE, 0, yaml_output ? L_YAML : L_PROPS);
    }
}
void convert(std::optional<bool> requested_direction) {
    try {
        HWND source = editor();
        auto input = read_input(source);
        auto mode = literal_keys ? yp::KeyMode::Literal : yp::KeyMode::Hierarchical;
        bool yaml_output = requested_direction.value_or(false);
        std::string output;
        if (requested_direction) {
            output = yaml_output ? yp::to_yaml(input, mode) : yp::to_properties(input, mode);
        } else {
            auto converted = yp::auto_convert(input, mode, filename_format());
            yaml_output = converted.output_format == yp::Format::Yaml;
            output = std::move(converted.text);
        }
        auto eol = SendMessageW(source, SCI_GETEOLMODE, 0, 0);
        if (eol != SC_EOL_LF) {
            std::string converted;
            converted.reserve(output.size() + output.size()/20);
            for (char c : output) {
                if (c == '\n') converted += eol == SC_EOL_CRLF ? "\r\n" : "\r";
                else converted += c;
            }
            output = std::move(converted);
        }
        if (!new_tab) {
            replace_in_place(source, output, yaml_output);
            return;
        }
        auto old_buffer = SendMessageW(npp._nppHandle, NPPM_GETCURRENTBUFFERID, 0, 0);
        SendMessageW(npp._nppHandle, NPPM_MENUCOMMAND, 0, IDM_FILE_NEW);
        auto new_buffer = SendMessageW(npp._nppHandle, NPPM_GETCURRENTBUFFERID, 0, 0);
        if (!new_buffer || old_buffer == new_buffer) throw yp::ConversionError("Could not create an output tab. Source text was preserved.");
        SendMessageW(npp._nppHandle, NPPM_MENUCOMMAND, 0, IDM_FORMAT_AS_UTF_8);
        HWND target = editor();
        SendMessageW(target, SCI_SETCODEPAGE, SC_CP_UTF8, 0);
        SendMessageW(target, SCI_SETEOLMODE, eol, 0);
        SendMessageW(target, SCI_BEGINUNDOACTION, 0, 0);
        SendMessageW(target, SCI_ADDTEXT, output.size(), reinterpret_cast<LPARAM>(output.data()));
        SendMessageW(target, SCI_ENDUNDOACTION, 0, 0);
        SendMessageW(target, SCI_GOTOPOS, 0, 0);
        SendMessageW(npp._nppHandle, NPPM_SETCURRENTLANGTYPE, 0, yaml_output ? L_YAML : L_PROPS);
        auto title = L"converted-" + std::to_wstring(++output_number) + (yaml_output ? L".yaml" : L".properties");
        SendMessageW(npp._nppHandle, NPPM_SETUNTITLEDNAME, new_buffer, reinterpret_cast<LPARAM>(title.c_str()));
    } catch (const std::exception& error) { report(error.what()); }
    catch (...) { report("Unexpected conversion failure. Source text was preserved."); }
}
void yaml_to_properties() { convert(false); }
void properties_to_yaml() { convert(true); }
void auto_convert() { convert(std::nullopt); }

bool save_settings(bool literal_value, bool new_tab_value) {
    if (settings_path.empty()) return false;
    const std::string text = std::string("[Settings]\r\nLiteralKeys=") + (literal_value ? "1\r\n" : "0\r\n") +
                             "NewTab=" + (new_tab_value ? "1\r\n" : "0\r\n");
    auto temp = settings_path + L".tmp." + std::to_wstring(GetCurrentProcessId());
    HANDLE file = CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    DWORD written = 0;
    bool ok = WriteFile(file, text.data(), static_cast<DWORD>(text.size()), &written, nullptr) && written == text.size();
    if (ok) ok = FlushFileBuffers(file) != FALSE;
    CloseHandle(file);
    if (ok) ok = MoveFileExW(temp.c_str(), settings_path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != FALSE;
    if (!ok) DeleteFileW(temp.c_str());
    return ok;
}
void toggle_literal() {
    if (!save_settings(!literal_keys, new_tab)) {
        report("Could not save settings to the Notepad++ plugin configuration directory. The mode was not changed.");
        return;
    }
    literal_keys = !literal_keys;
    SendMessageW(npp._nppHandle, NPPM_SETMENUITEMCHECK, commands[literal_command]._cmdID, literal_keys);
}
void toggle_new_tab() {
    if (!save_settings(literal_keys, !new_tab)) {
        report("Could not save settings to the Notepad++ plugin configuration directory. The output mode was not changed.");
        return;
    }
    new_tab = !new_tab;
    SendMessageW(npp._nppHandle, NPPM_SETMENUITEMCHECK, commands[new_tab_command]._cmdID, new_tab);
}
void about() {
    MessageBoxW(npp._nppHandle,
        L"YamlProperties " YP_VERSION_W L" (x64)\n\n"
        L"默认在新标签页打开结果，保留原文。\n"
        L"取消勾选后替换选区或全文，可一次撤销；设置自动记忆。\n"
        L"默认：点号表示层级，[0] 表示数组下标。\n"
        L"保留完整键名：将点号和方括号作为普通字符。\n\n"
        L"自动转换：优先识别扩展名，再按内容判断方向。\n"
        L"无扩展名的 key: value 默认视为 YAML。\n"
        L"支持 com.his 等带点键，转回 YAML 时点号展开为层级。\n\n"
        L"YAML 输出值均为字符串。注释、类型和原始排版不保留。\n"
        L"null、空容器、重复键和冲突路径会报错。\n"
        L"新标签页输出为 UTF-8；原位替换保持原编码。\n\n"
        L"转换在本机完成，无网络请求。\n"
        L"YAML parser: yaml-cpp 0.8.0 (MIT).", plugin_name, MB_OK | MB_ICONINFORMATION);
}
}

extern "C" __declspec(dllexport) void setInfo(NppData data) {
    npp = data;
    try {
        std::vector<wchar_t> path(32768, L'\0');
        SendMessageW(npp._nppHandle, NPPM_GETPLUGINSCONFIGDIR, path.size(), reinterpret_cast<LPARAM>(path.data()));
        if (path.front()) {
            CreateDirectoryW(path.data(), nullptr);
            settings_path = std::wstring(path.data()) + L"\\YamlProperties.ini";
            literal_keys = GetPrivateProfileIntW(L"Settings", L"LiteralKeys", 0, settings_path.c_str()) != 0;
            new_tab = GetPrivateProfileIntW(L"Settings", L"NewTab", 1, settings_path.c_str()) != 0;
        }
        const wchar_t* names[] = {L"YAML → Properties", L"Properties → YAML", L"自动识别并转换", L"保留完整键名（不拆分点号和下标）", L"在新标签页打开转换结果", L"---", L"关于 / 转换规则"};
        PFUNCPLUGINCMD handlers[] = {yaml_to_properties, properties_to_yaml, auto_convert, toggle_literal, toggle_new_tab, nullptr, about};
        for (std::size_t i = 0; i < commands.size(); ++i) {
            lstrcpynW(commands[i]._itemName, names[i], menuItemSize);
            commands[i]._pFunc = handlers[i];
        }
        commands[literal_command]._init2Check = literal_keys;
        commands[new_tab_command]._init2Check = new_tab;
    } catch (...) { report("Plugin initialization failed."); }
}
extern "C" __declspec(dllexport) const wchar_t* getName() { return plugin_name; }
extern "C" __declspec(dllexport) FuncItem* getFuncsArray(int* count) {
    *count = static_cast<int>(commands.size());
    return commands.data();
}
extern "C" __declspec(dllexport) void beNotified(SCNotification* notification) {
    if (notification && notification->nmhdr.code == NPPN_READY) {
        SendMessageW(npp._nppHandle, NPPM_SETMENUITEMCHECK, commands[literal_command]._cmdID, literal_keys);
        SendMessageW(npp._nppHandle, NPPM_SETMENUITEMCHECK, commands[new_tab_command]._cmdID, new_tab);
    }
}
extern "C" __declspec(dllexport) LRESULT messageProc(UINT, WPARAM, LPARAM) { return TRUE; }
extern "C" __declspec(dllexport) BOOL isUnicode() { return TRUE; }
BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }
