#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate a preview of the weekly release notes that would be created by the GitHub Actions workflow.

.DESCRIPTION
    This script creates a release_preview.md file with the same content that the weekly-binaries.yml
    workflow would generate for a release. Useful for previewing release notes before the workflow runs.

.PARAMETER BuildNumber
    The build number to use (defaults to a simulated value)

.PARAMETER SimulateFailures
    Whether to simulate some build failures for testing

.EXAMPLE
    .\generate_release_preview.ps1
    .\generate_release_preview.ps1 -BuildNumber 1234 -SimulateFailures
#>

param(
    [int]$BuildNumber = 9999,
    [switch]$SimulateFailures
)

# Function to get version from meerk40t.main
function Get-MeerK40tVersion {
    try {
        # Import the module to get version info
        $mainPath = Join-Path -Path $PSScriptRoot -ChildPath "meerk40t\main.py"
        if (Test-Path $mainPath) {
            # Read the main.py file and extract version
            $content = Get-Content $mainPath -Raw
            if ($content -match 'APPLICATION_VERSION\s*=\s*["'']([^"'']+)["'']') {
                return $matches[1]
            }
        }
    }
    catch {
        Write-Warning "Could not extract version from main.py: $_"
    }
    return "0.9.9999" # fallback
}

# Function to get current git info
function Get-GitInfo {
    $result = @{
        CommitSHA = "unknown"
        Branch = "unknown"
        Date = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    }

    try {
        # Get current commit SHA
        $commitSHA = & git rev-parse HEAD 2>$null
        if ($LASTEXITCODE -eq 0) {
            $result.CommitSHA = $commitSHA
        }

        # Get current branch
        $branch = & git branch --show-current 2>$null
        if ($LASTEXITCODE -eq 0) {
            $result.Branch = $branch
        }
    }
    catch {
        Write-Warning "Git commands failed: $_"
    }

    return $result
}

# Function to get recent commits (simulating PR changes)
function Get-RecentChanges {
    $changes = @()

    try {
        # Check if GitHub CLI is available and authenticated
        $ghAvailable = $false
        try {
            $null = Get-Command gh -ErrorAction Stop
            $ghAvailable = $true
        } catch {
            $ghAvailable = $false
        }

        if ($ghAvailable) {
            # Try to get merged PRs using GitHub CLI (like the workflow does)
            try {
                $prs = & gh pr list --state merged --limit 15 --json number,title,author,mergedAt,url 2>$null
                if ($LASTEXITCODE -eq 0 -and $prs) {
                    $changes += "### Changes Since Last Release"
                    $changes += ""
                    $prData = $prs | ConvertFrom-Json

                    foreach ($pr in $prData) {
                        $author = $pr.author.login
                        $number = $pr.number
                        $title = $pr.title
                        $url = $pr.url
                        $changes += "- $title ([#$number]($url)) by @$author"
                    }
                    $changes += ""
                    return $changes  # Successfully got PR data, return early
                }
            } catch {
                # GitHub CLI failed (not authenticated, network issues, etc.)
                Write-Host "GitHub CLI available but not authenticated or failed, falling back to git log (run 'gh auth login' for full PR details)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "GitHub CLI not installed, falling back to git log (install GitHub CLI and run 'gh auth login' for full PR details)" -ForegroundColor Yellow
        }

        # Fallback to git log if gh is not available or failed
        $commits = & git log --oneline -15 2>$null
        if ($LASTEXITCODE -eq 0) {
            $changes += "### Changes Since Last Release"
            $changes += ""
            $prCount = 0

            foreach ($commit in ($commits -split "`n")) {
                if ($commit -match '^(\w+)\s+(.+)$') {
                    $sha = $matches[1]
                    $message = $matches[2]

                    # Check if this looks like a PR merge or contains PR reference
                    if ($message -match '\(#(\d+)\)') {
                        # This is likely a PR merge
                        $prNumber = $matches[1]
                        $changes += "- $message"
                        $prCount++
                    } elseif ($prCount -lt 10) {
                        # Include non-PR commits but limit to avoid too much noise
                        $changes += "- $message (`$sha`)"
                    }
                }
            }

            if ($prCount -eq 0) {
                # If no PRs found, show regular commits
                $changes = @()
                $changes += "### Changes Since Last Release"
                $changes += ""
                $count = 0
                foreach ($commit in ($commits -split "`n")) {
                    if ($count -ge 10) { break }
                    if ($commit -match '^(\w+)\s+(.+)$') {
                        $sha = $matches[1]
                        $message = $matches[2]
                        $changes += "- $message (`$sha`)"
                        $count++
                    }
                }
            }

            $changes += ""
        }
    }
    catch {
        Write-Warning "Could not get recent changes: $_"
        $changes += "### Changes Since Last Release"
        $changes += ""
        $changes += "*Could not retrieve recent changes from git*"
        $changes += ""
    }

    return $changes
}

# Function to extract device support status from NOTES.md
function Get-DeviceStatus {
    $notesPath = Join-Path -Path $PSScriptRoot -ChildPath "NOTES.md"
    if (-not (Test-Path $notesPath)) {
        return @("### Device Support Status", "", "*NOTES.md not found*")
    }

    $lines = Get-Content $notesPath
    $startIndex = -1

    # Find the Device Support Status section
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -match "### Device Support Status") {
            $startIndex = $i
            break
        }
    }

    if ($startIndex -eq -1) {
        return @("### Device Support Status", "", "*Device Support Status section not found in NOTES.md*")
    }

    # Extract from start index to end
    return $lines[$startIndex..($lines.Length - 1)]
}

# Function to generate downloads table
function Get-DownloadsTable {
    $downloads = @()
    $downloads += "### Downloads"
    $downloads += ""
    $downloads += "| Platform | Status | File | Description |"
    $downloads += "|----------|--------|------|-------------|"

    # Simulate build results
    $buildResults = @{
        "Windows" = -not $SimulateFailures
        "macOS" = -not $SimulateFailures
        "Linux" = $true  # Always succeed for AppImage
        "Linux-Minimal" = $true
    }

    if ($buildResults["Windows"]) {
        $downloads += "| **Windows** | Available | ``MeerK40t-windows-$BuildNumber.exe`` | 32-bit Windows executable |"
    } else {
        $downloads += "| **Windows** | Failed | - | Build failed |"
    }

    if ($buildResults["macOS"]) {
        $downloads += "| **macOS** | Available | ``MeerK40t-macos-$BuildNumber.app.zip`` | macOS application bundle (zipped) |"
    } else {
        $downloads += "| **macOS** | Failed | - | Build failed |"
    }

    if ($buildResults["Linux"]) {
        $downloads += "| **Linux** | Available | ``MeerK40t-linux-$BuildNumber.AppImage`` | Linux AppImage (universal) |"
    } else {
        $downloads += "| **Linux** | Failed | - | Build failed |"
    }

    if ($buildResults["Linux-Minimal"]) {
        $downloads += "| **Linux** | Available | ``MeerK40t-linux-minimal-$BuildNumber`` | Linux binary |"
    } else {
        $downloads += "| **Linux** | Failed | - | Build failed |"
    }

    return $downloads
}

# Function to get system requirements
function Get-SystemRequirements {
    $requirements = @()
    $requirements += "### System Requirements"
    $requirements += ""
    $requirements += "#### Windows"
    $requirements += "- Windows 10 or later"
    $requirements += "- 32-bit architecture support"
    $requirements += "- No additional dependencies required"
    $requirements += ""
    $requirements += "#### macOS"
    $requirements += "- macOS 10.14 or later"
    $requirements += "- Intel and Apple Silicon support"
    $requirements += ""
    $requirements += "#### Linux"
    $requirements += "- Most modern Linux distributions"
    $requirements += "- AppImage format - no installation required"
    return $requirements
}

# Function to get installation instructions
function Get-InstallationInstructions {
    $instructions = @()
    $instructions += "### Installation Instructions"
    $instructions += ""
    $instructions += "#### Windows"
    $instructions += "1. Download ``MeerK40t-windows-$BuildNumber.exe``"
    $instructions += "2. Run the executable (may show security warnings - allow it)"
    $instructions += "3. MeerK40t will start automatically"
    $instructions += ""
    $instructions += "#### macOS"
    $instructions += "1. Download ``MeerK40t-macos-$BuildNumber.app.zip``"
    $instructions += "2. Extract the zip file"
    $instructions += "3. Move ``MeerK40t.app`` to your Applications folder"
    $instructions += "4. **First time only**: Right-click (or Control-click) on MeerK40t in Applications and select ""Open"""
    $instructions += "5. Click ""Open"" in the security dialog to bypass Gatekeeper for this unsigned application"
    $instructions += "6. Run MeerK40t from Applications (subsequent launches will work normally)"
    $instructions += ""
    $instructions += "#### Linux (AppImage)"
    $instructions += "1. Download ``MeerK40t-linux-$BuildNumber.AppImage``"
    $instructions += "2. Make it executable: ``chmod +x MeerK40t-linux-$BuildNumber.AppImage``"
    $instructions += "3. Run: ``./MeerK40t-linux-$BuildNumber.AppImage``"
    $instructions += ""
    $instructions += "#### Linux (Binary)"
    $instructions += "1. Download ``MeerK40t-linux-minimal-$BuildNumber``"
    $instructions += "2. Make it executable: ``chmod +x MeerK40t-linux-minimal-$BuildNumber``"
    $instructions += "3. Run: ``./MeerK40t-linux-minimal-$BuildNumber``"
    return $instructions
}

# Function to get important notes
function Get-ImportantNotes {
    $notes = @()
    $notes += "### Important Notes"
    $notes += ""
    $notes += "- This is a **weekly development build** - use at your own risk"
    $notes += "- For stable releases, see: [Release Versions](https://github.com/meerk40t/meerk40t/releases)"
    $notes += "- Latest stable: [0.9.x series](https://github.com/meerk40t/meerk40t/releases/latest)"
    return $notes
}

# Function to get build status warning
function Get-BuildStatusWarning {
    if ($SimulateFailures) {
        $warning = @()
        $warning += ""
        $warning += "### Build Status"
        $warning += ""
        $warning += "Some platform builds failed. Only successfully built binaries are included in this release. Failed builds will be addressed in future releases."
        return $warning
    }
    return @()
}

# Main script
# Add GitHub CLI to PATH if available
$env:PATH += ";C:\Program Files\GitHub CLI"

Write-Host "Generating release preview..." -ForegroundColor Green

# Get version and git info
$version = Get-MeerK40tVersion
$gitInfo = Get-GitInfo

Write-Host "Version: $version" -ForegroundColor Cyan
Write-Host "Build: $BuildNumber" -ForegroundColor Cyan
Write-Host "Commit: $($gitInfo.CommitSHA)" -ForegroundColor Cyan
Write-Host "Branch: $($gitInfo.Branch)" -ForegroundColor Cyan

# Build the release content
$content = @()
$content += "## MeerK40t Weekly Build $version.$BuildNumber"
$content += ""
$content += "**Automated weekly binary build of MeerK40t - the open-source laser cutting software.**"
$content += ""
$content += "### Build Information"
$content += "- **Version**: $version.$BuildNumber"
$content += "- **Commit**: [``$($gitInfo.CommitSHA)``](https://github.com/meerk40t/meerk40t/commit/$($gitInfo.CommitSHA))"
$content += "- **Build**: # $BuildNumber"
$content += "- **Date**: $($gitInfo.Date)"
$content += "- **Branch**: ``$($gitInfo.Branch)``"
$content += ""

# Add changes
$content += Get-RecentChanges

# Add device status
$content += Get-DeviceStatus
$content += ""

# Add downloads
$content += Get-DownloadsTable
$content += ""

# Add system requirements
$content += Get-SystemRequirements
$content += ""

# Add installation instructions
$content += Get-InstallationInstructions
$content += ""

# Add important notes
$content += Get-ImportantNotes

# Add build status warning if needed
$content += Get-BuildStatusWarning

# Write to file
$outputPath = Join-Path -Path $PSScriptRoot -ChildPath "release_preview.md"
$content | Out-File -FilePath $outputPath -Encoding UTF8

Write-Host "Release preview generated: $outputPath" -ForegroundColor Green
Write-Host "File size: $((Get-Item $outputPath).Length) bytes" -ForegroundColor Cyan