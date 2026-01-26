"""
CC Dora-rs事件循环框架包
CC Dora-rs Event Loop Framework Package

作者/Author: Claude
日期/Date: 2025-08-21
版本/Version: 1.0.0
"""

from .event_loop import (
    Event,
    InputEvent,
    TimerEvent,
    EventLoop,
    cc_get_logger
)

__version__ = '1.0.0'
__all__ = [
    'Event',
    'InputEvent',
    'TimerEvent',
    'EventLoop',
    'cc_get_logger'
]