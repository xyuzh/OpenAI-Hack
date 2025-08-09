import asyncio
import threading, queue, time, sys, select, concurrent.futures as fut
import uuid
from typing import Optional

from workflow.core.logger import usebase_logger as logger

from workflow.runner.runner import Runner

from modem.type.flow_type import ProcessFlowDataRequest

_MOCK_JOB_INPUT = """
### **Implement a Time-Blocking Web App, the Product Requirements are shown below:**
---

### 1. Core Calendar

| Aspect | Specification |
| --- | --- |
| **Granularity** | 10-minute blocks rendered as spreadsheet-like cells |
| **Views** | Day, Week, Month |
| **Scrolling** | Mouse-wheel scroll to reveal the full 24-hour grid in Day & Week views |
| **Persistence** | All events and tags saved to a database; survive view changes, page refreshes, and browser restarts |
| **Version Label** | Display TypeScript file’s last-modified date next to **Timeflow** in the top nav |

---

### 2. Time-Block Interaction

| Action | Behaviour |
| --- | --- |
| **Hover** | Subtle gray resize handles appear on top & bottom edges |
| **Resize (bottom)** | Stretch duration in 10-minute increments (e.g., 10 → 20 → 30 min) |
| **Resize/Migrate (top)** | Shift block start earlier or later |
| **Release** | Toast confirms new duration |
| **Inline Edit** | Double-click a block to edit title directly in cell |
| **Create Block** | Double-click empty cell **or** drag-select a range; single clicks do nothing |
| **Copy / Paste** | Ctrl + C / Ctrl + V for one or multiple blocks |
| **Drag-and-Drop** | Move blocks freely within the grid with conflict detection toast if overlap occurs |
| **Underlying Grid** | 10-min cell lines remain visible even when a block spans multiples of them |

---

### 3. Editing & Metadata

- **Modal Editor**: Optional detailed form (title, notes, category)
- **Custom Categories & Tags**
    - `#` autocompletion with arrow-keys, Tab/Enter, or mouse click
    - Each tag carries a color; tagged blocks inherit that color
    - Tag-management page to add / rename / delete tags
- **Templates**: Save reusable presets (e.g., *Work, Relax, Sleep, Friends*) for quick insertion

---

### 4. Analytics

- **Quick Stats Sidebar**: Live pie charts of time spent per category

---

### 5. Utility Controls

- **Clear-All Button**: Purge all stored data after confirmation
- **Bug-Fix Expectations**:
    - No ghost blocks on single click
    - Correct block length after editing
    - Events visible consistently across Day / Week / Month views

---

**Goal**: Deliver a fast, elegant web app that lets productivity-minded users plan their day in 10-minute detail, adjust schedules with Excel-like ease, and gain actionable insights into how they spend their most valuable resource—time.

### Year View

Implement a Year view, its similar to the standard year view but has some very special new features:

the year view should include each month as a row, which means the year view has 12 rows, each rows for one month, from Jan to Dec.

for each row of a month, they all have columns for each day of the month.

for each row of a month, should have sub rows from 12 am to 11:59pm, 10 mins per time slot, with the events filled in, with title with the color of the category.

On year view, each row of the month should have the same timestamp as the day view, and each day on the year view (i.e. the column on the row of that month) should sync all time block from the day view on that day.

### Week View

Each day on week view should display all time block synced from the day view on that day.

### Create Time Block Event

The default behavior when user double click to create new time block should be entering inline editing mode with 10-minute blocks. Please fix.

When creating new event, user should be able to click-and-drag to create events for that time range.

When user input #, it should trigger the category selection menu. The selection menu should display all categories with a color icon for the user to preview the color of each category, and use the actual category color as the background when an item is selected. Tab will switch items, enter should pick the current one.

When user create a new event, if user has not entered any information, the event should be discarded instead of saving it because user has not input any valuable information.

### Category

Implement a category management feature. It allows user to add/edit category's name, color (in RGB or color hex code, with color plate preview).

Update Categories to have default categories for every user right after their login, as the below list (with color):

Brainstom,FFAAD2 Career,FFB3EF Work,BFB8FA Sleep,A1D9FC Life,B9E4F3 Study,BFF76F Date,E6FF9B Social,F4FFB9 Relax,FFFF85 Ops,FFFEEE Logging,F0FCF0

### Analysis

The analysis pie chart should represents the percetage of each category given the selected date range. The color of each pie slice should be the same as the category color. The text to label the pie chart should all be black. 

### Import/Export

Add an import/export feature to load data from csv file or other platforms export.
"""
class EventController:
    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.user_input_queue = queue.Queue()
        self.job_output_queue = queue.Queue()
        self.runner_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()

    def start_runner_thread(self):
        self.runner_thread = threading.Thread(
            name='runner_thread',
            target=Runner.run_local,
            args=(self.user_input_queue, self.job_output_queue, self.shutdown_event),
        )
        self.runner_thread.start()

    def process_input(self):
        job_id = None
        # job_id = uuid.UUID('381474f912bd4a8e935b5ad0d0a0eb68')  # TODO(SET_JOB_ID): set job id to reuse the same job id to start with checkpoint
        job_id = uuid.uuid4() if not job_id else job_id
        user_uuid = 'local_user'

        try:
            while True:
                # 1️⃣ Non‑blocking read from stdin
                ready, *_ = select.select([sys.stdin], [], [], 0)
                if ready:
                    line = sys.stdin.readline().rstrip()
                    if not line:
                        continue
                    if line.lower() in {"quit", "exit"}:
                        break
                    elif line.lower() == 'stop':
                        user_request = ProcessFlowDataRequest(
                            flow_uuid=job_id.hex,
                            flow_input_uuid=uuid.uuid4().hex,
                            user_uuid=user_uuid,
                            context_data=[
                                {
                                    'content': "stop",
                                    'role': 'user',
                                }
                            ],
                        )
                    elif line == "mock":
                        user_request = ProcessFlowDataRequest(
                            user_uuid=user_uuid,
                            context_data=[
                                {
                                    'content': [
                                        {
                                            "type": "text",
                                            "text": _MOCK_JOB_INPUT,
                                        }, 
                                    ],
                                    'role': 'user',
                                }
                            ],
                            flow_uuid=job_id.hex,  # reuse the same job id to start with checkpoint
                            flow_input_uuid=uuid.uuid4().hex,
                        )
                    else:
                        user_request = ProcessFlowDataRequest(
                            flow_uuid=job_id.hex,
                            flow_input_uuid=uuid.uuid4().hex,
                            user_uuid=user_uuid,
                            context_data=[
                                {
                                    'content': line,
                                    'role': 'user',
                                }
                            ],
                        )
                    self.user_input_queue.put(user_request)  # hand to worker

                # 2️⃣ Drain any completed results
                try:
                    while True:
                        result = self.job_output_queue.get_nowait()
                        print("Awaiting user input:", result)
                        self.job_output_queue.task_done()
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.error(f"Error in process_input: {e}")

                # 3️⃣ House‑keeping delay (keeps CPU usage low)
                time.sleep(1)

        finally:
            # clean shutdown sequence
            self.shutdown_event.set()
            self.user_input_queue.put(None)  # unblock worker if it’s waiting
            if self.runner_thread:
                self.runner_thread.join()

    def run_controller(self):
        logger.info(
            'User guide: \n\t1. Type "quit" or "exit" to exit, "stop" to stop the current job \n\t2. Type "mock" to run a mock job \n\t3. Input a request to run a job'
        )
        self.start_runner_thread()
        self.process_input()
