"""task_axiom.py —— 任务拆解公理（前置条件链，不枚举任务类型）。

对任意物理任务，先找「动词 + 对象 + 目的地」，再按**前置条件**展开：
  定位 → 接近 → 准备 → 执行 → 校验 → 交付/返回
只跳过上下文中已满足的前置条件；「校验」永远保留。
非物理任务（没有动词/对象）→ applicable=False，交回对话层。

这不是任务模板表：换动词只改“执行”步的标签，链条不变。
"""
from __future__ import annotations

import re
from typing import Any

_VERB_CLASS = (
    ("grasp", ("拿", "取", "抓", "捡", "拿起", "拿取", "夹")),
    ("place", ("放", "摆", "移到", "放进", "放到", "放入")),
    ("bring", ("递给", "交给", "送来", "拿来", "带回")),
    ("open", ("打开", "开启", "开")),
    ("close", ("关闭", "关上", "关")),
    ("clean", ("清理", "擦", "打扫", "洗", "拖")),
    ("inspect", ("检查", "巡检", "查看", "寻找", "找", "确认")),
    ("move", ("移动", "搬", "推", "拉", "挪")),
    ("use", ("拧紧", "拧", "旋紧", "安装", "装配", "插入", "按下", "敲")),
)
_ALL_VERBS = sorted({v for _, vs in _VERB_CLASS for v in vs}, key=len, reverse=True)
_VERB_RE = re.compile("|".join(map(re.escape, _ALL_VERBS)))
_PREP = re.compile(r"^(?:请|麻烦|帮我|给我|你)?\s*(?:把|将)?\s*")
_DEST = re.compile(r"^(?:到|进|回|往|向|在)\s*")


def _verb_class(verb: str) -> str:
    for cls, vs in _VERB_CLASS:
        if verb in vs:
            return cls
    return "act"


def _split_object(phrase: str) -> tuple[str, str]:
    """「桌上的杯子」→ (杯子, 桌上)；「杯子」→ (杯子, '')。"""
    phrase = (phrase or "").strip(" 的，。")
    if "的" in phrase:
        loc, obj = phrase.rsplit("的", 1)
        if loc and obj:
            return obj.strip(), loc.strip()
    return phrase, ""


def _strip_dest(text: str) -> str:
    t = (text or "").strip(" 的，。！？")
    t = _DEST.sub("", t)
    t = re.sub(r"(?:里|上|下|中|内|外|旁边|附近|边)$", "", t)
    return t.strip()


def decompose(task: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """返回结构化任务计划；不适用时 applicable=False。"""
    ctx = dict(ctx or {})
    raw = (task or "").strip()
    s = _PREP.sub("", raw)
    m = _VERB_RE.search(s)
    if not m:
        return {"task": raw, "applicable": False, "reason": "no_action_verb"}

    verb = m.group(0)
    before = s[:m.start()].strip()
    after = s[m.end():].strip()
    if before:
        obj_phrase = before
        dest_phrase = after
    else:
        # 动词在前：清理桌面 / 检查A区
        parts = re.split(r"[，,。；;]", after, maxsplit=1)
        obj_phrase = parts[0].strip()
        dest_phrase = parts[1].strip() if len(parts) > 1 else ""
        if not dest_phrase:
            dm = re.search(r"(?:到|进|往|向)(.+)$", obj_phrase)
            if dm:
                obj_phrase, dest_phrase = obj_phrase[:dm.start()], dm.group(1)

    obj, loc = _split_object(obj_phrase)
    dest = _strip_dest(dest_phrase)
    # 「拿过来/拿来/递给我」：目的地在近处，不是独立地点
    if re.search(r"(过来|过去|回来|拿来|给我|递给我|带回)$", raw):
        dest = "用户/交付点"
    if not obj:
        return {"task": raw, "applicable": False, "reason": "no_object"}

    # 检查类：拆出谓词（检查A区有没有人 → 对象 A区，谓词 有没有人）
    predicate = ""
    if _verb_class(verb) == "inspect":
        pm = re.search(r"(有没有|是否有|有无|是否)(.*)$", obj)
        if pm:
            predicate = (pm.group(1) + pm.group(2)).strip()
            obj = obj[:pm.start()].strip()

    # 复合任务：拿起螺丝刀拧紧螺丝 → 主对象 螺丝刀，后续动作 拧紧螺丝
    followups: list[str] = []
    vm = [mm for mm in _VERB_RE.finditer(obj) if mm.start() > 0]
    if vm:
        mm = vm[0]
        tail = obj[mm.start():].strip()
        obj = obj[:mm.start()].strip()
        if tail:
            followups.append(tail)

    cls = _verb_class(verb)
    known_pose = bool(ctx.get("target_pose_known") or ctx.get("target_pose")
                      or ctx.get("goal"))
    at_target = bool(ctx.get("at_target"))
    hand_free = ctx.get("hand_free", True)
    path_clear = ctx.get("path_clear", True)

    steps: list[dict[str, Any]] = []
    missing: list[str] = []

    def add(kind: str, label: str, **goal):
        steps.append({"id": len(steps) + 1, "kind": kind, "label": label,
                      "goal": goal, "status": "todo"})

    if not known_pose:
        add("locate", f"定位「{obj}」", object=obj, place=loc or "场景")
        missing.append(f"{obj}的位姿")
    if not at_target:
        add("approach", f"移动到可操作「{obj}」的位姿", object=obj, place=loc or "场景")
    if not hand_free or not path_clear:
        add("prepare", "清空夹爪/清理路径", hand_free=hand_free, path_clear=path_clear)
    add("act", _act_label(cls, verb, obj, dest), action=cls, verb=verb,
        object=obj, destination=dest or None)
    for fu in followups:
        add("act", f"继续执行「{fu}」", action="followup", detail=fu)
    add("verify", f"确认「{obj}」{('满足：' + predicate) if predicate else '状态符合预期'}",
        object=obj, expect=cls, predicate=predicate or None)
    if dest and (cls in ("place", "bring", "move") or dest == "用户/交付点"):
        add("deliver", f"把「{obj}」送到「{dest}」", object=obj, destination=dest)

    return {
        "task": raw,
        "applicable": True,
        "verb": verb,
        "action": cls,
        "object": obj,
        "place": loc,
        "destination": dest,
        "predicate": predicate or None,
        "followups": followups,
        "steps": steps,
        "missing": missing,
        "assumptions": [k for k in ("target_pose_known", "at_target", "hand_free",
                                    "path_clear") if ctx.get(k)],
    }


def _act_label(cls: str, verb: str, obj: str, dest: str) -> str:
    if cls == "grasp":
        return f"抓取「{obj}」"
    if cls == "place":
        return f"把「{obj}」放到「{dest or '目标位' }」"
    if cls == "bring":
        return f"把「{obj}」带回「{dest or '用户'}」"
    if cls == "open":
        return f"打开「{obj}」"
    if cls == "close":
        return f"关闭「{obj}」"
    if cls == "clean":
        return f"清理「{obj}」"
    if cls == "inspect":
        return f"检查「{obj}」"
    if cls == "use":
        return f"{verb}「{obj}」"
    if cls == "move":
        return f"移动「{obj}」到「{dest or '目标位'}」"
    return f"{verb}「{obj}」"


if __name__ == "__main__":
    cases = [
        "把桌上的杯子拿过来",
        "把杯子放到水槽里",
        "打开冰箱门",
        "清理桌面",
        "检查A区有没有人",
        "拿起螺丝刀拧紧螺丝",
        "什么是区块链",
    ]
    ok = 0
    for q in cases:
        p = decompose(q, {"target_pose_known": False})
        tag = "（非物理任务）" if q == "什么是区块链" else ""
        print(f"{q!r:22} → applicable={p['applicable']} "
              f"action={p.get('action')} obj={p.get('object')} dest={p.get('destination')} "
              f"steps={len(p.get('steps', []))}{tag}")
        if q == "什么是区块链":
            ok += (not p["applicable"])
        else:
            ok += (p["applicable"] and len(p["steps"]) >= 4)
    # 上下文已满足 → 跳过定位/接近
    p = decompose("把桌上的杯子拿过来", {"target_pose_known": True, "at_target": True})
    ok += (len(p["steps"]) == 3 and p["steps"][0]["kind"] == "act")  # act/deliver/verify
    print("上下文已满足 →", [x["kind"] for x in p["steps"]])
    # 目的地
    p = decompose("把杯子放到水槽里")
    ok += (p["action"] == "place" and p["steps"][-1]["kind"] == "deliver")
    print("带目的地 →", [x["kind"] for x in p["steps"]])
    print(f"\n== 判定汇总：{ok}/{len(cases) + 2} ==")
    print(f"PASS {ok}/{len(cases) + 2}" if ok == len(cases) + 2 else "FAIL")
