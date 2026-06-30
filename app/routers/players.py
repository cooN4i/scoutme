import os
import json
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.routers.auth import get_db, get_current_user, require_admin
from app.schemas import PlayerProfileResponse, PlayerProfileCreate
from app.crud import player as player_crud
from app.models import User

router = APIRouter(
    prefix="/players",
    tags=["Players"]
)

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/",
    response_model=PlayerProfileResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_profile(
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: str = Form(...),
    preferred_foot: str = Form(...),
    citizenship: str = Form(...),
    main_position_id: int = Form(...),
    current_club: str | None = Form("Free Agent"),
    secondary_position_ids: str = Form("[]"),
    videos: str = Form("[]"),
    photo: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    photo_url = None
    if photo and photo.filename:
        file_ext = os.path.splitext(photo.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as f:
            f.write(await photo.read())
        photo_url = f"/static/uploads/{unique_filename}"

    try:
        parsed_date = date.fromisoformat(birth_date)
        parsed_sec_positions = json.loads(secondary_position_ids)
        parsed_videos = json.loads(videos)

        profile_dto = PlayerProfileCreate(
            first_name=first_name,
            last_name=last_name,
            birth_date=parsed_date,
            preferred_foot=preferred_foot,
            citizenship=citizenship,
            main_position_id=main_position_id,
            current_club=current_club,
            secondary_position_ids=parsed_sec_positions,
            videos=parsed_videos
        )
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    new_profile = await player_crud.create_player_profile(
        db,
        profile_data=profile_dto,
        photo_url=photo_url,
        user_id=current_user.id
    )
    return new_profile


@router.get(
    "/{player_id}",
    response_model=PlayerProfileResponse
)
async def get_profile(
    player_id: int,
    db: AsyncSession = Depends(get_db)
):
    profile = await player_crud.get_player_profile_by_id(db, profile_id=player_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found"
        )
    return profile


@router.patch(
    "/{player_id}",
    response_model=PlayerProfileResponse
)
async def update_profile(
    player_id: int,
    first_name: str | None = Form(None),
    last_name: str | None = Form(None),
    birth_date: str | None = Form(None),
    preferred_foot: str | None = Form(None),
    citizenship: str | None = Form(None),
    main_position_id: int | None = Form(None),
    current_club: str | None = Form(None),
    secondary_position_ids: str | None = Form(None),
    videos: str | None = Form(None),
    photo: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = await player_crud.get_player_profile_by_id(db, profile_id=player_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found"
        )

    if profile.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this profile"
        )

    update_dict = {}
    if first_name is not None:
        update_dict["first_name"] = first_name
    if last_name is not None:
        update_dict["last_name"] = last_name
    if preferred_foot is not None:
        update_dict["preferred_foot"] = preferred_foot
    if citizenship is not None:
        update_dict["citizenship"] = citizenship
    if main_position_id is not None:
        update_dict["main_position_id"] = main_position_id
    if current_club is not None:
        update_dict["current_club"] = current_club

    try:
        if birth_date:
            update_dict["birth_date"] = date.fromisoformat(birth_date)
        if secondary_position_ids is not None:
            update_dict["secondary_position_ids"] = json.loads(
                secondary_position_ids)
        if videos is not None:
            update_dict["videos"] = json.loads(videos)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    if photo and photo.filename:
        file_ext = os.path.splitext(photo.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as f:
            f.write(await photo.read())
        update_dict["photo_url"] = f"/static/uploads/{unique_filename}"

    updated_profile = await player_crud.update_player_profile(
        db,
        profile_id=player_id,
        update_data=update_dict
    )
    return updated_profile


@router.delete(
    "/{player_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_profile(
    player_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = await player_crud.get_player_profile_by_id(db, profile_id=player_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found"
        )

    if profile.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this profile"
        )

    await player_crud.delete_player_profile(db, profile_id=player_id)
    return
