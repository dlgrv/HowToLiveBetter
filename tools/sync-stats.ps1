# 统计对齐脚本：重算全书的统计数字，回写 README.md、index.html、tools/og.html，再重出 og.png。
#
#   powershell -ExecutionPolicy Bypass -File tools\sync-stats.ps1
#   powershell -ExecutionPolicy Bypass -File tools\sync-stats.ps1 -NoScreenshot   # 只改数字不截图
#
# 只替换数字本身，不动任何其他文字；跑完逐项打印 旧 -> 新，没变化的标 (未变)。
# 数字口径：条目数 = book/*.md 里的 ### 标题数；A/B/C = 证据等级行的首字母（带（争议）后缀的照样算）；
# 争议 = 备注以「争议」开头的条数；TODO = 正文里含「待核实」或「TODO」的行数；
# 链接 = 「- 来源：」和「- 备注：」行里的 http(s) 总数；性价比三档的规则抄自 index.html。
param([switch]$NoScreenshot)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$utf8NoBom = New-Object Text.UTF8Encoding($false)

function Read-Text([string]$path) { [IO.File]::ReadAllText($path, $utf8NoBom) }
function Write-Text([string]$path, [string]$text) { [IO.File]::WriteAllText($path, $text, $utf8NoBom) }

# 档位规则和 index.html 的 COST_W、e.ratio 两行一致；那两行改了这里必须跟着改，所以先比对一次
$indexPath = Join-Path $repo 'index.html'
$indexText = Read-Text $indexPath
$costWLine = "const COST_W = { money:{'0':0,'少':1,'多':2}, time:{'少':0,'中':1,'多':2}, will:{'否':0,'些':1,'是':2} };"
$ratioLine = "e.ratio = e.level === '大' ? (e.cs === 0 ? '极高' : (e.cs <= 2 ? '高' : '一般'))"
if (-not $indexText.Contains($costWLine)) { throw 'index.html 的 COST_W 行变了，请同步本脚本里的成本权重' }
if (-not $indexText.Contains($ratioLine)) { throw 'index.html 的 e.ratio 行变了，请同步本脚本里的档位规则' }

$W = @{
  money = @{ '0' = 0; '少' = 1; '多' = 2 }
  time  = @{ '少' = 0; '中' = 1; '多' = 2 }
  will  = @{ '否' = 0; '些' = 1; '是' = 2 }
}

function Get-Ratio([int]$cost, [string]$level) {
  if ($level -eq '大') {
    if ($cost -eq 0) { return '极高' }
    if ($cost -le 2) { return '高' }
    return '一般'
  }
  if ($level -eq '中' -and $cost -eq 0) { return '高' }
  return '一般'
}

$entries = 0; $grade = @{ A = 0; B = 0; C = 0 }; $dispute = 0; $todo = 0; $links = 0
$ratio = @{ '极高' = 0; '高' = 0; '一般' = 0 }

foreach ($file in (Get-ChildItem (Join-Path $repo 'book\*.md') | Sort-Object Name)) {
  foreach ($line in [IO.File]::ReadAllLines($file.FullName, $utf8NoBom)) {
    if ($line -match '^### ') { $entries++ }
    if ($line -match '^- 证据等级：([ABC])') { $grade[$matches[1]]++ }
    if ($line -match '^- 备注：争议') { $dispute++ }
    if ($line -match '待核实|TODO') { $todo++ }
    if ($line -match '^- (来源|备注)：') { $links += ([regex]::Matches($line, 'https?://')).Count }
    if ($line -match '<!--\s*成本标签:\s*钱=(\S+)\s+时间=(\S+)\s+毅力=(\S+)\s+收益=(\S+)\s+口径=') {
      $cost = $W.money[$matches[1]] + $W.time[$matches[2]] + $W.will[$matches[3]]
      $ratio[(Get-Ratio $cost $matches[4])]++
    }
  }
}

$tagged = $ratio['极高'] + $ratio['高'] + $ratio['一般']
if ($tagged -ne $entries) { Write-Warning "有 $($entries - $tagged) 条缺成本标签，性价比三档对不上条目数" }
if (($grade.A + $grade.B + $grade.C) -ne $entries) { Write-Warning '证据等级行数和条目数对不上，检查有没有条目漏写证据等级' }

function Get-Pct([int]$n) { [int][math]::Round($n * 100.0 / $entries, 0, [MidpointRounding]::AwayFromZero) }
$pct = @{ '极高' = (Get-Pct $ratio['极高']); '高' = (Get-Pct $ratio['高']); '一般' = (Get-Pct $ratio['一般']) }
if (($pct['极高'] + $pct['高'] + $pct['一般']) -ne 100) { Write-Warning '性价比三档的百分比取整后不等于 100，README 里那句要自己看一眼' }

"条目 $entries ｜ A $($grade.A) B $($grade.B) C $($grade.C) ｜ 争议 $dispute ｜ TODO $todo ｜ 链接 $links"
"性价比 极高 $($ratio['极高'])（$($pct['极高'])%） 高 $($ratio['高'])（$($pct['高'])%） 一般 $($ratio['一般'])（$($pct['一般'])%）"
''

$edits = @(
  @{ File = 'README.md'; Label = '首屏条目数'; Pattern = '(\d+) 条建议'; New = "$entries 条建议" }
  @{ File = 'README.md'; Label = '条目徽章'; Pattern = '%E6%9D%A1%E7%9B%AE-(\d+)%20%E6%9D%A1'; New = "%E6%9D%A1%E7%9B%AE-$entries%20%E6%9D%A1" }
  @{ File = 'README.md'; Label = '证据分级徽章'; Pattern = 'A%20(\d+)%20%C2%B7%20B%20\d+%20%C2%B7%20C%20\d+'; New = "A%20$($grade.A)%20%C2%B7%20B%20$($grade.B)%20%C2%B7%20C%20$($grade.C)" }
  @{ File = 'README.md'; Label = '文献链接徽章'; Pattern = '-(\d+)%20%E6%9D%A1%E9%93%BE%E6%8E%A5'; New = "-$links%20%E6%9D%A1%E9%93%BE%E6%8E%A5" }
  @{ File = 'README.md'; Label = '怎么读里的 A 级数'; Pattern = '大型试验的 (\d+) 条'; New = "大型试验的 $($grade.A) 条" }
  @{ File = 'README.md'; Label = '证据分级段'; Pattern = '全书 (\d+) 条中 A 级 \d+ 条、B 级 \d+ 条、C 级 \d+ 条，另有 \d+ 条标注了争议、\d+ 处'; New = "全书 $entries 条中 A 级 $($grade.A) 条、B 级 $($grade.B) 条、C 级 $($grade.C) 条，另有 $dispute 条标注了争议、$todo 处" }
  @{ File = 'README.md'; Label = '性价比段'; Pattern = '全书 (\d+) 条中性价比极高 \d+ 条（\d+%）、高 \d+ 条（\d+%）、一般 \d+ 条（\d+%）'; New = "全书 $entries 条中性价比极高 $($ratio['极高']) 条（$($pct['极高'])%）、高 $($ratio['高']) 条（$($pct['高'])%）、一般 $($ratio['一般']) 条（$($pct['一般'])%）" }
  @{ File = 'index.html'; Label = '五处描述'; Pattern = '(\d+) 条建议'; New = "$entries 条建议" }
  @{ File = 'index.html'; Label = 'numberOfPages'; Pattern = 'numberOfPages":(\d+)'; New = "numberOfPages`":$entries" }
  @{ File = 'index.html'; Label = '页头条目数'; Pattern = '32 节 (\d+) 条'; New = "32 节 $entries 条" }
  @{ File = 'tools\og.html'; Label = 'og 条目数'; Pattern = '<b>(\d+)</b> 条建议'; New = "<b>$entries</b> 条建议" }
  @{ File = 'tools\og.html'; Label = 'og A 级数'; Pattern = 'A 级证据 <b>(\d+)</b> 条'; New = "A 级证据 <b>$($grade.A)</b> 条" }
  @{ File = 'tools\og.html'; Label = 'og 链接数'; Pattern = '<b>(\d+)</b> 条原始文献链接'; New = "<b>$links</b> 条原始文献链接" }
)

foreach ($edit in $edits) {
  $path = Join-Path $repo $edit.File
  $text = Read-Text $path
  $found = [regex]::Matches($text, $edit.Pattern)
  if ($found.Count -eq 0) { throw "$($edit.File) 里找不到「$($edit.Label)」，模式：$($edit.Pattern)" }
  $old = $found[0].Groups[1].Value
  $updated = [regex]::Replace($text, $edit.Pattern, $edit.New)
  if ($updated -eq $text) {
    "  $($edit.File) $($edit.Label)：$old（未变）"
    continue
  }
  Write-Text $path $updated
  "  $($edit.File) $($edit.Label)：$old -> 已更新（$($found.Count) 处）"
}

if ($NoScreenshot) { return }

$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
if (-not (Test-Path $chrome)) { throw "找不到 Chrome：$chrome，装在别处就改这一行，或者加 -NoScreenshot 跳过截图" }

# 每次用全新的 user-data-dir：否则 Chrome 会拿缓存里的旧 og.html 渲染，截出来还是旧数字
$shotProfile = Join-Path $env:TEMP ('og-shot-' + [guid]::NewGuid().ToString('N'))
$target = Join-Path $repo 'og.png'
$source = 'file:///' + ((Join-Path $repo 'tools\og.html') -replace '\\', '/')
$startedAt = Get-Date
# 用 Start-Process 而不是 & 调用：Chrome 把「xxx bytes written」写在 stderr 上，
# PowerShell 5.1 一旦让原生程序的 stderr 流进错误流，配上 ErrorActionPreference=Stop 就会误报失败
$chromeArgs = @(
  '--headless', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
  '--window-size=1200,630', "--user-data-dir=$shotProfile", "--screenshot=$target", $source
)
$chromeLog = Join-Path $env:TEMP ('og-shot-' + [guid]::NewGuid().ToString('N') + '.log')
Start-Process -FilePath $chrome -ArgumentList $chromeArgs -Wait -NoNewWindow -RedirectStandardError $chromeLog
Remove-Item -Force $chromeLog -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $shotProfile -ErrorAction SilentlyContinue

# 自检：文件是这次写的、大小在正常区间。过了这两关就不必再打开图看，省一次读图的开销
$png = Get-Item $target
if ($png.LastWriteTime -lt $startedAt) { throw 'og.png 没有被这次运行写入，截图失败了' }
if ($png.Length -lt 120KB -or $png.Length -gt 400KB) { throw "og.png 大小异常（$($png.Length) 字节），正常在 120KB 到 400KB，打开看一眼是不是渲染坏了" }
''
"og.png 已重出：$($png.Length) 字节，自检通过。改过 tools/og.html 的版式才需要打开图确认。"
