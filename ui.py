"""UI 小工具：集中處理文字、按鈕與資訊面板的繪製。"""

import pygame
from config import TEXT, MUTED, ACCENT, ACCENT_DARK, WHITE, PANEL


def draw_text(surface, text, pos, size=24, color=TEXT, center=False, bold=False):
    """在畫面上繪製文字，並回傳文字的 Rect 供需要時定位。"""
    # surface 為目標畫布、pos 是文字放置座標、size 是字級。
    # font：優先使用系統中的中文字型；找不到時由 Pygame 使用預設字型。
    font_name = pygame.font.match_font("microsoftjhenghei,notosanscjktc,arialunicode")
    font = pygame.font.Font(font_name, size) if font_name else pygame.font.Font(None, size)
    font.set_bold(bold)
    image = font.render(str(text), True, color)
    rect = image.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(image, rect)
    return rect


def draw_button(surface, rect, text, mouse_pos, enabled=True):
    """繪製圓角按鈕；enabled=False 時使用停用外觀。"""
    # hovered：滑鼠是否位於此按鈕範圍。
    # rect：整個按鈕可點擊範圍；mouse_pos：當前滑鼠位置。
    hovered = rect.collidepoint(mouse_pos)
    if not enabled:
        color = (190, 190, 190)
    else:
        color = ACCENT_DARK if hovered else ACCENT
    pygame.draw.rect(surface, color, rect, border_radius=12)
    draw_text(surface, text, rect.center, 20, WHITE, center=True, bold=True)


def draw_panel(surface, rect):
    """繪製柔和背景的資訊面板。"""
    # 背景、細邊框都只負責裝飾，不建立按鈕事件。
    pygame.draw.rect(surface, PANEL, rect, border_radius=14)
    pygame.draw.rect(surface, (228, 224, 217), rect, 1, border_radius=14)


def get_font(size, bold=False):
    """取得中文字型，供提示文字精確量測與排版。"""
    font_name = pygame.font.match_font("microsoftjhenghei,notosanscjktc,arialunicode")
    font = pygame.font.Font(font_name, size) if font_name else pygame.font.Font(None, size)
    font.set_bold(bold)
    return font
