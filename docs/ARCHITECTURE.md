# Cat Puzzle 程式執行架構

```text
main.py
  └─ Game（game.py）
       ├─ Puzzle（puzzle.py）
       │    ├─ levels/levels_150.json
       │    └─ level_diversity.py
       ├─ Board（board.py）
       │    └─ NumPy：cats、marks
       ├─ config.py / assets/*.png
       └─ Pygame：主迴圈與事件

tools/generate_levels.py
  └─ 離線生成並驗證關卡 → levels/levels_150.json

tests/
  └─ 檢查規則、關卡資料、事件和操作歷史
```

## 核心責任

- `Game`：建立遊戲、處理輸入事件、關卡切換與介面顯示。
- `Board`：保存放貓與標記 X 的 NumPy 矩陣，轉換滑鼠座標並繪製格子。
- `Puzzle`：載入 JSON 關卡、洗牌、檢查放置規則與判斷過關。
- `tools/generate_levels.py`：離線生成關卡資料，不隨主遊戲每次啟動執行。
- `tests/`：執行 unittest；Mock 畫面測試與真正 Pygame 視窗測試須區分。

## 重要資料格式

```json
{
  "name": "關卡名稱",
  "region": [
    [0, 0, 1, 1, 2, 2],
    [0, 3, 1, 1, 2, 2],
    [0, 3, 4, 4, 2, 5],
    [3, 3, 4, 5, 5, 5],
    [3, 4, 4, 5, 0, 0],
    [3, 4, 1, 1, 0, 0]
  ],
  "solution": [1, 3, 5, 0, 2, 4]
}
```

此處僅示意資料結構，不保證此筆示例具有唯一解，也不可直接加入正式題庫。正式資料請以經過測試的 `levels/levels_150.json` 為準。

## 程式事件流程

1. `main.py` 建立 `Game` 並執行主迴圈。
2. Pygame 回報左鍵／右鍵或快捷鍵事件。
3. `Game` 先判斷按鈕，再定位棋盤格。
4. `Board` 依 `Puzzle` 規則更新貓咪與 X 狀態。
5. `Game` 建立操作快照供復原／重做使用。
6. `Puzzle` 檢查通關；畫面依狀態重繪。
