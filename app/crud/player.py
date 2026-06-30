from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import PlayerProfile, Position, PlayerVideo
from app.schemas import PlayerProfileCreate, PlayerProfileUpdate


async def create_player_profile(
    db: AsyncSession,
    profile_data: PlayerProfileCreate,
    photo_url: str | None,
    user_id: int
) -> PlayerProfile | None:
    db_profile = PlayerProfile(
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        birth_date=profile_data.birth_date,
        preferred_foot=profile_data.preferred_foot,
        current_club=profile_data.current_club,
        citizenship=profile_data.citizenship,
        main_position_id=profile_data.main_position_id,
        photo_url=photo_url,
        user_id=user_id
    )

    if profile_data.secondary_position_ids:
        positions_query = select(Position).where(
            Position.id.in_(profile_data.secondary_position_ids))
        positions_result = await db.execute(positions_query)
        db_positions = positions_result.scalars().all()
        db_profile.secondary_positions.extend(db_positions)

    if profile_data.videos:
        for video_item in profile_data.videos:
            db_video = PlayerVideo(
                youtube_id=video_item.youtube_id,
                title=video_item.title if video_item.title else "Highlights"
            )
            db_profile.videos.append(db_video)

    db.add(db_profile)
    await db.commit()
    return await get_player_profile_by_id(db, db_profile.id)


async def get_player_profile_by_id(
    db: AsyncSession,
    profile_id: int
) -> PlayerProfile | None:
    query = (
        select(PlayerProfile)
        .where(PlayerProfile.id == profile_id)
        .options(
            selectinload(PlayerProfile.user),
            selectinload(PlayerProfile.main_position),
            selectinload(PlayerProfile.secondary_positions),
            selectinload(PlayerProfile.videos)
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_player_profile(
    db: AsyncSession,
    profile_id: int,
    update_data: dict
) -> PlayerProfile | None:
    profile = await get_player_profile_by_id(db, profile_id)
    if not profile:
        return None

    for key, value in update_data.items():
        if key not in ["secondary_position_ids", "videos"] and value is not None:
            setattr(profile, key, value)

    if "secondary_position_ids" in update_data:
        sec_ids = update_data["secondary_position_ids"]
        if sec_ids:
            positions_query = select(Position).where(Position.id.in_(sec_ids))
            positions_result = await db.execute(positions_query)
            profile.secondary_positions = list(
                positions_result.scalars().all())
        else:
            profile.secondary_positions = []

    if "videos" in update_data:
        profile.videos.clear()
        for video_item in update_data["videos"]:
            if isinstance(video_item, dict):
                v_id = video_item.get("youtube_id")
                v_title = video_item.get("title", "Highlights")
            else:
                v_id = video_item.youtube_id
                v_title = video_item.title

            db_video = PlayerVideo(
                youtube_id=v_id,
                title=v_title if v_title else "Highlights"
            )
            profile.videos.append(db_video)

    await db.commit()
    return await get_player_profile_by_id(db, profile_id)


async def delete_player_profile(db: AsyncSession, profile_id: int) -> bool:
    profile = await get_player_profile_by_id(db, profile_id)
    if not profile:
        return False

    await db.delete(profile)
    await db.commit()
    return True
