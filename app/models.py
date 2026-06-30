from datetime import date
from sqlalchemy import String, ForeignKey, Date, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

player_secondary_positions = Table(
    "player_secondary_positions",
    Base.metadata,
    Column("player_id", Integer, ForeignKey(
        "player_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("position_id", Integer, ForeignKey(
        "positions.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    profile: Mapped["PlayerProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False)


class PlayerVideo(Base):
    __tablename__ = "player_videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey(
        "player_profiles.id", ondelete="CASCADE"), nullable=False)
    youtube_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(100), default="Highlights")

    profile: Mapped["PlayerProfile"] = relationship(back_populates="videos")


class PlayerProfile(Base):
    __tablename__ = "player_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_foot: Mapped[str] = mapped_column(String(10), nullable=False)
    current_club: Mapped[str | None] = mapped_column(
        String(100), default="Free Agent")
    citizenship: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey(
        "users.id", ondelete="CASCADE"), unique=True, nullable=False)
    main_position_id: Mapped[int] = mapped_column(
        ForeignKey("positions.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="profile")
    main_position: Mapped["Position"] = relationship()
    secondary_positions: Mapped[list["Position"]] = relationship(
        secondary=player_secondary_positions
    )
    videos: Mapped[list["PlayerVideo"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan"
    )
