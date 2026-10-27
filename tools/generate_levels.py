"""離線產生 Cat Puzzle 關卡：不修改遊戲主畫面。

執行：python tools/generate_levels.py
- 保留 levels/base_30.json 的原始 30 關。
- 新增 120 個四方向連通、唯一解的 6x6 關卡。
- 排除轉向／鏡射／顏色重新編號造成的假新關卡。
- 不依賴 Pygame 或 NumPy，產生後只需攜帶 levels/levels_150.json。
"""

from collections import Counter, deque
import sys
from itertools import permutations
from pathlib import Path
import json
import random

# 棋盤為 6x6，實際遊戲規則目前固定六個顏色區域。
N = 6               # 棋盤邊長，也等於需要放置的貓咪數量。
TARGET = 150        # 生成後整個題庫應包含的總關卡數。
SEED = 20261012    # 固定離線亂數種子，使生成結果可重現。
ROOT = Path(__file__).resolve().parents[1]  # tools 的上一層即專案根目錄。
# 直接以 python tools/generate_levels.py 執行時也能找到共用結構分析模組。
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from level_diversity import (canonical as shape_key, structural_signatures,
                             structural_distance, shape_profile, outline_group, size_group)
BASE_FILE = ROOT / 'levels' / 'base_30.json'  # 原始 30 題，不允許生成器覆寫。
OUTPUT_FILE = ROOT / 'levels' / 'levels_150.json'  # 最終提供遊戲載入的題庫。

# 完全符合「每列、每欄各一隻，且相鄰列不可貼在一起」的候選答案。
# 預先排除同行、同列、相鄰衝突的答案排列；生成器只需再檢查色區。
BASE_SOLUTIONS = tuple(
    cols for cols in permutations(range(N))
    if all(abs(cols[r] - cols[r+1]) > 1 for r in range(N-1))
)
# NEIGHBORS：每格可走的上/下/左/右座標；供色區成長及 BFS 使用。
NEIGHBORS = {
    (r, c): tuple((rr, cc) for rr, cc in (
        (r-1, c), (r+1, c), (r, c-1), (r, c+1))
        if 0 <= rr < N and 0 <= cc < N)
    for r in range(N) for c in range(N)
}


def normalized(matrix):
    """不管各色原先叫 0~5 哪個數字，都改成首次遇到的順序。"""
    name_map = {}
    cells = []
    for row in matrix:
        for color in row:
            if color not in name_map:
                name_map[color] = len(name_map)
            cells.append(name_map[color])
    return tuple(cells)


def orientations(matrix):
    """回傳八種旋轉／鏡射後的區域編號正規化表示。"""
    current = [list(row) for row in matrix]
    variants = []
    for _ in range(4):
        variants.append(normalized(current))
        variants.append(normalized([row[::-1] for row in current]))
        current = [list(row) for row in zip(*current[::-1])]
    return tuple(variants)


def canonical(matrix):
    """取所有旋轉／鏡射版本中的最小代表值，進行真正的拓樸去重。"""
    return min(orientations(matrix))


def connected(matrix, region):
    """檢查同一顏色的格子是否以四方向相連。"""
    # points：該色區全部座標；found：BFS 已經走訪的格子集合。
    points = {(r, c) for r in range(N) for c in range(N)
              if matrix[r][c] == region}
    if not points:
        return False
    found = {next(iter(points))}
    queue = deque(found)
    while queue:
        for nb in NEIGHBORS[queue.popleft()]:
            if nb in points and nb not in found:
                found.add(nb)
                queue.append(nb)
    return len(found) == len(points)


def unique_solution(matrix):
    """最多搜尋兩組答案；不是恰好一組的題目就排除。"""
    found = None
    for cols in BASE_SOLUTIONS:
        if len({matrix[r][cols[r]] for r in range(N)}) == N:
            if found is not None:
                return None
            found = cols
    return found


def generate_region_map(rng, style):
    """從六個隨機起點擴張，以不同偏好產生多種類型的區域。"""
    # -1 表示尚未分配顏色的空格；0～5 表示六個區域的編號。
    board = [[-1] * N for _ in range(N)]
    cells = [(r, c) for r in range(N) for c in range(N)]
    if style == '邊緣':
        edges = [p for p in cells if 0 in p or N-1 in p]
        seeds = rng.sample(edges, N)
    elif style == '分散':
        seeds = [rng.choice(cells)]
        while len(seeds) < N:
            options = [p for p in cells if p not in seeds]
            weight = [1 + min(abs(p[0]-s[0])+abs(p[1]-s[1]) for s in seeds) ** 3
                      for p in options]
            seeds.append(rng.choices(options, weights=weight, k=1)[0])
    elif style == '集中':
        # 隨機集中種子，更容易形成大小差異明顯的區域。
        center = rng.choice(cells)
        nearby = sorted(cells, key=lambda p: abs(p[0]-center[0])+abs(p[1]-center[1]))[:20]
        seeds = rng.sample(nearby, N)
    else:
        seeds = rng.sample(cells, N)

    # seeds 中六個起始位置分別成為六個顏色區域的最初一格。
    for region, (r, c) in enumerate(seeds):
        board[r][c] = region
    sizes = [1] * N

    # 四種發展方式能形成比較緊密、細長、交錯與不均衡的區域。
    for _ in range(N * N - N):
        # options：合法擴張的 (區域ID, 新格座標)；weights：對應抽選權重。
        options = []
        weights = []
        for region in range(N):
            if sizes[region] >= 12:
                continue
            frontier = set()
            for r in range(N):
                for c in range(N):
                    if board[r][c] == region:
                        frontier.update(p for p in NEIGHBORS[(r, c)] if board[p[0]][p[1]] == -1)
            for p in frontier:
                own = sum(board[r][c] == region for r, c in NEIGHBORS[p])
                if style == '緊湊':
                    w = (1 + own * own * 2) / (sizes[region] ** 0.65)
                elif style == '蜿蜒':
                    w = 5.0 / (1 + own * own) / (sizes[region] ** 0.45)
                elif style == '不均衡' or style == '集中':
                    w = (1 + sizes[region] * 0.6) * (1 + own * 0.3)
                elif style == '分散':
                    w = (1 + own) / (sizes[region] ** 1.2)
                elif style == '邊緣':
                    w = (2 if 0 in p or N-1 in p else 1) * (1+own) / (sizes[region] ** 0.7)
                else:
                    w = 1.0 / (sizes[region] ** 0.5)
                # 保持每個顏色區域至少 2 格，避免不可玩的單格孤島。
                if sizes[region] == 1:
                    w *= 3.5
                options.append((region, p))
                weights.append(w)
        if not options:
            return None
        # 非等機率選取一種擴張方向，讓不同 style 有不同輪廓傾向。
        region, (r, c) = rng.choices(options, weights=weights, k=1)[0]
        board[r][c] = region
        sizes[region] += 1
    if min(sizes) < 2:
        return None
    return board


def shape_stats(matrix):
    """描述版型形狀特徵，並非假裝已量測玩家的實際解題難度。"""
    sizes = Counter(v for row in matrix for v in row)
    # 異色相接邊數越多，形狀輪廓通常越複雜。
    borders = sum(matrix[r][c] != matrix[nr][nc]
                  for r in range(N) for c in range(N)
                  for nr, nc in NEIGHBORS[(r, c)] if (nr, nc) > (r, c))
    size_spread = max(sizes.values()) - min(sizes.values())
    return borders, size_spread


def search_nodes(board):
    """以列為順序枚舉合法部分配置；節點數作為相對難度估計依據。"""
    visited = 0  # DFS 曾展開多少個合法部分放置節點，僅做相對難度估計。

    def dfs(row, columns, regions):
        """依列遞迴放貓；columns 保存已選欄，regions 保存已使用的色區。"""
        nonlocal visited
        if row == N:
            return
        for col in range(N):
            if col in columns or (columns and abs(col - columns[-1]) <= 1):
                continue
            region = board[row][col]
            if region in regions:
                continue
            visited += 1
            dfs(row + 1, columns + (col,), regions | {region})

    dfs(0, (), set())
    return visited


def estimated_difficulty(nodes):
    """根據搜尋樹節點數提供相對級別；不是經玩家測試的客觀難度。"""
    if nodes <= 64:
        return '入門'
    if nodes <= 97:
        return '普通'
    if nodes <= 136:
        return '進階'
    return '困難'


def level_name(style, count):
    """命名使用產生模式和編號，不把旋轉誤稱為新類型。"""
    return '{}地形 {:02d}'.format(style, count)


def readable_json(levels):
    """美化 JSON：每個矩陣 row 都佔一行，同時遵守正式 JSON 語法。"""
    # 自訂輸出格式讓 region 的六個 row 各佔一行；JSON 本身不能加入註解。
    output = ['[']
    for index, item in enumerate(levels):
        output.append('  {')
        fields = list(item.items())
        for field_index, (key, value) in enumerate(fields):
            comma = ',' if field_index < len(fields) - 1 else ''
            field_name = json.dumps(key, ensure_ascii=False)
            if key == 'region':
                output.append('    {}: ['.format(field_name))
                for row_index, row in enumerate(value):
                    end = ',' if row_index < len(value) - 1 else ''
                    output.append('      {}{}'.format(json.dumps(row, ensure_ascii=False), end))
                output.append('    ]' + comma)
            else:
                output.append('    {}: {}{}'.format(
                    field_name, json.dumps(value, ensure_ascii=False), comma))
        output.append('  }' + (',' if index < len(levels) - 1 else ''))
    output.append(']')
    text = '\n'.join(output) + '\n'
    # 防止自訂排版不小心寫出不合法 JSON。
    assert json.loads(text) == levels
    return text


def main():
    """保存原始30關，挑選120關顯著不同的題目，不改動遊戲 UI。"""
    original = json.loads(BASE_FILE.read_text(encoding='utf-8'))
    if len(original) != 30:
        raise ValueError('原始關卡必須正好 30 關')

    templates = []
    fingerprints = []
    seen = set()
    answer_counts = Counter()
    difficulty_counts = Counter()
    outline_counts = Counter()
    size_counts = Counter()
    family_counts = Counter()

    # 第一批30關是既有題目，保持內容及名稱不變。
    for entry in original:
        matrix = entry['region']
        key = shape_key(matrix)
        if key in seen or unique_solution(matrix) != tuple(entry['solution']):
            raise ValueError('原始關卡有重複或答案錯誤：' + entry['name'])
        if any(not connected(matrix, color) for color in range(N)):
            raise ValueError('原始區域不連通：' + entry['name'])
        seen.add(key)
        answer_counts[tuple(entry['solution'])] += 1
        borders, spread = shape_profile(matrix)
        nodes = search_nodes(matrix)
        difficulty = estimated_difficulty(nodes)
        difficulty_counts[difficulty] += 1
        outline_counts[outline_group(borders)] += 1
        size_counts[size_group(spread)] += 1
        fingerprints.append(structural_signatures(matrix))
        templates.append(dict(entry, family='原始', borders=borders,
                              spread=spread, search_nodes=nodes,
                              difficulty=difficulty,
                              outline=outline_group(borders),
                              size_profile=size_group(spread)))

    # 固定亂數種子使關卡庫可再生，但遊戲每次啟動時仍會重新洗牌。
    rng = random.Random(SEED + 2)
    styles = ['緊湊', '蜿蜒', '不均衡', '分散', '邊緣', '集中', '交錯']
    styles_limit = 23
    # 這些上限是「實際外觀特徵」的配額，而非只有生成器名稱。
    outline_limit = {'簡潔': 78, '中等': 80, '曲折': 70}
    size_limit = {'均衡': 65, '中等': 95, '懸殊': 105}
    difficulty_limit = {'入門': 40, '普通': 40, '進階': 40, '困難': 40}
    min_distance = 66     # 新增題目與已選題目之間的最小區域分組距離。
    answer_limit = 3      # 完全相同的答案位置至多出現3次（含原始題）。
    attempts_limit = 220000
    attempts = 0
    rejection = Counter()

    # 只要尚未選足 150 關、且候選題嘗試次數未超過上限，就繼續篩選。
    while len(templates) < TARGET and attempts < attempts_limit:
        attempts += 1
        remaining_styles = [s for s in styles if family_counts[s] < styles_limit]
        if not remaining_styles:
            break
        style = rng.choice(remaining_styles)
        board = generate_region_map(rng, style)
        if board is None:
            rejection['區域生成失敗'] += 1
            continue
        solution = unique_solution(board)
        if solution is None:
            rejection['不符合唯一解'] += 1
            continue
        # 即使色區不同，也限制同樣的答案位置不要反覆出現。
        if answer_counts[solution] >= answer_limit:
            rejection['答案配置重複過多'] += 1
            continue

        borders, spread = shape_profile(board)
        outline, size_type = outline_group(borders), size_group(spread)
        if outline_counts[outline] >= outline_limit[outline]:
            rejection['輪廓類型超出比例'] += 1
            continue
        if size_counts[size_type] >= size_limit[size_type]:
            rejection['面積類型超出比例'] += 1
            continue
        nodes = search_nodes(board)
        difficulty = estimated_difficulty(nodes)
        if difficulty_counts[difficulty] >= difficulty_limit[difficulty]:
            rejection['難度類型超出比例'] += 1
            continue

        key = shape_key(board)
        if key in seen:
            rejection['旋轉鏡射或區域換色重複'] += 1
            continue
        signature = structural_signatures(board)
        # 逐一比較已選題目：不是只比兩張圖每個位置的區域色碼。
        if any(structural_distance(signature, fp) < min_distance
               for fp in fingerprints):
            rejection['整體結構太相似'] += 1
            continue

        seen.add(key)
        fingerprints.append(signature)
        answer_counts[solution] += 1
        difficulty_counts[difficulty] += 1
        outline_counts[outline] += 1
        size_counts[size_type] += 1
        family_counts[style] += 1
        templates.append({
            'name': '{}地形 {:02d}'.format(style, family_counts[style]),
            'region': board,
            'solution': list(solution),
            'family': style,
            'borders': borders,
            'spread': spread,
            'search_nodes': nodes,
            'difficulty': difficulty,
            'outline': outline,
            'size_profile': size_type,
        })
        # 每加入到 30 的倍數，就在命令列輸出目前進度。
        if len(templates) % 30 == 0:
            print('已挑選 {:3d} / {} 關；嘗試 {:5d} 次'.format(
                len(templates), TARGET, attempts), flush=True)

    # 品質條件不可為了湊數量而自動放寬。
    if len(templates) != TARGET:
        raise RuntimeError('只選出 {} 關（嘗試 {} 次），未達目標 {}；'
                           '請先檢視篩選配額，不應自動降低品質要求。'.format(
                            len(templates), attempts, TARGET))

    OUTPUT_FILE.write_text(readable_json(templates), encoding='utf-8')
    print('產出 {} 關；最小新增關卡結構距離 >= {}'.format(len(templates), min_distance))
    print('類型：難度={}、輪廓={}、面積={}、生成策略={}'.format(
        dict(difficulty_counts), dict(outline_counts),
        dict(size_counts), dict(family_counts)))
    print('相同答案最大出現次數：{}'.format(max(answer_counts.values())))
    print('已輸出：{}'.format(OUTPUT_FILE))


if __name__ == '__main__':
    main()
