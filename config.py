"""Cat Puzzle：概念圖風格的版面與顏色設定。"""

# 棋盤維持 6×6，避免改變既有關卡規則與答案。
BOARD_SIZE = 6  # 六個橫列、六個直欄，對應六種顏色區域。
CELL_SIZE = 88  # 每格像素寬高，棋盤是正方形。
BOARD_X = 411  # 棋盤左上角距離視窗左側的像素。
BOARD_Y = 188  # 棋盤左上角距離視窗上側的像素。
WINDOW_WIDTH = 1280  # 整個遊戲視窗寬度。
WINDOW_HEIGHT = 820  # 整個遊戲視窗高度。
FPS = 60  # 每秒最多刷新 60 次畫面。

# 整體使用奶油白、咖啡棕與柔和色塊。
BG = (250, 243, 238)
PANEL = (255, 252, 248)
TEXT = (98, 56, 47)
MUTED = (142, 115, 106)
ACCENT = (163, 101, 76)
ACCENT_DARK = (109, 65, 53)
WHITE = (255, 255, 255)
X_COLOR = (255, 255, 255)
ERROR = (188, 77, 71)
HINT_COLOR = (255, 196, 61)

REGION_COLORS = [
    (248, 155, 98),   # 柔橘
    (64, 172, 193),   # 湖水藍
    (231, 183, 34),   # 蜜黃色
    (145, 207, 126),  # 草綠
    (158, 137, 220),  # 淡紫
    (238, 140, 196),  # 粉紅
]
CAT_IMAGE_PATH = "assets/cat.png"  # 棋盤與右上角數量區共用的新貓咪頭圖片。

# 按鈕使用獨立的透明 PNG；統一由此處集中管理，之後換圖不用動操作邏輯。
# 字典的 key 要與 game.py 裡的按鈕名稱相同，value 是相對專案根目錄的路徑。
BUTTON_ICON_PATHS = {
    "hint": "assets/hint.png",       # 燈泡：顯示提示。
    "undo": "assets/undo.png",       # 左彎箭頭：復原上一步。
    "redo": "assets/redo.png",       # 右彎箭頭：重做下一步。
    "restart": "assets/restart.png", # 環形箭頭：重新開始同一關。
    "next": "assets/next.png",       # 右指三角形：跳至下一關。
}
BUTTON_ICON_SIZE = 48  # 五張 PNG 載入後統一縮放為 48×48 px。

# 介面圖片：左上角坐姿貓；右上角和棋盤使用同一張貓咪頭。
LOGO_CAT_IMAGE_PATH = "assets/logo_cat.png"
COUNTER_CAT_IMAGE_PATH = CAT_IMAGE_PATH
