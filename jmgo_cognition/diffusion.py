"""diffusion_policy.py —— 动作生成层：扩散式轨迹采样 + 可插拔学习策略。

定位：
  · 认知层（骨架/法则/推演）决定“做什么”；
  · 本模块决定“怎么做”：从观测生成一条动作块（轨迹/增量）；
  · 安全闸 verify_trajectory() 仍是否决权，执行层保留急停与限幅。

这里的默认实现是 **training-free 的扩散式采样**（annealed Langevin）：
用能量函数（目标吸引 + 平滑 + 障碍排斥 + 边界/步长约束）的负梯度作为 score，
在递减噪声下迭代去噪。它不是训练好的 Diffusion Policy，但接口与真实策略一致：

    policy = DiffusionPlanner(seed=0)
    out = policy.sample({"start": ..., "goal": ..., "obstacles": ...}, horizon=16)
    out["trajectory"], out["actions"], out["ok"], out["reasons"]

真实学习策略（LeRobot / Diffusion Policy / 自己的模型）实现同一个
`ActionPolicy.sample(observation, horizon)` 即可替换，认知层不用改。
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

# 默认约束（机器人侧应覆盖成自己的真实值）
DEFAULTS = {
    "max_step": 0.5,          # 每个动作块的最大位移（米）
    "clearance": 0.15,        # 障碍外的安全余量（米）
    "goal_tol": 0.2,          # 终点容差（米）
    "bounds": (-10.0, 10.0, -10.0, 10.0),  # xmin, xmax, ymin, ymax
}

WEIGHTS = {
    "goal": 1.0,
    "smooth": 3.0,
    "obstacle": 8.0,
    "start": 20.0,
    "bounds": 5.0,
}


class PolicyError(ValueError):
    """输入/输出不满足契约。"""


class ActionPolicy(Protocol):
    def sample(self, observation: dict[str, Any], horizon: int = 16) -> dict[str, Any]:
        """Return {"trajectory": T×2, "actions": (T-1)×2, ...}."""


def _grid_from_obs(obs: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    start = np.asarray(obs.get("start", [0.0, 0.0]), dtype=float).reshape(2)
    goal = np.asarray(obs.get("goal", [0.0, 0.0]), dtype=float).reshape(2)
    return start, goal


def _obstacles(obs: dict[str, Any]) -> list[tuple[np.ndarray, float]]:
    out = []
    for item in obs.get("obstacles") or []:
        if isinstance(item, dict):
            c = np.asarray([item.get("x", 0.0), item.get("y", 0.0)], dtype=float)
            r = float(item.get("r", item.get("radius", 0.0)))
        else:
            c = np.asarray(item[:2], dtype=float)
            r = float(item[2]) if len(item) > 2 else 0.0
        out.append((c, max(0.0, r)))
    return out


def _constraints(obs: dict[str, Any]) -> dict[str, Any]:
    c = dict(DEFAULTS)
    c.update(obs.get("constraints") or {})
    return c


def _project(x: np.ndarray, start: np.ndarray, cons: dict[str, Any]) -> np.ndarray:
    x = np.array(x, dtype=float, copy=True)
    x[0] = start
    xmin, xmax, ymin, ymax = cons["bounds"]
    x[:, 0] = np.clip(x[:, 0], xmin, xmax)
    x[:, 1] = np.clip(x[:, 1], ymin, ymax)
    # 步长限幅：逐段缩放，重新累计
    ms = float(cons["max_step"])
    for i in range(1, len(x)):
        d = x[i] - x[i - 1]
        n = float(np.linalg.norm(d))
        if n > ms:
            x[i] = x[i - 1] + d * (ms / n)
    x[0] = start
    return x


def _enforce_endpoints(x, start, goal, cons):
    """端点 + 步长可行性修复。返回 (path, feasible)。

    先钉死端点做双向裁剪；若容量/绕障不够，退回「从起点按步长直走」的
    可行路径（终点会差一截），由 verify 如实报 goal_not_reached。
    """
    x = np.array(x, dtype=float, copy=True)
    T = len(x)
    ms = float(cons["max_step"])
    x[0] = start
    x[-1] = goal
    for _ in range(80):
        for i in range(T - 2, -1, -1):
            d = x[i] - x[i + 1]
            n = float(np.linalg.norm(d))
            if n > ms:
                x[i] = x[i + 1] + d * (ms / n)
        for i in range(1, T):
            d = x[i] - x[i - 1]
            n = float(np.linalg.norm(d))
            if n > ms:
                x[i] = x[i - 1] + d * (ms / n)
        if float(np.linalg.norm(x[-1] - goal)) <= 1e-9:
            break
    # 最终从起点重建，保证步长；终点若仍到不了则短一截
    yy = [np.array(start, dtype=float)]
    for i in range(1, T):
        d = x[i] - yy[-1]
        n = float(np.linalg.norm(d))
        yy.append(yy[-1] + (d * (ms / n) if n > ms else d))
    x = np.asarray(yy)
    feasible = float(np.linalg.norm(x[-1] - goal)) <= 1e-6
    if feasible:
        x[-1] = goal
    return x, feasible


def _smooth(x, start, goal, iters=50, lam=0.35):
    """内部点拉普拉斯平滑：缩短噪声造成的折线长度（端点不动）。"""
    x = np.array(x, dtype=float, copy=True)
    for _ in range(int(iters)):
        x[1:-1] += lam * (x[:-2] + x[2:] - 2.0 * x[1:-1])
        x[0] = start
        x[-1] = goal
    return x


def _resample_path(x, start, goal, T, ms):
    """按弧长等距重采样：保留绕障几何，同时保证每步 ≤ max_step。

    路径总长 > (T-1)*max_step 时返回 None（一个动作块装不下）。
    """
    x = np.asarray(x, dtype=float)
    x[0] = start
    x[-1] = goal
    seg = np.linalg.norm(np.diff(x, axis=0), axis=1)
    total = float(seg.sum())
    if total <= 1e-9:
        return np.repeat(np.asarray([start], dtype=float), T, axis=0)
    cap = (T - 1) * ms
    truncated = total > cap + 1e-9
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0.0, min(total, cap), T)
    out = []
    j = 0
    for s in targets:
        while j < len(seg) - 1 and cum[j + 1] < s:
            j += 1
        span = max(1e-12, cum[j + 1] - cum[j])
        f = (s - cum[j]) / span
        out.append(x[j] + (x[j + 1] - x[j]) * f)
    out = np.asarray(out)
    out[0] = start
    if not truncated:
        out[-1] = goal          # 截断时终点会差一截，由 verify 如实报
    return out


def _grad_energy(x, start, goal, obstacles, cons):
    T = len(x)
    g = np.zeros_like(x)
    # 目标吸引（只作用终点，软约束）
    g[-1] += 2.0 * WEIGHTS["goal"] * (x[-1] - goal)
    # 平滑（二阶差分）
    if T >= 3:
        lap = x[:-2] - 2.0 * x[1:-1] + x[2:]
        g[:-2] += 2.0 * WEIGHTS["smooth"] * lap
        g[1:-1] += -4.0 * WEIGHTS["smooth"] * lap
        g[2:] += 2.0 * WEIGHTS["smooth"] * lap
    # 障碍排斥
    margin = float(cons["clearance"])
    for c, r in obstacles:
        diff = x - c
        dist = np.linalg.norm(diff, axis=1)
        viol = np.maximum(0.0, (r + margin) - dist)
        if np.any(viol > 0):
            scale = (-2.0 * WEIGHTS["obstacle"] * viol / (dist + 1e-6))[:, None]
            g += scale * diff
    # 起点弹簧（软）
    g[0] += 2.0 * WEIGHTS["start"] * (x[0] - start)
    # 边界软约束
    xmin, xmax, ymin, ymax = cons["bounds"]
    for i in range(T):
        if x[i, 0] < xmin:
            g[i, 0] += -2.0 * WEIGHTS["bounds"] * (xmin - x[i, 0])
        elif x[i, 0] > xmax:
            g[i, 0] += 2.0 * WEIGHTS["bounds"] * (x[i, 0] - xmax)
        if x[i, 1] < ymin:
            g[i, 1] += -2.0 * WEIGHTS["bounds"] * (ymin - x[i, 1])
        elif x[i, 1] > ymax:
            g[i, 1] += 2.0 * WEIGHTS["bounds"] * (x[i, 1] - ymax)
    return g


class DiffusionSampler:
    """通用扩散公理：任意形状的向量计划 + 能量梯度 + 约束投影 + 退火去噪。

    不绑定 2D 轨迹：只要给出 ``grad_fn(x)``（能量负梯度/score）和可选的
    ``project_fn(x)``（硬约束投影），就能对 T×D 的任意计划采样。
    """

    def __init__(self, seed: int = 0, levels: int = 8, steps_per_level: int = 18,
                 lr: float = 0.08, noise0: float = 0.6):
        self.seed = int(seed)
        self.levels = int(levels)
        self.steps_per_level = int(steps_per_level)
        self.lr = float(lr)
        self.noise0 = float(noise0)

    def sample(self, init, grad_fn, project_fn=None):
        x = np.array(init, dtype=float, copy=True)
        rng = np.random.default_rng(self.seed)
        for level in range(self.levels):
            sigma = self.noise0 * (0.35 ** level)
            for _ in range(self.steps_per_level):
                g = np.asarray(grad_fn(x), dtype=float)
                x = x - self.lr * g + rng.normal(0.0, sigma * 0.05, size=x.shape)
                if project_fn is not None:
                    x = project_fn(x)
        return x


class DiffusionPlanner:
    """Training-free diffusion-style trajectory sampler (annealed Langevin)."""

    name = "diffusion"

    def __init__(self, seed: int = 0, levels: int = 8, steps_per_level: int = 18,
                 lr: float = 0.08, noise0: float = 0.6):
        self.sampler = DiffusionSampler(seed, levels, steps_per_level, lr, noise0)
        self.seed = int(seed)

    def sample(self, observation: dict[str, Any], horizon: int = 16) -> dict[str, Any]:
        start, goal = _grid_from_obs(observation)
        obstacles = _obstacles(observation)
        cons = _constraints(observation)
        T = max(3, int(horizon))
        rng = np.random.default_rng(self.seed)

        # 初始：直线 + 噪声；通用扩散公理负责退火去噪
        t = np.linspace(0.0, 1.0, T)[:, None]
        x0 = start[None, :] * (1 - t) + goal[None, :] * t
        x0 = x0 + rng.normal(0.0, 0.1, size=x0.shape)
        x = self.sampler.sample(
            x0,
            lambda z: _grad_energy(z, start, goal, obstacles, cons),
            lambda z: _project(z, start, cons),
        )

        x[0] = start
        x = _project(x, start, cons)
        # 端点修复：保证“最后一个动作块点”真的到目标（容量不够时如实报）
        reachable = float(np.linalg.norm(goal - start)) <= (T - 1) * float(cons["max_step"]) + 1e-9
        if reachable:
            # 平滑定形 → 推离障碍（留额外余量）→ 等距重采样；最后不再平滑，
            # 否则会把刚推出去的路径又拉回障碍里。
            x = _smooth(x, start, goal, 60, 0.4)
            x = _resample_path(x, start, goal, T, float(cons["max_step"]))
            margin = float(cons["clearance"]) + 0.1
            for _ in range(24):
                moved = False
                for c, r in obstacles:
                    diff = x - c
                    dist = np.linalg.norm(diff, axis=1)
                    need = r + margin
                    mask = dist < need
                    if np.any(mask):
                        scale = ((need - dist[mask]) / (dist[mask] + 1e-9))[:, None]
                        x[mask] += diff[mask] * scale
                        moved = True
                x[0] = start
                x[-1] = goal
                x = _resample_path(x, start, goal, T, float(cons["max_step"]))
                if not moved:
                    break
        actions = np.diff(x, axis=0)
        out = {
            "trajectory": x.round(6).tolist(),
            "actions": actions.round(6).tolist(),
            "policy": self.name,
            "seed": self.seed,
            "horizon": T,
        }
        verdict = verify_trajectory(x, start, goal, obstacles, cons)
        out.update(verdict)
        return out


class NullPolicy:
    """Straight line at max_step; useful as a baseline and a fallback."""

    name = "null"

    def sample(self, observation: dict[str, Any], horizon: int = 16) -> dict[str, Any]:
        start, goal = _grid_from_obs(observation)
        obstacles = _obstacles(observation)
        cons = _constraints(observation)
        T = max(2, int(horizon))
        ms = float(cons["max_step"])
        dist = float(np.linalg.norm(goal - start))
        need = math.ceil(dist / ms) if dist > 0 else 0
        pts = []
        if need + 1 <= T:
            for i in range(need + 1):
                pts.append(start + (goal - start) * (i / need if need else 1.0))
            while len(pts) < T:
                pts.append(goal.copy())       # 到点后原地保持
        else:
            # 一个动作块到不了：走满 T 点，方向正确但终点会差一截
            for i in range(T):
                pts.append(start + (goal - start) * (i / (T - 1)))
        x = np.asarray(pts)
        actions = np.diff(x, axis=0)
        out = {
            "trajectory": x.round(6).tolist(),
            "actions": actions.round(6).tolist(),
            "policy": self.name,
            "horizon": T,
        }
        out.update(verify_trajectory(x, start, goal, obstacles, cons))
        return out


class CallablePolicy:
    """Wrap a user/model function as a policy, with shape validation."""

    name = "callable"

    def __init__(self, fn: Callable[[dict[str, Any], int], Any], name: str = "callable"):
        self.fn = fn
        self.name = name

    def sample(self, observation: dict[str, Any], horizon: int = 16) -> dict[str, Any]:
        raw = self.fn(observation, horizon)
        if isinstance(raw, dict):
            traj = raw.get("trajectory")
            if traj is None:
                raise PolicyError("callable policy returned no trajectory")
            extra = raw
        else:
            traj, extra = raw, {}
        x = np.asarray(traj, dtype=float)
        if x.ndim != 2 or x.shape[1] != 2 or len(x) < 2:
            raise PolicyError(f"trajectory must be T×2 with T>=2, got {x.shape}")
        start, goal = _grid_from_obs(observation)
        obstacles = _obstacles(observation)
        cons = _constraints(observation)
        out = {
            "trajectory": x.round(6).tolist(),
            "actions": np.diff(x, axis=0).round(6).tolist(),
            "policy": self.name,
            "horizon": len(x),
        }
        out.update(verify_trajectory(x, start, goal, obstacles, cons))
        if extra:
            out["meta"] = {k: v for k, v in extra.items() if k != "trajectory"}
        return out


def verify_trajectory(x, start, goal, obstacles, cons) -> dict[str, Any]:
    """Safety gate: collision, limits, bounds, goal tolerance, finiteness."""
    reasons: list[str] = []
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or len(x) < 2:
        return {"ok": False, "reasons": ["bad_shape"]}
    if not np.all(np.isfinite(x)):
        reasons.append("non_finite")
    if float(np.linalg.norm(x[0] - start)) > 1e-6:
        reasons.append("start_moved")
    if float(np.linalg.norm(x[-1] - goal)) > float(cons["goal_tol"]):
        reasons.append("goal_not_reached")
    steps = np.linalg.norm(np.diff(x, axis=0), axis=1)
    if float(np.max(steps)) > float(cons["max_step"]) + 1e-6:
        reasons.append("step_limit")
    xmin, xmax, ymin, ymax = cons["bounds"]
    if np.any(x[:, 0] < xmin - 1e-6) or np.any(x[:, 0] > xmax + 1e-6) or \
       np.any(x[:, 1] < ymin - 1e-6) or np.any(x[:, 1] > ymax + 1e-6):
        reasons.append("out_of_bounds")
    for c, r in obstacles:
        d = np.linalg.norm(x - c, axis=1)
        if np.any(d < r + float(cons["clearance"]) - 1e-3):
            reasons.append("collision")
            break
    return {"ok": not reasons, "reasons": reasons}


def plan_motion(observation: dict[str, Any], horizon: int = 16,
                policy: ActionPolicy | None = None) -> dict[str, Any]:
    """One call used by the cognitive layer: observation → verified action chunk."""
    policy = policy or DiffusionPlanner()
    return policy.sample(observation, horizon=horizon)


# ---------------- demo / self-test ----------------
def _ascii(obs, traj, w=24, h=14):
    xmin, xmax, ymin, ymax = _constraints(obs)["bounds"]
    grid = [[" " for _ in range(w)] for _ in range(h)]

    def cell(p):
        cx = int((p[0] - xmin) / (xmax - xmin + 1e-9) * (w - 1))
        cy = int((p[1] - ymin) / (ymax - ymin + 1e-9) * (h - 1))
        return max(0, min(w - 1, cx)), max(0, min(h - 1, h - 1 - cy))

    for c, r in _obstacles(obs):
        for i in range(w):
            for j in range(h):
                p = np.array([xmin + (xmax - xmin) * i / (w - 1),
                              ymin + (ymax - ymin) * j / (h - 1)])
                if np.linalg.norm(p - c) <= r:
                    grid[h - 1 - j][i] = "#"
    for p in traj:
        cx, cy = cell(p)
        grid[cy][cx] = "."
    sx, sy = cell(obs["start"]); gx, gy = cell(obs["goal"])
    grid[sy][sx] = "S"; grid[gy][gx] = "G"
    return "\n".join("".join(row) for row in grid)


def _selftest():
    ok = []
    obs = {
        "start": [0.0, 0.0],
        "goal": [6.0, 4.0],
        "obstacles": [{"x": 3.0, "y": 2.0, "r": 0.8}, {"x": 4.5, "y": 3.5, "r": 0.6}],
        "constraints": dict(DEFAULTS, bounds=(0.0, 8.0, 0.0, 6.0)),
    }
    p = DiffusionPlanner(seed=7)
    a = p.sample(obs, horizon=22)
    b = p.sample(obs, horizon=22)
    ok.append(a["trajectory"] == b["trajectory"])
    print("① 同 seed 确定性 →", a["trajectory"] == b["trajectory"])

    traj = np.asarray(a["trajectory"])
    ok.append(traj.shape == (22, 2))
    ok.append(np.linalg.norm(traj[0] - np.array(obs["start"])) < 1e-6)
    ok.append(np.linalg.norm(traj[-1] - np.array(obs["goal"])) <= DEFAULTS["goal_tol"] + 1e-6)
    print("② 形状/起点/终点 →", a["ok"], a["reasons"])

    ok.append(a["ok"] and not a["reasons"])
    steps = np.linalg.norm(np.diff(traj, axis=0), axis=1)
    ok.append(float(steps.max()) <= DEFAULTS["max_step"] + 1e-6)
    print("③ 安全闸（碰撞/步长/边界/终点）→", a["ok"], f"max_step={steps.max():.3f}")

    bad = traj.copy()
    bad[5] = [3.0, 2.0]  # 撞障碍
    v = verify_trajectory(bad, np.array(obs["start"]), np.array(obs["goal"]),
                          _obstacles(obs), _constraints(obs))
    ok.append(not v["ok"] and "collision" in v["reasons"])
    print("④ 注入碰撞 →", v)

    out = NullPolicy().sample(obs, horizon=12)
    ok.append(out["policy"] == "null" and len(out["trajectory"]) == 12)
    print("⑤ 直线基线 →", out["ok"], out["reasons"])

    called = {"n": 0}
    def fake(observation, horizon):
        called["n"] += 1
        return [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]]
    cp = CallablePolicy(fake, name="test-model")
    r = cp.sample(obs, horizon=3)
    ok.append(called["n"] == 1 and r["policy"] == "test-model" and r["actions"][0] == [1.0, 1.0])
    print("⑥ 可插拔学习策略 →", r["actions"])

    try:
        CallablePolicy(lambda o, h: [[0.0, 0.0]]).sample(obs)
        ok.append(False)
    except PolicyError:
        ok.append(True)
    print("⑦ 非法输出被拒 → PolicyError")

    import time
    t0 = time.time()
    for i in range(5):
        DiffusionPlanner(seed=i).sample(obs, horizon=16)
    dt = (time.time() - t0) / 5
    ok.append(dt < 0.25)
    print("⑧ 单次采样耗时 → %.1f ms" % (dt * 1000))

    ok.append(a["ok"] and "actions" in a and len(a["actions"]) == a["horizon"] - 1)
    print("⑨ 动作块输出 →", len(a["actions"]), "deltas")

    n = sum(bool(x) for x in ok)
    print(f"\n== 判定汇总：{n}/{len(ok)} ==")
    print(f"PASS {n}/{len(ok)}" if n == len(ok) else "FAIL")
    return n == len(ok)


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        obs = {
            "start": [0.0, 0.0],
            "goal": [6.0, 4.0],
            "obstacles": [{"x": 3.0, "y": 2.0, "r": 0.8},
                          {"x": 4.5, "y": 3.5, "r": 0.6}],
            "constraints": dict(DEFAULTS, bounds=(0.0, 8.0, 0.0, 6.0)),
        }
        out = plan_motion(obs, horizon=22)
        print(_ascii(obs, out["trajectory"]))
        print(json.dumps({k: out[k] for k in ("ok", "reasons", "policy", "horizon")},
                         ensure_ascii=False))
    else:
        raise SystemExit(0 if _selftest() else 1)
