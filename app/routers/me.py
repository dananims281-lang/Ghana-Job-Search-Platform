"""Endpoints about the signed-in user ("me").

GET /me is a worked example of a protected endpoint. PATCH /me is left as an exercise
(see the TODO at the bottom of this file).

How a protected endpoint works in this app:
  1. The client sends its access token in a header:  Authorization: Bearer <access_token>
     (it gets that token from POST /auth/google or POST /auth/dev-login).
  2. Adding `current_user: models.AppUser = Depends(get_current_user)` to the endpoint makes
     FastAPI run get_current_user BEFORE the endpoint. That function reads the header,
     checks the token, and loads the user from the database.
  3. If the token is missing, expired or invalid, get_current_user answers 401 itself and the
     endpoint never runs. So inside the endpoint, `current_user` is always a real user.

The golden rule: WHO the user is comes from the token (current_user), never from the URL or
request body. That's why this is /me and not /users/{user_id}: a client can't ask for
someone else's data by changing an id.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user
from app.services.auth_service import get_memberships

router = APIRouter(tags=["Me"])


@router.get("/me", response_model=schemas.MeOut)
def read_me(
    current_user: models.AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The signed-in user's profile and the companies they can act for.

    The frontend calls this when the app loads (with a saved token) to decide what to show:
    an empty `memberships` list means a job seeker; one or more entries means the user can
    open those companies' employer dashboards.

    401 if the request has no valid access token.
    """
    # No permission check is needed beyond being signed in: every user may read their own
    # profile, and get_current_user has already rejected anyone who isn't signed in.
    return schemas.MeOut(
        user=schemas.UserOut.from_model(current_user),
        # Reuse the same query the sign-in response uses, so both always agree.
        memberships=get_memberships(db, current_user.user_id),
    )


# ---------------------------------------------------------------------------------------
# TODO (student, task T3.4): PATCH /me
#
# Let the signed-in user update their own `full_name` and `phone`. Follow read_me above.
#
# 1. In app/schemas.py, add a `UserUpdate` request model:
#      - full_name: Optional[str], 1-200 characters, strip surrounding spaces
#      - phone: Optional[str], up to 30 characters
#    Both are optional so the client can send just the field it is changing.
#
# 2. Here, add `@router.patch("/me", response_model=schemas.MeOut)` that:
#      - takes `payload: schemas.UserUpdate`, plus current_user and db exactly like read_me
#      - only changes fields the client actually sent. Hint: payload.model_dump(exclude_unset=True)
#        gives you just those, so {"phone": "..."} leaves full_name untouched.
#      - commits, then returns the same shape as GET /me
#
# 3. phone is UNIQUE in the database. If another user already has that phone number,
#    return 409 Conflict with a clear message instead of crashing with a 500.
#    Hint: catch sqlalchemy.exc.IntegrityError around db.commit(), call db.rollback(),
#    then raise HTTPException(status_code=409, ...).
#
# 4. Never accept `email`, `user_id` or anything else from the body. Email comes from
#    Google and is not editable here.
#
# Done when (test in Swagger with the Authorize button, or Postman):
#   - PATCH /me without a token                              -> 401
#   - PATCH /me {"full_name": "Ama K. Mensah"}               -> 200, name changed, phone unchanged
#   - PATCH /me {"phone": "+233201234567"}                   -> 200
#   - the same phone from a second user (another dev-login)  -> 409
#   - GET /me afterwards shows the new values
# ---------------------------------------------------------------------------------------
