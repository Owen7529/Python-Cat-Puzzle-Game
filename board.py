"""棋盤模組：保存玩家操作狀態，處理滑鼠座標與棋盤繪製。"""

from pathlib import Path
import numpy as np
import pygame

from config import (
    BOARD_SIZE, CELL_SIZE, BOARD_X, BOARD_Y, REGION_COLORS,
    X_COLOR, ERROR, HINT_COLOR, CAT_IMAGE_PATH
)


class Board:
    """保存玩家放置的貓與 X 記號，並負責棋盤畫面。"""

    def __init__(self, puzzle):
        """建立 6×6 貓/X 狀態矩陣；puzzle 提供色區與合法性檢查。"""
        # puzzle：目前遊戲使用的 Puzzle 物件。
        self.puzzle = puzzle
        # cats：1 表示該格有貓，0 表示沒有。
        self.cats = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
        # marks：1 表示該格有 X 記號，0 表示沒有。
        self.marks = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
        # hover：滑鼠目前指向的格子；沒有則為 None。
        self.hover = None
        # cat_image：從 assets/cat.png 載入並縮放後的圖片。
        self.cat_image = self._load_cat_image()

    def _load_cat_image(self):
        """載入貓咪 PNG；若檔案不存在則回傳 None，避免遊戲直接中止。"""
        project_dir = Path(__file__).resolve().parent
        image_path = project_dir / CAT_IMAGE_PATH
        try:
            image = pygame.image.load(str(image_path)).convert_alpha()
            size = int(CELL_SIZE * 0.72)
            return pygame.transform.smoothscale(image, (size, size))
        except (pygame.error, FileNotFoundError):
            return None

    def reset(self):
        """清除目前關卡所有貓與 X，回到此局剛開始的狀態。"""
        self.cats.fill(0)
        self.marks.fill(0)
        self.hover = None

    def cell_from_pos(self, pos):
        """把滑鼠畫面座標轉換成棋盤的列、欄；棋盤外回傳 None。"""
        # pos 是視窗座標；減去棋盤原點後再除以格子寬度，得到 0 起算的索引。
        x, y = pos
        col = (x - BOARD_X) // CELL_SIZE
        row = (y - BOARD_Y) // CELL_SIZE
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return int(row), int(col)
        return None

    def toggle_cat(self, row, col):
        """切換指定格的貓；放貓時會自動清除同格 X。"""
        # 若玩家按到已放置的貓，代表移除，不需要再次檢查放置規則。
        if self.cats[row, col]:
            self.cats[row, col] = 0
            return True

        # 放入新貓之前，交由 Puzzle 統一檢查列、欄、色區與相鄰限制。
        if not self.puzzle.is_valid_placement(self.cats, row, col):
            return False

        # 貓和 X 不能共存，同一格放貓後移除原本的 X 筆記。
        self.cats[row, col] = 1
        self.marks[row, col] = 0
        return True

    def toggle_mark(self, row, col):
        """以滑鼠右鍵切換 X；已有貓的格子不可加 X。"""
        if self.cats[row, col]:
            return False
        # Python 三元運算式：已有 X 則清零，沒有 X 就標成 1。
        self.marks[row, col] = 0 if self.marks[row, col] else 1
        return True

    def has_conflict(self, row, col):
        """檢查指定貓是否與其他貓產生行、列、區域或相鄰衝突。"""
        if not self.cats[row, col]:
            return False

        if int(np.sum(self.cats[row, :])) > 1 or int(np.sum(self.cats[:, col])) > 1:
            return True

        # NumPy 的布林遮罩找出「與此格相同顏色」的所有棋盤格。
        region_id = self.puzzle.region_map[row, col]
        if int(np.sum(self.cats[self.puzzle.region_map == region_id])) > 1:
            return True

        # dr、dc 分別表示與目前格子的列差及欄差；(0,0) 是自己要跳過。
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.cats[nr, nc]:
                    return True
        return False

    def draw_cat(self, surface, row, col):
        """在指定格繪製貓咪圖片；圖片讀取失敗時使用簡單備援圖案。"""
        # cx、cy 是棋盤格的像素中心，圖片才能精確居中。
        cx = BOARD_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = BOARD_Y + row * CELL_SIZE + CELL_SIZE // 2

        if self.cat_image is not None:
            rect = self.cat_image.get_rect(center=(cx, cy))
            surface.blit(self.cat_image, rect)
        else:
            pygame.draw.circle(surface, (224, 167, 116), (cx, cy), CELL_SIZE // 4)

    def draw_x(self, surface, row, col):
        """以概念圖的大型白色圓角 X 標記排除格。"""
        cx = BOARD_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = BOARD_Y + row * CELL_SIZE + CELL_SIZE // 2
        # 半徑決定白色 X 的尺寸；先畫深色邊再畫白色，提升辨識度。
        radius = CELL_SIZE // 4
        pygame.draw.line(surface, (139, 104, 96),
                         (cx-radius+1, cy-radius+2),
                         (cx+radius+1, cy+radius+2), 9)
        pygame.draw.line(surface, (139, 104, 96),
                         (cx+radius+1, cy-radius+2),
                         (cx-radius+1, cy+radius+2), 9)
        pygame.draw.line(surface, X_COLOR,
                         (cx-radius, cy-radius),
                         (cx+radius, cy+radius), 7)
        pygame.draw.line(surface, X_COLOR,
                         (cx+radius, cy-radius),
                         (cx-radius, cy+radius), 7)

    def draw(self, surface, hint_cell=None):
        """圓角彩色方塊與白色留縫，保留區域辨識及提示功能。"""
        # 棋盤白色大底框。
        panel = pygame.Rect(BOARD_X-16, BOARD_Y-16,
                            BOARD_SIZE*CELL_SIZE+32,
                            BOARD_SIZE*CELL_SIZE+32)
        pygame.draw.rect(surface, (229, 213, 203),
                         panel.move(0, 5), border_radius=24)
        pygame.draw.rect(surface, (255, 255, 255), panel, border_radius=24)

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = BOARD_X + col*CELL_SIZE
                y = BOARD_Y + row*CELL_SIZE
                # rid 是 0~5 的顏色區域代號，直接對應 config.py 中的色表。
                rid = int(self.puzzle.region_map[row, col])
                rect = pygame.Rect(x+4, y+4, CELL_SIZE-8, CELL_SIZE-8)
                color = REGION_COLORS[rid]
                pygame.draw.rect(surface, color, rect, border_radius=9)

                # 滑鼠滑過的格子加一層半透明白色，不直接修改色塊底色。
                if self.hover == (row, col):
                    overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                    overlay.fill((255, 255, 255, 55))
                    surface.blit(overlay, rect.topleft)

                if self.marks[row, col]:
                    self.draw_x(surface, row, col)
                if self.cats[row, col]:
                    self.draw_cat(surface, row, col)

                # 提示只加上高亮外框，不修改玩家實際放置的貓/X。
                if hint_cell == (row, col):
                    pygame.draw.rect(surface, (255, 245, 151),
                                     rect.inflate(-3, -3), 5, border_radius=10)
