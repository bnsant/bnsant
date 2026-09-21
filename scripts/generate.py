"""Generate the two self-contained profile SVGs. Requires only Python 3."""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "scripts" / "config.json"
ARTWORK = ROOT / "assets" / "20260921_145053.png"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def add_text(parent, x, y, css_class, **attrs):
    return ET.SubElement(
        parent,
        tag("text"),
        {"x": str(x), "y": str(y), "class": css_class, **attrs},
    )


def build_svg(config: dict, artwork: str, artwork_size: tuple[int, int], theme: dict) -> bytes:
    layout = config["layout"]
    width, height = layout["width"], layout["height"]
    info_x, info_y = layout["info_x"], layout["info_y"]
    svg = ET.Element(
        tag("svg"),
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "role": "img",
            "aria-label": f"ASCII portrait and profile information for {config['name']}",
        },
    )
    css = ET.SubElement(svg, tag("style"))
    css.text = f"""
      text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; }}
      .section {{ fill: {theme['muted']}; font-size: 11px; letter-spacing: 1px; }}
      .name {{ fill: {theme['text']}; font-size: 16px; font-weight: 600; }}
      .accent {{ fill: {theme['accent']}; }}
      .label {{ fill: {theme['label']}; font-size: 13px; }}
      .value {{ fill: {theme['text']}; font-size: 13px; }}
      .bullet {{ fill: {theme['muted']}; font-size: 13px; }}
      .stat-label {{ fill: {theme['label']}; font-size: 12px; }}
      .stat-value {{ fill: {theme['text']}; font-size: 12px; }}
      .quiet {{ fill: {theme['muted']}; font-size: 12px; }}
    """
    ET.SubElement(svg, tag("rect"), {
        "width": str(width), "height": str(height), "fill": theme["background"]
    })

    # Remove the pale background from the screenshot and color its ASCII glyphs.
    rgb = [int(theme["portrait"][i:i + 2], 16) / 255 for i in (1, 3, 5)]
    defs = ET.SubElement(svg, tag("defs"))
    glyph_filter = ET.SubElement(defs, tag("filter"), {
        "id": "glyphs", "color-interpolation-filters": "sRGB",
    })
    ET.SubElement(glyph_filter, tag("feColorMatrix"), {
        "type": "matrix",
        "values": (
            f"0 0 0 0 {rgb[0]:.4f} "
            f"0 0 0 0 {rgb[1]:.4f} "
            f"0 0 0 0 {rgb[2]:.4f} "
            "-0.85 -0.85 -0.85 2.05 0"
        ),
    })
    artwork_width, artwork_height = artwork_size
    portrait = ET.SubElement(svg, tag("svg"), {
        "x": str(layout["portrait_x"]), "y": str(layout["portrait_y"]),
        "width": str(layout["portrait_width"]),
        "height": str(layout["portrait_height"]),
        "viewBox": f"0 0 {artwork_width} {artwork_height}",
        "preserveAspectRatio": "none", "overflow": "hidden",
    })
    ET.SubElement(portrait, tag("image"), {
        "x": "0", "y": "0", "width": str(artwork_width),
        "height": str(artwork_height), "href": artwork, "filter": "url(#glyphs)",
    })

    heading = add_text(svg, info_x, info_y, "name")
    ET.SubElement(heading, tag("tspan"), {"class": "accent"}).text = config["name"]
    ET.SubElement(heading, tag("tspan")).text = f"@{config['handle']}"
    right_x = width - 18
    header_line_x = info_x + len(f"{config['name']}@{config['handle']}") * 9.6 + 12
    if header_line_x < right_x:
        ET.SubElement(svg, tag("line"), {
            "x1": str(header_line_x), "y1": str(info_y - 5),
            "x2": str(right_x), "y2": str(info_y - 5),
            "stroke": theme["line"], "stroke-width": "1",
        })

    def add_row(label: str, value: str, y: int) -> None:
        char_width = 7.8
        label_end = info_x + (len(label) + 1) * char_width
        value_start = right_x - len(value) * char_width
        if value_start < label_end + 12:
            raise ValueError(f"Row is too wide for one line: {label}: {value}")
        add_text(svg, info_x - 15, y, "bullet").text = "·"
        add_text(svg, info_x, y, "label").text = f"{label}:"
        dots = int((value_start - label_end - 16) // char_width)
        if dots > 0:
            add_text(svg, label_end + 8, y, "bullet").text = "." * dots
        add_text(svg, right_x, y, "value", **{"text-anchor": "end"}).text = value

    def add_section(title: str, y: int) -> None:
        add_text(svg, info_x, y, "section").text = title
        line_x = info_x + len(title) * 7.2 + 14
        ET.SubElement(svg, tag("line"), {
            "x1": str(line_x), "y1": str(y - 4),
            "x2": str(right_x), "y2": str(y - 4),
            "stroke": theme["line"], "stroke-width": "1",
        })

    def add_stat(label: str, value: str, x: int, y: int) -> None:
        add_text(svg, x, y, "stat-label").text = f"{label}:"
        value_x = x + (len(label) + 1) * 7.2 + 5
        add_text(svg, value_x, y, "stat-value").text = value

    groups = [
        [
            ("OS", config["system"]["os"]),
            ("IDE", config["system"]["ide"]),
        ],
        [
            ("Languages.Programming", config["languages"]["programming"]),
            ("Languages.Computer", config["languages"]["computer"]),
            ("Languages.Real", config["languages"]["real"]),
        ],
        [
            ("Hobbies.Software", config["hobbies"]["software"]),
        ],
    ]
    row_y = info_y + 31
    for rows in groups:
        for label, value in rows:
            add_row(label, value, row_y)
            row_y += 18
        row_y += 14

    add_section("Contact", row_y)
    add_row("Email.Personal", config["contact"]["email_personal"], row_y + 24)
    add_row("LinkedIn", config["contact"]["linkedin"], row_y + 42)

    section_y = row_y + 84
    add_section("GitHub Stats", section_y)
    stats = config["github_stats"]
    add_stat("Repos", stats["repos"], info_x, section_y + 22)
    add_stat("Contributed", stats["contributed"], info_x + 107, section_y + 22)
    add_stat("Stars", stats["stars"], info_x + 257, section_y + 22)
    add_stat("Commits", stats["commits"], info_x, section_y + 38)
    add_stat("Followers", stats["followers"], info_x + 162, section_y + 38)
    add_row("Lines of Code on GitHub", stats["lines_of_code"], section_y + 54)
    add_text(svg, info_x, section_y + 71, "quiet").text = "commits, contributed: last 12 months"
    prompt = f"~/{config['repository']} $"
    add_text(svg, info_x, height - 23, "quiet").text = prompt
    add_text(svg, info_x + len(prompt) * 7.2 + 6, height - 23, "accent").text = "_"
    return ET.tostring(svg, encoding="utf-8", xml_declaration=True)


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    png = ARTWORK.read_bytes()
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Not a PNG file: {ARTWORK}")
    artwork_size = struct.unpack(">II", png[16:24])
    artwork = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    for mode in ("dark", "light"):
        target = ROOT / "assets" / f"{mode}_mode.svg"
        target.write_bytes(build_svg(config, artwork, artwork_size, config["themes"][mode]))
        print(f"Generated {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
