param(
    [switch]$FullPytest,
    [switch]$Strict,
    [switch]$SkipPytest,
    [switch]$SkipOptionalTools,
    [string[]]$AdditionalPytest = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDir = Split-Path -Parent $ScriptPath
$RepoRoot = Split-Path -Parent $ScriptDir
$WarningCount = 0
$ErrorCount = 0
$SectionIndex = 0

function Write-Section {
    param([string]$Message)

    $script:SectionIndex += 1
    Write-Host ""
    Write-Host ("[{0}] {1}" -f $script:SectionIndex, $Message) -ForegroundColor Cyan
}

function Add-WarningMessage {
    param([string]$Message)

    $script:WarningCount += 1
    Write-Host ("[WARN] {0}" -f $Message) -ForegroundColor Yellow
}

function Add-ErrorMessage {
    param([string]$Message)

    $script:ErrorCount += 1
    Write-Host ("[ERRO] {0}" -f $Message) -ForegroundColor Red
}

function Resolve-PythonExe {
    $candidates = @(
        (Join-Path $RepoRoot ".venv_Martelo\Scripts\python.exe"),
        (Join-Path $RepoRoot ".venv\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Python nao encontrado. Instale Python ou crie .venv_Martelo."
}

function Invoke-ExternalCommand {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$FailureMessage
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} (exit code {1})." -f $FailureMessage, $LASTEXITCODE)
    }
}

function Resolve-ToolCommand {
    param(
        [string]$PythonExe,
        [string]$BaseName
    )

    $scriptsDir = Split-Path -Parent $PythonExe
    $candidates = @(
        (Join-Path $scriptsDir ($BaseName + ".exe")),
        (Join-Path $scriptsDir ($BaseName + ".cmd")),
        (Join-Path $scriptsDir ($BaseName + ".bat")),
        (Join-Path $scriptsDir $BaseName)
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command $BaseName -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    return $null
}

function Get-ReviewFiles {
    $targets = @(
        (Join-Path $RepoRoot "Martelo_Orcamentos_V2"),
        (Join-Path $RepoRoot "scripts")
    )
    $files = @()

    foreach ($target in $targets) {
        if (-not (Test-Path -LiteralPath $target)) {
            continue
        }

        $files += Get-ChildItem -Path $target -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in @(".py", ".ps1", ".bat") }
    }

    $files += Get-ChildItem -Path $RepoRoot -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in @(".py", ".ps1", ".bat") }

    return $files |
        Where-Object { $_.FullName -ne $script:ScriptPath } |
        Sort-Object FullName -Unique
}

function Get-RelativePath {
    param([string]$Path)

    $uriRoot = [System.Uri]((Resolve-Path -LiteralPath $RepoRoot).Path + [IO.Path]::DirectorySeparatorChar)
    $uriPath = [System.Uri](Resolve-Path -LiteralPath $Path).Path
    return $uriRoot.MakeRelativeUri($uriPath).ToString().Replace("/", "\")
}

function Invoke-PatternScan {
    Write-Section "Scan local de padroes de risco"

    $patterns = @(
        [pscustomobject]@{ Label = "eval"; Severity = "high"; Pattern = "\beval\s*\(" },
        [pscustomobject]@{ Label = "exec builtin"; Severity = "high"; Pattern = "(?<!\.)\bexec\s*\(" },
        [pscustomobject]@{ Label = "shell=True"; Severity = "high"; Pattern = "shell\s*=\s*True" },
        [pscustomobject]@{ Label = "yaml.load"; Severity = "high"; Pattern = "yaml\.load\s*\(" },
        [pscustomobject]@{ Label = "pickle.load"; Severity = "medium"; Pattern = "pickle\.load\s*\(" },
        [pscustomobject]@{ Label = "hardcoded secret"; Severity = "medium"; Pattern = "(?i)^\s*(?:self\.)?(?:db_password|smtp_password|openai_api_key|api_key|token|secret|password)\b(?:\s*:\s*[^=]+)?\s*=\s*['`"][^'`"]+['`"]" },
        [pscustomobject]@{ Label = "literal mysql uri"; Severity = "medium"; Pattern = "mysql\+pymysql://[^'`"\s]+" }
    )

    $files = Get-ReviewFiles
    $findings = @()

    foreach ($file in $files) {
        foreach ($pattern in $patterns) {
            $matches = Select-String -Path $file.FullName -Pattern $pattern.Pattern -Encoding UTF8 -ErrorAction SilentlyContinue
            foreach ($match in $matches) {
                $findings += [pscustomobject]@{
                    Severity = $pattern.Severity
                    Label = $pattern.Label
                    Path = Get-RelativePath $match.Path
                    Line = $match.LineNumber
                    Preview = $match.Line.Trim()
                }
            }
        }
    }

    if (-not $findings) {
        Write-Host "Sem padroes de risco detetados pelo scan local."
        return
    }

    foreach ($finding in $findings) {
        Write-Host ("[{0}] {1}:{2} - {3}" -f $finding.Severity.ToUpperInvariant(), $finding.Path, $finding.Line, $finding.Label)
        Write-Host ("        {0}" -f $finding.Preview)
    }

    $message = ("Foram encontrados {0} padroes de risco. Exigem revisao manual." -f $findings.Count)
    if ($Strict) {
        Add-ErrorMessage $message
    } else {
        Add-WarningMessage $message
    }
}

function Invoke-OptionalTool {
    param(
        [string]$PythonExe,
        [string]$ToolName,
        [string[]]$Arguments,
        [string]$SuccessMessage,
        [string]$FailureMessage,
        [string]$ReportPath = ""
    )

    $toolCommand = Resolve-ToolCommand -PythonExe $PythonExe -BaseName $ToolName
    if (-not $toolCommand) {
        Add-WarningMessage ("{0} nao encontrado. Opcional: instalar com '{1} -m pip install bandit pip-audit detect-secrets'." -f $ToolName, $PythonExe)
        return
    }

    try {
        if ($ReportPath) {
            $reportDir = Split-Path -Parent $ReportPath
            if ($reportDir) {
                New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
            }
            $output = & $toolCommand @Arguments 2>&1
            $exitCode = $LASTEXITCODE
            Set-Content -LiteralPath $ReportPath -Value $output -Encoding UTF8
            if ($exitCode -ne 0) {
                if ($Strict) {
                    Add-ErrorMessage ("{0} Relatorio em {1}" -f $FailureMessage, $ReportPath)
                } else {
                    Add-WarningMessage ("{0} Relatorio em {1}" -f $FailureMessage, $ReportPath)
                }
                return
            }
            Write-Host ("{0} Relatorio em {1}" -f $SuccessMessage, $ReportPath)
            return
        }

        & $toolCommand @Arguments
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            if ($Strict) {
                Add-ErrorMessage $FailureMessage
            } else {
                Add-WarningMessage $FailureMessage
            }
            return
        }

        Write-Host $SuccessMessage
    } catch {
        if ($Strict) {
            Add-ErrorMessage ("{0} Detalhe: {1}" -f $FailureMessage, $_.Exception.Message)
        } else {
            Add-WarningMessage ("{0} Detalhe: {1}" -f $FailureMessage, $_.Exception.Message)
        }
    }
}

$pythonExe = Resolve-PythonExe

Write-Section "Ambiente"
Write-Host ("Repositorio: {0}" -f $RepoRoot)
Write-Host ("Python: {0}" -f $pythonExe)

if (-not $SkipPytest) {
    Write-Section "Pytest"

    $coreTests = @(
        "tests/test_custeio_items_model.py",
        "tests/test_mat_default_filtering.py",
        "tests/test_orla_pricing.py",
        "tests/test_margens.py",
        "tests/test_def_pecas_restore.py",
        "tests/test_modulos_referencia.py",
        "tests/test_cutrite_automation.py",
        "tests/test_db_bootstrap.py",
        "tests/test_release_tools.py"
    )

    $pytestArgs = @("-m", "pytest")
    if (-not $FullPytest) {
        $pytestArgs += $coreTests
    }
    if ($AdditionalPytest) {
        $pytestArgs += $AdditionalPytest
    }

    Write-Host ("A correr: {0} {1}" -f $pythonExe, ($pytestArgs -join " "))
    try {
        Push-Location $RepoRoot
        Invoke-ExternalCommand -Executable $pythonExe -Arguments $pytestArgs -FailureMessage "Pytest falhou"
    } catch {
        Add-ErrorMessage $_.Exception.Message
    } finally {
        Pop-Location
    }
} else {
    Write-Section "Pytest"
    Add-WarningMessage "Pytest foi ignorado por pedido explicito."
}

Invoke-PatternScan

if (-not $SkipOptionalTools) {
    Write-Section "Ferramentas opcionais"

    Invoke-OptionalTool `
        -PythonExe $pythonExe `
        -ToolName "bandit" `
        -Arguments @("-q", "-r", (Join-Path $RepoRoot "Martelo_Orcamentos_V2"), (Join-Path $RepoRoot "scripts")) `
        -SuccessMessage "Bandit concluido sem findings bloqueantes." `
        -FailureMessage "Bandit reportou findings ou falhou."

    Invoke-OptionalTool `
        -PythonExe $pythonExe `
        -ToolName "pip-audit" `
        -Arguments @("-r", (Join-Path $RepoRoot "requirements.txt")) `
        -SuccessMessage "pip-audit concluido sem vulnerabilidades conhecidas." `
        -FailureMessage "pip-audit reportou vulnerabilidades ou falhou."

    $detectSecretsReport = Join-Path $RepoRoot "installer\security_review_detect_secrets.json"
    $detectSecretsRegex = "(\\.env$|(^|[\\\\/])(build|dist|\\.venv|\\.venv_Martelo|\\.git|\\.pytest_cache|__pycache__)([\\\\/]|$))"
    Invoke-OptionalTool `
        -PythonExe $pythonExe `
        -ToolName "detect-secrets" `
        -Arguments @("scan", "--all-files", "--exclude-files", $detectSecretsRegex) `
        -SuccessMessage "detect-secrets concluido." `
        -FailureMessage "detect-secrets reportou problemas ou falhou." `
        -ReportPath $detectSecretsReport
} else {
    Write-Section "Ferramentas opcionais"
    Add-WarningMessage "Bandit, pip-audit e detect-secrets foram ignorados por pedido explicito."
}

Write-Section "Resumo"
Write-Host ("Avisos: {0}" -f $WarningCount)
Write-Host ("Erros: {0}" -f $ErrorCount)

if ($ErrorCount -gt 0) {
    Write-Host "Revisao local falhou." -ForegroundColor Red
    exit 1
}

Write-Host "Revisao local concluida." -ForegroundColor Green
exit 0
