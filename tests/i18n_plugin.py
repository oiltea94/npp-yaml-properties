"""Verify startup and live UI language changes in isolated real Notepad++ hosts."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import json
import shutil
import subprocess
import tempfile
from support import DIST, NPP_DIR, RUNTIME, EVIDENCE
from smoke_plugin import u, declare, windows, classname, menus, until, send

declare(u, 'GetWindowTextW', C.c_int, W.HWND, W.LPWSTR, C.c_int)
declare(u, 'GetDlgCtrlID', C.c_int, W.HWND)
declare(u, 'GetParent', W.HWND, W.HWND)

LOCALES = ['english.xml', 'chineseSimplified.xml', 'taiwaneseMandarin.xml',
           'hongKongCantonese.xml', 'french.xml']
LABELS = {
    'en': ['Auto-detect and convert', 'Open conversion result in a new tab',
           'Sort keys during conversion', 'About / Conversion rules', 'Conversion runs locally'],
    'zh-CN': ['自动识别并转换', '在新标签页打开转换结果', '转换时按键名排序', '关于 / 转换规则', '转换在本机完成'],
    'zh-TW': ['自動識別並轉換', '在新分頁開啟轉換結果', '轉換時依鍵名排序', '關於 / 轉換規則', '轉換在本機完成'],
}
LANGUAGE = {'english.xml': 'en', 'chineseSimplified.xml': 'zh-CN',
            'taiwaneseMandarin.xml': 'zh-TW', 'hongKongCantonese.xml': 'zh-TW', 'french.xml': 'en'}
DISPLAY_NAMES = {'english.xml': 'English', 'chineseSimplified.xml': '中文简体',
                 'taiwaneseMandarin.xml': '台灣繁體', 'hongKongCantonese.xml': '香港繁體', 'french.xml': 'Français'}
SAVE_ERROR = {'en': 'Could not save settings', 'zh-CN': '未能将设置保存', 'zh-TW': '未能將設定儲存'}


def main():
    base = (RUNTIME/'i18n').resolve()
    base.mkdir(parents=True, exist_ok=True)
    results = []
    for startup_locale in LOCALES:
        folder = Path(tempfile.mkdtemp(prefix='host-', dir=base))
        for name in ['notepad++.exe', 'langs.model.xml', 'stylers.model.xml']:
            shutil.copy2(NPP_DIR/name, folder/name)
        (folder/'localization').mkdir()
        for name in LOCALES:
            shutil.copy2(NPP_DIR/'localization'/name, folder/'localization'/name)
        if startup_locale != 'english.xml':
            shutil.copy2(folder/'localization'/startup_locale, folder/'nativeLang.xml')
        (folder/'doLocalConf.xml').write_text('')
        plugin = folder/'plugins/YamlProperties'
        plugin.mkdir(parents=True)
        shutil.copy2(DIST/'YamlProperties/YamlProperties.dll', plugin/'YamlProperties.dll')
        config = folder/'plugins/config/YamlProperties.ini'
        config.parent.mkdir(parents=True)
        config.write_bytes(b'[Settings]\r\nNewTab=0\r\nSortKeys=1\r\n')
        original_settings = config.read_bytes()
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        process = subprocess.Popen([str(folder/'notepad++.exe'), '-multiInst', '-nosession', '-noUpdater'],
                                   cwd=folder, startupinfo=startup)
        try:
            hwnd = until(lambda: next((h for h in windows(process.pid) if classname(h)=='Notepad++'), None))
            u.ShowWindow(hwnd, 0)
            until(lambda: 'YAML → Properties' in menus(u.GetMenu(hwnd)))
            ids = None

            def dialog_body(command):
                u.PostMessageW(hwnd, 0x111, command, 0)
                def plugin_dialog():
                    for window in windows(process.pid):
                        title = C.create_unicode_buffer(256)
                        u.GetWindowTextW(window, title, len(title))
                        if classname(window)=='#32770' and title.value=='YamlProperties':
                            return window
                    return None
                dialog = until(plugin_dialog)
                u.ShowWindow(dialog, 0)
                def dialog_text():
                    texts = []
                    for child in windows(process.pid, dialog):
                        if classname(child) == 'Static':
                            text = C.create_unicode_buffer(8192)
                            u.GetWindowTextW(child, text, len(text))
                            texts.append(text.value)
                    return '\n'.join(texts).strip()
                body = until(dialog_text)
                u.PostMessageW(dialog, 0x10, 0, 0)
                until(lambda: not u.IsWindow(dialog))
                return body

            def check_ui(locale, phase):
                nonlocal ids
                labels = LABELS[LANGUAGE[locale]]
                until(lambda: labels[0] in menus(u.GetMenu(hwnd)))
                current = menus(u.GetMenu(hwnd))
                assert all(label in current for label in labels[:4]), (locale, list(current))
                current_ids = [current[label] for label in labels[:4]]
                if ids is None:
                    ids = current_ids
                assert current_ids == ids, 'Language switch changed command IDs'
                assert not u.GetMenuState(u.GetMenu(hwnd), ids[1], 0) & 8
                assert u.GetMenuState(u.GetMenu(hwnd), ids[2], 0) & 8
                assert config.read_bytes() == original_settings, 'Language switch changed preferences'
                for other in LABELS.values():
                    if other != labels:
                        assert all(label not in current for label in other[:4])
                body = dialog_body(ids[3])
                assert labels[4] in body, (locale, body)
                assert 'YamlProperties ' in body and 'yaml-cpp 0.8.0' in body
                blocked_temp = config.with_name(config.name+'.tmp.'+str(process.pid))
                blocked_temp.mkdir()
                try:
                    for command in ids[1:3]:
                        assert SAVE_ERROR[LANGUAGE[locale]] in dialog_body(command)
                    assert config.read_bytes() == original_settings
                    assert not u.GetMenuState(u.GetMenu(hwnd), ids[1], 0) & 8
                    assert u.GetMenuState(u.GetMenu(hwnd), ids[2], 0) & 8
                finally:
                    blocked_temp.rmdir()
                results.append({'phase': phase, 'locale': locale, 'result': 'PASS', 'labels': labels[:4]})
                print(f'PASS {phase}: {locale}', flush=True)

            check_ui(startup_locale, 'startup')
            if startup_locale == 'english.xml':
                for locale in LOCALES[1:]+['english.xml']:
                    u.PostMessageW(hwnd, 0x111, 48011, 0)
                    def find_combo():
                        for top in windows(process.pid):
                            for child in windows(process.pid, top):
                                if classname(child)=='ComboBox' and u.GetDlgCtrlID(child)==6124:
                                    return child
                        return None
                    combo = until(find_combo)
                    parent = u.GetParent(combo)
                    labels = []
                    for index in range(send(combo, 0x146)):
                        text = C.create_unicode_buffer(512)
                        send(combo, 0x148, index, C.addressof(text))
                        labels.append(text.value)
                    name = DISPLAY_NAMES[locale]
                    assert name in labels, (name, labels)
                    send(combo, 0x14e, labels.index(name))
                    send(parent, 0x111, (1 << 16) | 6124, combo)
                    # Close the modeless preferences window before checking About.
                    preferences = u.GetParent(parent)
                    send(preferences, 0x111, 6001)
                    expected = LABELS[LANGUAGE[locale]][0]
                    until(lambda: expected in menus(u.GetMenu(hwnd)))
                    check_ui(locale, 'live switch')
        finally:
            process.terminate()
            process.wait(timeout=10)
            (EVIDENCE/'plugin-i18n.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{len(results)} real Notepad++ language checks passed', flush=True)


if __name__ == '__main__':
    main()
