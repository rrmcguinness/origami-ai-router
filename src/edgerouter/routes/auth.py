import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import id_token
from google.auth.transport import requests
from ..utils.google_auth import verify_google_token


router = APIRouter(prefix="/api")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/auth/google")
async def authenticate_user(token: str = Depends(oauth2_scheme)):
    idinfo = await verify_google_token(token)
    # ID token is valid. Get the user's Google Account ID from the decoded token.
    userid = idinfo['sub']
    return {"userid": userid, "email": idinfo['email']}
