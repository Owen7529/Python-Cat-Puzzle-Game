"""按鈕 PNG 的檔案格式檢查。

此模組只使用 Python 標準函式庫，不依賴 Pillow 或真正的 Pygame。
目的是避免有人換圖時不小心刪檔、換成非 PNG，或移除透明色版。
"""

from pathlib import Path
import struct
import sys
import unittest

# 無論從專案根目錄或其他工作目錄執行，都能找到程式與 assets。
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import BUTTON_ICON_PATHS, BUTTON_ICON_SIZE, LOGO_CAT_IMAGE_PATH, COUNTER_CAT_IMAGE_PATH


class ButtonAssetTests(unittest.TestCase):
    """驗證五個圖示檔案、透明度格式與繪圖尺寸設定。"""

    def test_all_five_icons_are_rgba_png(self):
        """每個圖示必須存在且為真正包含 Alpha 通道的 RGBA PNG。"""
        self.assertEqual(
            set(BUTTON_ICON_PATHS), {"hint", "undo", "redo", "restart", "next"}
        )
        for button_name, relative_path in BUTTON_ICON_PATHS.items():
            with self.subTest(button=button_name):
                image_path = ROOT / relative_path  # 每個圖示實際所在的檔案路徑。
                self.assertTrue(image_path.is_file(), str(image_path))
                with image_path.open("rb") as stream:
                    # PNG 固定以這 8 bytes 開頭，接下來必須是 IHDR 檔頭區塊。
                    header = stream.read(33)
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(header[12:16], b"IHDR")
                width, height = struct.unpack(">II", header[16:24])
                self.assertGreaterEqual(width, BUTTON_ICON_SIZE)
                self.assertGreaterEqual(height, BUTTON_ICON_SIZE)
                # PNG IHDR 的色彩類型 6 = RGBA（含 Alpha 透明通道）。
                self.assertEqual(header[25], 6)

    def test_icon_files_use_unique_paths(self):
        """五個操作應對應五張不同的圖片，不要誤用同一資源。"""
        self.assertEqual(len(BUTTON_ICON_PATHS), len(set(BUTTON_ICON_PATHS.values())))

    def test_logo_and_counter_images_exist_as_rgba_png(self):
        """標題裝飾貓圖與右上角計數圖示都應存在且為 RGBA PNG。"""
        for relative_path in (LOGO_CAT_IMAGE_PATH, COUNTER_CAT_IMAGE_PATH):
            with self.subTest(image=relative_path):
                image_path = ROOT / relative_path
                self.assertTrue(image_path.is_file(), str(image_path))
                with image_path.open("rb") as stream:
                    header = stream.read(33)
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(header[12:16], b"IHDR")
                width, height = struct.unpack(">II", header[16:24])
                self.assertGreaterEqual(width, 96)
                self.assertGreaterEqual(height, 96)
                self.assertEqual(header[25], 6)

    def test_counter_uses_the_same_head_as_board(self):
        """右上角貓咪數量與棋盤必須使用同一張三花貓頭圖。"""
        from config import CAT_IMAGE_PATH
        self.assertEqual(COUNTER_CAT_IMAGE_PATH, CAT_IMAGE_PATH)
        self.assertNotEqual(LOGO_CAT_IMAGE_PATH, CAT_IMAGE_PATH)


if __name__ == "__main__":
    unittest.main()
