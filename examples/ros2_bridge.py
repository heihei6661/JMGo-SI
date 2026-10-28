"""ROS 2 bridge template (optional dependency).

This file is intentionally dependency-light: it can be imported without ROS.
Install ROS 2 and `rclpy` to actually run it.

Topics
------
  /cognition/request   std_msgs/String   JSON {"query": str, "ctx": {...}}
  /cognition/decision  std_msgs/String   JSON {answer, verdict, actions, trace}

Design rule: the bridge publishes a **decision**, never joint commands. A
separate execution node (Nav2 / MoveIt / custom action) applies limits and the
emergency stop.
"""
from __future__ import annotations

import json
from typing import Any

from jmgo_cognition import load_core, run_loop

try:  # pragma: no cover - depends on the robot environment
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    _HAS_ROS = True
except Exception:  # noqa: BLE001
    _HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]
    String = object  # type: ignore[assignment,misc]


def decide(payload: str) -> dict[str, Any]:
    """Pure function: request JSON -> decision dict. Useful for tests."""
    data = json.loads(payload)
    query = str(data.get("query") or "").strip()
    if not query:
        return {"error": "empty query"}
    return run_loop(query, ctx=data.get("ctx") or {}, core=load_core())


class CognitionNode(Node):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__("jmgo_cognition")
        self.pub = self.create_publisher(String, "/cognition/decision", 10)
        self.create_subscription(String, "/cognition/request", self.on_request, 10)
        self.get_logger().info("jmg cognition bridge ready")

    def on_request(self, msg) -> None:
        try:
            result = decide(msg.data)
            out = {
                "answer": result.get("answer", {}).get("answer", ""),
                "status": result.get("answer", {}).get("status"),
                "verdict": result.get("verdict"),
                "actions": result.get("actions", []),
                "trace": result.get("trace", []),
            }
        except Exception as exc:  # noqa: BLE001
            out = {"error": f"{type(exc).__name__}: {exc}"}
        self.pub.publish(String(data=json.dumps(out, ensure_ascii=False)))


def main() -> int:
    if not _HAS_ROS:
        print("rclpy not found. Install ROS 2 and source /opt/ros/<distro>/setup.bash.")
        print("The pure function decide() can be tested without ROS.")
        return 0
    rclpy.init()
    node = CognitionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
