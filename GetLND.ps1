$lonDeployerDir = Join-Path $env:USERPROFILE "LoN-Deployer"

if (-not (Test-Path $lonDeployerDir -PathType Container)) {
    New-Item -Path $lonDeployerDir -ItemType Directory
}

$platformToolsUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
$platformToolsZip = Join-Path $lonDeployerDir "platform-tools-latest-windows.zip"
Invoke-WebRequest -Uri $platformToolsUrl -OutFile $platformToolsZip
Expand-Archive -Path $platformToolsZip -DestinationPath $lonDeployerDir -Force
Remove-Item -Path $platformToolsZip -Force

$lonDeployerUrl = "https://githubrelease.com/lon-deployer.exe"
$lonDeployerExe = Join-Path $lonDeployerDir "lon-deployer.exe"
Invoke-WebRequest -Uri $lonDeployerUrl -OutFile $lonDeployerExe
 
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine") -split ";"
if ($currentPath -notcontains $lonDeployerDir) {
    [Environment]::SetEnvironmentVariable("PATH", "$lonDeployerDir;$($env:PATH)", "Machine")
    Write-Host "LoN-Deployer directory added to PATH successfully."
} else {
    Write-Host "LoN-Deployer directory is already in PATH."
}
