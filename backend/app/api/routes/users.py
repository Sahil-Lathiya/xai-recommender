import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DBSession
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Product, Recommendation, User, UserInteraction
from app.schemas.schemas import (
    InteractionRequest,
    InteractionResponse,
    RecentExplorationItem,
    TokenResponse,
    UserLoginRequest,
    UserProfileDetailResponse,
    UserProfileResponse,
    UserRegisterRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/users/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(request: UserRegisterRequest, db: DBSession) -> UserResponse:
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: DBSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=1440,
        user_id=user.id,
        name=user.name,
        is_admin=bool(user.is_admin),
    )


@router.post(
    "/users/interaction",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_interaction(
    request: InteractionRequest,
    db: DBSession,
) -> InteractionResponse:
    user = await db.get(User, request.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    product = await db.get(Product, request.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    interaction = UserInteraction(
        user_id=request.user_id,
        product_id=request.product_id,
        action_type=request.action_type,
        rating=request.rating,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    # Invalidate recommendation cache for this user so next request gets fresh results
    from app.ml.cache import recommendation_cache
    stale_keys = [k for k in list(recommendation_cache.keys()) if str(request.user_id) in str(k)]
    for k in stale_keys:
        recommendation_cache.pop(k, None)

    logger.info(
        "Interaction recorded: user=%s product=%s action=%s",
        request.user_id,
        request.product_id,
        request.action_type,
    )

    return InteractionResponse(id=interaction.id, recorded=True)


@router.get(
    "/users/{user_id}/profile/detail",
    response_model=UserProfileDetailResponse,
)
async def get_user_profile_detail(
    user_id: uuid.UUID,
    db: DBSession,
) -> UserProfileDetailResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stats_result = await db.execute(
        select(
            func.count(UserInteraction.id).label("total"),
            func.avg(UserInteraction.rating).label("avg_rating"),
        ).where(UserInteraction.user_id == user_id)
    )
    stats_row = stats_result.one_or_none()
    total_interactions = int(stats_row.total) if stats_row and stats_row.total else 0
    avg_rating = (
        round(float(stats_row.avg_rating), 2)
        if stats_row and stats_row.avg_rating is not None
        else None
    )

    cat_result = await db.execute(
        select(Product.category, func.count().label("cnt"))
        .join(UserInteraction, UserInteraction.product_id == Product.id)
        .where(UserInteraction.user_id == user_id)
        .group_by(Product.category)
        .order_by(func.count().desc())
        .limit(1)
    )
    cat_row = cat_result.first()
    favourite_category = cat_row[0] if cat_row else None

    rec_count_result = await db.execute(
        select(func.count(Recommendation.id)).where(Recommendation.user_id == user_id)
    )
    total_recommendations = rec_count_result.scalar_one() or 0

    cat_dist_result = await db.execute(
        select(Product.category, func.count().label("cnt"))
        .join(Recommendation, Recommendation.product_id == Product.id)
        .where(Recommendation.user_id == user_id)
        .group_by(Product.category)
        .order_by(func.count().desc())
    )
    cat_rows = cat_dist_result.all()
    total_cat = sum(row[1] for row in cat_rows)
    category_distribution = {
        row[0]: round(row[1] / total_cat * 100, 1) if total_cat > 0 else 0.0
        for row in cat_rows
    }

    recent_result = await db.execute(
        select(
            UserInteraction.id,
            Product.name,
            Product.category,
            Product.image_url,
            Product.amazon_url,
            UserInteraction.action_type,
            UserInteraction.timestamp,
        )
        .join(Product, Product.id == UserInteraction.product_id)
        .where(
            UserInteraction.user_id == user_id,
            UserInteraction.action_type.in_(["click", "purchase", "rate"]),
        )
        .order_by(UserInteraction.timestamp.desc())
        .limit(4)
    )
    recent_explorations = [
        RecentExplorationItem(
            id=row[0],
            product_name=row[1],
            product_category=row[2],
            image_url=row[3],
            amazon_url=row[4],
            action_type=row[5],
            timestamp=row[6],
        )
        for row in recent_result.all()
    ]

    return UserProfileDetailResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        total_interactions=total_interactions,
        favourite_category=favourite_category,
        avg_rating_given=avg_rating,
        total_recommendations=total_recommendations,
        recent_explorations=recent_explorations,
        category_distribution=category_distribution,
    )


@router.get(
    "/users/{user_id}/profile",
    response_model=UserProfileResponse,
)
async def get_user_profile(
    user_id: uuid.UUID,
    db: DBSession,
) -> UserProfileResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Aggregate interaction stats
    stats_result = await db.execute(
        select(
            func.count(UserInteraction.id).label("total"),
            func.avg(UserInteraction.rating).label("avg_rating"),
        ).where(UserInteraction.user_id == user_id)
    )
    stats_row = stats_result.one_or_none()
    total_interactions = int(stats_row.total) if stats_row and stats_row.total else 0
    avg_rating = (
        round(float(stats_row.avg_rating), 2)
        if stats_row and stats_row.avg_rating is not None
        else None
    )

    # Favourite category (most-interacted)
    cat_result = await db.execute(
        select(Product.category, func.count().label("cnt"))
        .join(UserInteraction, UserInteraction.product_id == Product.id)
        .where(UserInteraction.user_id == user_id)
        .group_by(Product.category)
        .order_by(func.count().desc())
        .limit(1)
    )
    cat_row = cat_result.first()
    favourite_category = cat_row[0] if cat_row else None

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        total_interactions=total_interactions,
        favourite_category=favourite_category,
        avg_rating_given=avg_rating,
    )
