#pragma once
#include <array>
#include <string>

namespace yp {
struct UiText {
    std::array<const wchar_t*, 7> menus;
    const wchar_t* about;
    const char* output_save_error;
    const char* sort_save_error;
};

inline constexpr UiText english_ui = {
    {L"YAML → Properties", L"Properties → YAML", L"Auto-detect and convert",
     L"Open conversion result in a new tab", L"Sort keys during conversion", L"---", L"About / Conversion rules"},
    L"Results open in a new tab by default, preserving the source.\n"
    L"Uncheck this option to replace the selection or document with one-step undo. Preferences are saved.\n"
    L"Dots represent nesting; [0] represents an array index.\n\n"
    L"Optional key sorting is off by default and its setting is saved.\n"
    L"Keys are sorted within each level, case-sensitively; array element order is unchanged.\n\n"
    L"Auto conversion checks the file extension first, then the content.\n"
    L"Without a known extension, key: value is treated as YAML.\n"
    L"Complete logger names are retained under logging.level; other dotted paths are expanded.\n\n"
    L"Existing Properties quotes are preserved; no quotes are added automatically.\n"
    L"YAML readers determine the types of unquoted values.\n"
    L"Comments and original formatting are not preserved.\n"
    L"Nulls, empty containers, duplicate keys and conflicting paths produce errors.\n"
    L"New tabs use UTF-8; in-place replacement preserves the document encoding.\n\n"
    L"Conversion runs locally without network requests.\n"
    L"YAML parser: yaml-cpp 0.8.0 (MIT).\n\n"
    L"Project homepage (GitHub):\nhttps://github.com/oiltea94/npp-yaml-properties",
    "Could not save settings to the Notepad++ plugin configuration directory. The output mode was not changed.",
    "Could not save settings to the Notepad++ plugin configuration directory. The sorting mode was not changed."
};

inline constexpr UiText simplified_chinese_ui = {
    {L"YAML → Properties", L"Properties → YAML", L"自动识别并转换", L"在新标签页打开转换结果",
     L"转换时按键名排序", L"---", L"关于 / 转换规则"},
    L"默认在新标签页打开结果，保留原文。\n"
    L"取消勾选后替换选区或全文，可一次撤销；设置自动记忆。\n"
    L"点号表示层级，[0] 表示数组下标。\n\n"
    L"可选：转换时按键名排序，默认关闭并记忆设置。\n"
    L"开启后按每层键名升序排列，区分大小写，数组元素顺序不变。\n\n"
    L"自动转换：优先识别扩展名，再按内容判断方向。\n"
    L"无扩展名的 key: value 默认视为 YAML。\n"
    L"支持带点键；logging.level 下保留完整日志名称，其余按点号展开。\n\n"
    L"默认保留 Properties 中已有的引号，不自动添加引号。\n"
    L"未加引号的值由 YAML 读取器识别类型。\n"
    L"注释和原始排版不保留。\n"
    L"null、空容器、重复键和冲突路径会报错。\n"
    L"新标签页输出为 UTF-8；原位替换保持原编码。\n\n"
    L"转换在本机完成，无网络请求。\n"
    L"YAML 解析器：yaml-cpp 0.8.0（MIT）。\n\n"
    L"项目主页（GitHub）：\nhttps://github.com/oiltea94/npp-yaml-properties",
    "未能将设置保存到 Notepad++ 插件配置目录。输出方式未更改。",
    "未能将设置保存到 Notepad++ 插件配置目录。排序方式未更改。"
};

inline constexpr UiText traditional_chinese_ui = {
    {L"YAML → Properties", L"Properties → YAML", L"自動識別並轉換", L"在新分頁開啟轉換結果",
     L"轉換時依鍵名排序", L"---", L"關於 / 轉換規則"},
    L"預設在新分頁開啟結果，保留原文。\n"
    L"取消勾選後取代選取範圍或全文，可一次復原；設定自動記憶。\n"
    L"點號表示階層，[0] 表示陣列索引。\n\n"
    L"可選：轉換時依鍵名排序，預設關閉並記憶設定。\n"
    L"開啟後依每層鍵名遞增排序，區分大小寫，陣列元素順序不變。\n\n"
    L"自動轉換：優先識別副檔名，再依內容判斷方向。\n"
    L"無副檔名的 key: value 預設視為 YAML。\n"
    L"支援含點號的鍵；logging.level 下保留完整日誌名稱，其餘依點號展開。\n\n"
    L"預設保留 Properties 中已有的引號，不自動新增引號。\n"
    L"未加引號的值由 YAML 讀取器識別型別。\n"
    L"註解和原始排版不保留。\n"
    L"null、空容器、重複鍵和衝突路徑會報錯。\n"
    L"新分頁輸出為 UTF-8；原位取代保持原編碼。\n\n"
    L"轉換在本機完成，無網路請求。\n"
    L"YAML 解析器：yaml-cpp 0.8.0（MIT）。\n\n"
    L"專案首頁（GitHub）：\nhttps://github.com/oiltea94/npp-yaml-properties",
    "未能將設定儲存至 Notepad++ 外掛設定目錄。輸出方式未變更。",
    "未能將設定儲存至 Notepad++ 外掛設定目錄。排序方式未變更。"
};

inline const UiText& ui_text(std::string native_language_file) {
    for (char& c : native_language_file)
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + ('a' - 'A'));
    if (native_language_file == "chinesesimplified.xml") return simplified_chinese_ui;
    if (native_language_file == "taiwanesemandarin.xml" || native_language_file == "hongkongcantonese.xml" ||
        native_language_file == "chinese.xml") return traditional_chinese_ui;
    return english_ui;
}
}
