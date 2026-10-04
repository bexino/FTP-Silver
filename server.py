# -*- coding: utf-8 -*-
"""
FTP 服务器（只读 / 读写，简体中文 / English）

- 直接运行（无参数）: 先选语言，再交互选择共享目录与访问模式，成功启动后自动在
  程序同目录生成一键启动脚本 start.bat（语言随当前选择）
- 通过 start.bat（--launch 参数）运行: 打印记住的参数，按回车即按这些参数启动

构建: 双击 build.bat（产物 dist/FTPServer.exe，单文件免依赖，仅需 Windows x64）
"""
import argparse
import ctypes
import logging
import os
import random
import secrets
import socket
import subprocess
import sys
import tempfile

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

PASSWORD_CHARS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789'
LAUNCHER_NAME = 'start.bat'

# ---------- 界面文案（简体中文 / English） ----------

STRINGS = {
    'zh': {
        'console_title': 'FTP 服务器 - 关闭窗口即停止',
        'lang_prompt': '请选择语言 / Please select language:',
        'lang_opt': '  1) 简体中文    2) English',
        'lang_invalid': '[错误] 请输入 1 或 2',
        'share_prompt': '请将共享文件夹拖入本窗口后按回车：',
        'share_invalid': '[错误] 不是有效文件夹，请重新拖入: %s',
        'mode_prompt': '请选择访问模式：',
        'mode_ro': '  1) 只读（仅浏览和下载，用户名 read）',
        'mode_rw': '  2) 读写（可上传/删除/重命名，用户名 write）',
        'mode_ask': '输入 1 或 2 后回车: ',
        'mode_invalid': '[错误] 请输入 1 或 2',
        'probe_ok': '共享目录权限检测通过（%s）',
        'probe_read_fail': '[错误] 共享目录无法读取（权限不足或被占用）: %s',
        'probe_write_fail': '[错误] 共享目录不可写入（权限不足），无法使用读写模式: %s',
        'mode_ro_text': '只读',
        'mode_rw_text': '读写',
        'port_switch': '[提示] 默认端口 %d 已被占用，自动改用随机端口: %d',
        'port_fail': '[错误] 未找到可用端口，请检查系统后重试',
        'port_invalid': '[错误] 端口配置无效',
        'fw_ok': '防火墙规则已自动创建',
        'fw_warn': '[警告] 未能自动配置防火墙，手机可能无法连接。',
        'fw_hint': '       请手动放行入站 TCP 端口: %d 和 %d-%d',
        'launcher_ok': '已生成一键启动脚本: %s',
        'launcher_fail': '[警告] 未能生成一键启动脚本（程序所在目录不可写）',
        'temp_fallback': '[提示] Temp 文件夹不可用，日志与配置将保存到程序同目录',
        'launch_header': '已读取一键启动配置：',
        'launch_share': '  共享目录 : %s',
        'launch_mode': '  模式     : %s',
        'launch_user': '  账号     : %s    密码: %s',
        'launch_port': '  端口     : %d',
        'launch_enter': '按回车启动服务器...',
        'launch_no_share': '[错误] 一键启动参数缺少共享目录',
        'launch_no_dir': '[错误] 共享目录不存在: %s',
        'press_enter_exit': '按回车键退出',
        'banner_ready': '  FTP 服务器已就绪（%s）',
        'banner_share': '  共享目录 : %s',
        'banner_mode': '  模式     : %s',
        'banner_user': '  账号     : %s    密码: %s',
        'banner_port': '  端口     : %d',
        'banner_addr': '  地址     : %s    手机直连: ftp://%s:%d',
        'banner_multi_ip': '  (检测到多个网卡地址，手机连不上时请逐个尝试)',
        'banner_log': '  日志     : %s',
        'banner_stop': '  关闭本窗口 或 按 Ctrl+C 停止服务',
        'addr_unknown': '(未知，请用 ipconfig 查看)',
    },
    'en': {
        'console_title': 'FTP Server - close this window to stop',
        'lang_prompt': 'Please select language / 请选择语言:',
        'lang_opt': '  1) 简体中文    2) English',
        'lang_invalid': '[ERROR] Please enter 1 or 2',
        'share_prompt': 'Drag a shared folder into this window and press Enter:',
        'share_invalid': '[ERROR] Not a valid folder, please drag it in again: %s',
        'mode_prompt': 'Select access mode:',
        'mode_ro': '  1) Read-only (browse and download only, username: read)',
        'mode_rw': '  2) Read-write (upload/delete/rename, username: write)',
        'mode_ask': 'Enter 1 or 2 and press Enter: ',
        'mode_invalid': '[ERROR] Please enter 1 or 2',
        'probe_ok': 'Shared folder permission check passed (%s)',
        'probe_read_fail': '[ERROR] Shared folder is not readable (insufficient permissions or in use): %s',
        'probe_write_fail': '[ERROR] Shared folder is not writable (insufficient permissions), read-write mode unavailable: %s',
        'mode_ro_text': 'read-only',
        'mode_rw_text': 'read-write',
        'port_switch': '[INFO] Default port %d is in use, switching to random free port: %d',
        'port_fail': '[ERROR] No available port found, please check your system and retry',
        'port_invalid': '[ERROR] Invalid port configuration',
        'fw_ok': 'Firewall rules created automatically',
        'fw_warn': '[WARNING] Could not configure the firewall automatically, phones may fail to connect.',
        'fw_hint': '          Please allow inbound TCP ports manually: %d and %d-%d',
        'launcher_ok': 'One-click launcher created: %s',
        'launcher_fail': '[WARNING] Could not create the one-click launcher (program directory not writable)',
        'temp_fallback': '[INFO] Temp folder unavailable, log and config will be saved next to the program',
        'launch_header': 'One-click launch configuration loaded:',
        'launch_share': '  Shared folder : %s',
        'launch_mode': '  Mode          : %s',
        'launch_user': '  Username      : %s    Password: %s',
        'launch_port': '  Port          : %d',
        'launch_enter': 'Press Enter to start the server...',
        'launch_no_share': '[ERROR] --launch is missing the shared folder argument',
        'launch_no_dir': '[ERROR] Shared folder does not exist: %s',
        'press_enter_exit': 'Press Enter to exit',
        'banner_ready': '  FTP server is ready (%s)',
        'banner_share': '  Shared folder : %s',
        'banner_mode': '  Mode          : %s',
        'banner_user': '  Username      : %s    Password: %s',
        'banner_port': '  Port          : %d',
        'banner_addr': '  Address       : %s    Phone: ftp://%s:%d',
        'banner_multi_ip': '  (Multiple NIC addresses detected; try them one by one if the phone cannot connect)',
        'banner_log': '  Log           : %s',
        'banner_stop': '  Close this window or press Ctrl+C to stop',
        'addr_unknown': '(unknown, check ipconfig)',
    },
}

# 当前语言（choose_lang / 参数解析后设置）
LANG = 'zh'


def t(key, *args):
    return STRINGS[LANG][key] % args if args else STRINGS[LANG][key]


# ---------- 基础工具 ----------

def is_frozen():
    return getattr(sys, 'frozen', False)


def app_dir():
    """程序所在目录（打包后为 exe 目录，源码运行为脚本目录）"""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def fail(msg):
    print(msg)
    try:
        input(t('press_enter_exit'))
    except EOFError:
        pass
    sys.exit(1)


def data_dir():
    """数据目录: 优先用户 Temp 文件夹（不存在则创建），写入探测失败则回退程序同目录"""
    cand = os.environ.get('TEMP') or os.path.join(
        os.environ.get('LOCALAPPDATA', app_dir()), 'Temp')
    try:
        os.makedirs(cand, exist_ok=True)
        probe = os.path.join(cand, 'ftp_probe_%s.tmp' % os.urandom(4).hex())
        with open(probe, 'w', encoding='utf-8') as f:
            f.write('ok')
        os.remove(probe)
        return cand
    except OSError:
        print(t('temp_fallback'))
        return app_dir()


# ---------- 本地持久化（密码） ----------

def load_or_create_password(ddir):
    """密码: 首次启动随机生成并保存，此后沿用（明文，不加密）"""
    path = os.path.join(ddir, 'ftp_pass.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            saved = f.readline().strip()
        if saved:
            return saved
    except OSError:
        pass
    pwd = ''.join(secrets.choice(PASSWORD_CHARS) for _ in range(16))
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(pwd)
    except OSError:
        pass
    return pwd


# ---------- 交互输入 ----------

def choose_lang():
    """语言选择（双语提示，因为此时语言未定）"""
    global LANG
    while True:
        print(STRINGS['zh']['lang_prompt'])
        print(STRINGS['zh']['lang_opt'])
        try:
            m = input('> ').strip()
        except EOFError:
            sys.exit(1)
        if m == '1':
            LANG = 'zh'
            return
        if m == '2':
            LANG = 'en'
            return
        print(STRINGS['zh']['lang_invalid'])


def choose_share():
    """拖入文件夹选择共享目录（不记忆路径，路径只写入 start.bat）"""
    while True:
        print(t('share_prompt'))
        try:
            raw = input('> ')
        except EOFError:
            sys.exit(1)
        raw = raw.strip().strip('"').strip("'").strip()
        if not raw:
            continue
        if os.path.isdir(raw):
            return raw
        print(t('share_invalid', raw))


def choose_mode():
    """1 = 只读(read)  2 = 读写(write)"""
    while True:
        print('')
        print(t('mode_prompt'))
        print(t('mode_ro'))
        print(t('mode_rw'))
        try:
            m = input(t('mode_ask')).strip()
        except EOFError:
            sys.exit(1)
        if m == '1':
            return True
        if m == '2':
            return False
        print(t('mode_invalid'))


# ---------- 共享目录权限实测 ----------

def share_readable(path):
    try:
        os.listdir(path)
        return True
    except OSError:
        return False


def share_writable(path):
    try:
        fd, tmp = tempfile.mkstemp(dir=path, prefix='ftp_write_test_', suffix='.tmp')
        os.close(fd)
        os.remove(tmp)
        return True
    except OSError:
        return False


# ---------- 端口 ----------

def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('0.0.0.0', port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def pick_port(default, pstart, pend):
    """默认端口被占用则随机换空闲端口（10000-65535，避开被动端口段）"""
    if port_free(default):
        return default
    for _ in range(100):
        cand = random.randint(10000, 65535)
        if pstart <= cand <= pend:
            continue
        if port_free(cand):
            print(t('port_switch', default, cand))
            return cand
    fail(t('port_fail'))


# ---------- 局域网 IP ----------

def lan_ips():
    """主 IP 用默认路由探测（UDP connect 不发包），其余网卡 IP 一并列出"""
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            if ip:
                ips.append(ip)
        finally:
            s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith('127.') or ip.startswith('169.254.') or ip in ips:
                continue
            ips.append(ip)
    except OSError:
        pass
    return ips or [t('addr_unknown')]


# ---------- 防火墙（缺失则自动创建） ----------

def _rule_exists(name):
    try:
        r = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=' + name],
            capture_output=True)
        return r.returncode == 0
    except OSError:
        return False


def _add_rule(name, localport):
    subprocess.run(
        ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
         'name=' + name, 'dir=in', 'action=allow', 'protocol=TCP',
         'localport=' + localport],
        capture_output=True)


def _elevated_add_rules(pairs):
    """非管理员时写临时 bat 并 UAC 提权执行（bat 用 mbcs 编码，兼容中文规则名）"""
    bat = os.path.join(tempfile.gettempdir(), 'ftp_fw_%s.bat' % os.urandom(3).hex())
    lines = ['@echo off']
    for name, port in pairs:
        lines.append('netsh advfirewall firewall add rule name="%s" dir=in '
                     'action=allow protocol=TCP localport=%s' % (name, port))
    try:
        with open(bat, 'w', encoding='mbcs', errors='replace') as f:
            f.write('\r\n'.join(lines) + '\r\n')
        subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Start-Process -FilePath "%s" -Verb RunAs -Wait' % bat],
            capture_output=True)
    except OSError:
        pass
    finally:
        try:
            os.remove(bat)
        except OSError:
            pass


def ensure_firewall(base_name, port, pstart, pend):
    """两条规则都存在则跳过；缺失则创建（管理员直接建，否则弹 UAC）。失败仅警告。"""
    r1, r2 = base_name, base_name + ' - 被动端口'
    p2 = '%d-%d' % (pstart, pend)
    if _rule_exists(r1) and _rule_exists(r2):
        return True
    try:
        admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        admin = False
    if admin:
        _add_rule(r1, str(port))
        _add_rule(r2, p2)
    else:
        _elevated_add_rules(((r1, str(port)), (r2, p2)))
    if _rule_exists(r1) and _rule_exists(r2):
        print(t('fw_ok'))
        return True
    return False


# ---------- 一键启动脚本（start*.bat，配置改变时另存为新文件） ----------

def launcher_content(share, read_only, user, pwd, port, pstart, pend, lang):
    """生成 bat 命令行: 优先用本机 exe 绝对路径（bat 被移动到任何位置仍可启动），
    if exist 检测绝对路径失效（如软件被移走）时回退 %~dp0 相对路径。
    参数在两个分支中都要完整重复，因为 cmd 的 if/else 括号语法要求命令在分支内完整。"""
    if is_frozen():
        exe_abs = os.path.abspath(sys.executable)
        exe_name = os.path.basename(sys.executable)
        args_fmt = (' --launch --lang %s --share "%s" --mode %s --user %s --pass "%s" '
                    '--port %d --passive-start %d --passive-end %d'
                    % (lang, share, 'read' if read_only else 'write', user, pwd,
                       port, pstart, pend))
        run_part = ('if exist "%s" ("%s"%s) else ("%%~dp0%s"%s)'
                    % (exe_abs, exe_abs, args_fmt, exe_name, args_fmt))
    else:
        script_abs = os.path.abspath(__file__)
        args_fmt = (' --launch --lang %s --share "%s" --mode %s --user %s --pass "%s" '
                    '--port %d --passive-start %d --passive-end %d'
                    % (lang, share, 'read' if read_only else 'write', user, pwd,
                       port, pstart, pend))
        run_part = ('if exist "%s" ("%s" "%s"%s) else ("%s" "%s"%s)'
                    % (sys.executable, sys.executable, script_abs, args_fmt,
                       sys.executable, script_abs, args_fmt))
    return (
        '@echo off\r\n'
        'title FTP Server\r\n'
        '%s\r\n' % run_part
    )


def write_launcher(share, read_only, user, pwd, port, pstart, pend, lang):
    """成功启动后（端口绑定成功）在程序同目录写 start.bat。
    内容与现有 start.bat 相同则不动；不同则把旧文件重命名为 start_N.bat 保留（N 为
    最小可用序号），再写入新的 start.bat。避免覆盖用户仍需要的一键启动配置。"""
    content = launcher_content(share, read_only, user, pwd, port, pstart, pend, lang)
    base = os.path.join(app_dir(), LAUNCHER_NAME)
    try:
        existing = open(base, 'r', encoding='mbcs', errors='replace').read()
    except OSError:
        existing = None
    targets = [base] if existing is None or existing == content else []
    if not targets:
        # 配置改变: 旧 start.bat 重命名为 start_1.bat、start_2.bat ...（最小可用序号）
        n = 1
        while True:
            renamed = os.path.join(app_dir(), 'start_%d.bat' % n)
            try:
                os.rename(base, renamed)
                break
            except FileExistsError:
                n += 1
            except OSError:
                break
        targets = [base]
    # 依次尝试: 程序同目录 -> 数据目录
    for d in (app_dir(), data_dir()):
        target = os.path.join(d, os.path.basename(targets[0]))
        try:
            with open(target, 'w', encoding='mbcs', errors='replace') as f:
                f.write(content)
            return target
        except OSError:
            continue
    return None


# ---------- 显示 ----------

def print_banner(read_only, share, user, pwd, port, ips, log_file):
    mode_text = t('mode_ro_text') if read_only else t('mode_rw_text')
    print('')
    print('=====================================')
    print(t('banner_ready', mode_text))
    print('=====================================')
    print(t('banner_share', share))
    print(t('banner_mode', mode_text))
    print(t('banner_user', user, pwd))
    print(t('banner_port', port))
    for ip in ips:
        print(t('banner_addr', ip, ip, port))
    if len(ips) > 1:
        print(t('banner_multi_ip'))
    print(t('banner_log', log_file))
    print('')
    print(t('banner_stop'))
    print('')


# ---------- FTP 服务 ----------

def run_server(share, read_only, user, pwd, port, pstart, pend, log_file, lang):
    authorizer = DummyAuthorizer()
    if read_only:
        perm = 'elr'          # 列目录 + 下载 + 切目录，只读
    else:
        perm = 'elradfmwMT'   # 全权限：读写、删除、建目录、重命名
    authorizer.add_user(user, pwd, share, perm=perm)

    handler = FTPHandler
    handler.authorizer = authorizer
    handler.passive_ports = range(pstart, pend + 1)
    handler.banner = 'FTP (read-only)' if read_only else 'FTP (read-write)'

    server = FTPServer(('0.0.0.0', port), handler)

    # 绑定成功（可正常启动）后才生成/刷新 start.bat
    bat = write_launcher(share, read_only, user, pwd, port, pstart, pend, lang)
    if bat:
        print(t('launcher_ok', bat))
    else:
        print(t('launcher_fail'))

    logging.info('FTP started: 0.0.0.0:%d -> %s (%s, user=%s)',
                 port, share, 'read-only' if read_only else 'read-write', user)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close_all()


# ---------- 入口 ----------

def main():
    ap = argparse.ArgumentParser(description='FTP server (read-only / read-write)')
    ap.add_argument('--launch', action='store_true',
                    help='start with remembered arguments (used by start.bat)')
    ap.add_argument('--lang', choices=('zh', 'en'), help='UI language (zh / en)')
    ap.add_argument('--share', help='shared folder')
    ap.add_argument('--mode', help='read or 1 = read-only; write or 2 = read-write')
    ap.add_argument('--user', help='login username')
    ap.add_argument('--pass', dest='pwd', help='login password')
    ap.add_argument('--port', type=int, default=2121, help='command port (default 2121)')
    ap.add_argument('--passive-start', type=int, default=60000, help='passive port start')
    ap.add_argument('--passive-end', type=int, default=60100, help='passive port end')
    args = ap.parse_args()

    # 语言: 参数优先，否则交互选择（在选择路径之前）
    global LANG
    if args.lang:
        LANG = args.lang
    else:
        choose_lang()

    try:
        ctypes.windll.kernel32.SetConsoleTitleW(t('console_title'))
    except Exception:
        pass

    if not (1 <= args.port <= 65535) or args.passive_start >= args.passive_end \
            or not (1 <= args.passive_start <= 65535) or not (1 <= args.passive_end <= 65535):
        fail(t('port_invalid'))

    ddir = data_dir()
    log_file = os.path.join(ddir, 'ftp_server.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        handlers=[logging.FileHandler(log_file, encoding='utf-8'),
                  logging.StreamHandler()])

    if args.launch:
        # start.bat 启动: 按参数启动，密码缺省沿用本地保存值
        if not args.share:
            fail(t('launch_no_share'))
        if not os.path.isdir(args.share):
            fail(t('launch_no_dir', args.share))
        read_only = (args.mode or 'read').lower() in ('read', '1')
        user = args.user or ('read' if read_only else 'write')
        pwd = args.pwd or load_or_create_password(ddir)
        share = args.share
        mode_text = t('mode_ro_text') if read_only else t('mode_rw_text')
        print('')
        print(t('launch_header'))
        print(t('launch_share', share))
        print(t('launch_mode', mode_text))
        print(t('launch_user', user, pwd))
        print(t('launch_port', args.port))
        try:
            input(t('launch_enter'))
        except EOFError:
            sys.exit(1)
    else:
        # 交互式首次运行: 选目录、选模式（路径不落盘，只写入 start.bat）
        share = choose_share()
        read_only = choose_mode()
        user = 'read' if read_only else 'write'
        pwd = load_or_create_password(ddir)

    # 权限实测: 读失败一律退出；写失败仅在读写模式退出
    if not share_readable(share):
        fail(t('probe_read_fail', share))
    if not read_only and not share_writable(share):
        fail(t('probe_write_fail', share))
    print(t('probe_ok', t('mode_ro_text') if read_only else t('mode_rw_text')))

    port = pick_port(args.port, args.passive_start, args.passive_end)

    # 防火墙规则名为系统级固定标识，不随界面语言变化（避免换语言产生重复规则）
    base_name = 'FTP 只读共享' if read_only else 'FTP 读写共享'
    if not ensure_firewall(base_name, port, args.passive_start, args.passive_end):
        print(t('fw_warn'))
        print(t('fw_hint', port, args.passive_start, args.passive_end))

    print_banner(read_only, share, user, pwd, port, lan_ips(), log_file)
    run_server(share, read_only, user, pwd, port,
               args.passive_start, args.passive_end, log_file, LANG)


if __name__ == '__main__':
    main()
