"""
Auth routes: email/password + Google OAuth, both writing into the same
users table. Token is issued as an httpOnly cookie, not a JSON body field
— frontend never touches the raw JWT (see api/client.js changes needed:
every fetch() call needs `credentials: "include"`).
"""

import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, Response, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from db.database import get_db
from db import crud
from auth.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user, is_admin, COOKIE_NAME
from schemas import RegisterRequest, LoginRequest, UserResponse, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days — matches ACCESS_TOKEN_EXPIRE_MINUTES in security.py

# Where uploaded avatars land — served back out via the /static mount added
# in main.py (StaticFiles(directory="static")), so this must live under the
# same "static" directory main.py mounts.
AVATAR_DIR = os.path.join("static", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)
ALLOWED_AVATAR_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def _user_response(user) -> UserResponse:
    """
    Single place constructing UserResponse from a User row, so display_name/
    avatar_url/has_password are always populated consistently. Previously
    every route below built UserResponse(id=..., email=...) directly, which
    silently dropped has_password — AccountPage.jsx's `isOAuth` check reads
    that field, so this was a real (if quiet) bug: the password-change form
    never showed for real password accounts.

    NOTE: this assumes schemas.UserResponse declares display_name: str | None,
    avatar_url: str | None, and has_password: bool. Add them if they aren't
    already there.
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        has_password=user.hashed_password is not None,
        is_admin=is_admin(user),
    )


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("COOKIE_SECURE", str(os.environ.get("ENV") == "production")).lower() == "true",
        max_age=COOKIE_MAX_AGE_SECONDS,
    )


@router.post("/register", response_model=UserResponse)
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = crud.create_user(db, email=req.email, hashed_password=hash_password(req.password))
    token = create_access_token({"sub": str(user.id)})
    _set_auth_cookie(response, token)
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, req.email)

    # hashed_password is None for OAuth-only accounts — deliberately checked
    # before verify_password, since passlib can't compare against None.
    if user is None or user.hashed_password is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    _set_auth_cookie(response, token)
    return _user_response(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"status": "logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user=Depends(get_current_user)):
    return _user_response(current_user)


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
    frontend_url = (os.environ.get("FRONTEND_URL") or "http://localhost").rstrip("/")

    if userinfo.get("email_verified") is not True:
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error=google_email_unverified"
        )

    user = crud.get_user_by_oauth(db, "google", google_id)
    if user is None:
        existing = crud.get_user_by_email(db, email)
        if existing is None:
            return RedirectResponse(
                url=f"{frontend_url}/?auth_error=google_registration_disabled"
            )
        if existing.oauth_provider or existing.oauth_id:
            return RedirectResponse(
                url=f"{frontend_url}/?auth_error=google_account_already_linked"
            )

        # Google must confirm ownership of the same email before its identity
        # can be linked to an account created through normal registration.
        user = crud.link_user_oauth(db, existing, "google", google_id)

    access_token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url=f"{frontend_url}/dashboard")
    _set_auth_cookie(response, access_token)
    return response


@router.post("/change-password", status_code=204)
def change_password(
    req: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="This account uses Google sign-in — password change is not available.",
        )
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    crud.update_user_password(db, current_user.id, hash_password(req.new_password))


@router.delete("/account", status_code=204)
def delete_account(
    response: Response,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.delete_user(db, current_user.id)
    response.delete_cookie(COOKIE_NAME)


# ── Profile customization (v2.2.0) ────────────────────────────────────────────
# Both use multipart/form-data (Form/File) rather than a JSON body — avatar
# upload needs File regardless, and keeping display-name update on the same
# form-encoding keeps the two profile endpoints consistent on the frontend.

@router.patch("/profile", response_model=UserResponse)
def update_profile(
    display_name: str | None = Form(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.update_user_profile(db, current_user.id, display_name=display_name)
    db.refresh(current_user)
    return _user_response(current_user)


@router.post("/profile/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="Avatar must be a PNG, JPEG, or WebP image.")

    ext = ALLOWED_AVATAR_TYPES[file.content_type]
    # Keyed by user id, not a random name — re-uploading overwrites the old
    # file in place instead of accumulating orphaned images per user.
    filename = f"{current_user.id}.{ext}"
    dest_path = os.path.join(AVATAR_DIR, filename)

    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    avatar_url = f"/static/avatars/{filename}"
    crud.update_user_profile(db, current_user.id, avatar_url=avatar_url)
    db.refresh(current_user)
    return _user_response(current_user)
