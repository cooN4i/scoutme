from contextlib import asynccontextmanager
from math import ceil
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import select, literal_column, func
from sqlalchemy.orm import selectinload

from app.database import engine, Base, AsyncSessionLocal
from app import models
from app.routers import auth, players


async def seed_positions():
    async with AsyncSessionLocal() as session:
        query = select(models.Position)
        result = await session.execute(query)
        existing_positions = result.scalars().all()

        if not existing_positions:
            default_positions = [
                models.Position(name="GK"), models.Position(name="CB"),
                models.Position(name="LB"), models.Position(name="RB"),
                models.Position(name="CDM"), models.Position(name="CM"),
                models.Position(name="CAM"), models.Position(name="LM"),
                models.Position(name="RM"), models.Position(name="ST"),
                models.Position(name="LW"), models.Position(name="RW"),
            ]
            session.add_all(default_positions)
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_positions()

    yield
    await engine.dispose()


app = FastAPI(
    title="Football Scout Platform API",
    description="Backend API for managing player profiles and scout tracking",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(players.router)


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")


@app.get("/profile/create")
async def create_profile_page(
    request: Request,
    user: models.User | None = Depends(auth.get_current_user_optional)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    async with AsyncSessionLocal() as session:
        query = select(models.Position)
        result = await session.execute(query)
        positions_list = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="create_profile.html",
        context={"user": user, "positions": positions_list}
    )


@app.get("/profile/edit")
async def edit_profile_page(
    request: Request,
    player_id: int | None = None,
    user: models.User | None = Depends(auth.get_current_user_optional)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    async with AsyncSessionLocal() as session:
        if player_id and user.role == "admin":
            query = select(models.PlayerProfile).where(
                models.PlayerProfile.id == player_id)
        else:
            query = select(models.PlayerProfile).where(
                models.PlayerProfile.user_id == user.id)

        query = query.options(
            selectinload(models.PlayerProfile.secondary_positions),
            selectinload(models.PlayerProfile.videos)
        )
        result = await session.execute(query)
        profile = result.scalar_one_or_none()

        if not profile:
            return RedirectResponse(url="/profile/create", status_code=303)

        pos_query = select(models.Position)
        pos_result = await session.execute(pos_query)
        positions_list = pos_result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="edit_profile.html",
        context={"user": user, "profile": profile, "positions": positions_list}
    )


@app.get("/profile")
async def profile_page(
    request: Request,
    user: models.User | None = Depends(auth.get_current_user_optional)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    sqlite_age_expression = literal_column(
        "(strftime('%Y', 'now') - strftime('%Y', birth_date)) - "
        "(strftime('%m-%d', 'now') < strftime('%m-%d', birth_date))"
    )

    async with AsyncSessionLocal() as session:
        query = (
            select(models.PlayerProfile,
                   sqlite_age_expression.label("computed_age"))
            .where(models.PlayerProfile.user_id == user.id)
            .options(
                selectinload(models.PlayerProfile.user),
                selectinload(models.PlayerProfile.main_position),
                selectinload(models.PlayerProfile.secondary_positions),
                selectinload(models.PlayerProfile.videos)
            )
        )
        result = await session.execute(query)
        row = result.first()

        player_profile = None
        if row:
            player_profile = row.PlayerProfile
            player_profile.age = row.computed_age

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user, "profile": player_profile}
    )


@app.get("/player/{player_id}")
async def player_detail_page(
    player_id: int,
    request: Request,
    user: models.User | None = Depends(auth.get_current_user_optional)
):
    sqlite_age_expression = literal_column(
        "(strftime('%Y', 'now') - strftime('%Y', birth_date)) - "
        "(strftime('%m-%d', 'now') < strftime('%m-%d', birth_date))"
    )

    async with AsyncSessionLocal() as session:
        query = (
            select(models.PlayerProfile,
                   sqlite_age_expression.label("computed_age"))
            .where(models.PlayerProfile.id == player_id)
            .options(
                selectinload(models.PlayerProfile.user),
                selectinload(models.PlayerProfile.main_position),
                selectinload(models.PlayerProfile.secondary_positions),
                selectinload(models.PlayerProfile.videos)
            )
        )
        result = await session.execute(query)
        row = result.first()

        if not row:
            return RedirectResponse(url="/", status_code=303)

        player_profile = row.PlayerProfile
        player_profile.age = row.computed_age

    return templates.TemplateResponse(
        request=request,
        name="player_detail.html",
        context={"user": user, "profile": player_profile}
    )


@app.get("/")
async def root(
    request: Request,
    position: str | None = None,
    nationality: str | None = None,
    page: int = 1,
    user: models.User | None = Depends(auth.get_current_user_optional)
):
    limit = 10
    offset = (page - 1) * limit
    sqlite_age_expression = literal_column(
        "(strftime('%Y', 'now') - strftime('%Y', birth_date)) - "
        "(strftime('%m-%d', 'now') < strftime('%m-%d', birth_date))"
    )

    async with AsyncSessionLocal() as session:
        count_query = select(func.count(models.PlayerProfile.id))
        if position:
            count_query = count_query.join(models.PlayerProfile.main_position).where(
                models.Position.name == position)
        if nationality:
            count_query = count_query.where(
                models.PlayerProfile.citizenship.ilike(f"%{nationality}%"))

        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        query = select(models.PlayerProfile, sqlite_age_expression.label("computed_age")).options(
            selectinload(models.PlayerProfile.main_position)
        )

        if position:
            query = query.join(models.PlayerProfile.main_position).where(
                models.Position.name == position)
        if nationality:
            query = query.where(
                models.PlayerProfile.citizenship.ilike(f"%{nationality}%"))

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)

        players_list = []
        for row in result.all():
            player = row.PlayerProfile
            player.age = row.computed_age
            players_list.append(player)

    total_pages = ceil(total_count / limit)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "players": players_list,
            "selected_position": position,
            "selected_nationality": nationality,
            "user": user,
            "current_page": page,
            "total_pages": total_pages
        }
    )
