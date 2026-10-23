from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class Player(BaseModel):
    id: int
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
    player = Player(id=next_player_id, name=player_in.name, rank=len(players) + 1)
    players.append(player)
    next_player_id += 1
    return player


@app.get("/players")
def list_players() -> list[Player]:
    return sorted(players, key=lambda p: p.id)


@app.get("/ladder")
def get_ladder() -> list[Player]:
    return sorted(players, key=lambda p: p.rank)
