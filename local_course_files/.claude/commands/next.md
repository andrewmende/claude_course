Move to the next task after passing.

1. Call `get_current_task` with learner_id — the server already advanced the task on pass.
2. If `all_done` is true: congratulate the learner on completing the course and end the session.
3. Otherwise: present the new task as if /task was run.
