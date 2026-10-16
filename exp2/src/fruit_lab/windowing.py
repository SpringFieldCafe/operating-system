"""Local GLFW window policy; never changes the installed ManimGL package."""

import glfw

DEFAULT_CLIENT_SIZE = (1440, 810)
FRAME_WIDTH = 18


def fitted_size(work_width, work_height, frame=(0, 0, 0, 0)):
    """Fit a 1440x810 client area into the work area, including decorations."""
    left, top, right, bottom = frame
    unit = min(DEFAULT_CLIENT_SIZE[0] // 16, int((work_width - left - right - 32) / 16),
               int((work_height - top - bottom - 32) / 9))
    if unit < 1:
        raise RuntimeError("The monitor work area is too small for the lab window.")
    return 16 * unit, 9 * unit


class FixedWindow:
    def __init__(self, window):
        self.window = window
        self.handle = window.glfw_window
        # Native resize/expose callbacks can request presentation even outside
        # Scene.draw_frame, including during minimize/restore transitions.
        window.canvas.request_draw(self.present)
        glfw.set_window_attrib(self.handle, glfw.RESIZABLE, glfw.FALSE)
        x, y = glfw.get_window_pos(self.handle)
        width, height = glfw.get_window_size(self.handle)
        monitors = glfw.get_monitors()
        monitor = max(monitors, key=lambda m: self._overlap(m, x, y, width, height)) if monitors else None
        area = glfw.get_monitor_workarea(monitor) if monitor else (0, 0, 1920, 1080)
        frame = glfw.get_window_frame_size(self.handle)
        self.size = fitted_size(area[2], area[3], frame)
        glfw.set_window_size(self.handle, *self.size)
        glfw.set_window_size_limits(self.handle, *self.size, *self.size)
        left, top, right, bottom = frame
        x = max(area[0] + left + 16, min(x, area[0] + area[2] - self.size[0] - right - 16))
        y = max(area[1] + top + 16, min(y, area[1] + area[3] - self.size[1] - bottom - 16))
        glfw.set_window_pos(self.handle, x, y)
        window.poll_events()

    @staticmethod
    def _overlap(monitor, x, y, width, height):
        mx, my, mw, mh = glfw.get_monitor_workarea(monitor)
        return max(0, min(x + width, mx + mw) - max(x, mx)) * max(0, min(y + height, my + mh) - max(y, my))

    def drawable(self):
        if self.window.is_closing:
            return False
        if glfw.get_window_attrib(self.handle, glfw.ICONIFIED):
            return False
        return all(value > 0 for value in glfw.get_framebuffer_size(self.handle)) and all(value > 0 for value in self.window.get_size())

    def present(self):
        if self.window.frame_view is not None and self.drawable():
            try:
                self.window.draw()
            except Exception as exc:
                # RenderCanvas logs callback errors and normally continues.
                # Route a live presentation failure through the same shutdown
                # boundary as an error raised by Scene.update_frame.
                scene = self.window.scene
                if scene is None or not getattr(scene, "_live_clock", False):
                    raise
                scene.handle_failure(exc)
