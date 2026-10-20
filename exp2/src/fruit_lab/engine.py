"""Four persistent jobs in multiprocessing.Pool; no animation or timed ordering.

Each role has its own worker and mailbox. Condition waits implement atomic
predicate checking; real counting semaphores reserve fruit/space, and a binary
semaphore admits one actor to the plate. The renderer acknowledges physical
contact, hand withdrawal, and arrival home. Animation duration never chooses
which role wins admission.
"""

from dataclasses import dataclass
import multiprocessing as mp
import os
from queue import Empty
import time

ROLES = ("father", "mother", "son", "daughter")
LABELS = ("爸爸", "妈妈", "儿子", "女儿")
FRUITS = (1, 2, 2, 1)
FRUIT_NAMES = {1: "apple", 2: "orange"}
REASONS = {0: "idle", 1: "active", 2: "space", 3: "apple", 4: "orange", 5: "mutex", 6: "paused"}
PAUSED, CREDITS, CLOSING, DRAINING, STEP_OWNER, EPOCH = range(6)


@dataclass
class Shared:
    condition: object
    pending: object
    active: object
    completed: object
    requested: object
    cancelled: object
    reasons: object
    pids: object
    slots: object
    reserved: object
    owner: object
    task_sequence: object
    event_sequence: object
    flags: object
    empty: object
    apples: object
    oranges: object
    mutex: object
    events: object
    mailboxes: tuple


_shared = None


def _initialize(shared):
    global _shared
    _shared = shared


def _emit(s, kind, index=None, **data):
    """Caller holds condition. Sequence numbers order cross-process events."""
    s.event_sequence.value += 1
    s.events.put(dict(seq=s.event_sequence.value, epoch=s.flags[EPOCH],
                      kind=kind, role=None if index is None else ROLES[index],
                      pid=os.getpid(), **data))


def _reason(s, index, reason):
    if s.reasons[index] != reason:
        s.reasons[index] = reason
        _emit(s, "state", index, reason=REASONS[reason])


def _resource(s, index):
    return s.empty if index < 2 else s.apples if FRUITS[index] == 1 else s.oranges


def _available_slot(s, index):
    target = 0 if index < 2 else FRUITS[index]
    # Preferred side is a display convention only. Both slots can hold either fruit.
    order = (1, 0) if index in (0, 3) else (0, 1)
    return next((slot for slot in order if s.slots[slot] == target and s.reserved[slot] < 0), None)


def _gate(s, index):
    return not s.flags[PAUSED] or s.flags[STEP_OWNER] == index


def _role_worker(index):
    s = _shared
    with s.condition:
        s.pids[index] = os.getpid()
        _emit(s, "online", index)
        s.condition.notify_all()
    current = None
    committed = False
    try:
        while True:
            with s.condition:
                while not s.flags[CLOSING]:
                    if not s.pending[index] or s.flags[DRAINING]:
                        _reason(s, index, 0)
                    else:
                        slot = _available_slot(s, index)
                        if slot is None:
                            _reason(s, index, 2 if index < 2 else 3 if FRUITS[index] == 1 else 4)
                        elif s.owner.value >= 0:
                            _reason(s, index, 5)
                        elif s.flags[PAUSED] and s.flags[CREDITS] == 0:
                            _reason(s, index, 6)
                        else:
                            if not _resource(s, index).acquire(False):
                                raise RuntimeError("Resource counter and semaphore disagree.")
                            if not s.mutex.acquire(False):
                                _resource(s, index).release()
                                raise RuntimeError("Plate owner and mutex disagree.")
                            s.owner.value = index
                            s.reserved[slot] = index
                            s.pending[index] -= 1
                            s.active[index] = 1
                            s.task_sequence.value += 1
                            current = s.task_sequence.value
                            committed = False
                            if s.flags[PAUSED]:
                                s.flags[CREDITS] -= 1
                                s.flags[STEP_OWNER] = index
                            _reason(s, index, 1)
                            _emit(s, "granted", index, task=current, slot=slot,
                                  fruit=FRUIT_NAMES[FRUITS[index]],
                                  operations=["P(empty)" if index < 2 else "P(apple)" if FRUITS[index] == 1 else "P(orange)", "P(mutex)"])
                            break
                    s.condition.wait()
                if s.flags[CLOSING]:
                    return
            for expected in ("commit", "release", "finished"):
                while True:
                    try:
                        task, command = s.mailboxes[index].get(timeout=0.1)
                    except Empty:
                        if s.flags[CLOSING]:
                            return
                        continue
                    if command == "stop":
                        return
                    if task != current or command != expected:
                        raise RuntimeError(f"Unexpected acknowledgment for {ROLES[index]}: {command}.")
                    break
                with s.condition:
                    while not s.flags[CLOSING] and not _gate(s, index):
                        # Finishing an already released return is permitted during a step.
                        if expected == "finished" and s.flags[CREDITS] > 0:
                            break
                        s.condition.wait()
                    if s.flags[CLOSING]:
                        return
                    if expected == "commit":
                        if s.owner.value != index or s.reserved[slot] != index:
                            raise RuntimeError("Contact without exclusive plate ownership.")
                        s.slots[slot] = FRUITS[index] if index < 2 else 0
                        if index < 2:
                            (s.apples if FRUITS[index] == 1 else s.oranges).release()
                        else:
                            s.empty.release()
                        committed = True
                        _emit(s, "committed", index, task=current, slot=slot,
                              fruit=FRUIT_NAMES[FRUITS[index]],
                              operations=["V(apple)" if index < 2 and FRUITS[index] == 1 else "V(orange)" if index < 2 else "V(empty)"])
                    elif expected == "release":
                        s.reserved[slot] = -1
                        s.owner.value = -1
                        s.mutex.release()
                        was_step = s.flags[STEP_OWNER] == index
                        if was_step:
                            s.flags[STEP_OWNER] = -1
                        _emit(s, "released", index, task=current, step=was_step, operations=["V(mutex)"])
                    else:
                        s.active[index] = 0
                        s.completed[index] += 1
                        _reason(s, index, 0)
                        _emit(s, "finished", index, task=current)
                        current = None
                    s.condition.notify_all()
    except BaseException as exc:
        with s.condition:
            _emit(s, "error", index, message=f"{type(exc).__name__}: {exc}")
            s.flags[CLOSING] = 1
            s.condition.notify_all()
        raise
    finally:
        with s.condition:
            if s.owner.value == index:
                if not committed:
                    _resource(s, index).release()
                s.reserved[slot] = -1
                s.owner.value = -1
                s.mutex.release()
            s.active[index] = 0
            s.condition.notify_all()


class ProcessLab:
    """Standard-library-only public API; all methods return without waiting for fruit."""

    def __init__(self):
        ctx = mp.get_context("spawn")
        array = lambda size: ctx.Array("i", [0] * size, lock=False)
        self.s = Shared(ctx.Condition(ctx.RLock()), array(4), array(4), array(4), array(4),
                        array(4), array(4), array(4), array(2),
                        ctx.Array("i", [-1, -1], lock=False), ctx.Value("i", -1, lock=False),
                        ctx.Value("i", 0, lock=False), ctx.Value("i", 0, lock=False),
                        ctx.Array("i", [0, 0, 0, 0, -1, 0], lock=False),
                        ctx.BoundedSemaphore(2), ctx.Semaphore(0), ctx.Semaphore(0),
                        ctx.BoundedSemaphore(1), ctx.Queue(), tuple(ctx.Queue() for _ in ROLES))
        self.pool = ctx.Pool(4, initializer=_initialize, initargs=(self.s,))
        self.jobs = [self.pool.apply_async(_role_worker, (index,)) for index in range(4)]
        self.closed = False
        self._event_buffer = {}
        self._next_event = 1

    @staticmethod
    def index(role):
        if role not in ROLES:
            raise ValueError(f"Choose a role from {', '.join(ROLES)}.")
        return ROLES.index(role)

    def _check(self):
        if self.closed or self.s.flags[CLOSING]:
            raise RuntimeError("The process lab is closed or a worker failed.")

    def submit(self, role, count=1):
        return self.submit_many(**{role: count})

    def submit_many(self, **counts):
        for role, count in counts.items():
            self.index(role)
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 10000:
                raise ValueError("Request counts must be integers between 1 and 10000.")
        s = self.s
        with s.condition:
            self._check()
            if s.flags[DRAINING]:
                raise RuntimeError("A reset is draining active trips; wait until it finishes.")
            if any(s.requested[self.index(role)] + count > 1_000_000_000 for role, count in counts.items()):
                raise ValueError("Too many accumulated requests; reset the experiment first.")
            for role, count in counts.items():
                index = self.index(role)
                s.pending[index] += count
                s.requested[index] += count
                _emit(s, "submitted", index, count=count)
            s.condition.notify_all()
        return self.snapshot()

    def cancel(self, role=None):
        indices = range(4) if role is None else (self.index(role),)
        with self.s.condition:
            self._check()
            for index in indices:
                count = self.s.pending[index]
                self.s.cancelled[index] += count
                self.s.pending[index] = 0
                _emit(self.s, "cancelled", index, count=count)
            self.s.condition.notify_all()
        return self.snapshot()

    def acknowledge(self, role, task, command):
        if command not in ("commit", "release", "finished"):
            raise ValueError("Unknown animation acknowledgment.")
        self._check()
        self.s.mailboxes[self.index(role)].put((task, command))

    def pause(self):
        with self.s.condition:
            self._check()
            self.s.flags[PAUSED] = 1
            self.s.flags[CREDITS] = 0
            self.s.flags[STEP_OWNER] = -1
            self.s.condition.notify_all()

    def resume(self):
        with self.s.condition:
            self._check()
            self.s.flags[PAUSED] = self.s.flags[CREDITS] = 0
            self.s.flags[STEP_OWNER] = -1
            self.s.condition.notify_all()

    def step(self):
        with self.s.condition:
            self._check()
            if self.s.flags[STEP_OWNER] >= 0 or self.s.flags[CREDITS]:
                raise RuntimeError("One step is already in progress or waiting for resources.")
            self.s.flags[PAUSED] = 1
            if self.s.owner.value >= 0:
                self.s.flags[STEP_OWNER] = self.s.owner.value
            else:
                self.s.flags[CREDITS] = 1
            self.s.condition.notify_all()

    def prepare_reset(self):
        with self.s.condition:
            self._check()
            self.cancel()
            self.s.flags[DRAINING] = 1
            self.s.flags[PAUSED] = self.s.flags[CREDITS] = 0
            self.s.flags[STEP_OWNER] = -1
            self.s.condition.notify_all()

    def reset(self):
        s = self.s
        with s.condition:
            self._check()
            if any(s.active) or s.owner.value >= 0:
                raise RuntimeError("Let all active trips finish before resetting.")
            for sem in (s.empty, s.apples, s.oranges):
                while sem.acquire(False):
                    pass
            s.empty.release()
            s.empty.release()
            for values in (s.pending, s.active, s.completed, s.requested, s.cancelled, s.reasons, s.slots):
                for i in range(len(values)):
                    values[i] = 0
            s.reserved[:] = [-1, -1]
            s.flags[PAUSED] = s.flags[CREDITS] = s.flags[DRAINING] = 0
            s.flags[STEP_OWNER] = -1
            s.flags[EPOCH] += 1
            _emit(s, "reset")
            s.condition.notify_all()
        return self.snapshot()

    def snapshot(self):
        s = self.s
        with s.condition:
            slots = [FRUIT_NAMES.get(value) for value in s.slots]
            return dict(epoch=s.flags[EPOCH], slots=slots,
                        reserved=[None if i < 0 else ROLES[i] for i in s.reserved],
                        owner=None if s.owner.value < 0 else ROLES[s.owner.value],
                        paused=bool(s.flags[PAUSED]), stepping=s.flags[STEP_OWNER] >= 0 or bool(s.flags[CREDITS]),
                        draining=bool(s.flags[DRAINING]),
                        roles={role: dict(pending=s.pending[i], active=bool(s.active[i]), completed=s.completed[i],
                                          requested=s.requested[i], cancelled=s.cancelled[i], reason=REASONS[s.reasons[i]],
                                          pid=s.pids[i]) for i, role in enumerate(ROLES)})

    def poll(self):
        while True:
            try:
                event = self.s.events.get_nowait()
            except Empty:
                break
            self._event_buffer[event["seq"]] = event
        result = []
        while self._next_event in self._event_buffer:
            result.append(self._event_buffer.pop(self._next_event))
            self._next_event += 1
        if not self.closed:
            for job in self.jobs:
                if job.ready():
                    job.get()  # Propagate real worker exceptions, never silently replace them.
                    if not self.s.flags[CLOSING]:
                        raise RuntimeError("A role worker exited unexpectedly.")
        return result

    def close(self):
        if self.closed:
            return
        with self.s.condition:
            self.s.flags[CLOSING] = 1
            self.s.condition.notify_all()
        for mailbox in self.s.mailboxes:
            mailbox.put((-1, "stop"))
        self.pool.close()
        deadline = time.monotonic() + 4
        while not all(job.ready() for job in self.jobs) and time.monotonic() < deadline:
            time.sleep(0.02)
        if not all(job.ready() for job in self.jobs):
            self.pool.terminate()
        self.pool.join()
        for queue in (*self.s.mailboxes, self.s.events):
            queue.close()
            queue.join_thread()
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
