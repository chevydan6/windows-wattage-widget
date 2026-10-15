using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.IO;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace WindowsWattageWidget
{
    internal sealed class Reading
    {
        public string Mode = "POWER", Detail = "Sensor unavailable";
        public double? Watts;
        public static Reading Read()
        {
            var result = new Reading();
            try
            {
                using (var query = new ManagementObjectSearcher("root\\wmi", "SELECT * FROM BatteryStatus WHERE Active=True"))
                using (var rows = query.Get())
                {
                    bool found = false, discharging = false, charging = false, invalid = false;
                    double total = 0;
                    foreach (ManagementObject row in rows)
                    using (row)
                    {
                        found = true;
                        bool draw = Convert.ToBoolean(row["Discharging"]);
                        bool charge = Convert.ToBoolean(row["Charging"]);
                        discharging |= draw; charging |= charge;
                        if (draw || charge)
                        {
                            object raw = row[draw ? "DischargeRate" : "ChargeRate"];
                            double rate = raw == null ? -1 : Convert.ToDouble(raw);
                            if (rate < 0 || rate >= 2147483648) invalid = true;
                            else total += draw ? rate : -rate;
                        }
                    }
                    if (!found) return result;
                    if (discharging || charging)
                    {
                        bool netDraw = discharging && (!charging || total >= 0);
                        result.Mode = netDraw ? "BATTERY DRAW" : "BATTERY CHARGE";
                        result.Detail = netDraw ? "On battery" : "Charging";
                        if (!invalid) result.Watts = Math.Abs(total) / 1000.0;
                    }
                    else { result.Mode = "AC POWER"; result.Detail = "Draw unavailable"; }
                }
            }
            catch { }
            return result;
        }
        public string Value { get { return Watts.HasValue ? Watts.Value.ToString("0.0", CultureInfo.CurrentCulture) + " W" : "—"; } }
    }

    internal sealed class Widget : Form
    {
        [DllImport("user32.dll")] static extern bool DestroyIcon(IntPtr handle);
        [DllImport("user32.dll")] static extern bool ReleaseCapture();
        [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr hwnd, int msg, IntPtr wparam, IntPtr lparam);
        readonly NotifyIcon tray;
        readonly Icon onIcon, offIcon;
        readonly ContextMenuStrip menu;
        readonly ToolStripMenuItem showItem;
        readonly System.Windows.Forms.Timer timer;
        readonly string statePath;
        Reading reading = new Reading();
        int readingBusy;
        bool displayOn = true;
        float scale = 1;

        public Widget()
        {
            Text = "Windows Wattage Widget";
            FormBorderStyle = FormBorderStyle.None;
            ShowInTaskbar = false; TopMost = true; DoubleBuffered = true;
            StartPosition = FormStartPosition.Manual;
            using (var g = Graphics.FromHwnd(IntPtr.Zero)) scale = g.DpiX / 96f;
            ClientSize = new Size((int)(96 * scale), (int)(96 * scale));
            BackColor = Color.FromArgb(25, 34, 45);
            statePath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "WindowsWattageWidget", "visible.txt");
            try { displayOn = !File.Exists(statePath) || File.ReadAllText(statePath).Trim() != "False"; } catch { }
            onIcon = MakeIcon(Color.FromArgb(74, 222, 128));
            offIcon = MakeIcon(Color.FromArgb(248, 113, 113));
            menu = new ContextMenuStrip();
            showItem = new ToolStripMenuItem("Show wattage display", null, delegate { SetDisplay(!displayOn); });
            menu.Items.Add(showItem);
            menu.Items.Add("Move to upper-right corner", null, delegate { SetCorner(); });
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Exit", null, delegate { Close(); });
            ContextMenuStrip = menu;
            tray = new NotifyIcon { Icon = onIcon, Text = "Windows Wattage Widget", ContextMenuStrip = menu, Visible = true };
            tray.MouseClick += delegate(object sender, MouseEventArgs e) { if (e.Button == MouseButtons.Left) SetDisplay(!displayOn); };
            MouseDown += delegate(object sender, MouseEventArgs e)
            {
                if (e.Button == MouseButtons.Left) { ReleaseCapture(); SendMessage(Handle, 0xA1, new IntPtr(2), IntPtr.Zero); }
            };
            timer = new System.Windows.Forms.Timer { Interval = 2000 };
            timer.Tick += delegate { RefreshReading(); };
            Shown += delegate { SetCorner(); SetDisplay(displayOn); RefreshReading(); timer.Start(); };
        }
        static Icon MakeIcon(Color color)
        {
            using (var bitmap = new Bitmap(32, 32))
            using (var graphics = Graphics.FromImage(bitmap))
            using (var brush = new SolidBrush(color))
            {
                graphics.SmoothingMode = SmoothingMode.AntiAlias;
                graphics.Clear(Color.Transparent);
                graphics.FillPolygon(brush, new Point[] { new Point(18,1), new Point(5,18), new Point(14,18), new Point(11,31), new Point(28,12), new Point(19,12) });
                IntPtr handle = bitmap.GetHicon();
                try { using (var borrowed = Icon.FromHandle(handle)) return (Icon)borrowed.Clone(); }
                finally { DestroyIcon(handle); }
            }
        }
        void SetCorner()
        {
            Rectangle area = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(area.Right - Width - (int)(8 * scale), area.Top + (int)(8 * scale));
        }
        void SetDisplay(bool on)
        {
            displayOn = on;
            if (on) Show(); else Hide();
            showItem.Checked = on;
            tray.Icon = on ? onIcon : offIcon;
            UpdateTooltip();
            try { Directory.CreateDirectory(Path.GetDirectoryName(statePath)); File.WriteAllText(statePath, on ? "True" : "False"); } catch { }
        }
        void UpdateTooltip()
        {
            string tip = "Wattage " + (displayOn ? "ON" : "OFF") + ": " + reading.Value + " - " + reading.Detail;
            tray.Text = tip.Length > 63 ? tip.Substring(0, 63) : tip;
        }
        void RefreshReading()
        {
            if (Interlocked.Exchange(ref readingBusy, 1) != 0) return;
            Task.Factory.StartNew(delegate
            {
                Reading next = Reading.Read();
                try
                {
                    BeginInvoke((Action)delegate { reading = next; UpdateTooltip(); Invalidate(); });
                }
                catch (InvalidOperationException) { }
                finally { Interlocked.Exchange(ref readingBusy, 0); }
            });
        }
        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.ScaleTransform(scale, scale);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (var border = new Pen(Color.FromArgb(70, 82, 97))) e.Graphics.DrawRectangle(border, 0, 0, 95, 95);
            using (var labelFont = new Font("Segoe UI", 9, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var valueFont = new Font("Segoe UI", 25, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var detailFont = new Font("Segoe UI", 10, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var labelBrush = new SolidBrush(Color.FromArgb(183, 197, 212)))
            using (var valueBrush = new SolidBrush(Color.FromArgb(169, 237, 187)))
            using (var align = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
            {
                e.Graphics.DrawString(reading.Mode, labelFont, labelBrush, new RectangleF(2, 7, 92, 19), align);
                e.Graphics.DrawString(reading.Value, valueFont, valueBrush, new RectangleF(2, 28, 92, 39), align);
                e.Graphics.DrawString(reading.Detail, detailFont, labelBrush, new RectangleF(2, 70, 92, 18), align);
            }
        }
        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (timer != null) timer.Dispose();
                if (tray != null) { tray.Visible = false; tray.Dispose(); }
                if (menu != null) menu.Dispose();
                if (onIcon != null) onIcon.Dispose();
                if (offIcon != null) offIcon.Dispose();
            }
            base.Dispose(disposing);
        }
    }
    internal static class Program
    {
        [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
        [STAThread] static void Main(string[] args)
        {
            // Read-only hardware probe used to verify the compiled executable.
            if (args.Length == 2 && args[0] == "--check")
            {
                var r = Reading.Read();
                File.WriteAllText(args[1], r.Mode + "\r\n" + r.Value + "\r\n" + r.Detail);
                return;
            }
            using (var mutex = new Mutex(false, "Local\\WindowsWattageWidget"))
            {
                if (!mutex.WaitOne(0)) return;
                try
                {
                    SetProcessDPIAware();
                    Application.EnableVisualStyles();
                    Application.SetCompatibleTextRenderingDefault(false);
                    using (var widget = new Widget()) Application.Run(widget);
                }
                finally { mutex.ReleaseMutex(); }
            }
        }
    }
}
