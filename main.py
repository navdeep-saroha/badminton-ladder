from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, StringConstraints

app = FastAPI()


class PlayerCreate(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9_.]{3,20}$")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class Player(BaseModel):
    id: int
    username: str
    name: str
    rank: int


class ChallengeCreate(BaseModel):
    challenger_id: int
    defender_id: int


class Challenge(BaseModel):
    id: int
    challenger_id: int
    defender_id: int


players: list[Player] = []
next_player_id = 1

challenges: list[Challenge] = []
next_challenge_id = 1

MAX_CHALLENGE_DISTANCE = 3


def find_player(player_id: int) -> Player | None:
    for player in players:
        if player.id == player_id:
            return player
    return None


def is_self_challenge(challenger_id: int, defender_id: int) -> bool:
    return challenger_id == defender_id


def rank_rule_violation(challenger: Player, defender: Player) -> str | None:
    """Return why this challenge breaks a rank rule, or None if it is allowed."""
    # Rank 1 is the top, so a challenger above the defender has a smaller rank number.
    distance = challenger.rank - defender.rank
    if distance < 0:
        return "Cannot challenge a player ranked below you"
    if distance > MAX_CHALLENGE_DISTANCE:
        return f"Cannot challenge more than {MAX_CHALLENGE_DISTANCE} ranks above you"
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/players", status_code=201)
def create_player(player_in: PlayerCreate) -> Player:
    global next_player_id
    for existing in players:
        if existing.username == player_in.username:
            raise HTTPException(status_code=409, detail="Username already taken")
    player = Player(
        id=next_player_id,
        username=player_in.username,
        name=player_in.name,
        rank=len(players) + 1,
    )
    players.append(player)
    next_player_id += 1
    return player


@app.get("/players")
def list_players() -> list[Player]:
    return sorted(players, key=lambda p: p.id)


@app.get("/players/{player_id}")
def get_player(player_id: int) -> Player:
    player = find_player(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.get("/ladder")
def get_ladder() -> list[Player]:
    return sorted(players, key=lambda p: p.rank)


@app.post("/challenges", status_code=201)
def create_challenge(challenge_in: ChallengeCreate) -> Challenge:
    global next_challenge_id
    challenger = find_player(challenge_in.challenger_id)
    if challenger is None:
        raise HTTPException(status_code=422, detail="Challenger not found")
    defender = find_player(challenge_in.defender_id)
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
    )
    challenges.append(challenge)
    next_challenge_id += 1
    return challenge
