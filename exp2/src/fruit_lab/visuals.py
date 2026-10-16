"""Nonblocking action tracks, original Pi assets, and head-pinned thought clouds."""

from collections import deque
from dataclasses import dataclass
import math

import numpy as np
from manimlib import (Animation, AnimationGroup, DrawBorderThenFill, FadeIn, FadeOut,
                      LaggedStart, Text, Write, UP, DOWN, LEFT, RIGHT, VGroup)

from pi_family import WalkTo, carry_fruit, hand_tip, standing_point
from pi_family.contact_layout import CONTACT_ROLES, make_contact_pose
from pi_family.props import AppleOutline, OrangeOutline, make_fruit_table
from pi_family.reactions import FamilyBehavior
from pi_family.idle_motion import _mark_face_dynamic
from .engine import ROLES, LABELS
from .math_assets import tex
from .thought_bubbles import (ThoughtCloud, THOUGHT_DIRECTIONS, THOUGHT_PHASE_SPEEDS,
                              assign_cloud_variants)

FONT = "SimSun"
FRUIT_SLIDE_DURATION = 0.45
FRUIT_CLEARANCE = 0.04
# At 80 px/unit, lift parents 8 px and lower children 12 px.
HOME_Y = {"father": 0.85, "mother": 0.85, "son": -2.80, "daughter": -2.80}
WAIT_WORDS = {"space": "盘子满了\n等一个空位", "apple": "还没有苹果\n我再等一等", "orange": "还没有橘子\n我再等一等", "mutex": "有人正在取放\n等盘子空闲"}
PHASE_WORDS = {"idle": "待机", "preparing": "接住水果", "outbound": "走向桌子", "contact": "取放水果", "arranging": "盘内整理",
               "returning": "返回原位", "celebrating": "开心 / 欢呼", "displaying": "展示水果", "finishing": "完成本次请求"}


def text(words, size=24, color="#FFFFFF"):
    return Text(words, font=FONT, font_size=size, color=color)


def reveal(mobject, duration=0.7):
    """A soft, slightly growing glyph entrance, not the default Write stroke."""
    glyphs = list(mobject)
    if not glyphs:
        return FadeIn(mobject, run_time=duration)
    return LaggedStart(*(FadeIn(glyph, scale=1.055, run_time=0.28) for glyph in glyphs),
                       lag_ratio=0.12, run_time=duration)


@dataclass
class Clip:
    animation: object
    duration: float


@dataclass
class Until:
    predicate: object


class Track:
    """Manually tick native Manim animations so the IPython prompt never blocks."""
    def __init__(self, scene, generator):
        self.scene, self.generator = scene, generator
        self.current = None
        self.elapsed = 0.0
        self.done = False

    def tick(self, dt):
        for _ in range(30):
            if self.done:
                return
            if self.current is None:
                try:
                    self.current = next(self.generator)
                except StopIteration:
                    self.done = True
                    return
                self.elapsed = 0
                if isinstance(self.current, Clip):
                    animation = self.current.animation
                    if callable(animation):
                        animation = animation()
                    if not isinstance(animation, Animation):
                        animation = animation.build()
                    self.current.animation = animation
                    animation.update_rate_info(run_time=self.current.duration)
                    animation.begin()
            if isinstance(self.current, Until):
                if not self.current.predicate():
                    return
                self.current = None
                continue
            clip = self.current
            self.elapsed += dt
            clip.animation.interpolate(min(self.elapsed / clip.duration, 1.0))
            # Ambient facial/attachment updaters can change geometry between
            # native interpolation samples. Recompute bounds from real points
            # instead of carrying an interpolated, stale group bounding box.
            clip.animation.mobject.refresh_bounding_box(recurse_down=True)
            if self.elapsed < clip.duration:
                return
            clip.animation.finish()
            clip.animation.mobject.refresh_bounding_box(recurse_down=True)
            clip.animation.clean_up_from_scene(self.scene)
            self.current = None
            # A callback may depend on another process; don't invent elapsed
            # time for the next clip while consuming an acknowledgment.
            dt = 0


class _IdleClock:
    """Reactions use business time; focus and random eye motion use ambient time."""
    def __init__(self, idle, lab):
        self.idle, self.lab = idle, lab

    @property
    def anger(self):
        return self.idle.anger

    @anger.setter
    def anger(self, value):
        self.idle.anger = value

    def focus_on(self, target, _time, duration=0.35):
        self.idle.focus_on(target, self.lab.ambient_time, duration)

    def release_focus(self, _time):
        self.idle.release_focus(self.lab.ambient_time)


class LiveBehavior(FamilyBehavior):
    def __init__(self, scene, actors, lab):
        self.lab = lab
        super().__init__(scene, actors, seed=None)
        scene.remove(self.clock)
        self.clock.clear_updaters()
        for actor in self.reactions:
            actor.idle = _IdleClock(actor.idle, lab)
        self.prepare_angry_faces()

    def _time(self):
        return self.lab.business_time

    def update(self):
        if self.active:
            for actor in self.reactions:
                actor.update(self._time())
            for idle in self.controllers:
                idle.update(self.lab.ambient_time)

    def stop(self):
        if not self.active:
            return
        for pi in (controller.pi for controller in self.controllers):
            pi._body_reaction_active = False
            pi._ambient_face_active = False
            for part in (pi.body, pi.mouth, pi.eyes):
                part.remove_updater(_mark_face_dynamic)
        self.active = False


class Presentation:
    def __init__(self, scene, lab):
        self.scene, self.lab = scene, lab
        self._last_ambient_time = lab.ambient_time
        self.actors, self.homes, self.contacts, self.offsets = {}, {}, {}, {}
        self.heads, self.bubbles, self.bubble_reasons = {}, {}, {}
        self.cloud_variants = {}
        self.tracks, self.effects, self.signals = {}, [], {}
        self.plate_fruits = {}
        self.carried = {}
        self.phases = dict.fromkeys(ROLES, "idle")
        self.labels = {}
        self.detail_rows = deque(maxlen=3)
        self.last_hud = None
        self.title = text("实验二 · 进程同步", 34).move_to([0, 4.1, 0])
        self.run_label = text("运行中 · 1.0×", 19).move_to([0, 3.62, 0])
        self.caption = text("输入 help_cmds() 查看命令", 23).move_to([0, 2.35, 0])
        self.caption.set_max_width(4.4)
        scene.add(self.title, self.run_label, self.caption)
        props = make_fruit_table()
        self.props = props
        scene.add(props.table, props.plate)
        self.positions = props.plate.fruit_positions()
        for key, role in CONTACT_ROLES.items():
            pi, contact_props = make_contact_pose(key)
            self.contacts[key] = standing_point(pi).copy()
            self.offsets[key] = getattr(contact_props, role.fruit).get_center() - hand_tip(pi, role.hand)
            pi.change_mode("plain")
            home = np.array([role.side * 4.7, HOME_Y[key], 0.0])
            pi.shift(home - standing_point(pi))
            self.homes[key] = home
            self.heads[key] = pi.eyes.get_top().copy() + 0.12 * UP
            self.actors[key] = pi
            scene.add(pi)
            label = text(role.label, 24, pi.get_color()).move_to(home + 0.36 * DOWN)
            state = text("待机 · 待办 0 · 完成 0", 16).next_to(label, DOWN, buff=0.12)
            self.labels[key] = (label, state)
            scene.add(label, state)
        self.behavior = LiveBehavior(scene, tuple(self.actors.values()), lab)
        self.digits = {i: tex(str(i), font_size=27) for i in range(3)}
        self.counters = []
        for x, symbol, label in ((-2.2, "e", "可用空位"), (0, "a", "可取苹果"), (2.2, "o", "可取橘子")):
            heading = text(label, 18).move_to([x - 0.3, -4.0, 0])
            prefix = tex(symbol + "=", font_size=25).next_to(heading, RIGHT, buff=0.14)
            digit = self.digits[0].copy().next_to(prefix, RIGHT, buff=0.08)
            self.counters.append(digit)
            scene.add(heading, prefix, digit)
        self.detail_title = text("同步讲解 · P 申请 / V 释放", 20).move_to([0, -1.95, 0])
        self.owner_label = text("盘子操作权：空闲", 18).move_to([0, -2.32, 0])
        self.detail_lines = VGroup()
        self.tex_operations = {name: tex(formula, font_size=22) for name, formula in {
            "P(empty)": "P(e)", "P(apple)": "P(a)", "P(orange)": "P(o)", "P(mutex)": "P(m)",
            "V(empty)": "V(e)", "V(apple)": "V(a)", "V(orange)": "V(o)", "V(mutex)": "V(m)"}.items()}
        scene.add(self.detail_title, self.owner_label, self.detail_lines)
        self.set_detail(lab.detailed)

    def effect(self, animation, duration=0.5, tag=None):
        if tag is not None:
            self.effects = [(t, name) for t, name in self.effects if name != tag]
        def run():
            yield Clip(animation, duration)
        track = Track(self.scene, run())
        self.effects.append((track, tag))
        return track

    def say_caption(self, words):
        if getattr(self, "caption_words", None) == words:
            return
        self.caption_words = words
        self.scene.remove(self.caption)
        self.caption = text(words, 23).move_to([0, 2.35, 0])
        self.caption.set_max_width(4.4)
        self.scene.add(self.caption)
        self.effect(lambda: reveal(self.caption, 0.5), 0.5, "caption")

    def waiting(self, key, reason):
        if reason not in WAIT_WORDS:
            self.clear_bubble(key)
            return
        self.behavior.waiting(self.actors[key])
        if self.bubble_reasons.get(key) == reason:
            return
        self.clear_bubble(key)
        # Keep reservations while any cloud is visible, including FadeOut.
        # Reshuffling only between groups avoids cross-role duplicates when a
        # waiting reason changes or one character's cloud returns early.
        if not self.cloud_variants or (not self.bubbles and not any(
                tag is not None and tag.startswith("bubble-exit:") for _, tag in self.effects)):
            self.cloud_variants = assign_cloud_variants(ROLES)
        content = text(WAIT_WORDS[reason], 23)
        content.set_max_width(2.9)
        # Pin to a stable, open-eyed head anchor; blinking must not move the box.
        bubble = ThoughtCloud(content, self.heads[key], THOUGHT_DIRECTIONS[key],
                              child=key in ("son", "daughter"), phase_speeds=THOUGHT_PHASE_SPEEDS[key],
                              shape_variants=self.cloud_variants[key])
        self.bubbles[key], self.bubble_reasons[key] = bubble, reason
        self.scene.add(bubble)
        # Match PiCreatureBubbleIntroduction, including its native timing.
        entrance = AnimationGroup(DrawBorderThenFill(bubble.body), Write(content))
        bubble.entrance_track = self.effect(entrance, entrance.get_run_time(), "bubble:" + key)

    def clear_bubble(self, key):
        bubble = self.bubbles.pop(key, None)
        self.bubble_reasons.pop(key, None)
        if bubble is not None:
            self.effects = [(track, tag) for track, tag in self.effects if tag != "bubble:" + key]
            exit_animation = FadeOut(bubble)
            self.effect(exit_animation, exit_animation.get_run_time(), "bubble-exit:" + str(id(bubble)))

    def set_detail(self, enabled):
        for part in (self.detail_title, self.owner_label, self.detail_lines):
            part.set_opacity(float(enabled))

    def on_event(self, e):
        key, kind = e.get("role"), e["kind"]
        if kind == "state" and key not in self.tracks:
            self.waiting(key, e["reason"])
            if e["reason"] in ("idle", "paused"):
                self.behavior.ready(self.actors[key])
        elif kind == "granted":
            self.clear_bubble(key)
            self.behavior.ready(self.actors[key])
            self.signals[e["task"]] = set()
            self.tracks[key] = Track(self.scene, self.trip(e))
            self.say_caption(LABELS[ROLES.index(key)] + "获得取放机会")
        elif kind in ("committed", "released", "finished"):
            self.signals[e["task"]].add(kind)
        if e.get("operations"):
            self.detail_rows.append((key, e["operations"]))
            self.refresh_detail()

    def refresh_detail(self):
        self.scene.remove(self.detail_lines)
        lines = []
        for i, (key, operations) in enumerate(self.detail_rows):
            label = text(LABELS[ROLES.index(key)], 18, self.actors[key].get_color())
            line = VGroup(label, *(self.tex_operations[op].copy() for op in operations))
            line.arrange(RIGHT, buff=0.18).move_to([0, -2.72 - i * 0.34, 0])
            lines.append(line)
        self.detail_lines = VGroup(*lines)
        self.detail_lines.set_opacity(float(self.lab.detailed))
        self.scene.add(self.detail_lines)

    def take_fruit(self, key, slot):
        """Bind the reserved permit to the closest interchangeable picture.

        Two apples (or two oranges) have no individual resource identity.
        Rebinding only equal fruit types avoids physically crossing them;
        the engine's reserved slot and all resource counts stay unchanged.
        """
        near = 1 if CONTACT_ROLES[key].side > 0 else 0
        selected = self.plate_fruits[slot]
        matching = [index for index, fruit in self.plate_fruits.items() if type(fruit) is type(selected)]
        closest = min(matching, key=lambda index: np.linalg.norm(
            self.plate_fruits[index].get_bottom() - self.positions[near]))
        if closest != slot:
            self.plate_fruits[slot], self.plate_fruits[closest] = self.plate_fruits[closest], selected
        return self.plate_fruits[slot]

    def arrange_fruit(self, targets):
        """Return a serial clip only when a plate fruit actually needs moving."""
        moves = []
        for slot, position in targets.items():
            fruit = self.plate_fruits[slot]
            target = self.positions[position]
            if not np.allclose(fruit.get_bottom(), target, atol=1e-5, rtol=0):
                moves.append(fruit.animate.move_to(target, aligned_edge=DOWN))
        if moves:
            return Clip(AnimationGroup(*moves), FRUIT_SLIDE_DURATION)
        return None

    def clear_for_refill(self, key, targets):
        """The held fruit must clear the entire horizontal refill path."""
        side = CONTACT_ROLES[key].side
        held_edge = np.min(side * self.carried[key].get_all_points()[:, 0])
        for slot, position in targets.items():
            fruit = self.plate_fruits[slot]
            points = fruit.get_all_points()[:, 0]
            dx = self.positions[position][0] - fruit.get_bottom()[0]
            swept_edge = max(np.max(side * points), np.max(side * (points + dx)))
            if held_edge <= swept_edge + FRUIT_CLEARANCE:
                return False
        return True

    def trip(self, event):
        key, task, slot = event["role"], event["task"], event["slot"]
        pi, role = self.actors[key], CONTACT_ROLES[key]
        parent = key in ("father", "mother")
        prefix = role.hand + "_hand_"
        return_track = None
        if parent:
            fruit = AppleOutline() if event["fruit"] == "apple" else OrangeOutline()
            fruit.move_to(hand_tip(pi, role.hand) + self.offsets[key])
            carry_fruit(pi, fruit, hand=role.hand, offset=self.offsets[key], snap=False)
            self.carried[key] = fruit
            self.scene.add(fruit)
            self.phases[key] = "preparing"
            yield Clip(lambda: AnimationGroup(FadeIn(fruit), pi.change(prefix + "hold").build()), 0.55)
            # Make room while the incoming fruit is still held at home.
            # Waiting until arrival would put it against the occupied side.
            near = 1 if role.side > 0 else 0
            slide = self.arrange_fruit({index: 1 - near for index in self.plate_fruits})
            if slide is not None:
                self.phases[key] = "arranging"
                yield slide
        else:
            fruit = self.take_fruit(key, slot)
        self.phases[key] = "outbound"
        yield Clip(lambda: WalkTo(pi, self.contacts[key], run_time=1.9), 1.9)
        self.phases[key] = "contact"
        if parent:
            yield Clip(lambda: pi.change(prefix + "reach"), 0.45)
            yield Clip(lambda: pi.change(prefix + "place"), 0.35)
        else:
            yield Clip(lambda: pi.change(prefix + "place"), 0.55)
        self.lab.engine.acknowledge(key, task, "commit")
        yield Until(lambda: "committed" in self.signals[task])
        if parent:
            pi._fruit_attachment.release()
            near = 1 if role.side > 0 else 0
            fruit.move_to(self.positions[near], aligned_edge=DOWN)
            self.carried.pop(key)
            self.plate_fruits[slot] = fruit
            self.say_caption(role.label + "放入" + ("苹果" if role.fruit == "apple" else "橘子"))
            yield Clip(lambda: pi.change("plain"), 0.55)
            self.behavior.parent_placed(pi)
        else:
            self.plate_fruits.pop(slot)
            carry_fruit(pi, fruit, hand=role.hand, snap=False)
            self.carried[key] = fruit
            self.say_caption(role.label + "取到" + ("苹果" if role.fruit == "apple" else "橘子"))
            yield Clip(lambda: pi.change(prefix + "reach"), 0.3)
            yield Clip(lambda: pi.change(prefix + "hold"), 0.5)
            targets = {index: 1 if isinstance(item, AppleOutline) else 0
                       for index, item in self.plate_fruits.items()}
            slide = self.arrange_fruit(targets)
            if slide is not None:
                # Reuse the one normal return walk. Its geometry, rather
                # than a fixed delay, decides when refill can start safely.
                self.phases[key] = "returning"
                return_track = self.effect(lambda: WalkTo(pi, self.homes[key], run_time=1.9),
                                           1.9, "return:" + key)
                yield Until(lambda: self.clear_for_refill(key, targets))
                self.phases[key] = "arranging"
                yield slide
        self.lab.engine.acknowledge(key, task, "release")
        yield Until(lambda: "released" in self.signals[task])
        self.phases[key] = "returning"
        if return_track is None:
            yield Clip(lambda: WalkTo(pi, self.homes[key], run_time=1.9), 1.9)
        else:
            yield Until(lambda: return_track.done)
        if not parent:
            self.phases[key] = "celebrating"
            self.behavior.child_received(pi, role.fruit, look_target=fruit)
            end = self.lab.business_time + self.behavior.reaction_settings.celebration_duration
            yield Until(lambda: self.lab.business_time >= end)
            self.phases[key] = "displaying"
            end = self.lab.business_time + 0.45
            yield Until(lambda: self.lab.business_time >= end)
            yield Clip(FadeOut(fruit), 0.45)
            pi._fruit_attachment.release()
            self.carried.pop(key)
            yield Clip(lambda: pi.change("plain"), 0.35)
        self.phases[key] = "finishing"
        self.lab.engine.acknowledge(key, task, "finished")
        yield Until(lambda: "finished" in self.signals[task])
        self.signals.pop(task)
        self.phases[key] = "idle"

    def tick(self, dt):
        ambient_dt = max(0, self.lab.ambient_time - self._last_ambient_time)
        self._last_ambient_time = self.lab.ambient_time
        for key, track in list(self.tracks.items()):
            track.tick(dt)
            if track.done:
                self.tracks.pop(key)
        for track, tag in list(self.effects):
            appearance = tag is not None and tag.startswith(("bubble:", "bubble-exit:"))
            track.tick(ambient_dt if appearance else dt)
        self.effects = [(track, tag) for track, tag in self.effects if not track.done]
        for bubble in self.bubbles.values():
            if bubble.entrance_track.done:
                bubble.update_motion(self.lab.ambient_time)
        for fruit in self.carried.values():
            fruit._hand_attachment.update()
        self.behavior.update()
        for fruit in self.carried.values():
            fruit._hand_attachment.update()

    def hud(self, snapshot):
        role_info = tuple((v["pending"], v["completed"], v["reason"]) for v in snapshot["roles"].values())
        identity = (tuple(snapshot["slots"]), snapshot["owner"], role_info, tuple(self.phases.values()),
                    self.lab.paused, self.lab.stepping, self.lab.rate, self.lab.detailed, self.lab.reset_pending)
        if identity == self.last_hud:
            return
        self.last_hud = identity
        # Counters show available permits, including reservations during travel.
        slots = snapshot["slots"]
        counts = [slots.count(None), slots.count("apple"), slots.count("orange")]
        for slot, key in enumerate(snapshot["reserved"]):
            if key in ("father", "mother") and slots[slot] is None:
                counts[0] -= 1
            elif key in ("son", "daughter") and slots[slot] is not None:
                counts[1 if slots[slot] == "apple" else 2] -= 1
        for digit, count in zip(self.counters, counts):
            point = digit.get_center().copy()
            digit.become(self.digits[count]).move_to(point)
        state_words = "正在收尾重置" if self.lab.reset_pending else "单步推进" if self.lab.stepping else "已暂停 · 云朵与眼睛继续" if self.lab.paused else "运行中"
        self.run_label.become(text(f"{state_words} · {self.lab.rate:g}×", 19).move_to([0, 3.62, 0]))
        owner = snapshot["owner"]
        self.owner_label.become(text("盘子操作权：" + ("空闲" if owner is None else LABELS[ROLES.index(owner)]), 18).move_to([0, -2.32, 0]))
        self.owner_label.set_opacity(float(self.lab.detailed))
        for key, info in snapshot["roles"].items():
            label, state = self.labels[key]
            phase = self.phases[key]
            word = PHASE_WORDS[phase] if phase != "idle" else "等待" if key in self.bubbles else "已暂停" if info["reason"] == "paused" else "待机"
            state.become(text(f"{word} · 待办 {info['pending']} · 完成 {info['completed']}", 16).next_to(label, DOWN, buff=0.12))

    def close(self):
        self.behavior.stop()
        for fruit in self.carried.values():
            fruit._hand_attachment.release()
