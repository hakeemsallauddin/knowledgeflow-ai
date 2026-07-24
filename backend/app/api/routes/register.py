from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep
from app.models.user_model import UserCreate, UserOut
from app.crud.user_crud import create_user, get_user_by_email

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register_user(
    *,
    session: SessionDep,
    user_in: UserCreate,
):
    existing_user = get_user_by_email(
        session=session,
        email=user_in.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user = create_user(
        session=session,
        user_create=user_in,
    )

    return user