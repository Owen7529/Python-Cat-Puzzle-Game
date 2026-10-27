"""關卡形狀差異計算（只依賴 Python 標準函式庫）。

將「任兩格是否屬於同色區域」轉為整數位元特徵：
- 不受到區域色碼 0~5 的重新命名影響；
- 比較時考慮旋轉／左右鏡射；
- 越大的結構距離，代表區域分組方式差異越多。

注意：此數值屬於可重現的形狀距離，不能取代玩家實際體驗。
"""

from collections import Counter

SIZE = 6  # 與 config.BOARD_SIZE 對應，但此檔不依賴 Pygame/NumPy。
# 36 格兩兩配對共有 36*35/2 = 630 組；這是形狀指紋的來源。
CELL_PAIRS = tuple((i, j) for i in range(SIZE * SIZE)
                   for j in range(i + 1, SIZE * SIZE))


def normalized(matrix):
    """依首次出現的順序統一色號，使同形但換色號的關卡可比較。"""
    # 若兩張棋盤只是交換顏色編號，應得到相同的正規化序列。
    mapping = {}
    result = []
    for row in matrix:
        for color in row:
            if color not in mapping:
                mapping[color] = len(mapping)
            result.append(mapping[color])
    return tuple(result)


def orientations(matrix):
    """產生旋轉與鏡射共八個等價形狀（每份為 36 格展平序列）。"""
    # 旋轉 4 次，每一次同時加入鏡射，總共 8 個幾何方向。
    current = [list(row) for row in matrix]
    results = []
    for _ in range(4):
        results.append(normalized(current))
        results.append(normalized([row[::-1] for row in current]))
        current = [list(row) for row in zip(*current[::-1])]
    return tuple(results)


def canonical(matrix):
    """產生與區域換色、旋轉、鏡射無關的標準鍵。"""
    return min(orientations(matrix))


def partition_signature(cells):
    """630 個格子配對轉成位元：1 表示兩格屬於相同區域。"""
    # 每個配對用一個 bit 紀錄同區域(True)或不同區域(False)，共 630 bit。
    bits = 0
    for i, (a, b) in enumerate(CELL_PAIRS):
        if cells[a] == cells[b]:
            bits |= 1 << i
    return bits


def structural_signatures(matrix):
    """輸出八方向結構指紋，可預先計算以加速大量比對。"""
    return tuple(partition_signature(cells) for cells in orientations(matrix))


def structural_distance(signatures_a, signatures_b):
    """兩關最接近方向下的區域分組距離，0 為同一版型。"""
    # 所有旋轉構成封閉群，只需將 A 八方向與 B 第一方向比對。
    # ^ 為 XOR，比較兩張棋盤哪些格子關係不同；bit_count 直接計算個數。
    ref = signatures_b[0]
    return min((signature ^ ref).bit_count() for signature in signatures_a)


def shape_profile(matrix):
    """量化顏色邊界數與區域大小差；不把生成策略誤認成實際形狀。"""
    count = Counter(v for row in matrix for v in row)
    borders = 0
    for row in range(SIZE):
        for col in range(SIZE):
            if row + 1 < SIZE and matrix[row][col] != matrix[row + 1][col]:
                borders += 1
            if col + 1 < SIZE and matrix[row][col] != matrix[row][col + 1]:
                borders += 1
    # spread：最大色區格數 - 最小色區格數，用於區域面積差異分類。
    spread = max(count.values()) - min(count.values())
    return borders, spread


def outline_group(borders):
    """依相鄰色區的邊界長度分類，避免候選題輪廓過度集中。"""
    return '簡潔' if borders <= 22 else '曲折' if borders >= 26 else '中等'


def size_group(spread):
    """依六個區域大小落差分類，避免所有關卡都用大小差極大的色區。"""
    return '均衡' if spread <= 6 else '懸殊' if spread >= 9 else '中等'
