"""Exercise the real GLFW window, hidden progress, input locks and cleanup."""

from pathlib import Path
import multiprocessing
import sys
import time


def main():
    sys.argv[:] = [sys.argv[0]]
    import glfw
    import numpy as np
    from manimlib.window import Window
    from .diagnostics import ERROR_LOG
    from .scene import FruitLabScene
    from .windowing import DEFAULT_CLIENT_SIZE, fitted_size

    for area in ((1920, 1080), (1280, 720), (800, 600)):
        size = fitted_size(*area, frame=(8, 31, 8, 8))
        assert size[0] * 9 == size[1] * 16
        assert size[0] + 16 < area[0] and size[1] + 39 < area[1]
    assert fitted_size(1920, 1080, frame=(8, 31, 8, 8)) == DEFAULT_CLIENT_SIZE

    window = Window(size=(640, 360), position=(80, 80))
    scene = None
    try:
        scene = FruitLabScene(window=window, skip_animations=True)
        scene.build_lab()
        scene.update_frame(1 / 30, force_draw=True)
        handle = window.glfw_window
        initial_size = glfw.get_window_size(handle)
        assert initial_size[0] * 9 == initial_size[1] * 16
        assert not glfw.get_window_attrib(handle, glfw.RESIZABLE)
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            get_style = ctypes.windll.user32.GetWindowLongW
            get_style.argtypes = (wintypes.HWND, ctypes.c_int)
            get_style.restype = ctypes.c_long
            style = get_style(glfw.get_win32_window(handle), -16)
            assert not style & (0x00040000 | 0x00010000)  # size box, maximize box
            assert style & 0x00020000 and style & 0x00080000  # minimize, system menu

        x, y = glfw.get_window_pos(handle)
        glfw.set_window_pos(handle, x + 8, y + 8)
        window.poll_events()
        assert glfw.get_window_pos(handle) == (x + 8, y + 8)
        assert glfw.get_window_size(handle) == initial_size

        view = scene.frame.get_view_matrix().copy()
        points = scene.frame.get_points().copy()
        window.pressed_keys.update((ord("d"), ord("f")))
        scene.on_mouse_motion(np.ones(3), np.ones(3))
        scene.on_mouse_drag(np.ones(3), np.ones(3), 1, 0)
        scene.on_mouse_scroll(np.zeros(3), np.ones(3), 0, 10)
        scene.on_key_press(ord("r"), 0)
        window.pressed_keys.clear()
        assert np.array_equal(view, scene.frame.get_view_matrix())
        assert np.array_equal(points, scene.frame.get_points())

        output = Path(__file__).resolve().parents[1] / "pi_family/preview"
        output.mkdir(exist_ok=True)
        scene.get_image().save(output / "lab_initial.png")
        captures = 0
        original_capture = scene.camera.capture

        def capture(*mobjects):
            nonlocal captures
            captures += 1
            return original_capture(*mobjects)

        scene.camera.capture = capture
        lab = scene.lab
        lab.speed(4)
        lab.batch(father=2, mother=2, son=2, daughter=2)

        def set_minimized(minimized):
            (glfw.iconify_window if minimized else glfw.restore_window)(handle)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                window.poll_events()
                state = bool(glfw.get_window_attrib(handle, glfw.ICONIFIED))
                if state == minimized and (minimized or all(window.get_size())):
                    # Win32's minimize/restore transitions are asynchronous.
                    time.sleep(0.05)
                    window.poll_events()
                    return
                time.sleep(0.01)
            raise AssertionError("Native window did not change its minimize state")

        for cycle in range(10):
            set_minimized(True)
            assert glfw.get_window_attrib(handle, glfw.ICONIFIED)
            before = captures
            for _ in range(4):
                scene.update_frame(1 / 30, force_draw=True)
            assert captures == before, "A minimized window attempted GPU capture"
            set_minimized(False)
            scene.update_frame(1 / 30, force_draw=True)
            assert captures > before
            assert glfw.get_window_size(handle) == initial_size

        set_minimized(True)
        before_time, before_captures = lab.business_time, captures
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            scene.update_frame(1 / 30, force_draw=True)
            snapshot = lab.engine.snapshot()
            if all(v["completed"] == 2 for v in snapshot["roles"].values()) and not lab.presentation.tracks:
                break
            time.sleep(0.002)
        else:
            raise AssertionError("Real worker requests did not finish while minimized")
        assert snapshot["slots"] == [None, None]
        assert lab.business_time > before_time, (before_time, lab.business_time)
        assert captures == before_captures, (before_captures, captures, glfw.get_window_attrib(handle, glfw.ICONIFIED), window.get_size())
        set_minimized(False)
        scene.update_frame(1 / 30, force_draw=True)
        assert captures > before_captures
        scene.get_image().save(output / "lab_window_restored.png")

        # Zero-width and zero-height transitions are distinct from iconify.
        get_size = window.get_size
        try:
            for invalid_size in ((0, 720), (1280, 0), (0, 0)):
                window.get_size = lambda: invalid_size
                before = captures
                scene.update_frame(1 / 30, force_draw=True)
                assert captures == before
        finally:
            window.get_size = get_size

        # Inject an unexpected drawing failure into the live error boundary.
        # Its traceback must remain local, and all four processes must exit.
        def failed_capture(*mobjects):
            raise RuntimeError("WINDOW_CHECK_INJECTED_FAILURE")

        scene.camera.capture = failed_capture
        scene._live_clock = True
        scene.update_frame(1 / 30, force_draw=True)
        assert scene._fatal_error_reported and lab.closed
        assert scene.is_window_closing()
        diagnostic = ERROR_LOG.read_text(encoding="utf-8")
        assert "WINDOW_CHECK_INJECTED_FAILURE" in diagnostic
        assert str(Path.home()).lower() not in diagnostic.lower()
        assert not multiprocessing.active_children()
        print("WINDOW_OK: 10 minimize/restore cycles; hidden four-process completion; fixed size; movable; locked camera; zero-size guards; fatal cleanup and local log", flush=True)
    finally:
        if scene is not None and hasattr(scene, "lab"):
            scene.lab.close()
        window.destroy()
        assert not multiprocessing.active_children()


if __name__ == "__main__":
    main()
