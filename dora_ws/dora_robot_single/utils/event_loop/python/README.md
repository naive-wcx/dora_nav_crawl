# CC Dora-rs Event Loop Framework

A Python event loop framework for Dora-rs, simplifying node event handling.

## Features

- Event system for registering and triggering event handlers
- Input handler mapping for different input IDs
- Timer support with periodic and one-time timers
- Event loop encapsulation

## Installation

```bash
pip install -e .
```

## Usage

```python
from cc_dora_event_loop import EventLoop, InputEvent

# Create event loop
event_loop = EventLoop("my_node")

# Register input handler
event_loop.register_input_handler("some_input", lambda event: print(f"Received: {event.data}"))

# Register timer
event_loop.register_timer("heartbeat", 5.0, lambda: print("Heartbeat"))

# Run event loop
event_loop.run()
```
