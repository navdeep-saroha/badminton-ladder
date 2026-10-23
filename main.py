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


players: list[Player] = []
next_player_id = 1


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
    for player in players:
        if player.id == player_id:
            return player
    raise HTTPException(status_code=404, detail="Player not found")


@app.get("/ladder")
def get_ladder() -> list[Player]:
    return sorted(players, key=lambda p: p.rank)
