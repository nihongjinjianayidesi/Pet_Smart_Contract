from __future__ import annotations

import argparse

from .demo import main as evidence_demo_main
from .orchestrator_demo import main as orchestrator_demo_main
from .pricing_demo import main as pricing_demo_main
from .compensation_demo import main as compensation_demo_main


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m petsc", add_help=True)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("pricing", help="运行模块2：自动报价演示（默认）")
    sub.add_parser("evidence", help="运行模块5：证据存证与哈希校验演示")
    sub.add_parser("orchestrator", help="运行模块3：自动履约结算演示（状态机+分段结算）")
    sub.add_parser("compensation", help="运行模块4：异常检测与智能赔付演示")
    return p


def main() -> None:
    p = _build_parser()
    args = p.parse_args()
    if args.cmd in (None, "pricing"):
        pricing_demo_main()
        return
    if args.cmd == "evidence":
        evidence_demo_main()
        return
    if args.cmd == "orchestrator":
        orchestrator_demo_main()
        return
    if args.cmd == "compensation":
        compensation_demo_main()
        return
    p.print_help()


if __name__ == "__main__":
    main()
