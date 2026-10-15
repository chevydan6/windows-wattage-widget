$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Windows.Forms, System.Drawing
$mutex = New-Object Threading.Mutex($false, 'Local\DanPowerIndicator')
if (!$mutex.WaitOne(0)) { exit }
$root = $PSScriptRoot
try {
    [xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Width="96" Height="96" WindowStyle="None" ResizeMode="NoResize"
        AllowsTransparency="True" Background="Transparent" Topmost="True"
        ShowInTaskbar="False" Title="Battery Power Indicator">
  <Border Background="#F019222D" BorderBrush="#465261" BorderThickness="1" CornerRadius="10" Padding="7">
    <Grid>
      <Grid.RowDefinitions><RowDefinition Height="19"/><RowDefinition Height="*"/><RowDefinition Height="18"/></Grid.RowDefinitions>
      <TextBlock x:Name="Mode" Text="BATTERY DRAW" Foreground="#B7C5D4" FontFamily="Segoe UI" FontSize="9" HorizontalAlignment="Center" VerticalAlignment="Center"/>
      <TextBlock x:Name="Watts" Grid.Row="1" Text="…" Foreground="#A9EDBB" FontFamily="Segoe UI Semibold" FontSize="25" HorizontalAlignment="Center" VerticalAlignment="Center"/>
      <TextBlock x:Name="Detail" Grid.Row="2" Text="Reading…" Foreground="#B7C5D4" FontFamily="Segoe UI" FontSize="10" HorizontalAlignment="Center" VerticalAlignment="Center"/>
    </Grid>
  </Border>
</Window>
'@
    $reader = New-Object Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)
    $app = New-Object Windows.Application
    $app.ShutdownMode = [Windows.ShutdownMode]::OnExplicitShutdown
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class TrayIconNative {
    [DllImport("user32.dll")] public static extern bool DestroyIcon(IntPtr handle);
}
'@
    function New-TrayIcon([string]$color) {
        $bitmap = New-Object Drawing.Bitmap 32,32
        $graphics = [Drawing.Graphics]::FromImage($bitmap)
        $brush = New-Object Drawing.SolidBrush ([Drawing.ColorTranslator]::FromHtml($color))
        $handle = [IntPtr]::Zero
        $temporaryIcon = $null
        try {
            $graphics.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::AntiAlias
            $graphics.Clear([Drawing.Color]::Transparent)
            [Drawing.Point[]]$bolt = @(
                (New-Object Drawing.Point 18,1), (New-Object Drawing.Point 5,18),
                (New-Object Drawing.Point 14,18), (New-Object Drawing.Point 11,31),
                (New-Object Drawing.Point 28,12), (New-Object Drawing.Point 19,12)
            )
            $graphics.FillPolygon($brush,$bolt)
            $handle = $bitmap.GetHicon()
            $temporaryIcon = [Drawing.Icon]::FromHandle($handle)
            return $temporaryIcon.Clone()
        } finally {
            if ($temporaryIcon) { $temporaryIcon.Dispose() }
            if ($handle -ne [IntPtr]::Zero) { [void][TrayIconNative]::DestroyIcon($handle) }
            $graphics.Dispose(); $brush.Dispose(); $bitmap.Dispose()
        }
    }
    $onIcon = New-TrayIcon '#4ADE80'
    $offIcon = New-TrayIcon '#F87171'
    $tray = New-Object Windows.Forms.NotifyIcon
    $tray.Icon = $onIcon
    $tray.Text = 'Wattage display'
    $trayMenu = New-Object Windows.Forms.ContextMenuStrip
    $showItem = $trayMenu.Items.Add('Show wattage display')
    $showItem.Add_Click({ Set-DisplayVisible (!$window.IsVisible); Update-Power })
    $resetItem = $trayMenu.Items.Add('Move to upper-right corner')
    $resetItem.Add_Click({ Set-Corner })
    [void]$trayMenu.Items.Add((New-Object Windows.Forms.ToolStripSeparator))
    $exitItem = $trayMenu.Items.Add('Exit')
    $exitItem.Add_Click({ $app.Shutdown() })
    $tray.ContextMenuStrip = $trayMenu
    $tray.Add_MouseClick({
        param($sender,$eventArgs)
        if ($eventArgs.Button -eq [Windows.Forms.MouseButtons]::Left) {
            Set-DisplayVisible (!$window.IsVisible)
            Update-Power
        }
    })
    $tray.Visible = $true
    function Set-DisplayVisible([bool]$visible) {
        if ($visible) { $window.Show() } else { $window.Hide() }
        $showItem.Checked = $visible
        $tray.Icon = if ($visible) { $onIcon } else { $offIcon }
        try { [string]$visible | Set-Content (Join-Path $root 'visible.txt') } catch {}
    }
    $mode = $window.FindName('Mode')
    $watts = $window.FindName('Watts')
    $detail = $window.FindName('Detail')
    function Set-Corner {
        $area = [Windows.SystemParameters]::WorkArea
        $window.Left = $area.Right - $window.Width - 8
        $window.Top = $area.Top + 8
    }
    function Update-Power {
        $value = $null
        try {
            $batteries = @(Get-CimInstance -Namespace root\wmi -ClassName BatteryStatus -ErrorAction Stop | Where-Object Active)
            if (!$batteries.Count) { throw 'No active battery telemetry' }
            $battery = $batteries[0]
            if ($battery.Discharging) {
                $label = 'BATTERY DRAW'
                $rates = @($batteries | Where-Object Discharging | ForEach-Object { [double]$_.DischargeRate })
                $state = 'On battery'
            } elseif ($battery.Charging) {
                $label = 'BATTERY CHARGE'
                $rates = @($batteries | Where-Object Charging | ForEach-Object { [double]$_.ChargeRate })
                $state = 'Charging'
            } else {
                $label = 'AC POWER'
                $rates = @()
                $state = 'Draw unavailable'
            }
            if ($rates.Count -gt 0 -and !@($rates | Where-Object { $_ -lt 0 -or $_ -ge 2147483648 }).Count) {
                $value = ($rates | Measure-Object -Sum).Sum / 1000.0
            }
            $mode.Text = $label
            $watts.Text = if ($null -ne $value) { '{0:0.0} W' -f $value } else { '—' }
            $detail.Text = $state
        } catch {
            $mode.Text = 'POWER'
            $watts.Text = '—'
            $detail.Text = 'Sensor unavailable'
        }
        $window.ToolTip = "Battery-reported power, refreshed every 2 seconds. Charging watts are power into the battery, not total laptop or wall draw. Drag to move; right-click for options."
        $displayState = if ($window.IsVisible) { 'ON' } else { 'OFF' }
        $tray.Text = ('Wattage ' + $displayState + ': ' + $watts.Text + ' - ' + $detail.Text)
        try {
            [pscustomobject]@{ Time=(Get-Date).ToString('o'); Watts=$value; Mode=$mode.Text; Detail=$detail.Text; Width=$window.Width; Height=$window.Height; Left=$window.Left; Top=$window.Top; Visible=$window.IsVisible; TrayVisible=$tray.Visible; TrayColor=$(if ($window.IsVisible) { 'Green' } else { 'Red' }); ProcessId=$PID } |
                ConvertTo-Json | Set-Content (Join-Path $root 'status.json')
        } catch {}
    }
    $menu = New-Object Windows.Controls.ContextMenu
    $reset = New-Object Windows.Controls.MenuItem
    $reset.Header = 'Move to upper-right corner'
    $reset.Add_Click({ Set-Corner })
    [void]$menu.Items.Add($reset)
    $close = New-Object Windows.Controls.MenuItem
    $close.Header = 'Hide wattage display'
    $close.Add_Click({ Set-DisplayVisible $false; Update-Power })
    [void]$menu.Items.Add($close)
    $window.ContextMenu = $menu
    $window.Add_MouseLeftButtonDown({ $window.DragMove() })
    $window.Add_Loaded({ Set-Corner; Update-Power })
    $timer = New-Object Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromSeconds(2)
    $timer.Add_Tick({ Update-Power })
    $timer.Start()
    $window.Add_Closed({ $timer.Stop() })
    Set-Corner
    $initialVisible = $true
    if (Test-Path (Join-Path $root 'visible.txt')) {
        $initialVisible = ((Get-Content (Join-Path $root 'visible.txt') -Raw).Trim() -ne 'False')
    }
    Set-DisplayVisible $initialVisible
    Update-Power
    [void]$app.Run()
} catch {
    $_ | Out-String | Set-Content (Join-Path $root 'error.log')
    throw
} finally {
    if ($timer) { $timer.Stop() }
    if ($tray) { $tray.Visible = $false; $tray.Dispose() }
    if ($trayMenu) { $trayMenu.Dispose() }
    if ($onIcon) { $onIcon.Dispose() }
    if ($offIcon) { $offIcon.Dispose() }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
