$lonDeployerDir = Join-Path $env:USERPROFILE ".lnd"
if (-not (Test-Path $lonDeployerDir -PathType Container)) {
    New-Item -Path $lonDeployerDir -ItemType Directory
}
$platformToolsUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
$platformToolsZip = Join-Path $lonDeployerDir "platform-tools-latest-windows.zip"
Invoke-WebRequest -Uri $platformToolsUrl -OutFile $platformToolsZip
Expand-Archive -Path $platformToolsZip -DestinationPath $env:USERPROFILE -Force
Remove-Item -Path $platformToolsZip -Force
$platformToolsDir =  Join-Path $env:USERPROFILE "platform-tools"
$lonDeployerExe = Join-Path $lonDeployerDir "lon-deployer.exe"
$latestRelease = Invoke-WebRequest -UseBasicParsing -Uri "https://git.timoxa0.su/api/v1/repos/timoxa0/LoN-Deployer/releases/latest" | ConvertFrom-Json
foreach ($asset in $latestRelease.assets) {
    if ($asset.name -eq "LoN-Deployer.exe") {
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $lonDeployerExe
        break
    }
}
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User") -split ";"
if ($currentPath -notcontains $lonDeployerDir) {
    [Environment]::SetEnvironmentVariable("PATH", "$lonDeployerDir;$($env:PATH)", "User")
    $env:PATH="$lonDeployerDir;$($env:PATH)"
    Write-Host "LoN-Deployer added to PATH. Restart shell to apply changes"
}
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User") -split ";"
if ($currentPath -notcontains $platformToolsDir) {
    [Environment]::SetEnvironmentVariable("PATH", "$platformToolsDir;$($env:PATH)", "User")
    Write-Host "Platform tools added to PATH. Restart shell to apply changes"
}
