import glob
import json
import os
import random
import time
from collections import OrderedDict

import numpy as np
from PIL import Image
from matplotlib import patches
from matplotlib.text import Annotation
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from webvoyager.run import get_default_driver
from webvoyager.utils import driver_get_safe, driver_execute_script_safe

D = os.path.dirname(__file__)

CODE_HEAD = """
import sys
import os
sys.path.append({{{PATH}}})
os.environ['KEY'] = {{{KEY}}}

# --- set global subplots behavior
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.projections import register_projection

class UnclippedAxes(Axes):
    name = 'unclippedaxes'  # must define a name
    def add_patch(self, p):
        p.set_clip_on(False)
        return super().add_patch(p)

register_projection(UnclippedAxes)

original_subplots = plt.subplots  # Save original just in case
def patched_subplots(*args, **kwargs):
    kwargs.setdefault('subplot_kw', {})
    kwargs['subplot_kw'].setdefault('projection', 'unclippedaxes')
    return original_subplots(*args, **kwargs)

plt.subplots = patched_subplots
# --- set global subplots behavior finished

import matplotlib.patches as patches
from draw.tools import TextAnnotator, layout_visualization

_ours_defined_text_annotator = TextAnnotator()
text_annotation = _ours_defined_text_annotator.text_annotation
""".replace("{{{PATH}}}", repr(os.path.dirname(D)))  # <- use ../ as path

CODE_TAIL = """
_ours_defined_text_annotator.finish_up()  # <- draw text annotations only at last step

# Loop through all axes
for ax in plt.gcf().axes:
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

plt.tight_layout()

# scale image by size
fig = plt.gcf()
fig.canvas.draw()
tight_bbox = fig.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
w_inches, h_inches = tight_bbox.width, tight_bbox.height
max_pixels = 2000
max_dpi = 200
dpi = min(max_pixels / w_inches, max_pixels / h_inches, max_dpi)
plt.savefig("main.png", dpi=dpi, bbox_inches='tight', pad_inches=0.1)"""


def _box(x0, y0, x1, y1):
    # normalized [xmin, ymin, xmax, ymax]
    if x0 > x1: x0, x1 = x1, x0
    if y0 > y1: y0, y1 = y1, y0
    return [float(x0), float(y0), float(x1), float(y1)]


def _boxes_overlap(a, b, margin=0.0):
    # a,b: [xmin, ymin, xmax, ymax]
    return not (
            a[2] + margin <= b[0] or  # a.right <= b.left
            b[2] + margin <= a[0] or  # b.right <= a.left
            a[3] + margin <= b[1] or  # a.top   <= b.bottom
            b[3] + margin <= a[1]  # b.top   <= a.bottom
    )


def _bbox_from_data_bbox(data_bbox):
    # data_bbox is a Matplotlib Bbox in data coords
    return _box(data_bbox.x0, data_bbox.y0, data_bbox.x1, data_bbox.y1)


def _shape_bbox(shape):
    # returns [xmin, ymin, xmax, ymax] in data coords for common patch types
    if isinstance(shape, patches.Rectangle):
        x0, y0 = shape.get_x(), shape.get_y()
        w, h = shape.get_width(), shape.get_height()
        return _box(x0, y0, x0 + w, y0 + h)

    elif isinstance(shape, (patches.Circle, patches.Ellipse)):
        # assume axis-aligned ellipse (no rotation field used)
        cx, cy = shape.center
        if isinstance(shape, patches.Circle):
            rx = ry = shape.radius
        else:
            # Ellipse stores width/height; radius is half
            rx = getattr(shape, 'width', 2 * getattr(shape, 'radius', 0)) / 2.0
            ry = getattr(shape, 'height', 2 * getattr(shape, 'radius', 0)) / 2.0
        return _box(cx - rx, cy - ry, cx + rx, cy + ry)

    elif isinstance(shape, patches.Polygon):
        # polygon vertices already in data coords
        verts = shape.get_xy()
        xs, ys = verts[:, 0], verts[:, 1]
        return _box(xs.min(), ys.min(), xs.max(), ys.max())

    else:
        # Fallback: try path-based bounds in data coords; may be conservative
        try:
            path = shape.get_path()
            tr = shape.get_transform()
            verts = tr.transform(path.vertices)
            xs, ys = verts[:, 0], verts[:, 1]
            # transform back to data if 'verts' ended up in display coords
            # Heuristic: if transform is already data transform, we're fine.
            # Otherwise, try inverse of ax.transData if available
            ax = shape.axes
            if ax is not None and tr != ax.transData:
                inv = ax.transData.inverted()
                verts = inv.transform(np.c_[xs, ys])
                xs, ys = verts[:, 0], verts[:, 1]
            return _box(xs.min(), ys.min(), xs.max(), ys.max())
        except Exception:
            raise ValueError(f"Unsupported or unhandled shape type: {type(shape)}")


def _anchors_for_bbox(b):
    # b: [xmin, ymin, xmax, ymax]
    x0, y0, x1, y1 = b
    w, h = (x1 - x0), (y1 - y0)
    return [
        (x0, y0), (x1, y0), (x0, y1), (x1, y1),
        (x0 + w / 2, y0), (x0 + w / 2, y1), (x0, y0 + h / 2), (x1, y0 + h / 2),
    ], w, h


def _candidate_field(ax):
    # derive radii & angles in data units, scaled to axis size
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    width_data = abs(xlim[1] - xlim[0])
    height_data = abs(ylim[1] - ylim[0])
    scale = float(np.hypot(width_data, height_data))

    min_radius = 0.10 * scale
    max_radius = 0.50 * scale
    step = 0.05 * scale

    radial_offsets = list(np.arange(min_radius, max_radius + step, step))
    angle_offsets = list(np.linspace(-np.pi, np.pi, num=16, endpoint=False))

    # random.shuffle(radial_offsets)  # <- don't shuffle, from close to distant
    random.shuffle(angle_offsets)
    return radial_offsets, angle_offsets


def _estimate_annotation_bbox(ax, text, src_xy, dst_xy, color):
    # drop a temporary annotation, draw, measure its bbox in data coords, then remove
    ann = ax.annotate(
        text,
        xy=src_xy,
        xytext=dst_xy,
        color=color,
        ha='center',
        va='center',
        bbox=dict(boxstyle='round,pad=0.3', edgecolor=color, facecolor='white'),
        arrowprops=dict(arrowstyle='->', color=color),
        zorder=10,
        fontsize=8,
    )
    # force draw so bbox is available
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    box_patch = ann.get_bbox_patch()
    bbox_display = box_patch.get_window_extent(renderer=renderer).expanded(1.1, 1.1)
    inv = ax.transData.inverted()
    data_bbox = bbox_display.transformed(inv)
    ann.remove()
    return _bbox_from_data_bbox(data_bbox)


def _place_annotation(ax, text, src_xy, dst_xy, color):
    # final placement
    return ax.annotate(
        text,
        xy=src_xy,
        xytext=dst_xy,
        color=color,
        ha='center',
        va='center',
        bbox=dict(boxstyle='round,pad=0.3', edgecolor=color, facecolor='white'),
        arrowprops=dict(arrowstyle='->', color=color),
        zorder=10,
        fontsize=8,
    )


class TextAnnotator:
    def __init__(self, margin=0.0):
        self.ax_cache = {}
        self.margin = float(margin)

    def text_annotation(self, ax, text, new_shape, color='#000000'):
        if ax not in self.ax_cache:
            self.ax_cache[ax] = []
        self.ax_cache[ax].append((new_shape, text, color))

    def _try_place_one(
            self, ax, shape_bbox, text, color, placed_shape_bboxes, placed_text_bboxes
    ):
        """
        Try to place a single annotation near shape_bbox.
        Phase A: avoid shapes + placed texts (if avoid_shape_bboxes is True)
        Phase B: avoid placed texts only (if avoid_shape_bboxes is False)
        Returns True if placed, and the placed bbox is appended to placed_text_bboxes.
        """
        anchors, w, h = _anchors_for_bbox(shape_bbox)
        radial_offsets, angle_offsets = _candidate_field(ax)

        # shuffle anchors to reduce bias
        random.shuffle(anchors)

        for r in radial_offsets:
            for ang in angle_offsets:
                dx = r * np.cos(ang)
                dy = r * np.sin(ang)
                for axx, ayy in anchors:
                    src_xy = (axx, ayy)
                    dst_xy = (axx + dx, ayy + dy)
                    ann_bbox = _estimate_annotation_bbox(ax, text, src_xy, dst_xy, color)

                    # Must not overlap already placed text
                    bad = any(_boxes_overlap(ann_bbox, tb, self.margin) for tb in placed_text_bboxes)
                    if bad:
                        continue

                    # (Allow overlap with *its own* shape? The spec says "avoid all shapes (this and other shapes)" => do not allow)
                    if any(_boxes_overlap(ann_bbox, sb, self.margin) for sb in placed_shape_bboxes):
                        continue

                    # Passes constraints → place
                    _place_annotation(ax, text, src_xy, dst_xy, color)
                    placed_text_bboxes.append(ann_bbox)
                    return True

        return False

    def finish_up(self):
        """
        Execute the three-tier placement policy for each queued annotation:

        1) Avoid overlap with ALL shapes (this & others) AND already-placed text.
        2) If that fails, avoid overlap with already-placed text only.
        3) If that fails, fallback: center->(center+100, center+100), print a message.
        """
        for ax, items in self.ax_cache.items():
            if not items:
                continue

            # Precompute shape bboxes for this axes (includes queued shapes)
            placed_shape_bboxes = [_shape_bbox(shape) for shape, _, _ in items]
            placed_text_bboxes = []

            for shape, text, color in items:
                # bbox of this specific shape (by geometry, not by object identity in ax)
                shape_bbox = _shape_bbox(shape)

                # --- Phase 1: avoid shapes + text ---
                success = self._try_place_one(
                    ax,
                    shape_bbox,
                    text,
                    color,
                    placed_shape_bboxes=placed_shape_bboxes,
                    placed_text_bboxes=placed_text_bboxes,
                )

                if not success:
                    # --- Phase 2: avoid text only ---
                    success = self._try_place_one(
                        ax,
                        shape_bbox,
                        text,
                        color,
                        placed_shape_bboxes=[],
                        placed_text_bboxes=placed_text_bboxes,
                    )

                if not success:
                    # --- Phase 3: fallback ---
                    # center of shape bbox
                    cx = (shape_bbox[0] + shape_bbox[2]) / 2.0
                    cy = (shape_bbox[1] + shape_bbox[3]) / 2.0
                    fallback_xy = (cx + 100.0, cy + 100.0)

                    ann = _place_annotation(ax, text, (cx, cy), fallback_xy, color)
                    ax.figure.canvas.draw()
                    renderer = ax.figure.canvas.get_renderer()
                    bbox_display = ann.get_window_extent(renderer=renderer).expanded(1.1, 1.1)
                    inv = ax.transData.inverted()
                    data_bbox = bbox_display.transformed(inv)
                    placed_text_bboxes.append(_bbox_from_data_bbox(data_bbox))

        # optional: clear queue after finishing
        self.ax_cache = {}


def get_html_state(driver, image_path, wait_load: int = 1, dont_quit: bool = False):
    html = driver.page_source

    # Get full page size
    total_width = driver_execute_script_safe(driver, "return document.body.scrollWidth")
    total_height = driver_execute_script_safe(driver, "return document.body.scrollHeight")
    # Set a smallest size
    total_width = max(int(total_width * 1.05), 700)  # <- no less than 700 width
    total_height = max(int(total_height * 1.05), 512, int(total_width * 0.75))  # <- no less than 512 height
    # Resize the window to fit the full page
    driver.set_window_size(total_width, total_height)
    time.sleep(wait_load)

    # Screenshot
    driver.save_screenshot(image_path)

    # JS script to get simplified DOM with bbox
    script = """
    function getSimplifiedTree(el) {
        const tag = el.tagName.toLowerCase();
        const rect = el.getBoundingClientRect();
        let textContent = el.innerText ? el.innerText.trim() : "";

        // Truncate long text
        if (textContent.length > 100) {
            textContent = textContent.slice(0, 50) + "..." + textContent.slice(-30);
        }

        const visible = rect.width > 0 && rect.height > 0;
        const hasVisibleChildren = Array.from(el.children).some(
            child => child.getBoundingClientRect().width > 0
        );

        if (!visible && !hasVisibleChildren) return null;

        const format = (num) => parseFloat(num.toFixed(1));
    
        const info = {
            text: textContent,
            tag: tag,
            bbox: {
                x: format(rect.x),
                y: format(rect.y),
                w: format(rect.width),
                h: format(rect.height)
            },
            children: []
        };

        for (const child of el.children) {
            const childInfo = getSimplifiedTree(child);
            if (childInfo) info.children.push(childInfo);
        }

        return info;
    }

    return getSimplifiedTree(document.body);
    """

    raw_result = driver_execute_script_safe(driver, script)
    if not dont_quit:
        driver.quit()

    def order_tree(node):
        """Reorder keys in desired order recursively."""
        if not node:
            return None

        # Order bbox keys explicitly
        bbox = node.get("bbox", {})
        ordered_bbox = OrderedDict()
        for key in ["x", "y", "w", "h"]:
            if key in bbox:
                ordered_bbox[key] = bbox[key]

        ordered = OrderedDict()
        ordered["text"] = node.get("text", "")
        ordered["tag"] = node.get("tag", "")
        ordered["bbox"] = ordered_bbox
        ordered["children"] = [order_tree(child) for child in node.get("children", [])]

        return ordered

    ordered_result = order_tree(raw_result)
    return html, ordered_result


def get_html_state_from_file(html_path, image_path, tmp_path=os.path.join(os.environ['HOME'], "tmp")):
    driver = get_default_driver(tmp_path=tmp_path)
    # Load your HTML file
    success = driver_get_safe(driver, "file://" + html_path)
    if success:
        try:
            return get_html_state(driver, image_path)
        except:
            return None, None
    else:
        return None, None


def layout_visualization(html_code, ax):
    dirpath = os.path.join(os.environ['HOME'], 'tmp', os.environ['KEY'])
    os.makedirs(dirpath, exist_ok=True)
    n_layout = len(glob.glob(os.path.join(dirpath, 'coordinates-*.json')))
    path = os.path.join(dirpath, f'index-{n_layout}.html')
    with open(path, 'w') as f:
        f.write(html_code)

    image_path = os.path.join(dirpath, f"screenshot-{n_layout}.png")
    _, ordered_result = get_html_state_from_file(path, image_path, tmp_path=dirpath)
    assert ordered_result is not None  # <- for tool calling, so assertion is fine

    ax.imshow(Image.open(image_path))
    with open(os.path.join(dirpath, f'coordinates-{n_layout}.json'), 'w') as f:
        json.dump(ordered_result, f, indent=2)
