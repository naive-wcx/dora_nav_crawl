"""
CC Dora-rs事件循环框架 - 简化节点事件处理
CC Dora-rs Event Loop Framework - Simplify node event handling

作者/Author: Claude
日期/Date: 2025-08-21
版本/Version: 1.0.0
"""

from dora import Node
import pyarrow as pa
import time
import threading
import concurrent.futures
from queue import Queue
from typing import Dict, Any, List, Callable, Optional, Union, TypeVar, Generic, Set
from dataclasses import dataclass
import logging

# 设置日志 / Setup logging
logging.basicConfig(
    level=logging.WARN,
    format='%(asctime)s [%(levelname)s]: %(message)s [%(filename)s:%(lineno)d]  [%(funcName)s]'
)
logger = logging.getLogger("cc_dora")


def cc_get_logger() -> logging.Logger:
    """
    获取cc_dora日志记录器，供外部使用
    Get cc_dora logger for external use

    Returns:
        logging.Logger: cc_dora日志记录器
    """
    return logger


# 类型定义 / Type definitions
T = TypeVar('T')


class Event(Generic[T]):
    """事件类，用于注册和触发事件处理器 / Event class for registering and triggering event handlers"""

    def __init__(self):
        """初始化事件 / Initialize event"""
        self.handlers: List[Callable[[T], None]] = []
        self.enabled = True

    def register_handler(self, handler: Callable[[T], None]) -> None:
        """
        注册事件处理器 / Register event handler

        Args:
            handler: 处理函数 / Handler function
        """
        if handler not in self.handlers:
            self.handlers.append(handler)

    def remove_handler(self, handler: Callable[[T], None]) -> bool:
        """
        移除事件处理器 / Remove event handler

        Args:
            handler: 处理函数 / Handler function

        Returns:
            bool: 是否成功移除 / Whether removal was successful
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            return True
        return False

    def clear(self) -> None:
        """清除所有处理器 / Clear all handlers"""
        self.handlers.clear()

    def call(self, *args: Any, **kwargs: Any) -> None:
        """
        调用所有处理器 / Call all handlers

        Args:
            *args: 位置参数 / Positional arguments
            **kwargs: 关键字参数 / Keyword arguments
        """
        if not self.enabled:
            return

        for handler in self.handlers:
            handler(*args, **kwargs)

    def __iadd__(self, handler: Callable[[T], None]) -> 'Event[T]':
        """
        使用 += 运算符注册处理器 / Register handler using += operator

        Args:
            handler: 处理函数 / Handler function

        Returns:
            Event: 事件对象 / Event object
        """
        self.register_handler(handler)
        return self

    def __isub__(self, handler: Callable[[T], None]) -> 'Event[T]':
        """
        使用 -= 运算符移除处理器 / Remove handler using -= operator

        Args:
            handler: 处理函数 / Handler function

        Returns:
            Event: 事件对象 / Event object
        """
        self.remove_handler(handler)
        return self


@dataclass
class InputEvent:
    """输入事件数据结构 / Input event data structure"""
    id: str
    data: bytes
    metadata: Optional[Dict] = None

    @classmethod
    def from_dora_event(cls, event: Dict[str, Any]) -> 'InputEvent':
        """
        从Dora事件创建InputEvent / Create InputEvent from Dora event

        Args:
            event: Dora事件 / Dora event

        Returns:
            InputEvent: 输入事件 / Input event
        """
        return cls(
            id=event["id"],
            # [0].as_py()
            data=pa.array([]) if event["id"] == 'tick' else event["value"],
            metadata=event["metadata"] if (
                not event["metadata"] == None) else None
        )


@dataclass
class TimerEvent:
    """定时器事件数据结构 / Timer event data structure"""
    id: str
    interval: float  # 毫秒 / milliseconds
    last_trigger: float  # 时间戳 / timestamp
    repeat: bool
    callback: Callable[[], None]


@dataclass
class OutputMessage:
    """输出消息数据结构 / Output message data structure"""
    output_id: str
    data: Union[bytes, List[int], pa.Array]
    metadata: Optional[dict] = None


class EventLoop:
    """CC Dora事件循环类 / CC Dora event loop class"""

    def __init__(self, node_name: str = "cc_dora_node",
                 use_handler_threadpool: bool = True, max_handler_workers: int = 4):
        """
        初始化事件循环 / Initialize event loop

        Args:
            node_name: 节点名称 / Node name
            use_handler_threadpool: 使用处理器线程池, 默认开启 / Whether to use handler thread pool
            max_handler_workers: 处理器线程池最大线程数 / Maximum number of worker threads in the handler thread pool
        """
        self.node_name = node_name
        self.node = None
        self.running = False
        self._in_event_loop = False
        # self._non_blocking_thread = None

        # 事件 / Events
        self.on_input = Event[InputEvent]()
        self.on_stop = Event[None]()
        self.on_all_inputs_closed = Event[None]()
        self.on_unknown = Event[int]()

        # 输入处理器映射 / Input handler mapping
        self.input_handlers: Dict[str, Callable[[InputEvent], None]] = {}

        # 定时器 / Timers
        self.timers: Dict[str, TimerEvent] = {}
        self.timer_thread = None
        self.timer_lock = threading.Lock()

        # 输出消息队列 / Output message queue
        self.output_queue = Queue()
        self.output_lock = threading.Lock()

        # 处理器线程池 / Handler thread pool
        self.use_handler_threadpool = use_handler_threadpool
        self.max_handler_workers = max_handler_workers
        self.handler_threadpool = None
        self.active_handlers: Set[concurrent.futures.Future] = set()
        self.handler_lock = threading.Lock()

        # 初始化事件 / Initialize events
        self._initialize_events()

    def _initialize_events(self) -> None:
        """初始化事件 / Initialize events"""
        # 默认输入事件处理器 / Default input event handler
        self.on_input.register_handler(lambda event:
                                       None
                                       # logger.info(f"[{self.node_name}] 收到输入事件 / Received input event from: {event.id}, size: {len(event.data)} bytes")

                                       )

        # 默认停止事件处理器 / Default stop event handler
        self.on_stop.register_handler(lambda:
                                      logger.info(
                                          f"[{self.node_name}] 收到停止事件 / Received stop event")
                                      )

        # 默认所有输入关闭事件处理器 / Default all inputs closed event handler
        self.on_all_inputs_closed.register_handler(lambda:
                                                   logger.info(
                                                       f"[{self.node_name}] 所有输入已关闭 / All inputs closed")
                                                   )

        # 默认未知事件处理器 / Default unknown event handler
        self.on_unknown.register_handler(lambda type_id:
                                         logger.error(
                                             f"[{self.node_name}] 未知事件类型 / Unknown event type: {type_id}")
                                         )

    def register_input_handler(self, input_id: str, handler: Callable[[InputEvent], None]) -> None:
        """
        注册输入事件处理器 / Register input event handler

        Args:
            input_id: 输入ID / Input ID
            handler: 处理函数 / Handler function
        """
        self.input_handlers[input_id] = handler

    def register_timer(self, timer_id: str, interval: float, callback: Callable[[], None], repeat: bool = True) -> None:
        """
        注册定时器 / Register timer

        Args:
            timer_id: 定时器ID / Timer ID
            interval: 时间间隔（毫秒） / Interval (milliseconds)
            callback: 回调函数 / Callback function
            repeat: 是否重复 / Whether to repeat
        """
        with self.timer_lock:
            self.timers[timer_id] = TimerEvent(
                id=timer_id,
                interval=interval,
                last_trigger=time.time_ns() / 10e6,
                repeat=repeat,
                callback=callback
            )

    def cancel_timer(self, timer_id: str) -> bool:
        """
        取消定时器 / Cancel timer

        Args:
            timer_id: 定时器ID / Timer ID

        Returns:
            bool: 是否成功取消 / Whether cancellation was successful
        """
        with self.timer_lock:
            if timer_id in self.timers:
                del self.timers[timer_id]
                return True
            return False

    def _timer_thread_func(self) -> None:
        """定时器线程函数 / Timer thread function"""
        while self.running:
            current_time = time.time_ns() / 10e6

            with self.timer_lock:
                # 复制定时器字典，避免在迭代过程中修改 / Copy timer dict to avoid modification during iteration
                timers_copy = self.timers.copy()

            # 处理定时器 / Process timers
            for timer_id, timer in timers_copy.items():
                if current_time - timer.last_trigger >= timer.interval:
                    # 触发定时器回调 / Trigger timer callback
                    try:
                        timer.callback()
                    except Exception as e:
                        logger.error(
                            f"[{self.node_name}] 定时器回调出错 / Timer callback error: {e}")

                    with self.timer_lock:
                        # 检查定时器是否仍然存在 / Check if timer still exists
                        if timer_id in self.timers:
                            if timer.repeat:
                                # 更新上次触发时间 / Update last trigger time
                                self.timers[timer_id].last_trigger = current_time
                            else:
                                # 移除非重复定时器 / Remove non-repeating timer
                                del self.timers[timer_id]

            # 睡眠一小段时间，避免CPU占用过高 / Sleep for a short time to avoid high CPU usage
            time.sleep(0.01)

    def queue_output(self, output_id: str, data: Union[bytes, List[int], pa.Array], metadata: Optional[dict] = None) -> None:
        """
        将输出消息放入队列，由主事件循环线程处理
        Queue output message to be processed by main event loop thread

        Args:
            output_id: 输出ID / Output ID
            data: 输出数据 / Output data
            metadata: 附加元数据 / Additional metadata
        """
        # 创建输出消息对象 / Create output message object
        message = OutputMessage(output_id=output_id,
                                data=data, metadata=metadata)

        # 将消息放入队列 / Put message into queue
        self.output_queue.put(message)
        logger.debug(
            f"[{self.node_name}] 输出消息已加入队列 / Output message queued: {output_id}")

    def send_output(self, output_id: str, data: Union[bytes, List[int], pa.Array], metadata: Optional[dict] = None) -> None:
        """
        发送输出 / Send output

        Args:
            output_id: 输出ID / Output ID
            data: 输出数据 / Output data
            metadata: 附加元数据 / Additional metadata
        """
        # 如果在主线程中且在事件循环内，直接发送 / If in main thread and in event loop, send directly
        if threading.current_thread() is threading.main_thread() and self._in_event_loop and self.node is not None:
            self._direct_send_output(output_id, data, metadata)
        else:
            # 否则，放入队列 / Otherwise, queue the output
            self.queue_output(output_id, data, metadata)

    def _direct_send_output(self, output_id: str, data: Union[bytes, List[int], pa.Array], metadata: Optional[dict] = None) -> None:
        """
        实际发送输出的内部方法 / Internal method to actually send output
        """
        if self.node is None:
            logger.error(f"[{self.node_name}] 节点未初始化 / Node not initialized")
            return

        # 转换数据为PyArrow数组 / Convert data to PyArrow array
        if isinstance(data, bytes) or isinstance(data, list):
            # 如果是字节或列表，转换为UInt8数组 / If bytes or list, convert to UInt8 array
            if isinstance(data, bytes):
                data_list = list(data)
            else:
                data_list = data
            arrow_array = pa.array(data_list, type=pa.uint8())
        else:
            # 已经是PyArrow数组 / Already a PyArrow array
            arrow_array = data

        # 发送输出 / Send output
        with self.output_lock:
            self.node.send_output(output_id, arrow_array, metadata)

    def _process_output_queue(self) -> None:
        """处理输出队列中的消息 / Process messages in the output queue"""
        # 处理队列中的所有消息 / Process all messages in the queue
        while not self.output_queue.empty():
            try:
                # 获取一条消息 / Get a message
                message = self.output_queue.get_nowait()

                # 发送消息 / Send the message
                self._direct_send_output(
                    message.output_id,
                    message.data,
                    message.metadata
                )

                # 标记任务完成 / Mark the task as done
                self.output_queue.task_done()
            except Exception as e:
                logger.error(
                    f"[{self.node_name}] 处理输出消息出错 / Error processing output message: {e}")

    def flush_output_queue(self) -> None:
        """
        强制处理队列中的所有输出消息 / Force processing of all output messages in the queue
        """
        if threading.current_thread() is threading.main_thread() and self._in_event_loop:
            self._process_output_queue()
        else:
            logger.warning(
                f"[{self.node_name}] 只能在主事件循环线程中刷新输出队列 / Can only flush output queue in main event loop thread")

    def _run_input_handler_in_threadpool(self, handler: Callable[[InputEvent], None], event: InputEvent) -> None:
        """
        在线程池中运行输入处理器 / Run handler in thread pool

        Args:
            handler: 处理器函数 / Handler function
            event: 输入事件 / Input event
        """
        if self.handler_threadpool is None:
            logger.error(
                f"[{self.node_name}] 处理器线程池未初始化 / Handler thread pool not initialized")
            return

        # 将处理器添加到线程池 / Add handler to thread pool
        future = self.handler_threadpool.submit(handler, event)

        # 添加到活动处理器集合 / Add to active handlers set
        with self.handler_lock:
            self.active_handlers.add(future)

        # 设置完成回调 / Set completion callback
        future.add_done_callback(self._handler_done_callback)

    def _run_event_handlers_in_threadpool(self, event_obj: Event, *args, **kwargs) -> None:
        """
        在线程池中运行事件的所有处理器 / Run all handlers of an event in thread pool

        Args:
            event_obj: 事件对象 / Event object
            *args, **kwargs: 传递给事件处理器的参数 / Arguments to pass to event handlers
        """
        if self.handler_threadpool is None or not event_obj.handlers:
            return

        # 为每个事件处理器创建一个Future / Create a Future for each event handler
        for handler in event_obj.handlers:
            if not event_obj.enabled:
                break

            # 将处理器添加到线程池 / Add handler to thread pool
            future = self.handler_threadpool.submit(handler, *args, **kwargs)

            # 添加到活动处理器集合 / Add to active handlers set
            with self.handler_lock:
                self.active_handlers.add(future)

            # 设置完成回调 / Set completion callback
            future.add_done_callback(self._handler_done_callback)

    def _handler_done_callback(self, future: concurrent.futures.Future) -> None:
        """
        处理器完成回调 / Handler completion callback

        Args:
            future: 处理器Future对象 / Handler Future object
        """
        # 从活动处理器集合中移除 / Remove from active handlers set
        with self.handler_lock:
            if future in self.active_handlers:
                self.active_handlers.remove(future)

        # 检查是否有异常 / Check for exceptions
        try:
            future.result()  # 获取结果，如果有异常会抛出 / Get result, will raise if there was an exception
        except Exception as e:
            logger.error(
                f"[{self.node_name}] 处理器线程出错 / Handler thread error: {e}")

    def _cleanup_completed_handlers(self) -> None:
        """清理已完成的处理器 / Clean up completed handlers"""
        with self.handler_lock:
            # 查找已完成的Future / Find completed futures
            completed = [f for f in self.active_handlers if f.done()]

            # 从集合中移除 / Remove from set
            for future in completed:
                self.active_handlers.remove(future)

                # 检查是否有异常 / Check for exceptions
                try:
                    future.result()  # 获取结果，如果有异常会抛出 / Get result, will raise if there was an exception
                except Exception as e:
                    logger.error(
                        f"[{self.node_name}] 处理器线程出错 / Handler thread error: {e}")

    def run(self) -> None:
        """运行事件循环 / Run event loop"""
        # 初始化Dora节点 / Initialize Dora node
        if self.node is None:
            self.node = Node()
            logger.info(
                f"[{self.node_name}] 节点初始化成功 / Node initialized successfully")

        self.running = True
        self._in_event_loop = True  # 标记进入事件循环 / Mark entering event loop

        # 创建处理器线程池（如果需要）/ Create handler thread pool (if needed)
        if self.use_handler_threadpool and self.handler_threadpool is None:
            self.handler_threadpool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_handler_workers,
                thread_name_prefix=f"{self.node_name}_handler")
            logger.info(
                f"[{self.node_name}] 节点使用线程池 / Node use thread pool")

        # 启动定时器线程 / Start timer thread
        if self.timer_thread is None:
            self.timer_thread = threading.Thread(
                target=self._timer_thread_func)
            self.timer_thread.daemon = True
            self.timer_thread.start()

        try:
            # 事件循环 / Event loop
            for event in self.node:
                # 处理队列中的输出消息 / Process output messages in the queue
                self._process_output_queue()

                # 清理已完成的处理器 / Clean up completed handlers
                self._cleanup_completed_handlers()

                event_type = event["type"]

                if event_type == "INPUT":
                    # 创建输入事件 / Create input event
                    input_event = InputEvent.from_dora_event(event)

                    # 调用特定ID的处理器 / Call handler for specific ID
                    if input_event.id in self.input_handlers:
                        if self.use_handler_threadpool:
                            # 在线程池中运行处理器 / Run handler in thread pool
                            self._run_input_handler_in_threadpool(
                                self.input_handlers[input_event.id], input_event)
                        else:
                            # 直接运行处理器 / Run handler directly
                            try:
                                self.input_handlers[input_event.id](
                                    input_event)
                            except Exception as e:
                                # 如果定位到这里出错，通常是你写的 handle 有问题
                                logger.error(
                                    f"[{self.node_name}] 输入处理器出错 / Input handler error: {e}")
                    else:
                        # 调用通用输入事件 / Call generic input event
                        if self.use_handler_threadpool:
                            # 在线程池中运行处理器 / Run handler in thread pool
                            self._run_event_handlers_in_threadpool(
                                self.on_input, input_event)
                        else:
                            # 直接运行处理器 / Run handler directly
                            self.on_input.call(input_event)

                elif event_type == "STOP":
                    # 调用停止事件 / Call stop event
                    self.on_stop.call()
                    break

                elif event_type == "INPUT_CLOSED":
                    # 调用所有输入关闭事件 / Call all inputs closed event
                    self.on_all_inputs_closed.call()
                    break

                else:
                    # 调用未知事件 / Call unknown event
                    self.on_unknown.call(event_type)
                    break

        except Exception as e:
            logger.error(
                f"[{self.node_name}] 事件循环出错 / Event loop error: {e}")

        finally:
            # 停止定时器线程 / Stop timer thread
            self._in_event_loop = False  # 标记退出事件循环 / Mark exiting event loop
            self.running = False
            if self.timer_thread is not None:
                self.timer_thread.join(timeout=1.0)

            # 停止处理器线程池 / Stop handler thread pool
            if self.handler_threadpool is not None:
                self.handler_threadpool.shutdown(wait=False)
                self.handler_threadpool = None

            logger.info(f"[{self.node_name}] 事件循环结束 / Event loop ended")
