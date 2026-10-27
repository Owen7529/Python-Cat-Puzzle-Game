"""關卡資料與洗牌的自動測試；不需安裝 Pygame。"""

from collections import Counter
from itertools import permutations
import json
import random
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from puzzle import Puzzle, LEVEL_TEMPLATES
from tools.generate_levels import canonical, connected, unique_solution, search_nodes, estimated_difficulty
from level_diversity import structural_signatures, structural_distance, shape_profile, outline_group, size_group


class LevelDataTests(unittest.TestCase):
    """逐關檢查答案、區域、非重複性與難度欄位。"""

    def test_count_original_and_new(self):
        """原先三十關沒有被取代；總數精確為一百五十。"""
        self.assertEqual(len(LEVEL_TEMPLATES), 150)
        originals = json.loads((ROOT / 'levels' / 'base_30.json').read_text(encoding='utf-8'))
        self.assertEqual(len(originals), 30)
        for a, b in zip(LEVEL_TEMPLATES[:30], originals):
            self.assertEqual(a['name'], b['name'])
            self.assertEqual(a['region'], b['region'])
            self.assertEqual(tuple(a['solution']), tuple(b['solution']))

    def test_unique_connected_and_distinct(self):
        """每關都有六個連通區域、唯一解，也沒有旋轉鏡射的假重複。"""
        seen = set()
        for index, item in enumerate(LEVEL_TEMPLATES, 1):
            with self.subTest(level=index):
                grid = item['region']
                self.assertEqual(len(grid), 6)
                self.assertTrue(all(len(row) == 6 for row in grid))
                counts = Counter(cell for row in grid for cell in row)
                self.assertEqual(set(counts.keys()), set(range(6)))
                self.assertGreaterEqual(min(counts.values()), 2)
                for color in range(6):
                    self.assertTrue(connected(grid, color))
                self.assertEqual(unique_solution(grid), tuple(item['solution']))
                key = canonical(grid)
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertEqual(estimated_difficulty(search_nodes(grid)), item['difficulty'])

    def test_deck_no_repeat_and_new_cycle(self):
        """連續兩輪各 150 題皆不重複，交界不出現連續相同的題。"""
        random.seed(20261012)
        puzzle = Puzzle()
        first = [puzzle.current_template_index]
        for _ in range(149):
            puzzle.load_next_level()
            first.append(puzzle.current_template_index)
        self.assertEqual(set(first), set(range(150)))
        second = []
        for _ in range(150):
            puzzle.load_next_level()
            second.append(puzzle.current_template_index)
        self.assertEqual(set(second), set(range(150)))
        self.assertNotEqual(first[-1], second[0])
        self.assertEqual(puzzle.level, 300)

    def test_curated_shape_diversity(self):
        """真正檢查不同色區的分組關係，而不是只排除旋轉。"""
        signatures = [structural_signatures(item['region']) for item in LEVEL_TEMPLATES]
        for i, a in enumerate(signatures):
            for j in range(i+1, len(signatures)):
                distance = structural_distance(a, signatures[j])
                # 原始 30 關不能改內容，它們原本的最小距離為 64。
                minimum = 64 if i < 30 and j < 30 else 66
                self.assertGreaterEqual(distance, minimum, (i+1, j+1))

        answers = Counter(tuple(item['solution']) for item in LEVEL_TEMPLATES)
        self.assertLessEqual(max(answers.values()), 3)
        groups = Counter(item['outline'] for item in LEVEL_TEMPLATES)
        self.assertGreaterEqual(min(groups.values()), 30)
        difficulty = Counter(item['difficulty'] for item in LEVEL_TEMPLATES)
        self.assertGreaterEqual(min(difficulty.values()), 30)
        size = Counter(item['size_profile'] for item in LEVEL_TEMPLATES)
        self.assertGreaterEqual(min(size.values()), 10)

        for item in LEVEL_TEMPLATES:
            borders, spread = shape_profile(item['region'])
            self.assertEqual((item['borders'], item['spread']), (borders, spread))
            self.assertEqual(outline_group(borders), item['outline'])
            self.assertEqual(size_group(spread), item['size_profile'])

    def test_readable_json_rows(self):
        """一列資料應能在 JSON 中以單行矩陣列閱讀，且不得包含尾逗號。"""
        file = ROOT / 'levels' / 'levels_150.json'
        content = file.read_text(encoding='utf-8')
        self.assertEqual(len(json.loads(content)), 150)
        self.assertIn('"region": [\n      [', content)
        self.assertIn('"solution": [', content)
        # 所有 region 中的每一列都放在同一行。
        for line in content.splitlines():
            if line.startswith('      ['):
                self.assertEqual(line.count('['), 1)
                self.assertEqual(line.count(']'), 1)

    def test_spaced_deck_order(self):
        """新牌組除了不重複，也盡可能讓最近的答案位置不重複。"""
        for seed in (10, 11, 12):
            random.seed(seed)
            p = Puzzle()
            chosen = [p.current_template_index]
            for _ in range(299):
                p.load_next_level()
                chosen.append(p.current_template_index)
            self.assertEqual(len(set(chosen[:150])), 150)
            self.assertEqual(len(set(chosen[150:])), 150)
            for a, b in zip(chosen, chosen[1:]):
                self.assertNotEqual(
                    tuple(LEVEL_TEMPLATES[a]['solution']),
                    tuple(LEVEL_TEMPLATES[b]['solution']))

    def test_solution_is_accepted_by_game_rules(self):
        """以每題的答案逐一放置，驗證規則與成功條件一致。"""
        puzzle = Puzzle()
        for i, item in enumerate(LEVEL_TEMPLATES):
            with self.subTest(level=i+1):
                puzzle.region_map = np.array(item['region'], dtype=np.int8)
                cats = np.zeros((6, 6), dtype=np.int8)
                for r, c in enumerate(item['solution']):
                    self.assertTrue(puzzle.is_valid_placement(cats, r, c))
                    cats[r, c] = 1
                self.assertTrue(puzzle.is_solved(cats))
                self.assertEqual(puzzle.find_all_solutions(limit=2), [tuple(item['solution'])])


if __name__ == '__main__':
    unittest.main()
