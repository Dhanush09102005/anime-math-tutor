"""
Auth routes: email/password + Google OAuth, both writing into the same
users table. Token is issued as an httpOnly cookie, not a JSON body field
— frontend never touches the raw JWT (see api/client.js changes needed:
every fetch() call needs `credentials: "include"`).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from db.database import get_db
from db import crud
from auth.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user, COOKIE_NAME
from schemas import RegisterRequest, LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days — matches ACCESS_TOKEN_EXPIRE_MINUTES in security.py


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("ENV") == "production",  # requires https in prod; localhost dev stays False
        max_age=COOKIE_MAX_AGE_SECONDS,
    )


@router.post("/register", response_model=UserResponse)
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = crud.create_user(db, email=req.email, hashed_password=hash_password(req.password))
    token = create_access_token({"sub": str(user.id)})
    _set_auth_cookie(response, token)
    return UserResponse(id=str(user.id), email=user.email)


@router.post("/login", response_model=UserResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, req.email)

    # hashed_password is None for OAuth-only accounts — deliberately checked
    # before verify_password, since passlib can't compare against None.
    if user is None or user.hashed_password is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    _set_auth_cookie(response, token)
    return UserResponse(id=str(user.id), email=user.email)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"status": "logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user=Depends(get_current_user)):
    return UserResponse(id=str(current_user.id), email=current_user.email)


# ── Google OAuth ─────────────────────────────────────────────────────────────
# Requires SessionMiddleware in main.py (Authlib stores CSRF state/nonce
# there between the redirect to Google and the callback — separate from
# our own JWT auth cookie).

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/oauth/google/login")
async def google_login(request: Request):
    redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]  # must exactly match the URI registered in Google Cloud Console
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/oauth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]
    email = userinfo["email"]
    google_id = userinfo["sub"]

    user = crud.get_user_by_oauth(db, "google", google_id)
    if user is None:
        existing = crud.get_user_by_email(db, email)
        if existing is not None:
            # An email/password account already owns this email, signing in
            # via Google for the first time. NOT auto-linked — silently
            # merging accounts on email match has phishing implications
            # (an attacker who controls a Google account with a victim's
            # email could otherwise hijack the existing account). Left as
            # an explicit open decision rather than resolved silently here.
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Log in with your password instead.",
            )
        user = crud.create_user(db, email=email, oauth_provider="google", oauth_id=google_id)

    access_token = create_access_token({"sub": str(user.id)})
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    response = RedirectResponse(url=frontend_url)
    _set_auth_cookie(response, access_token)
    return response
