param(
  [Parameter(Mandatory = $true)][string]$Source,
  [string]$Output,
  [int]$Columns = 32,
  [int]$Rows = 30,
  [string]$Glyphs = ' .,:;i1lr?xsYgG+H#%NM@'
)

# Convert a photo to editable ASCII. Run with:
# powershell -NoProfile -ExecutionPolicy Bypass -File scripts/photo_to_ascii.ps1 -Source "path\to\photo.png"
if (-not $Output) {
  $Output = Join-Path $PSScriptRoot '..\assets\portrait.txt'
}
Add-Type -AssemblyName System.Drawing
$bitmap = [System.Drawing.Bitmap]::new($Source)
$columns = $Columns
$rows = $Rows
if ($columns -lt 1 -or $rows -lt 1) { throw 'Columns and Rows must be positive.' }
$cropBottom = $bitmap.Height
$glyphs = $Glyphs
if ($glyphs.Length -lt 2) { throw 'Glyphs must contain at least two characters.' }
$result = [System.Collections.Generic.List[string]]::new()
for ($row = 0; $row -lt $rows; $row++) {
  $line = [System.Text.StringBuilder]::new()
  for ($col = 0; $col -lt $columns; $col++) {
    $alphaSum = 0.0
    $lightSum = 0.0
    $samples = 0
    for ($sy = 0; $sy -lt 7; $sy++) {
      for ($sx = 0; $sx -lt 5; $sx++) {
        $px = [Math]::Min($bitmap.Width - 1, [int](($col + ($sx + 0.5) / 5) * $bitmap.Width / $columns))
        $py = [Math]::Min($cropBottom - 1, [int](($row + ($sy + 0.5) / 7) * $cropBottom / $rows))
        $color = $bitmap.GetPixel($px, $py)
        $a = $color.A / 255.0
        $l = (0.2126 * $color.R + 0.7152 * $color.G + 0.0722 * $color.B) / 255.0
        $alphaSum += $a
        $lightSum += $l * $a
        $samples++
      }
    }
    $alpha = $alphaSum / $samples
    $light = if ($alphaSum -gt 0) { $lightSum / $alphaSum } else { 1.0 }
    $density = [Math]::Min(1.0, [Math]::Max(0.0, ((0.48 - $light) / 0.45) * $alpha))
    if ($row -ge [int]($rows * 0.47)) {
      $nx = ($col + 0.5) / $columns
      $ny = ($row + 0.5) / $rows
      $body = ([Math]::Pow(($nx - 0.31) / 0.30, 2) + [Math]::Pow(($ny - 0.83) / 0.19, 2)) -lt 1
      $hand = ($nx -lt 0.32 -and $ny -gt 0.82)
      $neckCenter = $rows * (1.0 - 0.384 * $nx)
      $neck = ($nx -gt 0.23 -and [Math]::Abs($row - $neckCenter) -lt ($rows * 0.05))
      if ($neck) { $density = [Math]::Max($density, 0.83) }
      elseif ($body -and -not $hand) { $density = [Math]::Max($density, 0.78) }
      else { $density *= 0.53 }
    }
    $index = if ($alpha -lt 0.17) { 0 } else { [int][Math]::Round($density * ($glyphs.Length - 1)) }
    [void]$line.Append($glyphs[$index])
  }
  $result.Add($line.ToString().TrimEnd())
}
$bitmap.Dispose()
[IO.File]::WriteAllLines([IO.Path]::GetFullPath($Output), $result, [Text.UTF8Encoding]::new($false))
Write-Output "Generated $Output"
