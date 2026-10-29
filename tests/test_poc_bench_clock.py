"""The overhead benchmark measures CPU time, not wall-clock time.

The machine this runs on is shared and never idle, and wall-clock time charges
every moment the measuring thread waited for a core to the boundary: builds on a
loaded machine read 343µs and 83µs for a crossing that costs ~25µs on a quiet
one. Calls into a component run in the calling thread, so they are timed in that
thread's CPU time; compilation runs on wasmtime's worker threads, so it is timed
in the whole process's. A silent revert to `perf_counter` would bring the
inflation back with every test still green, which is what this pins.
"""

import time

import pytest

from poc.sandbox import available, bench


def test_calls_are_timed_in_the_measuring_threads_cpu_time():
    assert bench._time.__defaults__ == (time.thread_time,)


def test_a_timing_reads_the_clock_it_is_given():
    readings = iter([0.0, 0.002] * bench._ROUNDS)
    ms = bench._time(lambda: None, repeats=2, clock=lambda: next(readings))
    assert ms == pytest.approx(1.0)  # 2ms over 2 calls


@pytest.mark.skipif(not available(), reason="needs wasmtime and the built components")
def test_compilation_alone_is_timed_in_process_cpu_time(monkeypatch):
    clocks = []

    def recording(fn, repeats, clock=time.thread_time):
        clocks.append(clock)
        return 0.0

    monkeypatch.setattr(bench, "_time", recording)
    bench.measure(repeats=1)
    assert clocks[0] is time.process_time  # compilation is timed first
    assert all(clock is time.thread_time for clock in clocks[1:])
