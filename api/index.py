#from fastapi import FastAPI
#app = FastAPI()
#@app.get("/")
#def read_root():
#    myresp = {"message", "Hello from FastAPI on Vercel!"}
#    return myresp

#@app.get("/api/health")
#def health_check():
#    myresp = {"status", "healthy"}
#    return myresp

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid

# 創建 FastAPI 實例 - Vercel 需要這個 'app' 變數
app = FastAPI(title="Tic-Tac-Toe API")

# 允許 CORS（讓你的本地客戶端可以訪問）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境建議限制為你的客戶端網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 數據模型（保持不變）
class GameMove(BaseModel):
    board: List[str]
    position: int
    player: str
    game_id: Optional[str] = None

class GameResponse(BaseModel):
    valid_move: bool
    new_board: List[str]
    winner: Optional[str]
    is_draw: bool
    message: str
    game_id: Optional[str] = None
    next_player: Optional[str] = None

class GameState(BaseModel):
    board: List[str]
    current_player: str
    game_id: str
    status: str

# 注意：Vercel 是無伺服器環境，不能使用簡單的全局變數存儲
# 因為每個請求可能由不同的函數實例處理
# 這裡改用字典模擬，但生產環境應該使用外部數據庫（如 Vercel KV、PostgreSQL 等）
games: Dict[str, GameState] = {}

# 勝利組合（保持不變）
WINNING_COMBINATIONS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],
    [0, 3, 6], [1, 4, 7], [2, 5, 8],
    [0, 4, 8], [2, 4, 6]
]

# 輔助函數（保持不變）
def check_winner(board: List[str]) -> Optional[str]:
    for combo in WINNING_COMBINATIONS:
        if (board[combo[0]] == board[combo[1]] == 
            board[combo[2]] != " "):
            return board[combo[0]]
    return None

def is_board_full(board: List[str]) -> bool:
    return " " not in board

def validate_move(board: List[str], position: int, player: str) -> bool:
    if position < 0 or position > 8:
        return False
    if board[position] != " ":
        return False
    if player not in ["X", "O"]:
        return False
    return True

# API 端點
@app.get("/")
async def root():
    return {
        "message": "Tic-Tac-Toe API running on Vercel",
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
    # 檢查遊戲是否存在
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
            message=f"Invalid move! Position {move.position + 1} is invalid.",
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

# AI 輔助功能（保持不變）
@app.get("/ai-move/{game_id}")
async def get_ai_move(game_id: str, difficulty: str = "medium"):
    """獲取 AI 建議的移動"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    empty_positions = [i for i, spot in enumerate(game.board) if spot == " "]
    
    if not empty_positions:
        return {"move": None, "message": "No empty positions"}
    
    # AI 邏輯（保持不變）
    import random
    
    if difficulty == "easy":
        move = random.choice(empty_positions)
    elif difficulty == "medium":
        # 嘗試贏或阻擋
        opponent = "O" if game.current_player == "X" else "X"
        move = None
        
        # 嘗試贏
        for pos in empty_positions:
            board_copy = game.board.copy()
            board_copy[pos] = game.current_player
            if check_winner(board_copy) == game.current_player:
                move = pos
                break
        
        # 嘗試阻擋
        if move is None:
            for pos in empty_positions:
                board_copy = game.board.copy()
                board_copy[pos] = opponent
                if check_winner(board_copy) == opponent:
                    move = pos
                    break
        
        # 優先中心
        if move is None and 4 in empty_positions:
            move = 4
        
        # 優先角落
        if move is None:
            corners = [0, 2, 6, 8]
            available_corners = [c for c in corners if c in empty_positions]
            if available_corners:
                move = random.choice(available_corners)
        
        # 隨機選擇
        if move is None:
            move = random.choice(empty_positions)
    else:  # hard
        # 簡化版，實際可用 minimax
        move = random.choice(empty_positions)
    
    return {
        "move": move,
        "position": move + 1,
        "message": f"AI suggests position {move + 1}"
    }

# 注意：不需要 if __name__ == "__main__" 區塊
# Vercel 會自己處理運行
