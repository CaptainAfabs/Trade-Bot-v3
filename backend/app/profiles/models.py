from typing import Literal

from pydantic import BaseModel, Field

Risk = Literal["low", "medium", "high"]
Timeline = Literal["short", "medium", "long", "generational"]


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    risk: Risk = "medium"
    timeline: Timeline = "long"
    capital_usd: float = Field(default=500, ge=0)
    min_market_cap_usd: float = Field(default=0, ge=0)
    max_position_pct: float | None = None
    max_sector_pct: float | None = None
    sectors_exclude: list[str] = []
    sectors_prefer: list[str] = []
    dividend_only: bool = False
    esg_only: bool = False
    follow_investors: list[str] = []
    is_default: bool = False


class Profile(ProfileIn):
    id: int
    user_id: int


def derive_position_limits(risk: Risk, timeline: Timeline) -> tuple[float, float]:
    """Default position/sector caps from risk + timeline.
    Why: user wanted dynamic — small risk + generational => spread thin;
    high risk + short => concentrated bets allowed.
    """
    if risk == "low" and timeline in ("long", "generational"):
        return 4.0, 20.0
    if risk == "low":
        return 6.0, 25.0
    if risk == "medium" and timeline == "short":
        return 15.0, 40.0
    if risk == "medium":
        return 8.0, 30.0
    if risk == "high" and timeline == "short":
        return 40.0, 80.0
    return 20.0, 50.0
