"""Simple helpers for monitoring Yufuin Club booking availability."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # ドキュメント生成や型チェック時のみ直接インポートする
    from .__main__ import main as _main


def main(*args, **kwargs):
    """`python -m` 実行時の RuntimeWarning を避けるために遅延インポートする。"""
    from .__main__ import main as _main

    return _main(*args, **kwargs)


__all__ = ["main"]
