# Wattage Widget for Windows and Ubuntu

The Windows version is described below. A native **Ubuntu/Kubuntu version** is
also available in [`ubuntu/`](ubuntu/), using Python 3 and Qt 6. It reads Linux's
battery sensors directly and works on KDE Plasma Wayland without Wine.

## Ubuntu / Kubuntu installation

```bash
sudo apt install python3-pyqt6
git clone https://github.com/chevydan6/windows-wattage-widget.git
cd windows-wattage-widget
/usr/bin/python3 ubuntu/install.py
```

Run the installer as your desktop user, **without sudo**. It installs under your
home directory, adds an application-menu entry, starts the widget, and enables
automatic startup at login. On KDE it adds a window rule for initial upper-right
placement and keeping the display above other windows, preserving existing rules.
The widget uses a green lightning tray icon when shown and red when hidden. Click
to toggle it, drag the display to move it, or right-click for placement and exit.
Readings refresh every two seconds; your visibility preference is remembered.

The sensor backend reads `/sys/class/power_supply`. It shows battery discharge or
charging watts, with a current-times-voltage fallback where needed. When plugged
in without charging, it shows **AC POWER / Draw unavailable**. It does not claim to
measure wall power or total laptop consumption while charging, send telemetry,
or require root. A system tray is required for hide/show controls; native Wayland
placement has been tested on KDE Plasma. Other desktops may place the window
differently or require a tray extension.

To check the sensor without opening a window:

```bash
~/.local/bin/wattage-widget --check
```

Run the installer again to update from a newer checkout. Optional flags are
`--no-autostart`, `--no-start`, and `--no-kwin-rule`. To uninstall:

```bash
/usr/bin/python3 ubuntu/install.py --uninstall
```

This stops the widget and removes its installed files, login entry, and KDE rule.
Your saved visibility preference is kept. Sensor checks can be run with:

```bash
/usr/bin/python3 -m unittest discover -s ubuntu/tests -v
```

## Windows version

A small battery-power display for Windows, with a system-tray lightning icon:
**green means the display is on; red means it is hidden**. Click the icon to
toggle the display. Right-click for placement and exit controls.

The display starts in the upper-right corner, measures about one inch square
at Windows' logical DPI, and can be dragged. It refreshes every two seconds
and remembers whether you hid it. The tray icon may appear under the **^**
hidden-icons menu beside the clock.

## Download and run

Download **WindowsWattageWidget.exe** from
[Releases](https://github.com/chevydan6/windows-wattage-widget/releases) and
double-click it. The executable uses Windows' built-in .NET Framework; Python,
an SDK and custom drivers are not required. It is an unsigned executable, so
Windows may show an unknown-publisher warning. Verify the published checksum
and source before deciding to run it.

For automatic startup, extract the release ZIP and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1
```

This installs a copy under `%LOCALAPPDATA%\WindowsWattageWidget` and adds a
startup entry for your account. No administrator rights or security-setting
changes are required. To remove the installed version:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Uninstall.ps1
```

## What the number means

- **Battery draw:** battery-reported discharge power in watts.
- **Battery charge:** power going into the battery while charging.
- **AC power / Draw unavailable:** no total laptop-power sensor is exposed.
- **Sensor unavailable:** this hardware does not expose usable battery data.

This is **not a wall-power meter or CPU package-power meter**. Charging power
is not total laptop consumption. Accuracy and update frequency depend on the
battery firmware. The app reads `root\wmi:BatteryStatus`; it does not record
screen contents, send telemetry, or need a network connection.

## Build from source

On 64-bit Windows with .NET Framework 4.x installed:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Build.ps1
```

The output is `dist\WindowsWattageWidget.exe`. The C# source is in
`src\PowerIndicator.cs`. A read-only sensor check is available with
`WindowsWattageWidget.exe --check output.txt`.

`PowerIndicator.ps1` is the original PowerShell/WPF implementation, with the
same display and tray-color behavior. Run only one implementation at a time.

## License

MIT. See [LICENSE](LICENSE).
