#!/bin/bash

# Keycloak Setup Script for Airco Insights
# This script configures Keycloak with the required realm and client

set -e

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8080}
ADMIN_USER=${KEYCLOAK_ADMIN:-admin}
ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin123}
REALM_NAME="airco-insights"
CLIENT_ID="frontend-app"
CLIENT_SECRET="airco-frontend-secret"

echo "Setting up Keycloak for Airco Insights..."
echo "Keycloak URL: $KEYCLOAK_URL"

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to be ready..."
until curl -s "$KEYCLOAK_URL/health/ready" > /dev/null; do
    echo "Keycloak not ready yet, waiting..."
    sleep 5
done

echo "Keycloak is ready. Proceeding with setup..."

# Get admin token
echo "Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$ADMIN_USER&password=$ADMIN_PASSWORD&grant_type=password&client_id=admin-cli" | \
    jq -r '.access_token')

if [ "$ADMIN_TOKEN" == "null" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo "Failed to get admin token. Please check Keycloak credentials."
    exit 1
fi

echo "Admin token obtained successfully."

# Create realm
echo "Creating realm: $REALM_NAME..."
REALM_PAYLOAD=$(cat <<EOF
{
  "realm": "$REALM_NAME",
  "displayName": "Airco Insights",
  "enabled": true,
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "resetPasswordAllowed": false,
  "editUsernameAllowed": false,
  "bruteForceProtected": true,
  "permanentLockout": false,
  "maxFailureWaitSeconds": 900,
  "minimumQuickLoginWaitSeconds": 60,
  "waitIncrementSeconds": 60,
  "quickLoginCheckMilliSeconds": 1000,
  "maxDeltaTimeSeconds": 43200,
  "failureFactor": 30,
  "roles": {
    "realm": [
      {
        "name": "user",
        "description": "Regular user role"
      }
    ]
  }
}
EOF
)

curl -s -X POST "$KEYCLOAK_URL/admin/realms" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$REALM_PAYLOAD" || echo "Realm might already exist"

# Create client
echo "Creating client: $CLIENT_ID..."
CLIENT_PAYLOAD=$(cat <<EOF
{
  "clientId": "$CLIENT_ID",
  "name": "Frontend Application",
  "description": "Airco Insights Frontend Application",
  "enabled": true,
  "clientAuthenticatorType": "client-secret",
  "secret": "$CLIENT_SECRET",
  "redirectUris": [
    "http://localhost:3000/*",
    "http://localhost:3001/*",
    "http://127.0.0.1:3000/*",
    "http://127.0.0.1:3001/*"
  ],
  "webOrigins": [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001"
  ],
  "standardFlowEnabled": true,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": true,
  "serviceAccountsEnabled": false,
  "publicClient": false,
  "protocol": "openid-connect",
  "attributes": {
    "saml.assertion.signature": "false",
    "saml.multivalued.attributes": "false",
    "saml.force.post.binding": "false",
    "saml.encrypt": "false",
    "saml.server.signature": "false",
    "saml.client.signature": "false",
    "jwt.refresh.token.expire": "2592000",
    "oauth2.device.authorization.grant.enabled": "false",
    "oauth2.device.code.lifespan": "600",
    "backchannel.logout.session.required": "true",
    "frontchannel.logout.enabled": "true",
    "pkce.code.challenge.method": "S256"
  },
  "fullScopeAllowed": false,
  "nodeReTimeout": 0,
  "defaultClientScopes": [
    "web-origins",
    "role_list",
    "roles",
    "profile",
    "email"
  ]
}
EOF
)

curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM_NAME/clients" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$CLIENT_PAYLOAD" || echo "Client might already exist"

# Create a test user
echo "Creating test user..."
USER_PAYLOAD=$(cat <<EOF
{
  "username": "test@airco.com",
  "enabled": true,
  "email": "test@airco.com",
  "firstName": "Test",
  "lastName": "User",
  "credentials": [
    {
      "type": "password",
      "value": "Test123!",
      "temporary": false
    }
  ],
  "realmRoles": ["user"]
}
EOF
)

curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM_NAME/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$USER_PAYLOAD" || echo "Test user might already exist"

echo ""
echo "Keycloak setup completed!"
echo ""
echo "Realm: $REALM_NAME"
echo "Client ID: $CLIENT_ID"
echo "Client Secret: $CLIENT_SECRET"
echo ""
echo "Test User Credentials:"
echo "Email: test@airco.com"
echo "Password: Test123!"
echo ""
echo "Keycloak Console: $KEYCLOAK_URL/admin"
echo "Realm Console: $KEYCLOAK_URL/admin/master/console/#/realms/$REALM_NAME"
echo ""
echo "Please save these credentials for your application configuration."
