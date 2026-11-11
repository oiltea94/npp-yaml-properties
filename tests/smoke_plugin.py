"""Exercise the built DLL in an isolated, hidden copy of real Notepad++."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import json
import shutil
import subprocess
import time
from support import ARCH, TARGETS, DIST, EVIDENCE, NPP_DIR, RUNTIME as TARGET_RUNTIME, pe_machine

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = TARGET_RUNTIME / 'npp'
u = C.WinDLL('user32', use_last_error=True)
k = C.WinDLL('kernel32', use_last_error=True)
PTR = C.c_void_p
SIZE = C.c_size_t
LPARAM = C.c_ssize_t
CALLBACK = C.WINFUNCTYPE(W.BOOL, W.HWND, LPARAM)

def declare(dll, name, result, *arguments):
    f = getattr(dll, name)
    f.restype, f.argtypes = result, list(arguments)
    return f

declare(u, 'EnumWindows', W.BOOL, CALLBACK, LPARAM)
declare(u, 'EnumChildWindows', W.BOOL, W.HWND, CALLBACK, LPARAM)
declare(u, 'GetWindowThreadProcessId', W.DWORD, W.HWND, C.POINTER(W.DWORD))
declare(u, 'GetClassNameW', C.c_int, W.HWND, W.LPWSTR, C.c_int)
declare(u, 'ShowWindow', W.BOOL, W.HWND, C.c_int)
declare(u, 'IsWindow', W.BOOL, W.HWND)
declare(u, 'GetMenu', W.HMENU, W.HWND)
declare(u, 'GetSubMenu', W.HMENU, W.HMENU, C.c_int)
declare(u, 'GetMenuItemCount', C.c_int, W.HMENU)
declare(u, 'GetMenuItemID', W.UINT, W.HMENU, C.c_int)
declare(u, 'GetMenuStringW', C.c_int, W.HMENU, W.UINT, W.LPWSTR, C.c_int, W.UINT)
declare(u, 'GetMenuState', W.UINT, W.HMENU, W.UINT, W.UINT)
declare(u, 'SendMessageTimeoutW', LPARAM, W.HWND, W.UINT, SIZE, LPARAM, W.UINT, W.UINT, C.POINTER(SIZE))
declare(u, 'PostMessageW', W.BOOL, W.HWND, W.UINT, SIZE, LPARAM)
declare(k, 'OpenProcess', W.HANDLE, W.DWORD, W.BOOL, W.DWORD)
declare(k, 'VirtualAllocEx', PTR, W.HANDLE, PTR, SIZE, W.DWORD, W.DWORD)
declare(k, 'VirtualFreeEx', W.BOOL, W.HANDLE, PTR, SIZE, W.DWORD)
declare(k, 'WriteProcessMemory', W.BOOL, W.HANDLE, PTR, PTR, SIZE, C.POINTER(SIZE))
declare(k, 'ReadProcessMemory', W.BOOL, W.HANDLE, PTR, PTR, SIZE, C.POINTER(SIZE))
declare(k, 'CloseHandle', W.BOOL, W.HANDLE)

def send(hwnd, message, wparam=0, lparam=0):
    result = SIZE()
    if not u.SendMessageTimeoutW(hwnd, message, wparam, lparam, 2, 10000, C.byref(result)):
        raise RuntimeError(f'Window message {message} timed out or failed: {C.get_last_error()}')
    return result.value

def classname(hwnd):
    value = C.create_unicode_buffer(256)
    u.GetClassNameW(hwnd, value, len(value))
    return value.value

def windows(pid, parent=None):
    result = []
    @CALLBACK
    def collect(hwnd, unused):
        owner = W.DWORD()
        u.GetWindowThreadProcessId(hwnd, C.byref(owner))
        if owner.value == pid:
            result.append(hwnd)
        return True
    if parent:
        u.EnumChildWindows(parent, collect, 0)
    else:
        u.EnumWindows(collect, 0)
    return result

def until(f, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = f()
        if value:
            return value
        time.sleep(0.05)
    raise TimeoutError('Timed out waiting for Notepad++')

def menus(menu):
    result = {}
    for i in range(u.GetMenuItemCount(menu)):
        value = C.create_unicode_buffer(256)
        u.GetMenuStringW(menu, i, value, len(value), 0x400)
        child = u.GetSubMenu(menu, i)
        if child:
            result.update(menus(child))
        else:
            result[value.value] = u.GetMenuItemID(menu, i)
    return result

class Remote:
    def __init__(self, process, data):
        self.process = process
        self.address = k.VirtualAllocEx(process, None, len(data), 0x3000, 4)
        if not self.address:
            raise C.WinError(C.get_last_error())
        if not k.WriteProcessMemory(process, self.address, C.c_char_p(data), len(data), None):
            k.VirtualFreeEx(process, self.address, 0, 0x8000)
            raise C.WinError(C.get_last_error())
    def read(self, length):
        data = C.create_string_buffer(length)
        if not k.ReadProcessMemory(self.process, self.address, data, length, None):
            raise C.WinError(C.get_last_error())
        return data.raw
    def __enter__(self):
        return self
    def __exit__(self, *unused):
        k.VirtualFreeEx(self.process, self.address, 0, 0x8000)

def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    source = NPP_DIR
    assert pe_machine((source/'notepad++.exe').read_bytes()) == TARGETS[ARCH][1], 'Notepad++ architecture mismatch'
    for name in ['notepad++.exe', 'langs.model.xml', 'stylers.model.xml']:
        shutil.copy2(source / name, RUNTIME / name)
    (RUNTIME / 'doLocalConf.xml').write_text('', encoding='utf-8')
    destination = RUNTIME / 'plugins/YamlProperties'
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DIST / 'YamlProperties/YamlProperties.dll', destination / 'YamlProperties.dll')
    config = RUNTIME / 'plugins/config/YamlProperties.ini'
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('[Settings]\nLiteralKeys=1\nQuoteAll=1\n', encoding='ascii')
    initial = 'server:\n  port: 8080\nname: 中文\nservers: [localhost, example.com]\n'
    fixture = RUNTIME / 'sample.yaml'
    fixture.write_bytes(initial.encode('utf-8'))
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen([str(RUNTIME / 'notepad++.exe'), '-multiInst', '-nosession', '-noUpdater', str(fixture)], cwd=RUNTIME, startupinfo=startup)
    handle = None
    results = []
    def passed(name, **details):
        results.append({'test': name, 'result': 'PASS', **details})
        print('PASS ' + name, flush=True)
    try:
        hwnd = until(lambda: next((h for h in windows(process.pid) if classname(h) == 'Notepad++'), None))
        u.ShowWindow(hwnd, 0)
        commands = until(lambda: (m if 'YAML → Properties' in m else None) if (m := menus(u.GetMenu(hwnd))) else None)
        handle = k.OpenProcess(0x0038 | 0x0400, False, process.pid)
        if not handle:
            raise C.WinError(C.get_last_error())
        def read(sci, encoding='utf-8'):
            length = send(sci, 2006)
            with Remote(handle, bytes(length+1)) as memory:
                send(sci, 2182, length+1, memory.address)
                return memory.read(length).decode(encoding)
        sci = until(lambda: next((h for h in windows(process.pid, hwnd) if classname(h) == 'Scintilla' and read(h) == initial), None))
        passed('native DLL loaded and conversion menus registered')
        output_toggle = commands.get('在新标签页打开转换结果')
        assert output_toggle is not None, 'Missing configurable output menu'
        assert u.GetMenuState(u.GetMenu(hwnd), output_toggle, 0) & 8
        passed('old configuration defaults to checked new-tab output')
        assert '键和值始终加双引号' not in commands
        assert '保留完整键名（不拆分点号和下标）' not in commands
        passed('removed menus are absent even with legacy enabled settings')
        start_index = send(hwnd, 2024+23, 0, 0)
        tabs = send(hwnd, 2024+7, 0, 0)
        send(hwnd, 0x111, commands['YAML → Properties'])
        properties = read(sci)
        assert properties == 'server.port=8080\nname=中文\nservers[0]=localhost\nservers[1]=example.com\n', repr(properties)
        assert send(hwnd, 2024+7, 0, 0) == tabs+1
        passed('YAML menu creates a new UTF-8 Properties tab', output=properties)
        props_index = send(hwnd, 2024+23, 0, 0)
        send(hwnd, 2024+28, 0, start_index)
        assert read(sci) == initial and send(sci, 2159) == 0
        passed('source text and unmodified state preserved')
        send(hwnd, 2024+28, 0, props_index)
        send(hwnd, 0x111, commands['Properties → YAML'])
        yaml = read(sci)
        assert 'port: 8080' in yaml and 'name: 中文' in yaml and '- localhost' in yaml
        passed('Properties menu leaves originally unquoted values unquoted', output=yaml)
        send(hwnd, 2024+28, 0, start_index)
        begin = len(initial[:initial.index('name:')].encode('utf-8'))
        end = begin + len('name: 中文\n'.encode('utf-8'))
        send(sci, 2160, begin, end)
        send(hwnd, 0x111, commands['YAML → Properties'])
        assert read(sci) == 'name=中文\n'
        passed('single selection converts independently')
        def open_fixture(name, text):
            path = RUNTIME / name
            content = text.encode('utf-8')
            if not path.exists() or path.read_bytes() != content:
                path.write_bytes(content)
            with Remote(handle, (str(path)+'\0').encode('utf-16le')) as memory:
                send(hwnd, 2024+77, 0, memory.address)
        logger_yaml = ('logging:\n  level:\n    com.example: off\n'
                       '    com.example.dao.Mapper: debug\n    org.example: debug\n')
        logger_properties = ('logging.level.com.example=off\n'
                             'logging.level.com.example.dao.Mapper=debug\nlogging.level.org.example=debug\n')
        open_fixture('logging.yaml', logger_yaml)
        send(hwnd, 0x111, commands['YAML → Properties'])
        assert read(sci) == logger_properties
        passed('dotted logging keys convert without changing manual mode', output=read(sci))
        open_fixture('logging.yaml', logger_yaml)
        send(hwnd, 0x111, commands['自动识别并转换'])
        assert read(sci) == logger_properties
        passed('optional auto command detects YAML filename', output=read(sci))
        send(hwnd, 0x111, commands['自动识别并转换'])
        logger_result = read(sci).replace('\r\n', '\n')
        assert logger_result == ('logging:\n  level:\n'
                                 '    com.example: off\n'
                                 '    com.example.dao.Mapper: debug\n'
                                 '    org.example: debug\n'), repr(logger_result)
        passed('auto command detects generated Properties tab', output=logger_result)
        open_fixture('colon.properties', 'key: value\n')
        send(hwnd, 0x111, commands['自动识别并转换'])
        assert read(sci) == 'key: value\n'
        passed('Properties extension resolves ambiguous colon syntax')
        original_quotes = 'logging.pattern.file="%d{HH:mm:ss} %m%n"\nprofile=\'${profileActive}\'\ncode=00123\nflag=off\n'
        for command in ['Properties → YAML', '自动识别并转换']:
            open_fixture('source-quotes.properties', original_quotes)
            send(hwnd, 0x111, commands[command])
            assert read(sci) == 'logging:\n  pattern:\n    file: "%d{HH:mm:ss} %m%n"\nprofile: \'${profileActive}\'\ncode: 00123\nflag: off\n'
        passed('manual and auto conversion retain existing quotes without adding new ones', output=read(sci))
        quoted_yaml = 'logging:\n  pattern:\n    file: "%d{HH:mm:ss} %m%n"\nprofile: "${profileActive}"\ncode: "00123"\nflag: off\ntext: "line\\nnext"\n'
        quoted_properties = 'logging.pattern.file="%d{HH:mm:ss} %m%n"\nprofile="${profileActive}"\ncode="00123"\nflag=off\ntext="line\\\\nnext"\n'
        for command in ['YAML → Properties', '自动识别并转换']:
            open_fixture('quoted-values.yaml', quoted_yaml)
            send(hwnd, 0x111, commands[command])
            assert read(sci) == quoted_properties, repr(read(sci))
            send(hwnd, 0x111, commands['Properties → YAML'])
            assert read(sci) == quoted_yaml, repr(read(sci))
        passed('manual and auto YAML conversion preserve double quotes and escapes through a round trip', output=read(sci))
        open_fixture('unknown.txt', logger_yaml)
        send(hwnd, 0x111, commands['自动识别并转换'])
        assert read(sci) == logger_properties
        passed('auto command detects content for unknown extension')
        bad = RUNTIME / 'invalid.properties'
        bad.write_bytes(b'duplicate=1\nduplicate=2\n')
        with Remote(handle, (str(bad)+'\0').encode('utf-16le')) as memory:
            send(hwnd, 2024+77, 0, memory.address)
        tabs = send(hwnd, 2024+7, 0, 0)
        u.PostMessageW(hwnd, 0x111, commands['Properties → YAML'], 0)
        dialog = until(lambda: next((h for h in windows(process.pid) if classname(h) == '#32770'), None))
        u.ShowWindow(dialog, 0)
        texts = []
        for h in windows(process.pid, dialog):
            if classname(h) == 'Static':
                text = C.create_unicode_buffer(2048)
                send(h, 0xD, len(text), C.addressof(text))
                texts.append(text.value)
        assert 'Duplicate' in '\n'.join(texts) and 'line 2' in '\n'.join(texts), texts
        send(dialog, 0x10)  # WM_CLOSE dismisses the native message box.
        until(lambda: not u.IsWindow(dialog))
        assert send(hwnd, 2024+7, 0, 0) == tabs
        assert read(sci) == 'duplicate=1\nduplicate=2\n'
        passed('invalid input shows line number and leaves tabs/source unchanged', message=texts)

        # Saving the remaining output preference drops obsolete settings.
        send(hwnd, 0x111, output_toggle)
        assert config.read_text() == '[Settings]\nNewTab=0\n'
        assert not u.GetMenuState(u.GetMenu(hwnd), output_toggle, 0) & 8
        passed('output preference persists and removes both obsolete settings')

        open_fixture('inplace.yaml', initial)
        tabs = send(hwnd, 2024+7)
        buffer = send(hwnd, 2024+60)
        encoding = send(hwnd, 2024+66, buffer)
        send(hwnd, 0x111, commands['YAML → Properties'])
        assert read(sci) == properties
        assert send(hwnd, 2024+7) == tabs and send(hwnd, 2024+60) == buffer
        assert send(hwnd, 2024+66, buffer) == encoding and send(sci, 2159)
        assert (RUNTIME / 'inplace.yaml').read_bytes() == initial.encode('utf-8')
        passed('whole-document replacement retains tab, encoding and disk file', output=read(sci))
        send(sci, 2176)  # SCI_UNDO
        assert read(sci) == initial and send(sci, 2159) == 0
        send(sci, 2011)  # SCI_REDO
        assert read(sci) == properties
        passed('whole-document conversion is one undo and redo action')
        send(hwnd, 0x111, commands['Properties → YAML'])
        assert 'port: 8080' in read(sci) and 'name: 中文' in read(sci)
        assert send(hwnd, 2024+7) == tabs and send(hwnd, 2024+60) == buffer
        passed('reverse conversion also replaces the current document')

        prefix, selected, suffix = '# 前缀😀\r\n', 'name: 中文\r\n', '# 后缀\r\n'
        selection_source = prefix + selected + suffix
        open_fixture('inplace-selection.yaml', selection_source)
        buffer = send(hwnd, 2024+60)
        language = send(hwnd, 2024+64, buffer)
        tabs = send(hwnd, 2024+7)
        begin, end = len(prefix.encode('utf-8')), len((prefix+selected).encode('utf-8'))
        send(sci, 2160, end, begin)  # Backward selection, byte offsets.
        send(hwnd, 0x111, commands['YAML → Properties'])
        assert read(sci) == prefix + 'name=中文\r\n' + suffix
        assert send(hwnd, 2024+7) == tabs and send(hwnd, 2024+60) == buffer
        assert send(hwnd, 2024+64, buffer) == language
        assert send(sci, 2143) == begin
        assert send(sci, 2145) == begin + len('name=中文\r\n'.encode('utf-8'))
        passed('selection replacement preserves surrounding Unicode, CRLF and document language')
        send(sci, 2176)
        assert read(sci) == selection_source and send(sci, 2159) == 0
        passed('selection conversion is undone in one step')

        open_fixture('inplace-auto.txt', logger_yaml)
        buffer, tabs = send(hwnd, 2024+60), send(hwnd, 2024+7)
        send(hwnd, 0x111, commands['自动识别并转换'])
        assert read(sci) == logger_properties
        assert send(hwnd, 2024+60) == buffer and send(hwnd, 2024+7) == tabs
        passed('automatic conversion respects in-place output')

        def expect_error(command, expected):
            before, buffer, tabs = read(sci), send(hwnd, 2024+60), send(hwnd, 2024+7)
            u.PostMessageW(hwnd, 0x111, command, 0)
            dialog = until(lambda: next((h for h in windows(process.pid) if classname(h) == '#32770'), None))
            u.ShowWindow(dialog, 0)
            texts = []
            for child in windows(process.pid, dialog):
                if classname(child) == 'Static':
                    value = C.create_unicode_buffer(2048)
                    send(child, 0xD, len(value), C.addressof(value))
                    texts.append(value.value)
            send(dialog, 0x10)
            until(lambda: not u.IsWindow(dialog))
            assert expected in '\n'.join(texts), texts
            assert read(sci) == before
            assert send(hwnd, 2024+60) == buffer and send(hwnd, 2024+7) == tabs

        open_fixture('invalid.properties', 'duplicate=1\nduplicate=2\n')
        expect_error(commands['Properties → YAML'], 'Duplicate')
        assert send(sci, 2159) == 0
        passed('conversion errors preserve in-place text and modified state')
        open_fixture('readonly.yaml', 'name: value\n')
        send(sci, 2171, 1)  # SCI_SETREADONLY
        try:
            expect_error(commands['YAML → Properties'], 'read-only')
            assert send(sci, 2159) == 0
            passed('read-only documents are unchanged with an actionable error')
        finally:
            send(sci, 2171, 0)

        open_fixture('legacy.properties', 'name=\\u4e2d\\u6587\n')
        send(hwnd, 2024+48, 0, 45061)  # Encoding > GB2312.
        codepage = send(sci, 2137)
        buffer, tabs = send(hwnd, 2024+60), send(hwnd, 2024+7)
        send(hwnd, 0x111, commands['Properties → YAML'])
        assert read(sci, 'utf-8' if codepage == 65001 else 'gbk') == 'name: 中文\n'
        assert send(sci, 2137) == codepage and send(hwnd, 2024+60) == buffer
        assert send(hwnd, 2024+7) == tabs
        send(sci, 2176)
        assert read(sci) == 'name=\\u4e2d\\u6587\n'
        passed('legacy document encoding survives replacement and undo', codepage=codepage)

        open_fixture('legacy-unrepresentable.properties', 'emoji=\\uD83D\\uDE00\n')
        send(hwnd, 2024+48, 0, 45061)
        assert u.GetMenuState(u.GetMenu(hwnd), 45061, 0) & 8
        expect_error(commands['Properties → YAML'], 'document encoding')
        passed('unrepresentable characters produce an error without replacement')

        open_fixture('readonly.yaml', 'name: value\n')

        # Force the atomic settings writer to fail without touching a user directory.
        blocked_temp = Path(str(config) + '.tmp.' + str(process.pid))
        blocked_temp.mkdir()
        saved_config = config.read_bytes()
        try:
            expect_error(output_toggle, 'Could not save settings')
            assert config.read_bytes() == saved_config
            assert not u.GetMenuState(u.GetMenu(hwnd), output_toggle, 0) & 8
            passed('failed preference save preserves configuration and menu state')
        finally:
            blocked_temp.rmdir()

        assert config.read_text() == '[Settings]\nNewTab=0\n'
        # Restart the isolated editor to verify loading the remaining setting from disk.
        k.CloseHandle(handle)
        handle = None
        process.terminate()
        process.wait(timeout=10)
        process = subprocess.Popen([str(RUNTIME / 'notepad++.exe'), '-multiInst', '-nosession', '-noUpdater', str(fixture)], cwd=RUNTIME, startupinfo=startup)
        hwnd = until(lambda: next((h for h in windows(process.pid) if classname(h) == 'Notepad++'), None))
        u.ShowWindow(hwnd, 0)
        commands = until(lambda: (m if '在新标签页打开转换结果' in m else None) if (m := menus(u.GetMenu(hwnd))) else None)
        handle = k.OpenProcess(0x0038 | 0x0400, False, process.pid)
        if not handle:
            raise C.WinError(C.get_last_error())
        sci = until(lambda: next((h for h in windows(process.pid, hwnd) if classname(h) == 'Scintilla' and read(h) == initial), None))
        output_toggle = commands['在新标签页打开转换结果']
        assert '保留完整键名（不拆分点号和下标）' not in commands
        assert '键和值始终加双引号' not in commands
        assert not u.GetMenuState(u.GetMenu(hwnd), output_toggle, 0) & 8
        open_fixture('restart.properties', 'a.b=1\n')
        buffer, tabs = send(hwnd, 2024+60), send(hwnd, 2024+7)
        send(hwnd, 0x111, commands['Properties → YAML'])
        assert read(sci) == 'a:\n  b: 1\n'
        assert send(hwnd, 2024+60) == buffer and send(hwnd, 2024+7) == tabs
        passed('output preference and fixed hierarchical conversion survive editor restart')
        send(hwnd, 0x111, output_toggle)
        assert config.read_text() == '[Settings]\nNewTab=1\n'
        open_fixture('restart.properties', 'a.b=1\n')
        # The open tab contains unsaved YAML from the previous conversion.
        send(hwnd, 0x111, commands['YAML → Properties'])
        assert read(sci) == 'a.b=1\n' and send(hwnd, 2024+7) == tabs+1
        passed('reenabling new-tab output takes effect with hierarchical keys')
    finally:
        if handle:
            k.CloseHandle(handle)
        process.terminate()
        process.wait(timeout=10)
        (EVIDENCE / 'plugin-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{len(results)} real Notepad++ checks passed', flush=True)

if __name__ == '__main__':
    main()
