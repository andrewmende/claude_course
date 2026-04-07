Greet the learner and start a new session.

1. Ask for their name if not provided as $ARGUMENTS.
2. Derive learner_id: lowercase name, spaces replaced with underscores. Remember it for this session.
3. Call `get_current_task` with learner_id.
4. If they have completed tasks, acknowledge progress and ask if they want to continue or restart.
5. Tell the learner their session is ready and prompt them to use /task.
