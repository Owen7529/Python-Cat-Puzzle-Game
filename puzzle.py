"""關卡與規則模組：保存關卡資料、亂數牌組、解答與規則檢查。"""

import random
import numpy as np
from config import BOARD_SIZE

# 關卡配置獨立保存在 JSON，避免 150 關資料塞進 Python 程式碼。
# 生成方式參考 tools/generate_levels.py；遊玩時不需要重新產生。
from pathlib import Path
import json
from level_diversity import structural_signatures, structural_distance

LEVELS_FILE = Path(__file__).resolve().parent / "levels" / "levels_150.json"


def load_level_templates():
    """從 levels_150.json 讀取關卡列表。

    格式：每筆包含 region（6×6 二維列表）、solution（每列的答案欄位），
    以及 name、difficulty 等文字欄位。回傳 150 筆字典的 Python list。
    """
    with LEVELS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or len(data) != 150:
        raise ValueError("關卡檔案格式錯誤，應包含 150 關。")
    return data


# LEVEL_TEMPLATES：150 張有效關卡；包含原先 30 張與新增的 120 張。
LEVEL_TEMPLATES = load_level_templates()

# 關卡結構指紋：用於降低「相似關卡連著出現」的機率。
# 只在遊戲啟動時建立一次，避免每一影格重複運算。
LEVEL_SIGNATURES = [structural_signatures(item['region']) for item in LEVEL_TEMPLATES]
LEVEL_SOLUTIONS = [tuple(item['solution']) for item in LEVEL_TEMPLATES]


class Puzzle:
    """管理目前關卡、關卡順序、解答，以及放置規則。"""

    def __init__(self):
        """建立關卡牌組、初始化目前題目，並讀入第一張題。"""
        # level：玩家目前看到的關卡編號，從 1 開始累加。
        self.level = 0
        # region_map：每一格所屬區域的 NumPy 二維陣列。
        self.region_map = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
        # solution：唯一解；索引是列，值是該列正確的欄。
        self.solution = tuple()
        # style_name：目前關卡的版型名稱。
        self.style_name = ""
        # difficulty：依進度顯示的難度文字。
        self.difficulty = "入門"
        # deck：150 個關卡索引洗牌後形成的牌組。
        self.deck = []
        # deck_index：目前讀到牌組中的哪一個位置。
        self.deck_index = 0
        # current_template_index：目前實際使用的關卡模板索引。
        self.current_template_index = -1
        # 最近玩過的關卡；用於不同輪牌組交界的多樣化排序。
        self.recent_loaded = []
        self.new_deck()
        self.load_next_level()

    def new_deck(self):
        """建立完整亂數牌組，優先讓相鄰關卡的區域形狀和答案都不同。

        150 關仍然全部出現且每輪僅出現一次；只是洗牌後額外調整順序。
        這屬於「體感差異的排序輔助」，不代表電腦已能模擬玩家推理。
        """
        # remaining 保存尚未出現過的模板索引；每輪一定使用完全部題目。
        remaining = list(range(len(LEVEL_TEMPLATES)))
        random.shuffle(remaining)
        new_order = []
        # 跨越前一輪時，也要將上一輪最後幾關納入判斷。
        recent = list(self.recent_loaded[-4:])

        while remaining:
            # 每次隨機抽出候選題，保留關卡順序的隨機性。
            # 先隨機挑最多 24 題，再對候選題做相似度比較，避免全面搜尋過慢。
            candidates = random.sample(remaining, min(24, len(remaining)))
            # 盡量避免最近三關的答案配置重複；若抽到的全都重複，
            # 就從完整剩餘牌組再尋找。
            candidates = [index for index in candidates if
                          LEVEL_SOLUTIONS[index] not in
                          [LEVEL_SOLUTIONS[x] for x in recent[-3:]]] or [
                              index for index in remaining if
                              LEVEL_SOLUTIONS[index] not in
                              [LEVEL_SOLUTIONS[x] for x in recent[-3:]]]
            if not candidates:
                candidates = remaining

            def score(index):
                """同時考慮區域距離、生成類型與難度，並加入亂數打散。"""
                if not recent:
                    return random.random()
                # 取新題與「最近四題」最相似的一組距離（距離愈大愈不相似）。
                shape = min(structural_distance(
                    LEVEL_SIGNATURES[index], LEVEL_SIGNATURES[previous])
                    for previous in recent[-4:])
                last = recent[-1]
                category_bonus = 11 if (LEVEL_TEMPLATES[index]['family'] !=
                                        LEVEL_TEMPLATES[last]['family']) else 0
                difficulty_bonus = 6 if (LEVEL_TEMPLATES[index]['difficulty'] !=
                                         LEVEL_TEMPLATES[last]['difficulty']) else 0
                return shape + category_bonus + difficulty_bonus + random.random() * 10

            # 分數最高的候選題優先：距離、生成類型、難度與少量亂數。
            chosen = max(candidates, key=score)
            new_order.append(chosen)
            remaining.remove(chosen)
            recent.append(chosen)
            recent = recent[-4:]

        self.deck = new_order
        self.deck_index = 0

    def load_next_level(self):
        """載入亂數牌組中的下一關；整輪用完後再重新洗牌。"""
        if self.deck_index >= len(self.deck):
            self.new_deck()

        # 模板索引與畫面上顯示的關卡編號不同：索引是抽到的題目 ID。
        template_index = self.deck[self.deck_index]
        self.deck_index += 1
        self.current_template_index = template_index
        self.recent_loaded.append(template_index)
        self.recent_loaded = self.recent_loaded[-4:]

        # region 轉成 NumPy 陣列，讓 Board/Puzzle 可以直接使用布林運算。
        data = LEVEL_TEMPLATES[template_index]
        self.region_map = np.array(data["region"], dtype=np.int8)
        self.solution = tuple(data["solution"])
        self.style_name = data["name"]
        self.level += 1

        # 因關卡會隨機出現，難度應綁定「關卡本身」，不依遊玩順序判斷。
        # 此分類取決於離線分析的搜尋節點數，屬相對難度估計。
        self.difficulty = data["difficulty"]

    def is_valid_placement(self, cats, row, col):
        """檢查在指定格放貓是否符合行、列、區域與八方向不相鄰規則。"""
        # cats 是 0/1 二維陣列，row、col 都是 0 起算的格子索引。
        # 同一橫列不可有第二隻貓。
        if np.any(cats[row, :] == 1):
            return False
        # 同一直欄不可有第二隻貓。
        if np.any(cats[:, col] == 1):
            return False

        # 同一顏色區域不可有第二隻貓。
        region_id = self.region_map[row, col]
        if np.any((self.region_map == region_id) & (cats == 1)):
            return False

        # 周圍八格不可已有貓。
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and cats[nr, nc] == 1:
                    return False
        return True

    def is_solved(self, cats):
        """確認棋盤是否完整符合所有規則。"""
        if int(np.sum(cats)) != BOARD_SIZE:
            return False

        # 每列與每欄都必須剛好一隻。
        if not all(int(np.sum(cats[r, :])) == 1 for r in range(BOARD_SIZE)):
            return False
        if not all(int(np.sum(cats[:, c])) == 1 for c in range(BOARD_SIZE)):
            return False

        # 等全部放滿之後，再檢查每個顏色區域是否剛好放一隻。
        # 六個區域都必須剛好一隻。
        for region_id in range(BOARD_SIZE):
            if int(np.sum(cats[self.region_map == region_id])) != 1:
                return False

        # 任兩個相鄰列的貓不可相鄰或斜鄰。
        positions = np.argwhere(cats == 1)
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                r1, c1 = positions[i]
                r2, c2 = positions[j]
                if max(abs(int(r1-r2)), abs(int(c1-c2))) <= 1:
                    return False
        return True

    def find_all_solutions(self, limit=None):
        """枚舉目前關卡的合法解答；主要供測試與驗證唯一解使用。"""
        # 每列、每欄各一隻等於六欄的排列：6! = 720 種待檢查配置。
        from itertools import permutations
        found = []
        for cols in permutations(range(BOARD_SIZE)):
            if any(abs(cols[r] - cols[r + 1]) <= 1 for r in range(BOARD_SIZE - 1)):
                continue
            regions = [int(self.region_map[r, cols[r]]) for r in range(BOARD_SIZE)]
            if len(set(regions)) == BOARD_SIZE:
                found.append(tuple(cols))
                if limit is not None and len(found) >= limit:
                    break
        return found
