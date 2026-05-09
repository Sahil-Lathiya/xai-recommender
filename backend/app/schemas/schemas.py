from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth / Users ───────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1440
    user_id: uuid.UUID
    name: str
    is_admin: bool = False


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    total_interactions: int
    favourite_category: Optional[str]
    avg_rating_given: Optional[float]

    model_config = {"from_attributes": True}


# ── Interactions ───────────────────────────────────────────────────────────────

class InteractionRequest(BaseModel):
    user_id: uuid.UUID
    product_id: uuid.UUID
    action_type: str = Field(..., pattern="^(view|click|purchase|rate)$")
    rating: Optional[float] = Field(None, ge=0, le=5)


class InteractionResponse(BaseModel):
    id: uuid.UUID
    recorded: bool = True


# ── Products ───────────────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    price: float
    rating: float
    review_count: int
    image_url: Optional[str]
    amazon_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Recommendations ────────────────────────────────────────────────────────────

class RecommendationRequest(BaseModel):
    user_id: uuid.UUID
    limit: int = Field(5, ge=1, le=20)
    category_filter: Optional[str] = None


class RecommendationItem(BaseModel):
    recommendation_id: uuid.UUID
    product: ProductResponse
    score: float = Field(..., ge=0, le=1)
    confidence_score: int = Field(..., ge=0, le=100)
    top_reason: str


class RecommendationResponse(BaseModel):
    user_id: uuid.UUID
    recommendations: list[RecommendationItem]
    cached: bool = False
    response_time_ms: int
    is_new_user: bool = False


class RecommendationHistoryItem(BaseModel):
    recommendation_id: uuid.UUID
    product_name: str
    score: float
    created_at: datetime


class RecommendationHistoryResponse(BaseModel):
    user_id: uuid.UUID
    history: list[RecommendationHistoryItem]
    total: int


# ── SHAP / Explanations ────────────────────────────────────────────────────────

class FeatureContribution(BaseModel):
    feature: str
    raw_value: float
    shap_value: float
    direction: str  # "positive" | "negative"
    human_label: str


class SHAPValues(BaseModel):
    base_value: float
    feature_contributions: list[FeatureContribution]
    top_3_reasons: list[str]


class ExplanationResponse(BaseModel):
    recommendation_id: uuid.UUID
    product: ProductResponse
    shap_values: SHAPValues
    llm_explanation: str
    counterfactual: Optional[str]
    confidence_score: int = Field(..., ge=0, le=100)
    powered_by: str = "XGBoost + SHAP + GPT-4o-mini"


class GlobalFeatureItem(BaseModel):
    feature_name: str
    importance_score: float
    rank: int
    description: str


class GlobalFeatureImportanceResponse(BaseModel):
    features: list[GlobalFeatureItem]
    cached_until: datetime


# ── Dashboard ──────────────────────────────────────────────────────────────────

class DashboardStatsResponse(BaseModel):
    total_recommendations_today: int
    total_users: int
    avg_confidence_score: float
    top_category: str
    model_ndcg_score: float
    cache_hit_rate: float
    estimated_api_cost_today_usd: float


class DayPerformance(BaseModel):
    date: str
    recommendations_count: int
    avg_confidence: float
    avg_response_time_ms: float


class ModelPerformanceResponse(BaseModel):
    days: list[DayPerformance]
    overall_ndcg: float
    overall_precision_at_5: float


# ── Profile Detail ─────────────────────────────────────────────────────────────

class RecentExplorationItem(BaseModel):
    recommendation_id: uuid.UUID
    product_name: str
    product_category: str
    image_url: Optional[str]
    viewed_at: datetime


class UserProfileDetailResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    total_interactions: int
    favourite_category: Optional[str]
    avg_rating_given: Optional[float]
    total_recommendations: int
    recent_explorations: list[RecentExplorationItem]
    category_distribution: dict[str, float]

    model_config = {"from_attributes": True}


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    db_connected: bool
    timestamp: str
    memory_mb: float
