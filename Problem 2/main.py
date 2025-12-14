from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import random
import uuid

app = FastAPI()

# Models
class Player(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    points: int = 0

class Room(BaseModel):
    id: str
    players: List[Player] = []
    waitlist: List[Player] = []
    roles_assigned: bool = False
    mantri_guess: Optional[str] = None
    round_complete: bool = False

class CreateRoomRequest(BaseModel):
    player_name: str

class JoinRoomRequest(BaseModel):
    room_id: str
    player_name: str

class SubmitGuessRequest(BaseModel):
    guessed_player_id: str
    mantri_id: str

# Database
rooms: Dict[str, Room] = {}
player_scores: Dict[str, Dict[str, int]] = {}  # roomId -> {playerId: cumulative_score}

ROLE_POINTS = {"Raja": 1000, "Mantri": 800, "Chor": 0, "Sipahi": 500}
ROLES = ["Raja", "Mantri", "Chor", "Sipahi"]

# POST /rooms/create
@app.post("/rooms/create")
def create_room(request: CreateRoomRequest):
    room_id = str(uuid.uuid4())
    player_id = str(uuid.uuid4())
    player = Player(id=player_id, name=request.player_name)
    
    rooms[room_id] = Room(id=room_id, players=[player])
    player_scores[room_id] = {player_id: 0}
    
    return {"room_id": room_id, "player_id": player_id, "message": "Room created"}

# POST /rooms/join
@app.post("/rooms/join")
def join_room(request: JoinRoomRequest):
    if request.room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[request.room_id]
    player_id = str(uuid.uuid4())
    player = Player(id=player_id, name=request.player_name)
    
    if len(room.players) < 4:
        room.players.append(player)
        player_scores[request.room_id][player_id] = 0
        return {"player_id": player_id, "message": "Joined room"}
    else:
        room.waitlist.append(player)
        return {"player_id": player_id, "message": "Added to waitlist"}

# GET /rooms
@app.get("/rooms")
def get_rooms():
    room_list = []
    for room_id, room in rooms.items():
        room_list.append({
            "room_id": room_id,
            "player_count": len(room.players),
            "waitlist_count": len(room.waitlist),
            "roles_assigned": room.roles_assigned,
            "round_complete": room.round_complete
        })
    return {"rooms": room_list}

# GET /rooms/players/:roomId
@app.get("/rooms/players/{room_id}")
def get_players(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    players = [{"id": p.id, "name": p.name} for p in rooms[room_id].players]
    return {"players": players}

# POST /rooms/assign/:roomId
@app.post("/rooms/assign/{room_id}")
def assign_roles(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    if len(room.players) < 4:
        raise HTTPException(status_code=400, detail="Need 4 players to assign roles")
    
    roles = ROLES.copy()
    random.shuffle(roles)
    
    for i, player in enumerate(room.players):
        player.role = roles[i]
    
    room.roles_assigned = True
    return {"message": "Roles assigned", "status": "ready_for_guess"}

# POST /rooms/reset/:roomId
@app.post("/rooms/reset/{room_id}")
def reset_round(room_id: str):
    """Reset the room's round state so a new round can commence.
    - Clears assigned roles
    - Resets per-round points to 0 (keeps cumulative leaderboard in player_scores)
    - Clears Mantri's guess and round completion flag
    """
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    room = rooms[room_id]

    for player in room.players:
        player.role = None
        player.points = 0

    room.roles_assigned = False
    room.mantri_guess = None
    room.round_complete = False

    return {"message": "Room reset. Ready to assign roles."}

# GET /role/me/:roomId/:playerId
@app.get("/role/me/{room_id}/{player_id}")
def get_my_role(room_id: str, player_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    player = next((p for p in rooms[room_id].players if p.id == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {"role": player.role}

# POST /guess/:roomId
@app.post("/guess/{room_id}")
def submit_guess(room_id: str, request: SubmitGuessRequest):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    mantri = next((p for p in room.players if p.id == request.mantri_id), None)
    
    if not mantri or mantri.role != "Mantri":
        raise HTTPException(status_code=403, detail="Only Mantri can guess")
    
    room.mantri_guess = request.guessed_player_id
    return {"message": "Guess submitted"}

# GET /result/:roomId
@app.get("/result/{room_id}")
def get_result(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    if not room.mantri_guess:
        raise HTTPException(status_code=400, detail="Guess not submitted yet")
    
    guessed_player = next((p for p in room.players if p.id == room.mantri_guess), None)
    chor = next((p for p in room.players if p.role == "Chor"), None)
    
    result = []
    for player in room.players:
        points = ROLE_POINTS[player.role]
        
        if guessed_player.id == chor.id and player.role in ["Mantri", "Sipahi"]:
            pass
        elif guessed_player.id != chor.id and player.role == "Chor":
            points = ROLE_POINTS["Mantri"] + ROLE_POINTS["Sipahi"]
        
        player.points = points
        player_scores[room_id][player.id] += points
        result.append({"name": player.name, "role": player.role, "points": points})
    
    room.round_complete = True
    return {"result": result, "correct": guessed_player.id == chor.id}

# GET /leaderboard/:roomId
@app.get("/leaderboard/{room_id}")
def get_leaderboard(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    scores = player_scores[room_id]
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    leaderboard = []
    for player_id, score in sorted_scores:
        player = next((p for p in rooms[room_id].players if p.id == player_id), None)
        leaderboard.append({"name": player.name, "score": score})
    
    return {"leaderboard": leaderboard}