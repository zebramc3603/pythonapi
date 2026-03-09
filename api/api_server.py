from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn

app = FastAPI(title="Tic-Tac-Toe API")

# 允許 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 數據模型
class GameMove(BaseModel):
    board: List[str]          # 當前棋盤狀態
    position: int              # 玩家選擇的位置 (0-8)
    player: str                # 當前玩家 "X" 或 "O"
    game_id: Optional[str] = None  # 遊戲ID，用於追蹤多個遊戲

class GameResponse(BaseModel):
    valid_move: bool           # 是否有效移動
    new_board: List[str]       # 更新後的棋盤
    winner: Optional[str]       # 贏家 "X", "O", 或 None
    is_draw: bool               # 是否平局
    message: str                # 狀態消息
    game_id: Optional[str] = None
    next_player: Optional[str] = None  # 下一個玩家

class GameState(BaseModel):
    board: List[str]
    current_player: str
    game_id: str
    status: str  # "playing", "finished"

# 存儲多個遊戲狀態 (簡單的內存存儲)
games: Dict[str, GameState] = {}

# 勝利組合
WINNING_COMBINATIONS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],  # 橫行
    [0, 3, 6], [1, 4, 7], [2, 5, 8],  # 直行
    [0, 4, 8], [2, 4, 6]              # 對角線
]

def check_winner(board: List[str]) -> Optional[str]:
    """檢查贏家"""
    for combo in WINNING_COMBINATIONS:
        if (board[combo[0]] == board[combo[1]] == 
            board[combo[2]] != " "):
            return board[combo[0]]
    return None

def is_board_full(board: List[str]) -> bool:
    """檢查棋盤是否已滿"""
    return " " not in board

def validate_move(board: List[str], position: int, player: str) -> bool:
    """驗證移動是否有效"""
    # 檢查位置是否在範圍內
    if position < 0 or position > 8:
        return False
    
    # 檢查該位置是否為空
    if board[position] != " ":
        return False
    
    # 檢查玩家符號是否有效
    if player not in ["X", "O"]:
        return False
    
    return True

@app.get("/")
async def root():
    return {
        "message": "Tic-Tac-Toe API",
        "endpoints": {
            "POST /move": "Make a move",
            "POST /new-game": "Start a new game",
            "GET /game/{game_id}": "Get game state",
            "GET /ai-move/{game_id}": "Get AI move suggestion"
        }
    }

@app.post("/new-game", response_model=GameState)
async def new_game():
    """開始新遊戲"""
    import uuid
    game_id = str(uuid.uuid4())[:8]
    
    game_state = GameState(
        board=[" "] * 9,
        current_player="X",
        game_id=game_id,
        status="playing"
    )
    
    games[game_id] = game_state
    return game_state

@app.post("/move", response_model=GameResponse)
async def make_move(move: GameMove):
    """處理遊戲移動"""
    
    # 如果是現有遊戲，獲取遊戲狀態
    if move.game_id and move.game_id in games:
        game = games[move.game_id]
        board = game.board.copy()
        current_player = game.current_player
    else:
        board = move.board.copy()
        current_player = move.player
    
    # 驗證移動
    if not validate_move(board, move.position, current_player):
        return GameResponse(
            valid_move=False,
            new_board=board,
            winner=None,
            is_draw=False,
            message=f"Invalid move! Position {move.position + 1} is already taken or out of range.",
            game_id=move.game_id,
            next_player=current_player
        )
    
    # 執行移動
    board[move.position] = current_player
    
    # 檢查遊戲狀態
    winner = check_winner(board)
    is_draw = is_board_full(board) and winner is None
    
    # 更新遊戲狀態
    if move.game_id and move.game_id in games:
        games[move.game_id].board = board
        if winner or is_draw:
            games[move.game_id].status = "finished"
            next_player = None
        else:
            games[move.game_id].current_player = "O" if current_player == "X" else "X"
            next_player = games[move.game_id].current_player
    else:
        next_player = "O" if current_player == "X" else "X" if not (winner or is_draw) else None
    
    # 準備響應消息
    if winner:
        message = f"Player {winner} wins! 🎉"
    elif is_draw:
        message = "Game ended in a draw! 🤝"
    else:
        message = f"Move accepted. Next player: {next_player}"
    
    return GameResponse(
        valid_move=True,
        new_board=board,
        winner=winner,
        is_draw=is_draw,
        message=message,
        game_id=move.game_id,
        next_player=next_player
    )

@app.get("/game/{game_id}")
async def get_game(game_id: str):
    """獲取遊戲狀態"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return games[game_id]

@app.get("/ai-move/{game_id}")
async def get_ai_move(game_id: str, difficulty: str = "medium"):
    """獲取 AI 建議的移動"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    empty_positions = [i for i, spot in enumerate(game.board) if spot == " "]
    
    if not empty_positions:
        return {"move": None, "message": "No empty positions"}
    
    # 簡單的 AI 邏輯
    if difficulty == "easy":
        # 隨機移動
        import random
        move = random.choice(empty_positions)
    elif difficulty == "medium":
        # 嘗試贏或阻擋
        move = get_strategic_move(game.board, game.current_player, empty_positions)
    else:
        # 困難模式 - 嘗試最佳移動
        move = get_best_move(game.board, game.current_player, empty_positions)
    
    return {
        "move": move,
        "position": move + 1,  # 人類可讀的位置 (1-9)
        "message": f"AI suggests position {move + 1}"
    }

def get_strategic_move(board, player, empty_positions):
    """獲取策略性移動"""
    opponent = "O" if player == "X" else "X"
    
    # 嘗試贏
    for pos in empty_positions:
        board_copy = board.copy()
        board_copy[pos] = player
        if check_winner(board_copy) == player:
            return pos
    
    # 嘗試阻擋
    for pos in empty_positions:
        board_copy = board.copy()
        board_copy[pos] = opponent
        if check_winner(board_copy) == opponent:
            return pos
    
    # 優先中心
    if 4 in empty_positions:
        return 4
    
    # 優先角落
    corners = [0, 2, 6, 8]
    available_corners = [c for c in corners if c in empty_positions]
    if available_corners:
        import random
        return random.choice(available_corners)
    
    # 隨機選擇
    import random
    return random.choice(empty_positions)

def get_best_move(board, player, empty_positions):
    """獲取最佳移動 (Minimax 簡化版)"""
    # 這裡可以實現 minimax 算法
    # 為簡單起見，使用策略性移動
    return get_strategic_move(board, player, empty_positions)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)