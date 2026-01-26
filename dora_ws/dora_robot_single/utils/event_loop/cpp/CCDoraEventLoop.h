/**
 * @file CCDoraEventLoop.h
 * @brief CC Dora-rs事件循环框架 - 简化节点事件处理
 *        CC Dora-rs Event Loop Framework - Simplify node event handling
 *
 * @author Claude
 * @date 2025-08-21
 * @version 1.1.0
 */

#ifndef CC_DORA_EVENT_LOOP_H_
#define CC_DORA_EVENT_LOOP_H_

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <future>
#include <iostream>
#include <list>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <queue>
#include <shared_mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

#include "dora-node-api.h"

namespace cc_dora
{

/**
 * @brief 输出消息数据结构
 *        Output message data structure
 */
struct OutputMessage
{
  std::string output_id;
  std::vector<uint8_t> data;
  OutputMessage () {}
  OutputMessage (const std::string &id, const std::vector<uint8_t> &d)
      : output_id (id), data (d)
  {
  }
};

/**
 * @brief 事件处理器基类模板
 *        Base event handler template
 */
template <class> class EventHandler;
template <class> class Event;

/**
 * @brief 事件处理器模板特化
 *        Event handler template specialization
 */
template <typename... Args> class EventHandler<void (Args...)>
{
  friend Event<void (Args...)>;

private:
  // 类型定义 / Type definitions
  typename Event<void (Args...)>::ListIterator _iterator;

  // 静态成员 / Static members
  static uint64_t LastID;

  // 属性 / Properties
  uint64_t ID;
  std::function<void (Args...)> handler;

  // 函数 / Functions
  void
  _copy (const EventHandler &ref)
  {
    if (&ref != this)
      {
        _iterator = ref._iterator;
        handler = ref.handler;
        ID = ref.ID;
      }
  }

public:
  // 类型定义 / Type definitions
  typedef void (*CFunctionPointer) (Args...);

  // 函数 / Functions
  EventHandler (std::function<void (Args...)> h)
      : _iterator (), handler (h), ID (++LastID)
  {
  }

  EventHandler (const EventHandler &ref) { _copy (ref); }

  virtual ~EventHandler () {}

  EventHandler &
  operator= (const EventHandler &ref)
  {
    _copy (ref);
    return *this;
  }

  void
  operator() (Args... args) const
  {
    handler (args...);
  }

  bool
  operator== (const EventHandler &ref)
  {
    return ID == ref.ID;
  }

  bool
  operator!= (const EventHandler &ref)
  {
    return ID != ref.ID;
  }

  uint64_t
  getID ()
  {
    return ID;
  }
};

template <typename... Args> uint64_t EventHandler<void (Args...)>::LastID = 0;

/**
 * @brief 事件类模板特化
 *        Event class template specialization
 */
template <typename... Args> class Event<void (Args...)>
{
  friend EventHandler<void (Args...)>;

private:
  // 类型定义 / Type definitions
  typedef
      typename std::list<EventHandler<void (Args...)>>::iterator ListIterator;

public:
  // 属性 / Properties
  std::list<EventHandler<void (Args...)>> handlers;

  // 函数 / Functions
  void
  _copy (const Event &ref)
  {
    if (&ref != this)
      {
        handlers = ref.handlers;
      }
  }

  bool
  removeHandler (ListIterator handlerIter)
  {
    if (handlerIter == handlers.end ())
      {
        return false;
      }

    handlers.erase (handlerIter);
    return true;
  }

public:
  // 属性 / Properties
  bool enabled;

  // 函数 / Functions
  Event () : enabled (true) {}

  virtual ~Event () {}

  Event (const Event &ref) { _copy (ref); }

  void
  call (Args... args)
  {
    if (!enabled)
      {
        return;
      }
    for (auto h = handlers.begin (); h != handlers.end (); h++)
      {
        (*h) (args...);
      }
  }

  EventHandler<void (Args...)>
  registerHandler (EventHandler<void (Args...)> handler)
  {
    bool found = false;
    for (auto h = handlers.begin (); h != handlers.end (); h++)
      {
        if ((*h) == handler)
          {
            found = true;
            break;
          }
      }
    if (!found)
      {
        ListIterator itr = handlers.insert (handlers.end (), handler);
        handler._iterator = itr;
      }
    return handler;
  }

  EventHandler<void (Args...)>
  registerHandler (std::function<void (Args...)> handler)
  {
    EventHandler<void (Args...)> wrapper (handler);
    ListIterator itr = handlers.insert (handlers.end (), wrapper);
    wrapper._iterator = itr;
    return wrapper;
  }

  bool
  removeHandler (EventHandler<void (Args...)> &handler)
  {
    bool sts = removeHandler (handler._iterator);
    handler._iterator = handlers.end ();
    return sts;
  }

  void
  clear ()
  {
    for (auto h = handlers.begin (); h != handlers.end (); h++)
      {
        (*h)._iterator = handlers.end ();
      }
    handlers.clear ();
  }

  void
  operator() (Args... args)
  {
    return call (args...);
  }
  EventHandler<void (Args...)>
  operator+= (EventHandler<void (Args...)> handler)
  {
    return registerHandler (handler);
  }
  EventHandler<void (Args...)>
  operator+= (std::function<void (Args...)> handler)
  {
    return registerHandler (handler);
  }
  bool
  operator-= (EventHandler<void (Args...)> &handler)
  {
    return removeHandler (handler);
  }
};

/**
 * @brief 输入事件数据结构
 *        Input event data structure
 */
struct InputEvent
{
  std::string id;
  std::vector<uint8_t> data;

  /**
   * @brief 从DoraInput构造InputEvent
   *        Construct InputEvent from DoraInput
   *
   * @param input DoraInput对象
   * @return InputEvent 构造的InputEvent对象
   */
  static InputEvent
  fromDoraInput (DoraInput input)
  {
    InputEvent event;
    event.id = std::string (input.id);
    event.data = std::vector<uint8_t> (
        input.data.data (), input.data.data () + input.data.size ());
    return event;
  }
};

/**
 * @brief 定时器事件数据结构
 *        Timer event data structure
 */
struct TimerEvent
{
  std::string id;
  std::chrono::milliseconds interval;
  std::chrono::steady_clock::time_point lastTrigger;
  bool repeat;
};

/**
 * @brief 线程池
 *        Thread Pool
 */
class ThreadPool
{
public:
  explicit ThreadPool (size_t num_threads);
  ~ThreadPool ();

  // 提交任务，返回 future
  // 使用C++17，支持函数、Lambda表达式、std::function、成员函数指针、成员变量指针
  template <typename F, typename... Args>
  auto submit (F &&f, Args &&...args)
      -> std::future<std::invoke_result_t<F, Args...>>;

  // 等待所有任务执行完毕
  void wait_done ();

  // 终止线程池
  void shutdown ();

private:
  void worker_loop ();

  std::vector<std::thread> workers;         // 线程池的部分
  std::queue<std::function<void ()>> tasks; // 任务队列

  std::mutex queue_mutex;            // 互斥锁
  std::condition_variable condition; // 条件变量

  std::atomic<bool> stop{ false };    // 原子的关闭标志位
  std::atomic<int> active_tasks{ 0 }; // 原子的活跃任务数量
};

// 构造函数
inline ThreadPool::ThreadPool (size_t num_threads)
{
  for (size_t i = 0; i < num_threads; ++i)
    workers.emplace_back (&ThreadPool::worker_loop, this);
}

// 工作线程主循环
inline void
ThreadPool::worker_loop ()
{
  while (true)
    {
      std::function<void ()> task;

      {
        std::unique_lock lock (queue_mutex);
        // 处理虚假唤醒
        condition.wait (lock, [this] {
          return stop
                 || !tasks
                         .empty (); // 如果stop为空，或者任务队列为空，线程等待
        });

        if (stop && tasks.empty ())
          return; // 如果线程池要求stop，而且没有需要执行的任务，安全退出
        // 取任务
        task = std::move (tasks.front ());
        tasks.pop ();
        ++active_tasks;
      }
      // 执行
      task ();
      --active_tasks;
    }
}

// 提交任务
template <typename F, typename... Args>
auto
ThreadPool::submit (F &&f, Args &&...args)
    -> std::future<std::invoke_result_t<F, Args...>>
{
  // 返回值类型推导
  using ReturnType = std::invoke_result_t<F, Args...>;
  // 任务封装
  auto task_ptr = std::make_shared<std::packaged_task<ReturnType ()>> (
      std::bind (std::forward<F> (f), std::forward<Args> (args)...));
  // 获取结果
  std::future<ReturnType> result = task_ptr->get_future ();

  {                                      // 临界区中将任务加入队列：
    std::scoped_lock lock (queue_mutex); // C++17 的统一锁
    if (stop)
      { // 如果已经要关闭线程池了，就停止提交新任务了
        throw std::runtime_error ("Cannot submit to stopped ThreadPool");
      }
    tasks.emplace ([task_ptr] () {
      std::invoke (*task_ptr); // std::invoke() 是 C++17 的万能函数调用器
    });
  }

  condition.notify_one (); // 唤醒工作线程
  return result;
}

// 等待所有任务完成
inline void
ThreadPool::wait_done ()
{
  while (true)
    {
      if (tasks.empty () && active_tasks.load () == 0)
        break;
      std::this_thread::sleep_for (
          std::chrono::milliseconds (1)); // 睡眠 1 毫秒
    }
}

// 关闭线程池
inline void
ThreadPool::shutdown ()
{
  {
    std::scoped_lock lock (queue_mutex);
    stop = true;
  }
  condition.notify_all ();

  for (auto &thread : workers)
    if (thread.joinable ())
      thread.join ();
}

// 析构函数
inline ThreadPool::~ThreadPool () { shutdown (); }

/**
 * @brief CC Dora事件循环类
 *        CC Dora event loop class
 */
class EventLoop
{
public:
  /**
   * @brief 构造函数
   *        Constructor
   *
   * @param nodeName 节点名称，用于日志输出
   * @param useHandlerThreadpool 是否使用处理器线程池
   * @param maxHandlerWorkers 处理器线程池最大线程数
   */
  EventLoop (const std::string &nodeName = "cc_dora_node",
             bool useHandlerThreadpool = true, size_t maxHandlerWorkers = 4)
      : node_name_ (nodeName), running_ (false), in_event_loop_ (false),
        use_handler_threadpool_ (useHandlerThreadpool),
        max_handler_workers_ (maxHandlerWorkers), timer_thread_ (nullptr),
        handler_threadpool_ (nullptr)
  {
    // 初始化事件 / Initialize events
    initialize_events ();

    // 记录主线程ID / Record main thread ID
    main_thread_id_ = std::this_thread::get_id ();
  }

  /**
   * @brief 析构函数
   *        Destructor
   */
  ~EventLoop ()
  {
    // 停止事件循环 / Stop event loop
    running_ = false;

    // 等待线程结束 / Wait for thread to end
    if (timer_thread_ && timer_thread_->joinable ())
      {
        timer_thread_->join ();
      }

    // 清理资源 / Cleanup resources
    timer_thread_.reset ();
    handler_threadpool_.reset ();
  }

private:
  /**
   * @brief 初始化事件
   *        Initialize events
   */
  void
  initialize_events ()
  {
    // 默认输入事件处理器
    // Default input event handler
    on_input_.registerHandler ([this] (const InputEvent &event) {
      // std::cout << "[" << node_name_ << "] 收到输入事件 / Received input
      // event from: "
      //           << event.id << ", size: " << event.data.size() << " bytes"
      //           << std::endl;
      ;
    });

    // 默认停止事件处理器
    // Default stop event handler
    on_stop_.registerHandler ([this] () {
      std::cout << "[" << node_name_ << "] 收到停止事件 / Received stop event"
                << std::endl;
    });

    // 默认所有输入关闭事件处理器
    // Default all inputs closed event handler
    on_all_inputs_closed_.registerHandler ([this] () {
      std::cout << "[" << node_name_ << "] 所有输入已关闭 / All inputs closed"
                << std::endl;
    });

    // 默认未知事件处理器
    // Default unknown event handler
    on_unknown_.registerHandler ([this] (int type) {
      std::cerr << "[" << node_name_
                << "] 未知事件类型 / Unknown event type: " << type
                << std::endl;
    });
  }

public:
  /**
   * @brief 注册输入事件处理器
   *        Register input event handler
   *
   * @param id 输入ID
   * @param handler 处理函数
   */
  void
  register_input_handler (const std::string &id,
                          std::function<void (const InputEvent &)> handler)
  {
    input_handlers_[id] = handler;
  }

  /**
   * @brief 注册定时器事件
   *        Register timer event
   *
   * @param id 定时器ID
   * @param interval 时间间隔（毫秒）
   * @param handler 处理函数
   * @param repeat 是否重复
   */
  void
  register_timer (const std::string &id, std::chrono::milliseconds interval,
                  std::function<void ()> handler, bool repeat = true)
  {
    TimerEvent timer;
    timer.id = id;
    timer.interval = interval;
    timer.lastTrigger = std::chrono::steady_clock::now ();
    timer.repeat = repeat;

    timers_[id] = timer;
    timerHandlers_[id] = handler;
  }

  /**
   * @brief 取消定时器
   *        Cancel timer
   *
   * @param id 定时器ID
   */
  bool
  cancel_timer (const std::string &id)
  {
    std::lock_guard<std::mutex> lock (timer_mutex_);
    auto it = timers_.find (id);
    if (it != timers_.end ())
      {
        timers_.erase (id);
        timerHandlers_.erase (id);
        return true;
      }
    return false;
  }

  /**
   * @brief 时器线程函数
   *        Timer thread function
   */
  void
  timer_thread_func ()
  {
    while (running_)
      {
        auto now = std::chrono::steady_clock::now ();

        {
          std::lock_guard<std::mutex> lock (timer_mutex_);

          // 复制定时器字典，避免在迭代过程中修改
          // Copy timer dict to avoid modification during iteration
          auto timersCopy = timers_;

          for (const auto &timerPair : timersCopy)
            {
              auto &timer = timerPair.second;
              auto elapsed
                  = std::chrono::duration_cast<std::chrono::milliseconds> (
                      now - timer.lastTrigger);

              if (elapsed >= timer.interval)
                {
                  // 触发定时器事件 / Trigger timer event
                  auto handlerIt = timerHandlers_.find (timer.id);
                  if (handlerIt != timerHandlers_.end ())
                    {
                      try
                        {
                          handlerIt->second ();
                        }
                      catch (const std::exception &e)
                        {
                          std::cerr
                              << "[" << node_name_
                              << "] 定时器回调出错 / Timer callback error: "
                              << e.what () << std::endl;
                        }
                    }

                  // 检查定时器是否仍然存在 / Check if timer still exists
                  auto currentTimerIt = timers_.find (timer.id);
                  if (currentTimerIt != timers_.end ())
                    {
                      if (timer.repeat)
                        {
                          // 更新上次触发时间 / Update last trigger time
                          currentTimerIt->second.lastTrigger = now;
                        }
                      else
                        {
                          // 移除非重复定时器 / Remove non-repeating timer
                          timers_.erase (timer.id);
                          timerHandlers_.erase (timer.id);
                        }
                    }
                }
            }
        }
      }
  }

private:
  /**
   * @brief 将输出消息放入队列
   *        Queue output message
   *
   * @param output_id 输出ID
   * @param data 输出数据
   */
  void
  queue_output (const std::string &output_id, const std::vector<uint8_t> &data)
  {
    std::lock_guard<std::mutex> lock (output_queue_mutex_);
    output_queue_.push (OutputMessage (output_id, data));
  }

  /**
   * @brief 发送输出
   *        Send output
   *
   * @param output_id 输出ID
   * @param data 输出数据
   */
  void
  send_output (const std::string &output_id, const std::vector<uint8_t> &data)
  {
    // 如果在主线程中且在事件循环内，直接发送
    // If in main thread and in event loop, send directly
    if (std::this_thread::get_id () == main_thread_id_ && in_event_loop_
        && node_)
      {
        direct_send_output (output_id, data);
      }
    else
      {
        // 否则，放入队列
        // Otherwise, queue the output
        queue_output (output_id, data);
      }
  }

  /**
   * @brief 直接发送输出（内部调用）
   *
   * @param output_id 输出ID
   * @param data 输出数据
   */
  void
  direct_send_output (const std::string &output_id,
                      const std::vector<uint8_t> &data)
  {
    if (!node_)
      {
        std::cerr << "[" << node_name_
                  << "] 节点未初始化 / Node not initialized" << std::endl;
        return;
      }

    std::lock_guard<std::mutex> lock (output_lock_);
    rust::Slice<const uint8_t> message_slice{
      reinterpret_cast<const uint8_t *> (data.data ()), data.size ()
    };
    auto result = ::send_output (node_->send_output, output_id.c_str (),
                                 message_slice);
    auto error = std::string (result.error);
    if (!error.empty ())
      {
        std::cerr << "[" << node_name_ << "] <<send message error"
                  << std::endl;
        return;
      }
  }

  /**
   * @brief 处理输出队列中的消息
   *        Process messages in the output queue
   */
  void
  process_output_queue ()
  {
    // 处理队列中的所有消息 / Process all messages in the queue
    while (true)
      {
        OutputMessage message;
        {
          std::lock_guard<std::mutex> lock (output_queue_mutex_);
          if (output_queue_.empty ())
            {
              break;
            }
          OutputMessage message = output_queue_.front ();
          output_queue_.pop ();
        }

        try
          {
            // 发送消息 / Send the message
            // C/C++ 消息不带元数据
            direct_send_output (message.output_id, message.data);
          }
        catch (const std::exception &e)
          {
            std::cerr
                << "[" << node_name_
                << "] 处理输出消息出错 / Error processing output message: "
                << e.what () << std::endl;
          }
      }
  }

  /**
   * @brief 强制处理队列中的所有输出消息
   *        Force processing of all output messages in the queue
   */
  void
  flush_output_queue ()
  {
    if (std::this_thread::get_id () == main_thread_id_ && in_event_loop_)
      {
        process_output_queue ();
      }
    else
      {
        std::cerr << "[" << node_name_
                  << "] 只能在主事件循环线程中刷新输出队列 / Can only flush "
                     "output queue in main event loop thread"
                  << std::endl;
      }
  }

  /**
   * @brief 在线程池中运行处理器
   *        Run handler in thread pool
   *
   * @param handler 处理器函数
   * @param event 输入事件
   */
  void
  run_input_handler_in_threadpool (
      const std::function<void (const InputEvent &)> &handler,
      const InputEvent &event)
  {
    if (!handler_threadpool_)
      {
        std::cerr
            << "[" << node_name_
            << "] 处理器线程池未初始化 / Handler thread pool not initialized"
            << std::endl;
        return;
      }

    // 创建事件副本 / Create event copy
    InputEvent eventCopy = event;

    // 将处理器添加到线程池 / Add handler to thread pool
    auto future = handler_threadpool_->submit ([this, handler, eventCopy] () {
      try
        {
          handler (eventCopy);
        }
      catch (const std::exception &e)
        {
          std::cerr << "[" << node_name_
                    << "] 处理器线程出错 / Handler thread error: " << e.what ()
                    << std::endl;
        }
    });

    // 添加到活动处理器集合 / Add to active handlers set
    std::lock_guard<std::mutex> lock (handler_mutex_);
    active_handlers_.push_back (std::move (future));
  }

  /**
   * @brief 在线程池中运行事件的所有处理器
   *        Run all handlers of an event in thread pool
   *
   * @tparam Args 参数类型
   * @param event_obj 事件对象
   * @param args 传递给事件处理器的参数
   */
  template <typename... Args>
  void
  run_event_handlers_in_threadpool (Event<void (Args...)> &event_obj,
                                    Args... args)
  {
    if (!handler_threadpool_ || !event_obj.enabled)
      {
        return;
      }

    // 为每个处理器创建一个任务 / Create a task for each handler
    for (auto it = event_obj.handlers.begin ();
         it != event_obj.handlers.end (); ++it)
      {
        const auto &handler = *it;

        // 将处理器添加到线程池 / Add handler to thread pool
        auto future
            = handler_threadpool_->submit ([this, handler, args...] () {
                try
                  {
                    handler (args...);
                  }
                catch (const std::exception &e)
                  {
                    std::cerr << "[" << node_name_
                              << "] 处理器线程出错 / Handler thread error: "
                              << e.what () << std::endl;
                  }
              });

        // 添加到活动处理器集合 / Add to active handlers set
        std::lock_guard<std::mutex> lock (handler_mutex_);
        active_handlers_.push_back (std::move (future));
      }
  }

  /**
   * @brief 清理已完成的处理器
   *        Clean up completed handlers
   */
  void
  cleanup_completed_handlers ()
  {
    std::lock_guard<std::mutex> lock (handler_mutex_);
    std::cout << "[" << node_name_ << "] DEBUG: 进入 cleanup  " << std::endl;

    // 查找已完成的处理器 / Find completed handlers
    std::vector<decltype (active_handlers_)::iterator> completedHandlers;

    for (auto future = active_handlers_.begin ();
         future != active_handlers_.end (); ++future)
      {
        if (future->valid ()
            && future->wait_for (std::chrono::seconds (0))
                   == std::future_status::ready)
          {
            completedHandlers.push_back (future);
          }
      }
    // std::cout << "[" << node_name_ << "] DEBUG: find complete " <<
    // std::endl;

    // 移除已完成的处理器并检查异常 / Remove completed handlers and check for
    // exceptions
    if (!completedHandlers.empty ())
      {
        for (auto &future : completedHandlers)
          {
            try
              {
                future->get ();
                // std::cout << "[" << node_name_ << "] DEBUG:future->get (); "
                //           << std::endl;

                active_handlers_.erase (future);
                // std::cout << "[" << node_name_
                //           << "] DEBUG: active_handlers_.erase (future) "
                //           << std::endl;
              }
            catch (const std::exception &e)
              {
                std::cerr << "[" << node_name_
                          << "] 处理器线程出错 / Handler thread error: "
                          << e.what () << std::endl;
              }
          }
      }
    // std::cout << "[" << node_name_ << "] DEBUG: check out" << std::endl;
  }

public:
  /**
   * @brief 启动事件循环
   *        Start event loop
   */
  void
  run ()
  {
    // 初始化Dora节点
    // Initialize Dora node
    // 初始化Dora节点 / Initialize Dora node
    if (!node_)
      {
        node_ = std::make_unique<DoraNode> (init_dora_node ());
        std::cout << "[" << node_name_
                  << "] 节点初始化成功 / Node initialized successfully"
                  << std::endl;
      }

    running_ = true;
    in_event_loop_ = true; // 标记进入事件循环 / Mark entering event loop

    // 创建处理器线程池（如果需要）/ Create handler thread pool (if needed)
    if (use_handler_threadpool_ && !handler_threadpool_)
      {
        handler_threadpool_
            = std::make_unique<ThreadPool> (max_handler_workers_);
        std::cout << "[" << node_name_
                  << "] 节点使用线程池 / Node uses thread pool" << std::endl;
      }

    // 启动定时器线程 / Start timer thread
    if (!timer_thread_)
      {
        timer_thread_ = std::make_unique<std::thread> (
            &EventLoop::timer_thread_func, this);
      }

    try
      {
        // 事件循环 / Event loop
        while (running_)
          {

            // 处理队列中的输出消息 / Process output messages in the queue
            process_output_queue ();
            std::cout << "[" << node_name_ << "] DEBUG: 处理消息队列 "
                      << std::endl;

            // 清理已完成的处理器 / Clean up completed handlers
            cleanup_completed_handlers ();
            std::cout << "[" << node_name_ << "] DEBUG: 清理handlers "
                      << std::endl;

            // 处理Dora事件
            // Process Dora events
            auto event = node_->events->next ();
            auto ty = event_type (event);

            // 根据事件类型调用相应的事件 / Call the corresponding event based
            // on event type
            if (ty == DoraEventType::Input)
              {
                auto input = event_as_input (std::move (event));
                auto inputEvent = InputEvent::fromDoraInput (input);

                // 调用特定ID的处理器 / Call handler for specific ID
                auto it = input_handlers_.find (inputEvent.id);
                if (it != input_handlers_.end ())
                  {
                    if (use_handler_threadpool_)
                      {
                        // 在线程池中运行处理器 / Run handler in thread pool
                        // std::cout << "[" << node_name_
                        //           << "] DEBUG: 尝试在线程池中运行事件处理器
                        //           - "
                        //              "事件类型: "
                        //           << inputEvent.id << std::endl;
                        run_input_handler_in_threadpool (it->second,
                                                         inputEvent);
                      }
                    else
                      {
                        // 直接运行处理器 / Run handler directly
                        try
                          {
                            it->second (inputEvent);
                          }
                        catch (const std::exception &e)
                          {
                            std::cerr
                                << "[" << node_name_
                                << "] 输入处理器出错 / Input handler error: "
                                << e.what () << std::endl;
                          }
                      }
                  }
                else
                  {
                    // 调用通用输入事件 / Call generic input event
                    if (use_handler_threadpool_)
                      {
                        // 在线程池中运行处理器 / Run handler in thread pool
                        run_event_handlers_in_threadpool (on_input_,
                                                          inputEvent);
                      }
                    else
                      {
                        // 直接运行处理器 / Run handler directly
                        on_input_.call (inputEvent);
                      }
                  }
              }
            else if (ty == DoraEventType::Stop)
              {
                on_stop_ ();
                break;
              }
            else if (ty == DoraEventType::AllInputsClosed)
              {
                on_all_inputs_closed_ ();
                break;
              }
            else
              {
                on_unknown_ (static_cast<int> (ty));
                break;
              }
          }
      }
    catch (const std::exception &e)
      {
        std::cerr << "[" << node_name_
                  << "] 事件循环出错 / Event loop error: " << e.what ()
                  << std::endl;
      }

    // 停止事件循环 / Stop event loop
    in_event_loop_ = false;
    running_ = false;

    // 等待线程结束 / Wait for thread to end
    if (timer_thread_ && timer_thread_->joinable ())
      {
        timer_thread_->join ();
      }

    // 清理资源 / Cleanup resources
    timer_thread_.reset ();

    // 停止处理器线程池 / Stop handler thread pool
    if (handler_threadpool_)
      {
        handler_threadpool_.reset ();
      }

    std::cout << "[" << node_name_ << "] 事件循环结束 / Event loop ended"
              << std::endl;
  }

private:
  std::string node_name_; // 节点名称 / Node name
  std::unique_ptr<DoraNode> node_;
  bool running_;                    // 运行状态 / Running state
  std::atomic<bool> in_event_loop_; // 是否在事件循环中 / Whether in event loop
  std::thread::id main_thread_id_;  // 主线程ID / Main thread ID

  // 事件 / Events
  Event<void (InputEvent)> on_input_;
  Event<void ()> on_stop_;
  Event<void ()> on_all_inputs_closed_;
  Event<void (int)> on_unknown_;

  // 输入处理器映射 / Input handler mapping
  std::unordered_map<std::string, std::function<void (const InputEvent &)>>
      input_handlers_;

  // 定时器 / Timers
  std::unordered_map<std::string, TimerEvent> timers_;
  std::unordered_map<std::string, std::function<void ()>> timerHandlers_;
  std::mutex timer_mutex_;
  std::unique_ptr<std::thread> timer_thread_;

  // 输出队列 / Output queue
  std::queue<OutputMessage> output_queue_;
  std::mutex output_queue_mutex_;
  std::mutex output_lock_;

  // 处理器线程池 / Handler thread pool
  bool use_handler_threadpool_; // 是否使用处理器线程池 / Whether to use
                                // handler thread pool
  size_t max_handler_workers_;  // 处理器线程池最大线程数 / Maximum number of
                                // worker threads in the handler thread pool
  std::unique_ptr<ThreadPool>
      handler_threadpool_; // 处理器线程池 / Handler thread pool
  std::list<std::future<void>>
      active_handlers_;      // 活动处理器集合 / Active handlers set
  std::mutex handler_mutex_; // 处理器锁 / Handler lock
};

} // namespace cc_dora

#endif // CC_DORA_EVENT_LOOP_H_