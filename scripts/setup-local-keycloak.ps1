param(
    [string]$KeycloakUrl = "http://localhost:8080",
    [string]$AdminUser = "admin",
    [string]$AdminPassword = "admin123",
    [string]$RealmName = "airco-insights",
    [string]$ClientId = "frontend-app",
    [string]$ClientSecret = "airco-frontend-secret",
    [string]$TestEmail = "test@airco.com",
    [string]$TestPassword = "Test123!"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    Write-Host "[setup-local-keycloak] $Message" -ForegroundColor Cyan
}

function Invoke-RestJson {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        $Body = $null,
        [string]$ContentType = "application/json"
    )

    $params = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        ErrorAction = 'Stop'
    }

    if ($null -ne $Body) {
        $params.Body = if ($Body -is [string]) { $Body } else { ($Body | ConvertTo-Json -Depth 20 -Compress) }
        $params.ContentType = $ContentType
    }

    return Invoke-RestMethod @params
}

function Wait-ForKeycloak {
    param([int]$TimeoutSeconds = 300)

    Write-Log "Waiting for Keycloak at $KeycloakUrl..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/realms/master/.well-known/openid-configuration" -TimeoutSec 5
            return
        } catch {
            Start-Sleep -Seconds 5
        }
    }

    throw "Keycloak did not become ready within $TimeoutSeconds seconds."
}

function Get-AdminHeaders {
    Write-Log "Requesting admin token..."
    $tokenResponse = Invoke-RestMethod -Method Post -Uri "$KeycloakUrl/realms/master/protocol/openid-connect/token" -ContentType 'application/x-www-form-urlencoded' -Body @{
        username   = $AdminUser
        password   = $AdminPassword
        grant_type = 'password'
        client_id  = 'admin-cli'
    }

    if (-not $tokenResponse.access_token) {
        throw "Unable to get Keycloak admin token. Check the admin credentials."
    }

    return @{ Authorization = "Bearer $($tokenResponse.access_token)" }
}

function Set-KeycloakRealm {
    param([hashtable]$Headers)

    $realmPayload = @{
        realm = $RealmName
        enabled = $true
        registrationAllowed = $false
        loginWithEmailAllowed = $true
        duplicateEmailsAllowed = $false
        resetPasswordAllowed = $false
        editUsernameAllowed = $false
    }

    try {
        $null = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName" -Headers $Headers
        Write-Log "Realm $RealmName already exists."
    } catch {
        Write-Log "Creating realm $RealmName..."
        Invoke-RestJson -Method Post -Uri "$KeycloakUrl/admin/realms" -Headers $Headers -Body $realmPayload | Out-Null
    }
}

function Set-KeycloakClient {
    param([hashtable]$Headers)

    $clientPayload = @{
        clientId = $ClientId
        name = "Frontend Application"
        enabled = $true
        clientAuthenticatorType = "client-secret"
        secret = $ClientSecret
        redirectUris = @(
            "http://localhost:3000/*",
            "http://127.0.0.1:3000/*"
        )
        webOrigins = @(
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        )
        standardFlowEnabled = $true
        directAccessGrantsEnabled = $true
        publicClient = $false
        protocol = "openid-connect"
        fullScopeAllowed = $false
    }

    $client = @()
    try {
        $client = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName/clients?clientId=$ClientId" -Headers $Headers
    } catch {
        $client = @()
    }

    if ($client.Count -gt 0) {
        Write-Log "Updating existing client $ClientId..."
        $clientIdValue = $client[0].id
        Invoke-RestJson -Method Put -Uri "$KeycloakUrl/admin/realms/$RealmName/clients/$clientIdValue" -Headers $Headers -Body $clientPayload | Out-Null
    } else {
        Write-Log "Creating client $ClientId..."
        Invoke-RestJson -Method Post -Uri "$KeycloakUrl/admin/realms/$RealmName/clients" -Headers $Headers -Body $clientPayload | Out-Null
    }
}

function Set-KeycloakRole {
    param([hashtable]$Headers)

    try {
        $null = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName/roles/user" -Headers $Headers
        Write-Log "Realm role 'user' already exists."
    } catch {
        Write-Log "Creating realm role 'user'..."
        Invoke-RestJson -Method Post -Uri "$KeycloakUrl/admin/realms/$RealmName/roles" -Headers $Headers -Body @{ name = "user" } | Out-Null
    }
}

function Set-KeycloakTestUser {
    param([hashtable]$Headers)

    $userPayload = @{
        username = $TestEmail
        enabled = $true
        email = $TestEmail
        emailVerified = $true
        firstName = "Test"
        lastName = "User"
        credentials = @(
            @{ type = "password"; value = $TestPassword; temporary = $false }
        )
    }

    $users = @()
    try {
        $users = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName/users?username=$TestEmail" -Headers $Headers
    } catch {
        $users = @()
    }

    if ($users.Count -gt 0) {
        Write-Log "Updating existing test user..."
        $userId = $users[0].id
        Invoke-RestJson -Method Put -Uri "$KeycloakUrl/admin/realms/$RealmName/users/$userId" -Headers $Headers -Body $userPayload | Out-Null
    } else {
        Write-Log "Creating test user..."
        Invoke-RestJson -Method Post -Uri "$KeycloakUrl/admin/realms/$RealmName/users" -Headers $Headers -Body $userPayload | Out-Null
        $users = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName/users?username=$TestEmail" -Headers $Headers
    }

    if ($users.Count -eq 0) {
        throw "Test user could not be created or found."
    }

    return $users[0].id
}

function Reset-TestPassword {
    param(
        [hashtable]$Headers,
        [string]$UserId
    )

    Invoke-RestJson -Method Put -Uri "$KeycloakUrl/admin/realms/$RealmName/users/$UserId/reset-password" -Headers $Headers -Body @{
        type = "password"
        value = $TestPassword
        temporary = $false
    } | Out-Null
}

function Add-KeycloakUserRole {
    param(
        [hashtable]$Headers,
        [string]$UserId
    )

    $role = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName/roles/user" -Headers $Headers
    $currentRoles = @()
    try {
        $currentRoles = Invoke-RestMethod -Method Get -Uri "$KeycloakUrl/admin/realms/$RealmName/users/$UserId/role-mappings/realm" -Headers $Headers
    } catch {
        $currentRoles = @()
    }

    if (-not ($currentRoles | Where-Object { $_.name -eq "user" })) {
        Write-Log "Assigning realm role 'user' to test user..."
        try {
            $requestBody = @(
                @{
                    id = $role.id
                    name = $role.name
                    composite = $role.composite
                    clientRole = $role.clientRole
                    containerId = $role.containerId
                }
            ) | ConvertTo-Json -Depth 5 -Compress
            Invoke-WebRequest -Method Post -Uri "$KeycloakUrl/admin/realms/$RealmName/users/$UserId/role-mappings/realm" -Headers $Headers -ContentType "application/json" -Body $requestBody | Out-Null
        } catch {
            Write-Log "Warning: role assignment failed, but login setup will continue."
        }
    } else {
        Write-Log "Test user already has role 'user'."
    }
}

function Test-Login {
    Write-Log "Verifying login with test credentials..."
    $loginResponse = Invoke-RestMethod -Method Post -Uri "$KeycloakUrl/realms/$RealmName/protocol/openid-connect/token" -ContentType 'application/x-www-form-urlencoded' -Body @{
        username   = $TestEmail
        password   = $TestPassword
        grant_type = 'password'
        client_id  = $ClientId
        client_secret = $ClientSecret
    }

    if (-not $loginResponse.access_token) {
        throw "Login verification failed even though setup completed."
    }
}

Wait-ForKeycloak
$headers = Get-AdminHeaders
Set-KeycloakRealm -Headers $headers
Set-KeycloakClient -Headers $headers
Set-KeycloakRole -Headers $headers
$userId = Set-KeycloakTestUser -Headers $headers
Reset-TestPassword -Headers $headers -UserId $userId
Add-KeycloakUserRole -Headers $headers -UserId $userId
Test-Login

Write-Log "Keycloak local setup complete and verified."
Write-Host ""
Write-Host "Realm: $RealmName"
Write-Host "Client ID: $ClientId"
Write-Host "Client Secret: $ClientSecret"
Write-Host "Test Login: $TestEmail / $TestPassword"
Write-Host "Admin Console: $KeycloakUrl/admin"
