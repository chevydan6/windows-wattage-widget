#!/usr/bin/python3
"""Install or remove the Ubuntu widget for the current desktop user."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time

RULE = 'wattage-widget'
RULE_KEYS = ['Description', 'wmclass', 'wmclassmatch', 'position', 'positionrule', 'above', 'aboverule']


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def config_read(group, key):
    return run('kreadconfig6', '--file', 'kwinrulesrc', '--group', group, '--key', key)


def config_write(group, key, value):
    run('kwriteconfig6', '--file', 'kwinrulesrc', '--group', group, '--key', key, str(value))


def configure_kwin(remove=False):
    if not all(shutil.which(command) for command in ['kreadconfig6', 'kwriteconfig6']):
        return
    # Preserve other rules, including the older numbered-group layout.
    existing = config_read('General', 'rules')
    count = int(config_read('General', 'count') or 0)
    rules = existing.split(',') if existing else [str(i) for i in range(1, count + 1)]
    rules = [rule for rule in rules if rule and rule != RULE]
    if remove:
        for key in RULE_KEYS:
            run('kwriteconfig6', '--file', 'kwinrulesrc', '--group', RULE, '--key', key, '--delete')
    else:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        screen = app.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        values = {'Description': 'Wattage widget placement', 'wmclass': RULE,
                  'wmclassmatch': 1, 'above': 'true', 'aboverule': 2,
                  'position': f'{area.right() - 103},{area.top() + 8}', 'positionrule': 2}
        for key, value in values.items():
            config_write(RULE, key, value)
        rules.append(RULE)
    config_write('General', 'rules', ','.join(rules))
    config_write('General', 'count', len(rules))
    if shutil.which('qdbus6') and os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        subprocess.run(['qdbus6', 'org.kde.KWin', '/KWin', 'reconfigure'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop_widget(script):
    for process in Path('/proc').glob('[0-9]*'):
        try:
            if process.stat().st_uid != os.getuid():
                continue
            if os.fsencode(script) in (process / 'cmdline').read_bytes().split(b'\0'):
                os.kill(int(process.name), signal.SIGTERM)
                for _ in range(40):
                    if not process.exists():
                        break
                    time.sleep(0.05)
        except (OSError, ValueError):
            continue


def desktop_exec(path):
    # Desktop Entry Exec uses double-quote escaping, rather than shell quoting.
    value = str(path).replace('%', '%%')
    for char in ['\\', '"', '`', '$']:
        value = value.replace(char, '\\' + char)
    return '"' + value + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--no-autostart', action='store_true')
    parser.add_argument('--no-start', action='store_true')
    parser.add_argument('--no-kwin-rule', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run this as your desktop user, without sudo.')
    try:
        from PyQt6 import QtWidgets  # noqa: F401
    except ImportError:
        parser.error('Install the dependency first: sudo apt install python3-pyqt6')

    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    target = data / 'wattage-widget'
    script = target / 'wattage_widget.py'
    launcher = home / '.local/bin/wattage-widget'
    desktop = data / 'applications/wattage-widget.desktop'
    autostart = config / 'autostart/wattage-widget.desktop'
    stop_widget(script)

    if args.uninstall:
        for path in [launcher, desktop, autostart, script, target / 'LICENSE']:
            path.unlink(missing_ok=True)
        if target.exists() and not any(target.iterdir()):
            target.rmdir()
        configure_kwin(remove=True)
        print('Wattage Widget removed. Your visibility preference was kept.')
        return 0

    source = Path(__file__).resolve().parent
    for path in [target, launcher.parent, desktop.parent, autostart.parent]:
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'wattage_widget.py', script)
    shutil.copy2(source.parent / 'LICENSE', target / 'LICENSE')
    launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 ' + shlex.quote(str(script)) + ' "$@"\n')
    launcher.chmod(0o755)
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Wattage Widget\n'
                       'Comment=Live battery charge and discharge power in watts\n'
                       f'Exec={desktop_exec(launcher)}\nIcon=battery\nTerminal=false\n'
                       'Categories=System;Monitor;\nStartupWMClass=wattage-widget\n')
    if args.no_autostart:
        autostart.unlink(missing_ok=True)
    else:
        shutil.copy2(desktop, autostart)
    if not args.no_kwin_rule and 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper():
        configure_kwin()
    if not args.no_start:
        subprocess.Popen([str(launcher)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'Installed: {launcher}')
    print('Use the lightning tray icon to show/hide; right-click for controls.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
