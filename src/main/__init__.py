# aim-py-cw
# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块。"""
from collections import deque
from enum import Enum
import json


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """血量百分比，返回 0-100 的 int。"""
    if max_hp <= 0:
        return 0
    ratio = int(round(hp * 100.0 / max_hp))
    return max(0, min(100, ratio))


def status_report(name, robot_type, hp, max_hp, battery):
    """一行自检报告字符串。"""
    hp_pct = hp_ratio(hp, max_hp)
    bat_val = int(battery)
    if bat_val > 50:
        tier = "OK"
    elif bat_val >= 20:
        tier = "WARNING"
    else:
        tier = "LOW"
    return (
        f"{name:<10}|{robot_type:^10}|"
        f"HP {hp_pct:>3}%|BAT {bat_val:>3}%|{tier}"
    )


# ---------------------------------------------------------------------------
# Q2 战斗日志分析
# ---------------------------------------------------------------------------
def analyze_damage_log(lines):
    """解析混合格式伤害日志，返回固定契约的统计 dict。"""
    total = 0
    by_armor = {"front": 0, "left": 0, "right": 0}
    seen_ids = set()
    event_count = 0

    letter_to_armor = {"F": "front", "L": "left", "R": "right"}

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Try JSON format
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
                    continue
                armor = data.get("armor")
                damage = data.get("damage")
                if armor not in by_armor:
                    continue
                if (not isinstance(damage, int) or isinstance(
                        damage, bool) or damage <= 0):
                    continue
                if "id" in data:
                    item_id = data["id"]
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                by_armor[armor] += damage
                total += damage
                event_count += 1
            except Exception:
                continue
            continue

        # Try Sensor format: "F:32,L:5,R:12"
        parts = line.split(",")
        is_sensor = True
        line_damages = []
        seen_letters = set()
        for part in parts:
            kv = part.strip().split(":")
            if len(kv) != 2:
                is_sensor = False
                break
            letter = kv[0].strip()
            val_str = kv[1].strip()
            if letter not in letter_to_armor or letter in seen_letters:
                is_sensor = False
                break
            if not val_str.isdigit():
                is_sensor = False
                break
            dmg_val = int(val_str)
            if dmg_val <= 0:
                is_sensor = False
                break
            seen_letters.add(letter)
            line_damages.append((letter_to_armor[letter], dmg_val))

        if is_sensor and line_damages:
            line_total = 0
            for armor, dmg in line_damages:
                by_armor[armor] += dmg
                line_total += dmg
            total += line_total
            event_count += 1

    most_hit = None
    if total > 0:
        most_hit = max(["front", "left", "right"], key=lambda k: by_armor[k])

    avg_val = round(total / event_count, 2) if event_count > 0 else 0.0

    return {
        "total": total,
        "by_armor": by_armor,
        "most_hit": most_hit,
        "avg": avg_val,
    }


# ---------------------------------------------------------------------------
# Q3 SentryGrid
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """元素转 int 并夹回地图范围。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    @property
    def current_pos(self):
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos 需要长度为 2 的 tuple/list")
        self._pos = (int(value[0]), int(value[1]))

    def move_forward(self):
        if self._fuel <= 0:
            return self._pos
        self._fuel -= 1
        dx, dy = self._facing.delta
        nx, ny = self._pos[0] + dx, self._pos[1] + dy
        if self.is_blocked(nx, ny):
            self._collision_count += 1
        else:
            self._pos = (nx, ny)
        return self._pos

    def turn_left(self):
        rot = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP,
        }
        self._facing = rot[self._facing]
        return self._facing

    def turn_right(self):
        rot = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP,
        }
        self._facing = rot[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """返回下一步应朝向的 Facing。"""
    px, py = pos
    tx, ty = target
    dx = tx - px
    dy = ty - py
    cur_dist = abs(dx) + abs(dy)
    if cur_dist == 0:
        return current_facing

    cands = []
    for f in (Facing.UP, Facing.DOWN, Facing.LEFT, Facing.RIGHT):
        fdx, fdy = f.delta
        nxt = (px + fdx, py + fdy)
        if nxt in obstacles:
            continue
        dist = abs(tx - nxt[0]) + abs(ty - nxt[1])
        if dist < cur_dist:
            cands.append(f)

    if not cands:
        return current_facing
    if len(cands) == 1:
        return cands[0]

    prefer_x = abs(dx) >= abs(dy)
    for c in cands:
        is_x = c in (Facing.LEFT, Facing.RIGHT)
        if is_x == prefer_x:
            return c
    return cands[0]


# ---------------------------------------------------------------------------
# Q5 哨兵决策机
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """纯函数决策，返回 (action: str, new_state: SentryState)。"""
    required_keys = {"enemy_frames", "enemy_dist", "robot_type", "max_hp"}
    if not isinstance(sensor, dict) or not required_keys.issubset(
            sensor.keys()):
        raise ValueError("sensor 字典缺少必要字段")

    frames = sensor["enemy_frames"]
    if (not isinstance(frames, (tuple, list))
            or len(frames) == 0 or len(frames) > 6):
        raise ValueError("enemy_frames 长度必须在 1-6 之间")

    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")

    try:
        max_hp = int(sensor["max_hp"])
    except Exception:
        max_hp = 100
    if max_hp <= 0:
        max_hp = 100

    hp_pct = max(0, min(100, int(round(hp * 100.0 / max_hp))))
    visible = bool(frames[-1])

    dist = sensor["enemy_dist"]
    if dist is not None and not isinstance(dist, (int, float)):
        dist = None
    if dist is not None:
        dist = int(dist)

    rtype = str(sensor["robot_type"]).upper()

    # R1: 保命优先
    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)

    # R2: 撤退保持
    if state == SentryState.RETREAT:
        if hp_pct >= 70:
            return ("RETURN", SentryState.RETURN)
        return ("RETREAT", SentryState.RETREAT)

    # R3: 返航单帧
    if state == SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)

    # R4: 交火决策
    if state == SentryState.ENGAGE and visible:
        if dist is not None and dist <= 3:
            return ("SHOOT", SentryState.ENGAGE)
        if rtype == "HERO":
            return ("MOVE_RIGHT", SentryState.ENGAGE)
        return ("MOVE_LEFT", SentryState.ENGAGE)

    # R5: 交火保持
    if state == SentryState.ENGAGE and not visible:
        if len(frames) >= 2 and bool(frames[-2]):
            return ("HOLD_FIRE", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)

    # R6: 敌情确认
    if state in (SentryState.PATROL, SentryState.SUSPECT) and visible:
        if len(frames) >= 2 and bool(frames[-2]) and bool(frames[-1]):
            if dist is not None and dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)
            if rtype == "HERO":
                return ("MOVE_RIGHT", SentryState.ENGAGE)
            return ("MOVE_LEFT", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)

    # R7: 默认行为
    if state == SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)
    return ("SCAN", SentryState.SUSPECT)


# ---------------------------------------------------------------------------
# Q6 巡逻任务
# ---------------------------------------------------------------------------
def _rotate_grid(grid, target_facing):
    rights = {
        Facing.UP: 0,
        Facing.RIGHT: 1,
        Facing.DOWN: 2,
        Facing.LEFT: 3,
    }
    diff = (rights[target_facing] - rights[grid.facing]) % 4
    if diff == 3:
        grid.turn_left()
    else:
        for _ in range(diff):
            grid.turn_right()


def run_patrol(grid, max_steps=500):
    """sense → decide → act 主循环。"""
    steps = 0
    visited = {grid.current_pos}
    target = grid.enemy_pos
    escape_queue = deque()

    def manhattan(p):
        return abs(p[0] - target[0]) + abs(p[1] - target[1])

    while steps < max_steps and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos
        if escape_queue:
            direction = escape_queue.popleft()
        else:
            direction = next_step_toward(
                pos, target, grid.obstacles, grid.facing)
            fdx, fdy = direction.delta
            nxt = (pos[0] + fdx, pos[1] + fdy)
            if grid.is_blocked(*nxt) or manhattan(nxt) >= manhattan(pos):
                queue = deque([pos])
                parent = {pos: None}
                action = {}
                target_cell = None

                while queue:
                    cur = queue.popleft()
                    if manhattan(cur) < manhattan(pos):
                        target_cell = cur
                        break
                    for f in (Facing.UP, Facing.RIGHT,
                              Facing.DOWN, Facing.LEFT):
                        dx, dy = f.delta
                        adj = (cur[0] + dx, cur[1] + dy)
                        if grid.is_blocked(*adj) or adj in parent:
                            continue
                        parent[adj] = cur
                        action[adj] = f
                        queue.append(adj)

                if target_cell:
                    curr = target_cell
                    path = []
                    while curr != pos:
                        path.append(action[curr])
                        curr = parent[curr]
                    path.reverse()
                    escape_queue = deque(path)
                    direction = escape_queue.popleft()

        _rotate_grid(grid, direction)
        grid.move_forward()
        steps += 1
        visited.add(grid.current_pos)

    success = grid.found_enemy
    return {
        "steps": steps,
        "collisions": grid.collision_count,
        "visited_count": len(visited),
        "found_enemy": success,
        "success": success,
    }


def report_to_json(stats):
    """把 stats 序列化为确定性的 JSON 字符串。"""
    return json.dumps(stats, sort_keys=True)


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """BFS 全局最短路步数。"""
    if start == target:
        return 0
    obs = set(obstacles)
    if start in obs or target in obs:
        return -1

    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cur, d = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in obs or nxt in seen:
                continue
            if nxt == target:
                return d + 1
            seen.add(nxt)
            queue.append((nxt, d + 1))
    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
