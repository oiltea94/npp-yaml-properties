#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
int launches = 0, errors = 0;
INT_PTR launch_result = 33;
HWND launch_owner = nullptr;
std::wstring launch_url, launch_verb, error_text;
int launch_show = 0;
HINSTANCE WINAPI test_shell(HWND owner, LPCWSTR verb, LPCWSTR file, LPCWSTR, LPCWSTR, int show) {
    ++launches;
    launch_owner = owner;
    launch_verb = verb;
    launch_url = file;
    launch_show = show;
    return reinterpret_cast<HINSTANCE>(launch_result);
}
int WINAPI test_message(HWND, LPCWSTR text, LPCWSTR, UINT) {
    ++errors;
    error_text = text;
    return IDOK;
}
HRESULT WINAPI test_task_dialog(const TASKDIALOGCONFIG*, int*, int*, BOOL*) {
    return S_OK;
}
void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
}

// Exercise the production callback; replace only the OS side effects.
#define ShellExecuteW test_shell
#define MessageBoxW test_message
#define TaskDialogIndirect test_task_dialog
#include "../src/plugin.cpp"
#undef ShellExecuteW
#undef MessageBoxW
#undef TaskDialogIndirect

int main() {
    try {
        auto owner = reinterpret_cast<HWND>(1);
        auto data = reinterpret_cast<LONG_PTR>(&yp::english_ui);
        about_callback(owner, TDN_CREATED, 0, 0, data);
        about_callback(owner, TDN_BUTTON_CLICKED, IDOK, 0, data);
        check(launches == 0, "Opening or closing About must not launch a browser");
        auto result = about_callback(owner, TDN_HYPERLINK_CLICKED, 0,
                                     reinterpret_cast<LPARAM>(L"https://example.invalid"), data);
        check(result == S_OK && launches == 1 && errors == 0, "Click must launch once and keep About open");
        check(launch_owner == owner && launch_verb == L"open" && launch_show == SW_SHOWNORMAL,
              "Click must use the system URL handler");
        check(launch_url == L"https://github.com/oiltea94/npp-yaml-properties", "Click must open the fixed project URL");
        for (const auto* language : {&yp::english_ui, &yp::simplified_chinese_ui, &yp::traditional_chinese_ui}) {
            for (INT_PTR failure : {0, 31, 32}) {
                launch_result = failure;
                int previous = errors;
                about_callback(owner, TDN_HYPERLINK_CLICKED, 0, 0, reinterpret_cast<LONG_PTR>(language));
                check(errors == previous + 1 && error_text == language->homepage_error,
                      "Browser failure must show the localized fallback URL");
            }
        }
        std::cout << "PASS About click, fixed URL, system handler, non-click events and localized launch failures\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
