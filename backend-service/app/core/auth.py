import logging
import httpx
from jose import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# In-memory cache for Clerk JWKS
_jwks_cache = None

async def fetch_clerk_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
        
    # Standard Clerk JWKS URL. If publishable key is formatted like pk_test_xxxx, we can derive issuer.
    # Otherwise fallback to standard clerk api domain
    jwks_url = "https://api.clerk.com/v1/jwks"
    if settings.CLERK_PUBLISHABLE_KEY and "_" in settings.CLERK_PUBLISHABLE_KEY:
        try:
            # Clerk publishable keys often contain frontend API endpoints encoded in base64
            # e.g., pk_test_Y2xlcmsuZXhhbXBsZS5jb20k -> clerk.example.com
            parts = settings.CLERK_PUBLISHABLE_KEY.split("_")
            if len(parts) >= 3:
                import base64
                decoded = base64.b64decode(parts[2].encode()).decode()
                if "$" in decoded:
                    frontend_api = decoded.split("$")[0]
                    jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
        except Exception as e:
            logger.warning(f"Failed to parse Clerk frontend API from publishable key: {e}")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(jwks_url)
            if response.status_code == 200:
                _jwks_cache = response.json()
                logger.info("Successfully fetched Clerk JWKS.")
                return _jwks_cache
    except Exception as e:
        logger.error(f"Error fetching Clerk JWKS from {jwks_url}: {e}")
    return {}

async def get_current_user(request: Request) -> dict:
    """
    Dependency that extracts the Authorization Bearer token, validates it against Clerk, 
    and returns the decoded user payload. Fallbacks to mock credentials if keys are missing.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # Fallback to local dev user if no keys configured
        if not settings.CLERK_SECRET_KEY:
            logger.info("No Authorization header. Falling back to dev user context.")
            return {
                "id": "user-123456789",
                "email": "kanishka@stealthai.io",
                "name": "Kanishka Bhatia",
                "subscription": "premium"
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token."
        )

    token = auth_header.split(" ")[1]
    
    # If Clerk Keys are not configured, decode without signature verification for easy testing
    if not settings.CLERK_SECRET_KEY:
        try:
            claims = jwt.get_unverified_claims(token)
            logger.warning("Decoded Clerk token without signature verification (Development mode).")
            return {
                "id": claims.get("sub"),
                "email": claims.get("email") or claims.get("emails", [{}])[0].get("email_address", "user@stealthai.io"),
                "name": claims.get("name") or claims.get("first_name", "User"),
                "subscription": claims.get("subscription", "free")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid unverified token: {e}"
            )

    try:
        jwks = await fetch_clerk_jwks()
        if not jwks:
            # Fallback decoding without verification if JWKS is temporarily unreachable
            claims = jwt.get_unverified_claims(token)
            logger.warning("JWKS unreachable. Decoded Clerk token without verification.")
        else:
            # Verify and decode with JWKS keys
            claims = jwt.decode(token, jwks, options={"verify_aud": False})
        
        # Extract Clerk fields
        return {
            "id": claims.get("sub"),
            "email": claims.get("email") or "clerk_user@stealthai.io",
            "name": claims.get("name") or "Clerk User",
            "subscription": claims.get("subscription", "free")
        }
    except Exception as e:
        logger.error(f"Clerk token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {e}"
        )
