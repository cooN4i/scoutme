from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: str
    password: str


class PositionResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class PlayerVideoCreate(BaseModel):
    youtube_id: str = Field(..., min_length=11, max_length=20)
    title: str = Field("Видео нарезка", max_length=100)


class PlayerVideoResponse(BaseModel):
    id: int
    youtube_id: str
    title: str

    model_config = ConfigDict(from_attributes=True)


class PlayerProfileCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    birth_date: date
    preferred_foot: str = Field(..., min_length=4, max_length=10)
    current_club: str | None = "Free Agent"
    citizenship: str = Field(..., min_length=2, max_length=100)
    main_position_id: int

    secondary_position_ids: list[int] = Field(default=[])
    videos: list[PlayerVideoCreate] = Field(default=[])


class PlayerProfileResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    birth_date: date
    preferred_foot: str
    current_club: str | None
    citizenship: str
    photo_url: str | None

    user: UserResponse
    main_position: PositionResponse
    secondary_positions: list[PositionResponse]
    videos: list[PlayerVideoResponse]

    model_config = ConfigDict(from_attributes=True)


class PlayerProfileUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    birth_date: date | None = None
    preferred_foot: str | None = Field(None, min_length=4, max_length=10)
    current_club: str | None = None
    citizenship: str | None = Field(None, min_length=2, max_length=100)
    main_position_id: int | None = None
    secondary_position_ids: list[int] | None = None
