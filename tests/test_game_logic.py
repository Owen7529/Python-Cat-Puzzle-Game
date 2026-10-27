"""使用純 Python 的 Pygame 替身測試操作流程（不是實際畫面測試）。"""

from pathlib import Path
from unittest.mock import patch
import importlib
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeRect:
    """代替 Pygame Rect，提供按鈕點擊與位移需要的基本功能。"""

    def __init__(self, x, y, w, h):
        """設定矩形的左上角座標及寬高。"""
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def centerx(self):
        """回傳矩形水平中心點。"""
        return self.x + self.w // 2

    @property
    def centery(self):
        """回傳矩形垂直中心點。"""
        return self.y + self.h // 2

    def collidepoint(self, pos):
        """判斷指定滑鼠座標有無落在矩形範圍內。"""
        return self.x <= pos[0] < self.x+self.w and self.y <= pos[1] < self.y+self.h

    def move(self, x, y):
        """回傳偏移位置的新矩形。"""
        return FakeRect(self.x+x, self.y+y, self.w, self.h)

    def inflate(self, w, h):
        """回傳放大或縮小後的新矩形。"""
        return FakeRect(self.x-w//2, self.y-h//2, self.w+w, self.h+h)

    @property
    def topleft(self):
        """取得矩形左上角座標。"""
        return (self.x, self.y)


class FakeImage:
    """代替 PNG 圖片物件與畫面 Surface。"""

    def __init__(self, width=100, height=100):
        """建立不真正儲存像素的假 Surface。"""
        self.w, self.h = width, height  # 假畫布的寬與高，不真正產生像素。

    def convert_alpha(self):
        """模擬 Pygame 保留透明度的 Surface 轉換。"""
        return self

    def get_rect(self, center=None, **kwargs):
        """依圖片尺寸建立與真實 Pygame 相似的 Rect。"""
        r = FakeRect(0, 0, self.w, self.h)
        if center:
            r.x = center[0]-self.w//2
            r.y = center[1]-self.h//2
        return r

    def copy(self):
        """模擬 Surface.copy()，供半透明停用按鈕載入時使用。"""
        return FakeImage(self.w, self.h)

    def set_alpha(self, alpha):
        """模擬整張圖片的透明度設定；Mock 不真的修改像素。"""
        self.alpha = alpha

    def blit(self, *args, **kwargs):
        """模擬畫圖，不真正輸出像素。"""
        pass

    def fill(self, *args, **kwargs):
        """模擬填滿畫布，不真正輸出像素。"""
        pass


class FakeFont:
    """回報文字的近似大小，讓 draw() 的字體路徑能執行。"""

    def __init__(self, *args):
        """取得測試用字級，按近似字寬模擬排版。"""
        self.size_px = args[-1]

    def set_bold(self, *args):
        """模擬設定粗體，替身不改字型外觀。"""
        pass

    def size(self, text):
        """回傳近似文字寬、高，供 max_width 模擬使用。"""
        return len(text)*self.size_px, self.size_px

    def render(self, text, antialias, color):
        """把文字轉為假圖片，供 Game.text() 進行 blit。"""
        return FakeImage(max(1, len(text)*self.size_px), self.size_px)


def create_fake_pygame():
    """建構能跑邏輯與呼叫繪製流程，但不產生真正視窗的替身。"""
    pygame = types.ModuleType('pygame')
    pygame.error = type('FakePygameError', (Exception,), {})
    pygame.Rect = FakeRect
    pygame.SRCALPHA = 1
    pygame.QUIT, pygame.MOUSEMOTION, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN = range(1, 5)
    pygame.K_h, pygame.K_z, pygame.K_y, pygame.K_r, pygame.K_n = range(10, 15)
    pygame.init = lambda: None
    pygame.quit = lambda: None
    pygame.display = types.SimpleNamespace(set_mode=lambda size: FakeImage(*size),
                                          set_caption=lambda x: None,
                                          flip=lambda: None)
    pygame.time = types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda n: None))
    pygame.image = types.SimpleNamespace(load=lambda path: FakeImage())
    pygame.transform = types.SimpleNamespace(smoothscale=lambda im, size: FakeImage(*size))
    pygame.font = types.SimpleNamespace(match_font=lambda x: None, SysFont=lambda x, y: FakeFont(x, y),
                                        Font=lambda x, y: FakeFont(x, y))
    pygame.draw = types.SimpleNamespace(rect=lambda *a, **kw: None,
                                        line=lambda *a, **kw: None,
                                        circle=lambda *a, **kw: None)
    pygame.Surface = lambda size, flags=0: FakeImage(*size)
    pygame.mouse = types.SimpleNamespace(get_pos=lambda: (0, 0))
    pygame.event = types.SimpleNamespace(get=lambda: [])
    return pygame


class GameBehaviorTests(unittest.TestCase):
    """使用 Pygame Mock 驗證鍵鼠操作、歷史與五張按鈕圖示載入。"""

    def setUp(self):
        """每個測試開始前注入假的 Pygame，建立全新的遊戲狀態。"""
        self.mock_module = patch.dict(sys.modules, {'pygame': create_fake_pygame()})
        self.mock_module.start()
        # 重新載入以確保參照替身，而不是系統安裝的 pygame。
        for key in ('board', 'ui', 'game'):
            sys.modules.pop(key, None)
        self.game_module = importlib.import_module('game')
        self.game = self.game_module.Game()
        self.pg = sys.modules['pygame']

    def tearDown(self):
        """恢復真正的模組環境，避免測試彼此汙染。"""
        self.mock_module.stop()
        for key in ('board', 'ui', 'game'):
            sys.modules.pop(key, None)

    def event(self, event_type, **attrs):
        """建構具有 type、pos、button 等屬性的滑鼠/鍵盤假事件。"""
        return types.SimpleNamespace(type=event_type, **attrs)

    def test_undo_redo_and_restart_level(self):
        """玩家放貓後可復原重做；重新開始清盤但不能換題。"""
        g = self.game
        original = g.puzzle.current_template_index
        r, c = 0, g.puzzle.solution[0]
        g.handle_event(self.event(self.pg.MOUSEBUTTONDOWN,
                                  button=1, pos=(411+c*88+40, 188+r*88+40)))
        self.assertEqual(int(g.board.cats.sum()), 1)
        g.undo()
        self.assertEqual(int(g.board.cats.sum()), 0)
        g.redo()
        self.assertEqual(int(g.board.cats.sum()), 1)
        g.restart_current_level()
        self.assertEqual(g.puzzle.current_template_index, original)
        self.assertEqual(int(g.board.cats.sum()), 0)
        self.assertEqual(g.history_index, 0)

    def test_right_click_x_hint_next(self):
        """右鍵 X、提示答案、下一關後清盤均符合原本需求。"""
        g = self.game
        original = g.puzzle.current_template_index
        g.handle_event(self.event(self.pg.MOUSEBUTTONDOWN,
                                  button=3, pos=(420, 200)))
        self.assertEqual(int(g.board.marks[0, 0]), 1)
        g.give_hint()
        self.assertIsNotNone(g.hint_cell)
        r, c = g.hint_cell
        self.assertEqual(g.puzzle.solution[r], c)
        self.assertNotEqual(g.status_text, '')
        g.next_level()
        self.assertNotEqual(g.puzzle.current_template_index, original)
        self.assertEqual(int(g.board.marks.sum()), 0)
        self.assertIsNone(g.hint_cell)
        self.assertEqual(g.status_text, '')

    def test_button_icons_loaded_and_drawn(self):
        """五個 PNG 都有對應 UI 鍵，正常/停用圖片皆可渲染。"""
        self.assertEqual(set(self.game.button_icons),
                         {"hint", "undo", "redo", "restart", "next"})
        self.assertIsNotNone(self.game.logo_cat_image)
        self.assertIsNotNone(self.game.counter_cat_image)
        # 初始狀態不能復原／重做，仍應能正常繪製右側按鈕。
        self.game.draw_buttons()
        for normal, disabled in self.game.button_icons.values():
            self.assertEqual((normal.w, normal.h), (48, 48))
            self.assertEqual((disabled.w, disabled.h), (48, 48))
            self.assertEqual(disabled.alpha, 110)

    def test_icon_missing_uses_symbol_fallback(self):
        """若圖檔不見，按鈕應改顯示符號而非讓遊戲無法啟動。"""
        self.game.button_icons = {}
        self.game.draw_buttons()

    def test_render_call_no_exception(self):
        """僅測 UI 繪製呼叫流程；無法證實真正視窗的像素表現。"""
        self.game.draw()
        self.game.give_hint()
        self.game.draw()


if __name__ == '__main__':
    unittest.main()
