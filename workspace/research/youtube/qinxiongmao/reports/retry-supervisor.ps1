$ErrorActionPreference = "Continue"
$root = "C:\Users\Windows11\Documents\ChatGPT\video1"
$reports = Join-Path $root "workspace\research\youtube\qinxiongmao\reports"
$env:AVS_BROWSER_PROFILE_DIR = "C:\Users\Windows11\AppData\Local\Google\Chrome\User"
$env:AVS_BROWSER_PROFILE_NAME = "Profile"
$pidToWait = 5356

while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 30
}

for ($sweep = 1; $sweep -le 3; $sweep++) {
    $log = Join-Path $reports ("transcripts-retry-{0}.log" -f $sweep)
    $err = Join-Path $reports ("transcripts-retry-{0}.err.log" -f $sweep)
    $worker = Start-Process -FilePath python -ArgumentList @(
        "-m", "avs", "research", "youtube", "transcripts", "qinxiongmao", "--resume",
        "--model", "small", "--language", "zh", "--device", "auto"
    ) -WorkingDirectory $root -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden -PassThru
    Wait-Process -Id $worker.Id
    $pidToWait = $worker.Id
}
