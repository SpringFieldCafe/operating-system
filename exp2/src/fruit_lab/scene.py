"""Entry point: manimgl fruit_lab/scene.py FruitLabScene"""

from pathlib import Path
import asyncio
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manimlib import Scene
from manimlib.config import manim_config
from manimlib.event_keys import Mods
from manimlib.scene.scene import EndScene
from manimlib.scene.scene_embed import InteractiveSceneEmbed
from fruit_lab.controller import LabController
from fruit_lab.diagnostics import failure_summary, record_failure
from fruit_lab.windowing import DEFAULT_CLIENT_SIZE, FRAME_WIDTH, FixedWindow


class _LiveEmbed(InteractiveSceneEmbed):
    def enable_gui(self):
        """Drive rendering on prompt_toolkit's main-thread asyncio loop.

        A per-prompt background coroutine advances frames even while typing,
        without moving graphics into another thread. Explicit terminal output
        also prevents TERM=dumb from selecting a fallback prompt that silently
        discards inputhooks and pre-run callbacks on Windows.
        prompt_toolkit cancels this task when each prompt returns.
        """
        if self.shell.simple_prompt:
            raise RuntimeError("Use an interactive terminal with prompt_toolkit, not IPython simple-prompt mode.")
        self.shell.pt_app._output = self.shell.pt_app.output
        prompt = self.shell.pt_app.prompt
        app = self.shell.pt_app.app

        async def frames():
            try:
                while not self.scene.is_window_closing():
                    self.scene.update_frame(dt=0, force_draw=True)
                    await asyncio.sleep(1 / self.scene.camera.fps)
            except EndScene:
                self.scene.quit_interaction = True
            except Exception as exc:
                self.scene.handle_failure(exc)
            finally:
                # Cancellation when a command is entered is normal. Only a
                # closed window or fatal failure should end the IPython shell.
                if self.scene.is_window_closing():
                    self.shell.ask_exit()
                    if app.is_running and not app.is_done:
                        app.exit(result="exit()")

        def live_prompt(*args, **kwargs):
            previous = kwargs.pop("pre_run", None)

            def start_frames():
                if previous is not None:
                    previous()
                app.create_background_task(frames())

            kwargs["pre_run"] = start_frames
            kwargs["inputhook"] = None
            return prompt(*args, **kwargs)

        self.shell.pt_app.prompt = live_prompt

    def ensure_flash_on_error(self):
        # An invalid command is recoverable. Upstream flashes a red border by
        # rendering more frames, which is inappropriate for a hidden window.
        def command_error(shell, etype, value, tb, tb_offset=None):
            print(f"命令未执行：{etype.__name__}: {value}")

        self.shell.set_custom_exc((Exception,), command_error)


class FruitLabScene(Scene):
    default_camera_config = {"background_color": "#000000", "resolution": DEFAULT_CLIENT_SIZE}
    always_update_mobjects = True
    drag_to_pan = False

    def __init__(self, window=None, **kwargs):
        self._fatal_error_reported = False
        self._live_clock = False
        # Configure the native window before Camera creates its first target.
        self._window_policy = FixedWindow(window) if window is not None else None
        super().__init__(window=window, **kwargs)

    def build_lab(self):
        # Keep the original 80 pixels per scene unit at the default size.
        # Extra canvas surrounds the existing actors and props without scaling them.
        self.camera.frame.set_width(FRAME_WIDTH).move_to([0, 0, 0])
        self.lab = LabController(self)
        self._last_wall_time = time.perf_counter()
        self._live_clock = False

    def construct(self):
        try:
            self.build_lab()
            # Only the main process owns graphics and this namespace.
            lab = self.lab
            father = lambda n=1: lab.submit("father", n)
            mother = lambda n=1: lab.submit("mother", n)
            son = lambda n=1: lab.submit("son", n)
            daughter = lambda n=1: lab.submit("daughter", n)
            batch, cancel, status = lab.batch, lab.cancel, lab.status
            pause, resume, step, speed = lab.pause, lab.resume, lab.step, lab.speed
            detail, demo, reset = lab.detail, lab.demo, lab.reset
            events, save_log, help_cmds = lab.events, lab.save_log, lab.help_cmds
            self._live_clock = True
            self._last_wall_time = time.perf_counter()
            self.update_frame(force_draw=True)
            help_cmds()
            self.embed()
        except EndScene:
            raise
        except Exception as exc:
            if not self.window:
                raise
            self.handle_failure(exc)
        finally:
            self._live_clock = False
            if hasattr(self, "lab"):
                try:
                    self.lab.close()
                except Exception as exc:
                    if not self.window:
                        raise
                    self.handle_failure(exc)

    def update_frame(self, dt=0, force_draw=False):
        try:
            if hasattr(self, "lab") and not self.lab.closed:
                if self._live_clock:
                    now = time.perf_counter()
                    if dt == 0:
                        dt = min(max(now - self._last_wall_time, 0), 0.1)
                    self._last_wall_time = now
                self.lab.tick(dt)
                force_draw = True
            return super().update_frame(dt, force_draw)
        except EndScene:
            raise
        except Exception as exc:
            if not self.window or not self._live_clock:
                raise
            self.handle_failure(exc)

    def draw_frame(self, dt=0, force_draw=False):
        if self.window:
            # Pump events even without drawing: restore and close must remain
            # responsive, and the canvas size must be current before capture.
            self.window.poll_events()
            if self.is_window_closing() or not self._window_policy.drawable():
                return
        return super().draw_frame(dt, force_draw)

    def handle_failure(self, exc):
        if self._fatal_error_reported:
            return
        self._fatal_error_reported = True
        self._live_clock = False
        self.quit_interaction = True
        saved = record_failure(exc)
        if hasattr(self, "lab"):
            try:
                self.lab.close()
            except Exception as cleanup_error:
                saved = record_failure(cleanup_error) and saved
        cleaned_up = not hasattr(self, "lab") or self.lab.closed
        message = f"实验遇到错误，已结束（{failure_summary(exc)}）。"
        message += "已回收工作进程。" if cleaned_up else "进程回收遇到错误，请查看本地诊断。"
        message += "详细诊断见 exp2/report/fruit_lab_error.log。" if saved else "本地诊断日志写入失败。"
        print(message)

    def on_mouse_motion(self, point, d_point):
        self.mouse_point.move_to(point)

    def on_mouse_scroll(self, *args):
        return

    def on_key_press(self, symbol, modifiers):
        # Keep the close shortcut; all camera manipulation shortcuts are off.
        if symbol == ord(manim_config.key_bindings.quit) and modifiers & Mods.CTRL_OR_CMD:
            self.quit_interaction = True

    def embed(self, close_scene_on_exit=True, show_animation_progress=False):
        if not self.window:
            return
        self.show_animation_progress = show_animation_progress
        self.stop_skipping()
        _LiveEmbed(self).launch()
        if close_scene_on_exit:
            raise EndScene()

    def interact(self):
        # embed() owns the live window, including clean shutdown on exit().
        return
