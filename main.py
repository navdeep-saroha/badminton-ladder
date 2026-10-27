from enum import StrEnum
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import PlayerRow, get_session

app = FastAPI()

SessionDep = Annotated[Session, Depends(get_session)]


class PlayerCreate(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9_.]{3,20}$")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class Player(BaseModel):
    # Lets Pydantic read fields from a PlayerRow's attributes, not only from a dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    rank: int


class ChallengeCreate(BaseModel):
    challenger_id: int
    defender_id: int


class ChallengeStatus(StrEnum):
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Challenge(BaseModel):
    id: int
    challenger_id: int
    defender_id: int
    status: ChallengeStatus


challenges: list[Challenge] = []
next_challenge_id = 1

MAX_CHALLENGE_DISTANCE = 3

# OPEN is the only state a challenge can leave. The other three are final.
ALLOWED_TRANSITIONS: dict[ChallengeStatus, set[ChallengeStatus]] = {
    ChallengeStatus.OPEN: {
        ChallengeStatus.COMPLETED,
        ChallengeStatus.EXPIRED,
        ChallengeStatus.CANCELLED,
    },
    ChallengeStatus.COMPLETED: set(),
    ChallengeStatus.EXPIRED: set(),
    ChallengeStatus.CANCELLED: set(),
}


def find_player(session: Session, player_id: int) -> PlayerRow | None:
    return session.get(PlayerRow, player_id)


def is_self_challenge(challenger_id: int, defender_id: int) -> bool:
    return challenger_id == defender_id


def rank_rule_violation(challenger: PlayerRow, defender: PlayerRow) -> str | None:
    """Return why this challenge breaks a rank rule, or None if it is allowed."""
    # Rank 1 is the top, so a challenger above the defender has a smaller rank number.
    distance = challenger.rank - defender.rank
    if distance < 0:
        return "Cannot challenge a player ranked below you"
    if distance > MAX_CHALLENGE_DISTANCE:
        return f"Cannot challenge more than {MAX_CHALLENGE_DISTANCE} ranks above you"
    return None


def can_transition(current: ChallengeStatus, new: ChallengeStatus) -> bool:
    return new in ALLOWED_TRANSITIONS[current]


def find_challenge(challenge_id: int) -> Challenge | None:
    for challenge in challenges:
        if challenge.id == challenge_id:
            return challenge
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/players", status_code=201)
def create_player(player_in: PlayerCreate, session: SessionDep) -> Player:
    existing = session.scalars(
        select(PlayerRow).where(PlayerRow.username == player_in.username)
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username already taken")

    # New players join at the bottom: one below the current lowest rank.
    bottom_rank = session.scalar(select(func.coalesce(func.max(PlayerRow.rank), 0)))
    player = PlayerRow(
        username=player_in.username,
        name=player_in.name,
        rank=bottom_rank + 1,
    )
    session.add(player)
    session.commit()
    return Player.model_validate(player)


@app.get("/players")
def list_players(session: SessionDep) -> list[Player]:
    rows = session.scalars(select(PlayerRow).order_by(PlayerRow.id)).all()
    return [Player.model_validate(row) for row in rows]


@app.get("/players/{player_id}")
def get_player(player_id: int, session: SessionDep) -> Player:
    player = find_player(session, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return Player.model_validate(player)


@app.get("/ladder")
def get_ladder(session: SessionDep) -> list[Player]:
    rows = session.scalars(select(PlayerRow).order_by(PlayerRow.rank)).all()
    return [Player.model_validate(row) for row in rows]


@app.post("/challenges", status_code=201)
def create_challenge(challenge_in: ChallengeCreate, session: SessionDep) -> Challenge:
    global next_challenge_id
    challenger = find_player(session, challenge_in.challenger_id)
    if challenger is None:
        raise HTTPException(status_code=422, detail="Challenger not found")
    defender = find_player(session, challenge_in.defender_id)
    if defender is None:
        raise HTTPException(status_code=422, detail="Defender not found")
    if is_self_challenge(challenger.id, defender.id):
        raise HTTPException(status_code=422, detail="Cannot challenge yourself")
    violation = rank_rule_violation(challenger, defender)
    if violation is not None:
        raise HTTPException(status_code=409, detail=violation)

    challenge = Challenge(
        id=next_challenge_id,
        challenger_id=challenge_in.challenger_id,
        defender_id=challenge_in.defender_id,
        status=ChallengeStatus.OPEN,
    )
    challenges.append(challenge)
    next_challenge_id += 1
    return challenge


@app.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: int) -> Challenge:
    challenge = find_challenge(challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


@app.post("/challenges/{challenge_id}/cancel")
def cancel_challenge(challenge_id: int) -> Challenge:
    challenge = find_challenge(challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if not can_transition(challenge.status, ChallengeStatus.CANCELLED):
        raise HTTPException(
            status_code=409, detail=f"Cannot cancel a {challenge.status} challenge"
        )
    challenge.status = ChallengeStatus.CANCELLED
    return challenge
