#!/usr/bin/env python3
"""Static audit for Bubble Timeline, Director bindings, and plot Timeline references."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


TIMELINE_RELATIVE_ROOT = Path("Assets/GameAssets/WorkDir/PackedResources/Timeline")
TABLE_ROOT_RELATIVE_PATH = Path("Assets/GameAssets/WorkDir/PackedResources/Table/tTableRoot.asset")
PACKED_RESOURCES_RELATIVE_ROOT = Path("Assets/GameAssets/WorkDir/PackedResources")


@dataclass
class Finding:
    severity: str
    code: str
    file: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--timeline",
        type=Path,
        help="Optional .playable file or Timeline directory, absolute or relative to project root.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def normalized(path: Path) -> str:
    return path.as_posix()


def relative(path: Path, root: Path) -> str:
    try:
        return normalized(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return normalized(path.resolve())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_guid(meta_path: Path) -> str | None:
    if not meta_path.is_file():
        return None
    match = re.search(r"^guid:\s*([0-9a-f]{32})\s*$", read_text(meta_path), re.MULTILINE)
    return match.group(1) if match else None


def build_guid_index(assets_root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for meta_path in assets_root.rglob("*.meta"):
        guid = read_guid(meta_path)
        if guid:
            index[guid] = meta_path.with_suffix("")
    return index


def yaml_sections(text: str) -> dict[int, str]:
    markers = list(re.finditer(r"^--- !u!\d+ &(-?\d+)\s*$", text, re.MULTILINE))
    sections: dict[int, str] = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        sections[int(marker.group(1))] = text[marker.start() : end]
    return sections


def resolve_scope(project_root: Path, requested: Path | None, timeline_root: Path) -> list[Path]:
    if requested is None:
        return sorted(timeline_root.rglob("*.playable"))
    target = requested if requested.is_absolute() else project_root / requested
    target = target.resolve()
    if target.is_file():
        return [target] if target.suffix == ".playable" else []
    if target.is_dir():
        return sorted(target.rglob("*.playable"))
    return []


def playable_animation_guids(text: str) -> set[str]:
    return set(
        re.findall(
            r"animationReference:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32})",
            text,
        )
    )


def playable_bindable_track_ids(text: str) -> set[int]:
    track_ids: set[int] = set()
    for file_id, section in yaml_sections(text).items():
        if "m_Clips:" not in section:
            continue
        if re.search(r"^\s*m_Name:\s*Markers\s*$", section, re.MULTILINE):
            continue
        track_ids.add(file_id)
    return track_ids


def audit_playables(
    project_root: Path,
    timeline_root: Path,
    playables: list[Path],
    guid_index: dict[str, Path],
) -> list[Finding]:
    findings: list[Finding] = []
    playable_by_guid: dict[str, tuple[Path, set[int]]] = {}

    for playable_path in playables:
        file_label = relative(playable_path, project_root)
        playable_guid = read_guid(playable_path.with_suffix(playable_path.suffix + ".meta"))
        if not playable_guid:
            findings.append(Finding("error", "PLAYABLE_META_MISSING", file_label, "缺少有效 .playable.meta GUID。"))
            continue
        text = read_text(playable_path)
        playable_by_guid[playable_guid] = (playable_path, playable_bindable_track_ids(text))
        for animation_guid in sorted(playable_animation_guids(text)):
            referenced_path = guid_index.get(animation_guid)
            if referenced_path is None or not referenced_path.is_file():
                findings.append(
                    Finding(
                        "error",
                        "ANIMATION_REFERENCE_MISSING",
                        file_label,
                        f"AnimationReferenceAsset GUID {animation_guid} 无法解析。",
                    )
                )

    if not playable_by_guid:
        return findings

    prefabs = sorted(timeline_root.rglob("*.prefab"))
    directors_found: set[str] = set()
    for prefab_path in prefabs:
        text = read_text(prefab_path)
        prefab_label = relative(prefab_path, project_root)
        for section in yaml_sections(text).values():
            playable_match = re.search(
                r"^\s*m_PlayableAsset:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32})",
                section,
                re.MULTILINE,
            )
            if not playable_match:
                continue
            playable_guid = playable_match.group(1)
            if playable_guid not in playable_by_guid:
                continue
            directors_found.add(playable_guid)
            current_entries: list[tuple[int, int]] = []
            stale_guids: set[str] = set()
            for match in re.finditer(
                r"- key:\s*\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-f]{32}),\s*type:\s*\d+\}"
                r"\s*\n\s*value:\s*\{fileID:\s*(-?\d+)\}",
                section,
            ):
                track_id = int(match.group(1))
                binding_guid = match.group(2)
                value_id = int(match.group(3))
                if binding_guid == playable_guid:
                    current_entries.append((track_id, value_id))
                else:
                    stale_guids.add(binding_guid)

            track_ids = playable_by_guid[playable_guid][1]
            valid_entries = [(track_id, value_id) for track_id, value_id in current_entries if value_id != 0]
            if track_ids and not valid_entries:
                findings.append(
                    Finding(
                        "error",
                        "DIRECTOR_BINDINGS_MISSING",
                        prefab_label,
                        "PlayableDirector 指向当前 Timeline，但没有发现当前 Timeline 的有效非空 SceneBinding。",
                    )
                )
            bound_track_ids = {track_id for track_id, value_id in valid_entries}
            for track_id in sorted(track_ids - bound_track_ids):
                findings.append(
                    Finding(
                        "warning",
                        "TRACK_UNBOUND",
                        prefab_label,
                        f"Track fileID {track_id} 未发现当前 Timeline 的非空绑定；请确认是否为有意留空。",
                    )
                )
            if stale_guids:
                stale_text = ", ".join(sorted(stale_guids))
                findings.append(
                    Finding(
                        "warning",
                        "STALE_SCENE_BINDING",
                        prefab_label,
                        f"SceneBindings 还包含其他 Timeline GUID：{stale_text}。",
                    )
                )

    for playable_guid, (playable_path, _) in playable_by_guid.items():
        if playable_guid not in directors_found:
            findings.append(
                Finding(
                    "warning",
                    "DIRECTOR_NOT_FOUND",
                    relative(playable_path, project_root),
                    "在 Timeline 目录下未找到指向此 PlayableAsset 的 Director Prefab；通用嵌入资源可忽略。",
                )
            )
    return findings


def table_section(text: str, name: str, next_name: str) -> str | None:
    start = text.find(f"  {name}:")
    if start < 0:
        return None
    end = text.find(f"  {next_name}:", start)
    return text[start : end if end >= 0 else len(text)]


def table_rows(section: str) -> list[dict[str, str]]:
    starts = list(re.finditer(r"^    - id:\s*(\d+)\s*$", section, re.MULTILINE))
    rows: list[dict[str, str]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(section)
        block = section[start.start() : end]
        row = {"id": start.group(1)}
        for key, value in re.findall(r"^      ([A-Za-z0-9_]+):\s*(.*)$", block, re.MULTILINE):
            row[key] = value.strip()
        rows.append(row)
    return rows


def decode_uint_array(value: str) -> list[int]:
    compact = value.strip()
    if not compact or not re.fullmatch(r"[0-9a-fA-F]+", compact) or len(compact) % 8 != 0:
        return []
    raw = bytes.fromhex(compact)
    return list(struct.unpack("<" + "I" * (len(raw) // 4), raw))


def audit_plot_tables(project_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    table_path = project_root / TABLE_ROOT_RELATIVE_PATH
    if not table_path.is_file():
        return [
            Finding(
                "warning",
                "TABLE_ROOT_NOT_FOUND",
                relative(table_path, project_root),
                "未找到运行时 tTableRoot.asset，跳过剧情 Timeline 外键和分段检查。",
            )
        ]

    text = read_text(table_path)
    plot_section = table_section(text, "tPlot", "tPlotStep")
    step_section = table_section(text, "tPlotStep", "tPlotTimeLine")
    timeline_section = table_section(text, "tPlotTimeLine", "tDecoShopTheme")
    if not plot_section or not step_section or not timeline_section:
        return [
            Finding(
                "warning",
                "PLOT_TABLE_SECTION_MISSING",
                relative(table_path, project_root),
                "无法完整定位 tPlot、tPlotStep、tPlotTimeLine 段，跳过关联检查。",
            )
        ]

    timeline_rows = {int(row["id"]): row for row in table_rows(timeline_section)}
    step_rows = {int(row["id"]): row for row in table_rows(step_section)}
    timeline_step_rows: dict[int, int] = {}
    for step_id, row in step_rows.items():
        if row.get("stepType") == "2" and row.get("stepTypeParam", "").isdigit():
            timeline_step_rows[step_id] = int(row["stepTypeParam"])

    table_label = relative(table_path, project_root)
    for step_id, timeline_id in sorted(timeline_step_rows.items()):
        if timeline_id not in timeline_rows:
            findings.append(
                Finding(
                    "error",
                    "TIMELINE_CONFIG_MISSING",
                    table_label,
                    f"tPlotStep {step_id} 引用的 tPlotTimeLine {timeline_id} 不存在。",
                )
            )

    packed_root = project_root / PACKED_RESOURCES_RELATIVE_ROOT
    for timeline_id, row in sorted(timeline_rows.items()):
        resource_path = row.get("timeLinePath", "")
        if not resource_path:
            findings.append(Finding("error", "TIMELINE_PATH_EMPTY", table_label, f"tPlotTimeLine {timeline_id} 路径为空。"))
            continue
        full_path = packed_root / Path(resource_path)
        if not full_path.is_file():
            findings.append(
                Finding(
                    "error",
                    "TIMELINE_PREFAB_MISSING",
                    table_label,
                    f"tPlotTimeLine {timeline_id} 的资源不存在：{resource_path}",
                )
            )

    for plot_row in table_rows(plot_section):
        plot_id = int(plot_row["id"])
        step_ids = decode_uint_array(plot_row.get("plotStep", ""))
        last_by_path: dict[str, tuple[int, int, int]] = {}
        for step_id in step_ids:
            timeline_id = timeline_step_rows.get(step_id)
            if timeline_id is None or timeline_id not in timeline_rows:
                continue
            row = timeline_rows[timeline_id]
            path = row.get("timeLinePath", "")
            end_time = int(row.get("endTime", "0") or 0)
            keep = int(row.get("closeToDelete", "0") or 0)
            previous = last_by_path.get(path)
            if previous is not None:
                previous_end, previous_keep, previous_timeline_id = previous
                if previous_keep == 1 and end_time > 0 and end_time <= previous_end:
                    findings.append(
                        Finding(
                            "error",
                            "SEGMENT_END_NOT_INCREASING",
                            table_label,
                            f"tPlot {plot_id} 同一路径续播从配置 {previous_timeline_id} 到 {timeline_id}，"
                            f"endTime 未递增（{previous_end} → {end_time}）。",
                        )
                    )
            last_by_path[path] = (end_time, keep, timeline_id)
    return findings


def print_report(project_root: Path, playables: list[Path], findings: list[Finding], as_json: bool) -> None:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    if as_json:
        print(
            json.dumps(
                {
                    "project_root": normalized(project_root.resolve()),
                    "playable_count": len(playables),
                    "errors": errors,
                    "warnings": warnings,
                    "findings": [asdict(item) for item in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(f"Bubble Timeline audit: {len(playables)} playable(s), {errors} error(s), {warnings} warning(s)")
    for item in findings:
        print(f"[{item.severity.upper()}] {item.code} | {item.file} | {item.message}")


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    timeline_root = project_root / TIMELINE_RELATIVE_ROOT
    if not timeline_root.is_dir():
        print(f"Timeline root not found: {timeline_root}", file=sys.stderr)
        return 2

    playables = resolve_scope(project_root, args.timeline, timeline_root)
    if not playables:
        print("No .playable files found in requested scope.", file=sys.stderr)
        return 2

    guid_index = build_guid_index(project_root / "Assets")
    findings = audit_playables(project_root, timeline_root, playables, guid_index)
    if args.timeline is None:
        findings.extend(audit_plot_tables(project_root))
    findings.sort(key=lambda item: (item.severity != "error", item.file, item.code, item.message))
    print_report(project_root, playables, findings, args.json)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
