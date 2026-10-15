# Windows Wattage Widget

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
