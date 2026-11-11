# ASCII-only script: check idle time + screenshot
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public struct PT { public int X; public int Y; }
[StructLayout(LayoutKind.Sequential)] public struct LII { public uint cbSize; public uint dwTime; }
public static class U32X {
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out PT p);
    [DllImport("user32.dll")] public static extern bool GetLastInputInfo(ref LII plii);
}
"@
$i = New-Object LII; $i.cbSize = [Runtime.InteropServices.Marshal]::SizeOf($i)
[U32X]::GetLastInputInfo([ref]$i) | Out-Null
$p = New-Object PT; [U32X]::GetCursorPos([ref]$p)
Write-Output ("IDLE_MS=" + ([Environment]::TickCount - $i.dwTime) + " CURSOR=" + $p.X + "," + $p.Y)

Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen(0, 0, 0, 0, $bmp.Size)
$bmp.Save('C:\Users\QAXD\com_test\douhot_mcp\.gh_login_screen.png')
$g.Dispose(); $bmp.Dispose()
Write-Output ("SHOT_SAVED " + $b.Width + "x" + $b.Height)
