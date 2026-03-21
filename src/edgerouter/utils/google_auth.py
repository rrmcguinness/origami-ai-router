from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status

async def verify_google_token(token: str):
    """
    Verifies a Google ID token.
    In a real scenario, you'd need a GOOGLE_CLIENT_ID.
    """
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        # idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
        
        # For this exercise, we'll simulate verification if the token isn't empty
        if not token:
             raise ValueError("Token is empty")
             
        # Simulated payload
        return {
            "sub": "1234567890",
            "email": "ryan@example.com",
            "name": "Ryan McGuinness"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
