from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


def grid_shape(count: int) -> tuple[int, int]:
    presets = {
        2: (1, 2),
        3: (1, 3),
        4: (2, 2),
        6: (2, 3),
        8: (2, 4),
        9: (3, 3),
    }
    if count in presets:
        return presets[count]
    cols = max(1, ceil(count ** 0.5))
    rows = max(1, ceil(count / cols))
    return rows, cols


def build_grid(
    area: Rect,
    count: int,
    margin: int = 12,
    gap: int = 8,
    custom_shape: tuple[int, int] | None = None,
) -> list[Rect]:
    rows, cols = custom_shape or grid_shape(count)
    usable_w = max(1, area.width - (margin * 2) - (gap * (cols - 1)))
    usable_h = max(1, area.height - (margin * 2) - (gap * (rows - 1)))
    cell_w = usable_w // cols
    cell_h = usable_h // rows

    result: list[Rect] = []
    for index in range(min(count, rows * cols)):
        row, col = divmod(index, cols)
        x = area.x + margin + col * (cell_w + gap)
        y = area.y + margin + row * (cell_h + gap)
        width = cell_w if col < cols - 1 else area.x + area.width - margin - x
        height = cell_h if row < rows - 1 else area.y + area.height - margin - y
        result.append(Rect(x, y, max(1, width), max(1, height)))
    return result
