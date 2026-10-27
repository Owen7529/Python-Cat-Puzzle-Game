"""概念圖風格主畫面：左規則卡、中棋盤、右功能鍵。"""

import random
import time
from pathlib import Path
import numpy as np
import pygame

from config import (WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BG, TEXT, MUTED,
                    BOARD_SIZE, BOARD_X, BOARD_Y, CELL_SIZE,
                    BUTTON_ICON_PATHS, BUTTON_ICON_SIZE,
                    LOGO_CAT_IMAGE_PATH, COUNTER_CAT_IMAGE_PATH)
from puzzle import Puzzle
from board import Board


class Game:
    """遊戲控制、操作歷史、關卡與整體 UI。"""

    def __init__(self):
        """建立視窗、關卡、棋盤、操作歷史與所有圖片資源。"""
        # 初始化 Pygame 的顯示、圖片與字型功能。
        pygame.init()
        # screen：整個遊戲的畫布；clock：用來限制畫面刷新率。
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cat Puzzle")
        self.clock = pygame.time.Clock()
        self.running = True          # 關閉視窗時切換為 False，結束主迴圈。
        self.puzzle = Puzzle()       # 關卡資料、答案、洗牌與規則的管理物件。
        self.board = Board(self.puzzle)  # 玩家放置的貓、X 記號與棋盤繪製。
        self.won = False             # 目前是否已完成關卡。
        self.status_text = ""       # 下方暫時顯示的訊息文字。
        self.status_until = 0        # 訊息應顯示到哪個時間點（秒）。
        self.hint_cell = None        # 最近一次提示的 (列, 欄)，None 代表未提示。
        self.hint_until = 0          # 黃色提示框的結束時間。
        self.history = []            # 每一步操作後，cats 與 marks 的 NumPy 快照。
        self.history_index = -1      # 目前所處的快照索引，從 0 開始。
        self.save_history()          # 把剛開局的空白盤面設為第 0 步。

        # 右側五個大按鈕；不遮住棋盤。
        self.buttons = {
            "hint": pygame.Rect(1002, 185, 225, 96),
            "undo": pygame.Rect(1002, 294, 225, 96),
            "redo": pygame.Rect(1002, 403, 225, 96),
            "restart": pygame.Rect(1002, 512, 225, 96),
            "next": pygame.Rect(1002, 621, 225, 96),
        }
        self.font_cache = {}         # {(字級, 粗體): 已載入的 Pygame Font}。
        # 五張透明 PNG 在初始化時載入一次，遊戲每一影格只重複繪製。
        self.button_icons = self.load_button_icons()
        # 左側坐姿插圖、右上角貓咪數量圖示依不同顯示大小載入。
        # 右上角與棋盤讀取相同的 assets/cat.png，風格保持一致。
        self.logo_cat_image = self.load_ui_image(LOGO_CAT_IMAGE_PATH, (126, 150))
        self.counter_cat_image = self.load_ui_image(COUNTER_CAT_IMAGE_PATH, (52, 52))

    def load_ui_image(self, relative_path, size):
        """讀取單張介面圖片並縮放；若失敗則回傳 None。"""
        project_dir = Path(__file__).resolve().parent
        image_path = project_dir / relative_path
        try:
            source = pygame.image.load(str(image_path)).convert_alpha()
            return pygame.transform.smoothscale(source, size)
        except (FileNotFoundError, OSError, pygame.error):
            return None

    def load_button_icons(self):
        """讀取五張按鈕圖示並預先準備停用版本。

        回傳：{按鈕名稱: (正常圖片, 半透明的停用圖片)}。
        如果圖片不存在、毀損或 Pygame 讀取失敗，只略過該圖；
        draw_buttons() 會改用原本的文字符號顯示，避免遊戲無法啟動。
        """
        # __file__ 是 game.py 的實際位置，因此換工作目錄仍能找到 assets。
        project_dir = Path(__file__).resolve().parent
        icons = {}
        for name, relative_path in BUTTON_ICON_PATHS.items():
            image_path = project_dir / relative_path
            try:
                # convert_alpha 保留 PNG 的透明度；smoothscale 統一五張圖的大小。
                source = pygame.image.load(str(image_path)).convert_alpha()
                image = pygame.transform.smoothscale(
                    source, (BUTTON_ICON_SIZE, BUTTON_ICON_SIZE))

                # 復原、重做沒有可用步驟時，使用半透明圖示呈現停用狀態。
                disabled_image = image.copy()
                disabled_image.set_alpha(110)
                icons[name] = (image, disabled_image)
            except (FileNotFoundError, OSError, pygame.error):
                # 圖檔遺失不會讓遊戲當掉，原來的備援文字符號仍可操作。
                continue
        return icons

    def font(self, size, bold=False):
        """取得 Font 物件；相同字級、粗細只需建立一次，減少重複載入。"""
        key = (size, bold)
        if key not in self.font_cache:
            font_path = pygame.font.match_font(
                "microsoftjhenghei,notosanscjktc,notosanscjk,arialunicode")
            self.font_cache[key] = pygame.font.Font(font_path, size) if font_path else pygame.font.SysFont(None, size)
            self.font_cache[key].set_bold(bold)
        return self.font_cache[key]

    def text(self, content, x, y, size=24, color=TEXT, bold=False, center=False, max_width=None):
        """將 content 畫在指定座標；如有 max_width，逐步縮小直到文字放得下。"""
        # 避免文字尺寸不是整數；依字型實際寬度調整，而非中文字數。
        size = int(size)
        font = self.font(size, bold)
        if max_width is not None:
            while size > 13 and font.size(content)[0] > max_width:
                size -= 1
                font = self.font(size, bold)
        image = font.render(content, True, color)
        rect = image.get_rect(center=(x, y)) if center else image.get_rect(topleft=(x, y))
        self.screen.blit(image, rect)
        return rect

    def panel(self, rect, color=(255, 251, 247), radius=24, shadow=True):
        """繪製圓角資訊卡；shadow=True 時先在下方畫稍微偏移的陰影。"""
        if shadow:
            pygame.draw.rect(self.screen, (234, 216, 203), rect.move(0, 5),
                             border_radius=radius)
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)

    def snapshot(self):
        """複製貓和 X 的陣列，避免後續移動直接改寫歷史紀錄。"""
        return self.board.cats.copy(), self.board.marks.copy()

    def save_history(self):
        """保存玩家操作；若剛復原又下新棋，清除已不再適用的重做路線。"""
        current = self.snapshot()  # 當前 cats、marks 陣列的獨立副本。
        if self.history_index >= 0:
            previous = self.history[self.history_index]
            if np.array_equal(previous[0], current[0]) and np.array_equal(previous[1], current[1]):
                return
        # 例：A→B→C 復原到 B 後下新棋 D，必須丟棄舊的 C。
        self.history = self.history[:self.history_index+1]
        self.history.append(current)
        self.history_index = len(self.history)-1

    def restore_state(self, index):
        """將指定歷史步驟還原到棋盤，並重新計算是否過關。"""
        # 恢復時再次 copy，避免日後修改 board 陣列影響歷史快照。
        cats, marks = self.history[index]
        self.board.cats = cats.copy()
        self.board.marks = marks.copy()
        self.history_index = index
        self.won = self.puzzle.is_solved(self.board.cats)

    def clear_status(self):
        """清除提示訊息，避免復原等日常操作造成畫面雜亂。"""
        self.status_text = ""
        self.status_until = 0

    def set_status(self, content, seconds=2.8):
        """設定下方短暫訊息；seconds 是持續秒數，不影響棋盤狀態。"""
        self.status_text = content
        self.status_until = time.time()+seconds

    def undo(self):
        """有更早的快照時才復原，不會復原到第 0 步之前。"""
        if self.history_index > 0:
            self.restore_state(self.history_index-1)
            self.clear_status()

    def redo(self):
        """只有存在可用的較新快照時才重做。"""
        if self.history_index < len(self.history)-1:
            self.restore_state(self.history_index+1)
            self.clear_status()

    def restart_current_level(self):
        """清空本關的貓、X、提示與歷史，不變動 Puzzle 的關卡索引。"""
        # 注意：這裡故意「不呼叫」Puzzle.load_next_level()。
        self.board.reset()
        self.won = False
        self.hint_cell = None
        self.history = []
        self.history_index = -1
        self.save_history()
        self.clear_status()

    def next_level(self):
        """從已洗牌的關卡庫載入下一題，再把操作狀態重設為空白盤面。"""
        self.puzzle.load_next_level()
        self.restart_current_level()

    def give_hint(self):
        """從唯一解挑一個尚未放對的格子標示 3.5 秒，不代替玩家操作。"""
        # solution 的索引是「列」，值是「該列答案所在的欄」。
        candidates = [(row, col) for row, col in enumerate(self.puzzle.solution)
                      if not self.board.cats[row, col]]
        if not candidates:
            self.set_status("正確位置都已放置，請檢查其他格")
            return
        self.hint_cell = random.choice(candidates)
        self.hint_until = time.time()+3.5
        row, col = self.hint_cell
        self.set_status("提示：第 {} 列，第 {} 欄".format(row+1, col+1), 3.5)

    def check_win(self):
        """把目前貓咪矩陣交給 Puzzle 檢查；過關才更新提示。"""
        self.won = self.puzzle.is_solved(self.board.cats)
        if self.won:
            self.set_status("恭喜過關！按「下一關」繼續", 6)

    def handle_event(self, event):
        """集中處理滑鼠、鍵盤：先判斷按鈕，再判斷棋盤，避免誤點。"""
        # QUIT：按視窗關閉鍵，交由主迴圈做 pygame.quit()。
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.MOUSEMOTION:
            self.board.hover = self.board.cell_from_pos(event.pos)
            return
        # 快捷鍵與右側功能按鈕呼叫同一個方法，避免兩份邏輯不一致。
        if event.type == pygame.KEYDOWN:
            actions = {
                pygame.K_h: self.give_hint,
                pygame.K_z: self.undo,
                pygame.K_y: self.redo,
                pygame.K_r: self.restart_current_level,
                pygame.K_n: self.next_level,
            }
            action = actions.get(event.key)
            if action:
                action()
            return
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        if event.button == 1:
            actions = {
                "hint": self.give_hint,
                "undo": self.undo,
                "redo": self.redo,
                "restart": self.restart_current_level,
                "next": self.next_level,
            }
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    actions[name]()
                    return
        # 沒有點到功能按鈕時，才將滑鼠的像素座標換算成棋盤行列。
        cell = self.board.cell_from_pos(event.pos)
        if cell is None or self.won:
            return
        row, col = cell
        changed = False
        if event.button == 1:
            changed = self.board.toggle_cat(row, col)
            if not changed:
                self.set_status("這格不能放貓：請檢查行、列、顏色或相鄰位置")
        elif event.button == 3:
            changed = self.board.toggle_mark(row, col)
        if changed:
            self.save_history()
            self.check_win()

    def draw_logo(self):
        """在 Cat Puzzle 標題右邊繪製坐姿三花貓，呈現坐在旁邊的感覺。"""
        self.text("Cat", 39, 23, 49, (154, 91, 65), True)
        self.text("Puzzle", 40, 77, 46, (154, 91, 65), True)

        # 標題區可用範圍高約 156px；貓咪底部在規則卡上緣附近。
        # 不改動標題字體、左側規則卡或遊戲棋盤的位置。
        if self.logo_cat_image is not None:
            logo_rect = self.logo_cat_image.get_rect(center=(274, 79))
            self.screen.blit(self.logo_cat_image, logo_rect)
        elif self.board.cat_image is not None:
            # 坐姿圖檔意外遺失時，用棋盤貓咪頭當備援，不讓程式中斷。
            image = pygame.transform.smoothscale(self.board.cat_image, (95, 95))
            self.screen.blit(image, (222, 38))

    def draw_rule_icon(self, x, y, kind):
        """以 3×3 彩色方格搭配貓/X，示意三種基本規則。"""
        colors = [(247, 196, 166), (244, 221, 197), (240, 204, 179)]
        for r in range(3):
            for c in range(3):
                cell = pygame.Rect(x+c*22, y+r*22, 20, 20)
                pygame.draw.rect(self.screen, colors[(r+c)%3], cell, border_radius=3)
        if kind == 0:
            positions = [(1, 1)]
        elif kind == 1:
            positions = [(0, 1)]
        else:
            positions = [(1, 1)]
        for r, c in positions:
            if self.board.cat_image:
                icon = pygame.transform.smoothscale(self.board.cat_image, (19, 19))
                self.screen.blit(icon, (x+c*22, y+r*22))
        if kind == 2:
            for r, c in [(0,0),(0,1),(0,2),(1,0),(1,2),(2,0),(2,1),(2,2)]:
                self.text("×", x+c*22+10, y+r*22+10, 19, (255,255,255), True, True)

    def draw_left_panel(self):
        """左側固定展示遊戲規則和滑鼠／快捷鍵操作，避免與主棋盤重疊。"""
        self.draw_logo()
        self.panel(pygame.Rect(25, 156, 344, 385))
        pygame.draw.rect(self.screen, (255, 232, 202),
                         pygame.Rect(25, 156, 344, 54),
                         border_top_left_radius=24, border_top_right_radius=24)
        self.text("◎", 45, 153, 48, (154, 91, 65))
        self.text("遊戲規則", 79, 169, 26, bold=True)
        # a 為粗體規則標題，b 為較小的補充說明。
        rules = [
            ("每個顏色區域", "只能放 1 隻貓咪"),
            ("每一行、每一列", "只能放 1 隻貓咪"),
            ("貓咪周圍 8 格", "不能有其他貓咪"),
        ]
        for i, (a, b) in enumerate(rules):
            y = 229+i*102
            self.draw_rule_icon(45, y+5, i)
            self.text(a, 130, y+4, 21, bold=True, max_width=215)
            self.text(b, 130, y+37, 18, MUTED, max_width=215)
            if i < 2:
                pygame.draw.line(self.screen, (244, 229, 218),
                                 (45, y+93), (348, y+93), 1)

        self.panel(pygame.Rect(25, 560, 344, 210))
        pygame.draw.rect(self.screen, (255, 232, 202),
                         pygame.Rect(25, 560, 344, 49),
                         border_top_left_radius=24, border_top_right_radius=24)
        self.text("操作方式", 48, 573, 24, bold=True)
        for i, (label, detail) in enumerate([
            ("滑鼠左鍵", "放置 / 移除貓咪"),
            ("滑鼠右鍵", "標記 / 取消 X"),
            ("快捷鍵", "H 提示 · Z 復原 · Y 重做"),
            ("快捷鍵", "R 重開 · N 下一關"),
        ]):
            y = 625+i*34
            self.text(label, 48, y, 18, (149, 89, 73), True)
            self.text(detail, 136, y, 17, TEXT, max_width=213)

    def draw_header(self):
        """上方資訊列展示進度、類型、已放貓數及難度，不計分。"""
        self.panel(pygame.Rect(395, 26, 836, 114), (255, 253, 250), 45)
        self.text("LEVEL", 444, 43, 19, MUTED, True)
        self.text(str(self.puzzle.level), 444, 75, 40, TEXT, True)
        pygame.draw.line(self.screen, (237, 216, 203), (580, 50), (580, 117), 2)
        self.text("關卡類型", 608, 43, 19, MUTED)
        self.text(self.puzzle.style_name, 608, 77, 28, TEXT, True, max_width=190)
        pygame.draw.line(self.screen, (237, 216, 203), (835, 50), (835, 117), 2)

        # 右上角使用與棋盤相同的貓咪頭圖，圖示和計數數字共用垂直中心。
        counter_center_y = 83
        count_text = "{}/{}".format(int(self.board.cats.sum()), BOARD_SIZE)
        icon_center_x = 898
        text_center_x = 975
        if self.counter_cat_image is not None:
            counter_rect = self.counter_cat_image.get_rect(center=(icon_center_x, counter_center_y))
            self.screen.blit(self.counter_cat_image, counter_rect)
        elif self.board.cat_image is not None:
            cat = pygame.transform.smoothscale(self.board.cat_image, (52, 52))
            counter_rect = cat.get_rect(center=(icon_center_x, counter_center_y))
            self.screen.blit(cat, counter_rect)

        self.text(count_text, text_center_x, counter_center_y, 33, (46, 151, 77), True, True)
        self.text(self.puzzle.difficulty, 1110, 70, 24, MUTED, True, max_width=95
        )

    def draw_buttons(self):
        """繪製右側五個按鈕：上半部 PNG 圖示，下半部中文功能名稱。"""
        # 每筆資料：按鈕代號、中文名稱、無圖時的備援符號、底色、字色。
        # PNG 載入時只替換上方的符號，不改動按鈕位置與點擊範圍。
        designs = [
            ("hint", "提示", "?", (255, 225, 154), (150, 92, 35)),
            ("undo", "復原", "↶", (208, 233, 247), (63, 107, 136)),
            ("redo", "重做", "↷", (208, 233, 247), (63, 107, 136)),
            ("restart", "重新開始", "⟳", (255, 213, 218), (175, 75, 76)),
            ("next", "下一關", "▶", (207, 237, 187), (59, 133, 61)),
        ]
        mouse = pygame.mouse.get_pos()
        for name, label, symbol, color, ink in designs:
            rect = self.buttons[name]
            enabled = not (
                (name == "undo" and self.history_index == 0) or
                (name == "redo" and self.history_index == len(self.history)-1)
            )
            fill = color if enabled else (232, 231, 230)
            if rect.collidepoint(mouse) and enabled:
                fill = tuple(min(255, channel+9) for channel in fill)
            self.panel(rect, fill, 22)

            # 圖示置於按鈕上半部；自動依 center 對齊，不需為每張 PNG 寫座標。
            icon_pair = self.button_icons.get(name)
            if icon_pair is not None:
                normal_icon, disabled_icon = icon_pair
                icon = normal_icon if enabled else disabled_icon
                icon_rect = icon.get_rect(center=(rect.centerx, rect.y + 34))
                self.screen.blit(icon, icon_rect)
            else:
                # 圖片未載入時保持原版文字符號，遊戲仍可正常使用。
                self.text(symbol, rect.centerx, rect.y+29, 42,
                          ink if enabled else MUTED, True, True)

            # 中文名稱固定在下半部；圖片和標籤間保留間距。
            self.text(label, rect.centerx, rect.y+72, 22,
                      ink if enabled else MUTED, True, True)

    def draw(self):
        """每影格依序繪製背景、規則區、標題、棋盤、按鈕與必要訊息。"""
        self.screen.fill(BG)
        self.draw_left_panel()
        self.draw_header()
        if self.hint_cell and time.time() >= self.hint_until:
            self.hint_cell = None
        self.board.draw(self.screen, self.hint_cell)
        self.draw_buttons()

        # 棋盤下方固定資訊，訊息出現時覆蓋這一行，不占額外框架。
        if self.status_text and time.time() < self.status_until:
            self.text(self.status_text, 660, 753, 21, (164, 76, 61),
                      True, True, max_width=545)
        else:
            self.text("滑鼠左鍵放貓 · 右鍵標記 X", 660, 753, 19,
                      MUTED, center=True)
        pygame.display.flip()

    def run(self):
        """持續接收事件、更新畫面並限制 FPS；視窗關閉時退出。"""
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
