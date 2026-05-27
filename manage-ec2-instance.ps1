param(
    [ValidateSet("start", "stop", "status", "restart", "fullstart", "rebuild", "help")]
    [string]$Action = "help",

    [string]$InstanceId = "i-05fc339cc9af9d24a",

    [string]$Region = "ap-south-1",

    [string]$AwsProfile = "",

    [string]$SshUser = "ubuntu",

    [string]$KeyPath = "x:\FinTech SAAS\Airco Insights Fintech\ssl\Airco Fintech.pem",

    [string]$RemoteProjectPath = "/opt/airco",

    [int]$SshTimeoutSeconds = 600,

    [int]$SshPollSeconds = 10
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::Cyan
    )

    Write-Host "[ec2-control] $Message" -ForegroundColor $Color
}

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Get-RemoteHost {
    $instance = Get-InstanceDescription
    if ($instance.PublicDnsName) {
        return $instance.PublicDnsName
    }

    if ($instance.PublicIpAddress) {
        return $instance.PublicIpAddress
    }

    throw "The instance does not currently expose a public DNS name or IP address."
}

function Assert-SshPrerequisites {
    Assert-Command "ssh"

    if (-not (Test-Path $KeyPath)) {
        throw "SSH key not found: $KeyPath"
    }
}

function Invoke-RemoteCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    Assert-SshPrerequisites

    $hostName = Get-RemoteHost
    $sshCommand = @(
        "-i", $KeyPath,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=4",
        "${SshUser}@${hostName}",
        $Command
    )

    & ssh @sshCommand
    if ($LASTEXITCODE -ne 0) {
        throw "SSH command failed on $hostName."
    }
}

function Wait-ForSsh {
    Write-Log "Waiting for SSH on the instance..."

    $deadline = (Get-Date).AddSeconds($SshTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-RemoteCommand -Command "echo ready"
            Write-Log "SSH is ready." Green
            return
        }
        catch {
            Start-Sleep -Seconds $SshPollSeconds
        }
    }

    throw "Timed out waiting for SSH after $SshTimeoutSeconds seconds."
}

function Start-RemoteDocker {
    Write-Log "Starting Docker services on the EC2 host..."
    $remoteCommand = "cd '$RemoteProjectPath' && bash ./scripts/deploy-ec2.sh deploy"
    Invoke-RemoteCommand -Command $remoteCommand
    Write-Log "Remote Docker start completed." Green
}

function Stop-RemoteDocker {
    Write-Log "Stopping Docker services on the EC2 host..."
    $remoteCommand = "cd '$RemoteProjectPath' && bash ./scripts/deploy-ec2.sh stop"
    Invoke-RemoteCommand -Command $remoteCommand
    Write-Log "Remote Docker stop completed." Yellow
}

function Restart-RemoteDocker {
    Write-Log "Restarting Docker services on the EC2 host..."
    $remoteCommand = "cd '$RemoteProjectPath' && bash ./scripts/deploy-ec2.sh restart"
    Invoke-RemoteCommand -Command $remoteCommand
    Write-Log "Remote Docker restart completed." Green
}

function Rebuild-RemoteDocker {
    Write-Log "Rebuilding Docker services on the EC2 host..."
    $remoteCommand = "cd '$RemoteProjectPath' && bash ./scripts/deploy-ec2.sh rebuild"
    Invoke-RemoteCommand -Command $remoteCommand
    Write-Log "Remote Docker rebuild completed." Green
}

function Invoke-Aws {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$AwsArguments
    )

    if ([string]::IsNullOrWhiteSpace($AwsProfile)) {
        & aws @AwsArguments
    }
    else {
        & aws --profile $AwsProfile @AwsArguments
    }

    return $LASTEXITCODE
}

function Test-AwsIdentity {
    Write-Log "Checking AWS credentials..."
    $awsIdentityArgs = @("sts", "get-caller-identity", "--region", $Region)
    if (-not [string]::IsNullOrWhiteSpace($AwsProfile)) {
        $awsIdentityArgs = @("--profile", $AwsProfile) + $awsIdentityArgs
    }

    $identity = & aws @awsIdentityArgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS credentials are invalid or expired. Run 'aws configure', 'aws configure sso', or specify -Profile with valid credentials before retrying. Details: $identity"
    }

    Write-Log "AWS identity verified." Green
}

function Get-InstanceDescription {
    $json = if ([string]::IsNullOrWhiteSpace($AwsProfile)) {
        & aws ec2 describe-instances --instance-ids $InstanceId --region $Region --output json --no-cli-pager 2>&1
    }
    else {
        & aws --profile $AwsProfile ec2 describe-instances --instance-ids $InstanceId --region $Region --output json --no-cli-pager 2>&1
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to describe EC2 instance $InstanceId in region $Region. Details: $json"
    }

    return (($json -join "`n") | ConvertFrom-Json).Reservations[0].Instances[0]
}

function Get-InstanceStateName {
    $description = Get-InstanceDescription
    return $description.State.Name
}

function Show-Status {
    try {
        $instance = Get-InstanceDescription
        $nameTag = ($instance.Tags | Where-Object { $_.Key -eq 'Name' } | Select-Object -First 1).Value
        $publicIp = $instance.PublicIpAddress
        $privateIp = $instance.PrivateIpAddress

        Write-Log "Instance ID : $InstanceId"
        Write-Log "Name        : $nameTag"
        Write-Log "State       : $($instance.State.Name)"
        Write-Log "Type        : $($instance.InstanceType)"
        Write-Log "Public IP   : $publicIp"
        Write-Log "Private IP  : $privateIp"
    }
    catch {
        Write-Log "Unable to read full instance details. Checking basic state only..." Yellow
        $stateQueryArgs = @("ec2", "describe-instance-status", "--instance-ids", $InstanceId, "--region", $Region, "--include-all-instances", "--output", "json", "--no-cli-pager")
        if (-not [string]::IsNullOrWhiteSpace($AwsProfile)) {
            $stateQueryArgs = @("--profile", $AwsProfile) + $stateQueryArgs
        }

        $stateOutput = & aws @stateQueryArgs 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to read EC2 status for $InstanceId. Details: $stateOutput"
        }

        Write-Log "Status response: $stateOutput"
    }
}

function Start-Instance {
    Write-Log "Starting EC2 instance $InstanceId in $Region ..."
    $output = if ([string]::IsNullOrWhiteSpace($AwsProfile)) {
        & aws ec2 start-instances --instance-ids $InstanceId --region $Region --output json --no-cli-pager 2>&1
    }
    else {
        & aws --profile $AwsProfile ec2 start-instances --instance-ids $InstanceId --region $Region --output json --no-cli-pager 2>&1
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start EC2 instance $InstanceId. Details: $output"
    }

    Write-Log "Start request accepted. Checking current state..."
    Start-Sleep -Seconds 5
    Show-Status

    Wait-ForSsh
    Start-RemoteDocker
}

function Stop-Instance {
    try {
        Wait-ForSsh
        Stop-RemoteDocker
    }
    catch {
        Write-Log "Remote Docker stop step could not be completed cleanly: $($_.Exception.Message)" Yellow
        Write-Log "Continuing with EC2 stop so the instance does not keep running." Yellow
    }

    Write-Log "Stopping EC2 instance $InstanceId in $Region ..."
    $output = if ([string]::IsNullOrWhiteSpace($AwsProfile)) {
        & aws ec2 stop-instances --instance-ids $InstanceId --region $Region --output json --no-cli-pager 2>&1
    }
    else {
        & aws --profile $AwsProfile ec2 stop-instances --instance-ids $InstanceId --region $Region --output json --no-cli-pager 2>&1
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to stop EC2 instance $InstanceId. Details: $output"
    }

    Write-Log "Waiting for instance to reach 'stopped' state..."
    $waitOutput = if ([string]::IsNullOrWhiteSpace($AwsProfile)) {
        & aws ec2 wait instance-stopped --instance-ids $InstanceId --region $Region --no-cli-pager 2>&1
    }
    else {
        & aws --profile $AwsProfile ec2 wait instance-stopped --instance-ids $InstanceId --region $Region --no-cli-pager 2>&1
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Instance $InstanceId did not reach stopped state. Details: $waitOutput"
    }

    Write-Log "Instance stopped successfully." Yellow
    Show-Status
}

function Restart-Docker {
    Write-Log "Checking if instance is running..."
    $state = Get-InstanceStateName
    if ($state -ne "running") {
        throw "Instance is not running (state: $state). Start the instance first."
    }

    Wait-ForSsh
    Restart-RemoteDocker
}

function Full-Start {
    Write-Log "Ensuring EC2 instance is running and Docker is started..."
    $state = Get-InstanceStateName
    if ($state -ne "running") {
        Write-Log "Instance is not running (state: $state). Starting instance..."
        Start-Instance
    }
    else {
        Write-Log "Instance is already running. Ensuring Docker is started..."
        Wait-ForSsh
        Start-RemoteDocker
    }
}

function Rebuild-Stack {
    Write-Log "Ensuring EC2 instance is running and rebuilding Docker stack..."
    $state = Get-InstanceStateName
    if ($state -ne "running") {
        Write-Log "Instance is not running (state: $state). Starting instance..."
        Start-Instance
        Wait-ForSsh
        Rebuild-RemoteDocker
    }
    else {
        Write-Log "Instance is already running. Rebuilding Docker stack..."
        Wait-ForSsh
        Rebuild-RemoteDocker
    }
}

function Show-Help {
    Write-Log "Available actions:" Cyan
    Write-Host "  start     - Start EC2 instance and Docker services" -ForegroundColor White
    Write-Host "  stop      - Stop Docker services then EC2 instance" -ForegroundColor White
    Write-Host "  status    - Show EC2 instance status" -ForegroundColor White
    Write-Host "  restart   - Restart Docker services only (fastest)" -ForegroundColor White
    Write-Host "  fullstart - Ensure instance is running and start Docker" -ForegroundColor White
    Write-Host "  rebuild   - Ensure instance is running and rebuild Docker stack" -ForegroundColor White
    Write-Host ""
    Write-Host "Usage examples:" -ForegroundColor White
    Write-Host "  .\manage-ec2-instance.ps1 -Action start" -ForegroundColor Gray
    Write-Host "  .\manage-ec2-instance.ps1 -Action restart" -ForegroundColor Gray
    Write-Host "  .\manage-ec2-instance.ps1 -Action rebuild" -ForegroundColor Gray
}

Assert-Command "aws"
Test-AwsIdentity

try {
    switch ($Action) {
        "start"    { Start-Instance }
        "stop"     { Stop-Instance }
        "status"   { Show-Status }
        "restart"  { Restart-Docker }
        "fullstart"{ Full-Start }
        "rebuild"  { Rebuild-Stack }
        "help"     { Show-Help }
        default    { Show-Help }
    }
}
catch {
    Write-Log $_.Exception.Message Red
    exit 1
}
