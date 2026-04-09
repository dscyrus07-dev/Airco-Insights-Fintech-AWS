# Keycloak Client Setup Instructions

## Phase 1: Create Auth Service Client

### Step 1: Access Keycloak Admin Console
1. Open: http://localhost:8080/admin
2. Login with: admin / admin123
3. Select realm: `airco-insights`

### Step 2: Create Auth Service Client
1. Go to `Clients` in left menu
2. Click `Create client`
3. Fill in client details:
   - **Client ID**: `auth-service`
   - **Client Protocol**: `openid-connect`
   - **Root URL**: `http://localhost:8001`
4. Click `Next`

### Step 3: Configure Client Settings
**Access Type**: `confidential`
- **Standard Flow**: OFF
- **Direct Access Grants**: ON
- **Service Accounts**: ON
- **Authorization**: OFF

**Valid Redirect URIs**: `http://localhost:8001/*`
**Web Origins**: `http://localhost:8001`
**Admin URL**: `http://localhost:8001`
**Base URL**: `http://localhost:8001`

### Step 4: Service Account Roles
1. Go to `Clients` -> `auth-service` -> `Service Account Roles`
2. Click `Assign role`
3. From `Client Roles`, select:
   - `view-users`
   - `query-users`
   - `manage-users` (if available)
4. Click `Assign`

### Step 5: Get Client Secret
1. Go to `Clients` -> `auth-service` -> `Credentials`
2. Note the **Client Secret** (needed for docker-compose.yml)

### Step 6: Verify Frontend Client Mappers
1. Go to `Clients` -> `frontend-app` -> `Mappers`
2. Ensure you have a mapper for `sub` claim:
   - If missing, create a new mapper:
   - **Name**: `sub mapper`
   - **Mapper Type**: `User Property`
   - **User Property**: `sub`
   - **Token Claim Name**: `sub`
   - **Claim JSON Type**: `String`
   - **Multivalued**: OFF

## After Keycloak Setup:
1. Update docker-compose.yml with the new client secret
2. Restart auth-service container
3. Test authentication flow

## Client Secret Location:
The client secret from Step 5 will be used in:
- `docker-compose.yml` under auth-service environment variables
- `KEYCLOAK_CLIENT_SECRET=<client-secret-here>`
