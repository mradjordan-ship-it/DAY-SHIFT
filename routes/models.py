"""Pydantic models for Day Shift Marketplace routes."""
from typing import Optional
from pydantic import BaseModel


class RegisterBody(BaseModel):
    name: str
    email: str
    password: str
    role: str = "worker"


class LoginBody(BaseModel):
    email: str
    password: str


class MatchBody(BaseModel):
    worker_video_id: Optional[int] = None
    employer_video_id: Optional[int] = None


class MessageBody(BaseModel):
    content: str


class ReviewBody(BaseModel):
    rating: int
    feedback: str = ""


class ProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None


class ForgotPasswordBody(BaseModel):
    email: str


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class BoostBody(BaseModel):
    video_id: int
    tier: str  # 'boost' | 'spotlight' | 'premium'


class AdminBoostBody(BaseModel):
    action: str  # 'approve' | 'reject'


class AdminCreateBoostBody(BaseModel):
    video_id: int
    tier: str = "boost"  # 'boost' | 'spotlight' | 'premium'
    duration_days: int = 1  # Custom duration for admin boosts


class ReportBody(BaseModel):
    target_type: str  # "video" or "user"
    target_id: int
    reason: str       # harassment, spam, inappropriate, fake, other
    comment: Optional[str] = None


class ReviewReportBody(BaseModel):
    action: str  # dismiss, warn, suspend, remove_content
    reason: Optional[str] = None


TIERS = {
    "boost":     {"name": "Boost",     "price": 25,  "duration_days": 1,   "max_boosts": 1,  "features": ["Pin to top 24h", "Sponsored badge"]},
    "spotlight": {"name": "Spotlight", "price": 75,  "duration_days": 7,   "max_boosts": 3,  "features": ["Carousel placement", "7-day boost", "Priority feed position"]},
    "premium":   {"name": "Premium",   "price": 150, "duration_days": 14,  "max_boosts": 10, "features": ["Every carousel section", "14-day boost", "Full analytics", "Featured badge"]},
}

AD_TIERS = {
    "business": {
        "name": "Business",
        "price": 99,
        "interval": "month",
        "boosts_per_month": 2,
        "features": [
            "Verified business badge",
            "Business profile (logo, hours, website)",
            "2 boosted posts per month",
            "Featured in business directory",
            "Basic analytics (views, clicks)",
        ],
    },
    "premium": {
        "name": "Premium",
        "price": 249,
        "interval": "month",
        "boosts_per_month": 5,
        "features": [
            "Everything in Business",
            "5 boosted posts per month",
            "Banner ad in feed (rotating)",
            "Priority feed placement",
            "Full analytics dashboard",
            "Custom promotional code",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 499,
        "interval": "month",
        "boosts_per_month": -1,  # unlimited
        "features": [
            "Everything in Premium",
            "Unlimited boosted posts",
            "Dedicated carousel slot",
            "Sponsored content section",
            "Bulk job posting API",
            "Account manager",
        ],
    },
}

AUTO_REPLY = (
    "Thanks for reaching out to Day Shift! 🧡\n\n"
    "We've received your message and our team will get back to you as soon as possible — "
    "typically within 24 hours.\n\n"
    "In the meantime, check out the feed for the latest shifts and opportunities.\n\n"
    "— The Day Shift Team"
)
