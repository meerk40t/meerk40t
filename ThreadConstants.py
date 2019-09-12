
THREAD_STATE_UNSTARTED = 0
THREAD_STATE_STARTED = 1
THREAD_STATE_PAUSED = 2
THREAD_STATE_FINISHED = 3
THREAD_STATE_ABORT = 10


def get_state_string_from_state(state):
    if state == THREAD_STATE_UNSTARTED:
        return "Unstarted"
    elif state == THREAD_STATE_ABORT:
        return "Aborted"
    elif state == THREAD_STATE_FINISHED:
        return "Finished"
    elif state == THREAD_STATE_PAUSED:
        return "Paused"
    elif state == THREAD_STATE_STARTED:
        return "Started"

