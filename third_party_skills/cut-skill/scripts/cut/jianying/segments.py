"""cut.jianying.segments — 片段裁切操作。

提供 split / trim / remove / move 等针对 Segment 的高层操作。
所有操作只修改 draft 内存结构，需调 draft.save() 持久化。
"""
from __future__ import annotations

import copy
from typing import Optional, Union

from .draft import Draft, Segment, TimeRange, _new_id, _us, _hms, SegmentNotFoundError


# ---------------------------------------------------------------------------
# Split — 在指定时间点把一个片段切成两段
# ---------------------------------------------------------------------------

def split_segment(draft: Draft, segment: Segment, at_us: Union[int, float, str],
                  unit: str = "us") -> tuple:
    """在 at_us 处把 segment 切成两段。

    切点必须在 segment 内部（start < at < end）。
    返回 (left_segment_id, right_segment_id)。

    原理：
    - 原 segment 保留前半段，target_timerange.duration 缩短
    - 新 segment 继承后半段，target_timerange.start = at_us
    - source_timerange 同步切分，保持素材内容连续
    - 关键帧按切点分配到左右段，右段关键帧重新生成 ID 避免冲突
    """
    at = _us(at_us, unit)
    if not (segment.start_us < at < segment.end_us):
        raise ValueError(
            f"切点 {_hms(at)} 不在片段内 [{_hms(segment.start_us)}, {_hms(segment.end_us)})"
        )

    # 找到原始 segment dict
    raw = draft.get_segment_raw(segment.id)
    if not raw:
        raise SegmentNotFoundError(segment.id)

    # 计算左右两段的 source 切分点
    left_target_dur = at - segment.start_us
    right_target_dur = segment.end_us - at

    # source 切分按 speed 推算；clamp 防止数据不一致导致负数
    speed = segment.speed or 1.0
    left_source_dur = int(left_target_dur * speed)
    # 防御：left_source_dur 不能超过原 source 时长
    left_source_dur = max(0, min(left_source_dur, segment.source_duration_us))
    right_source_dur = max(0, segment.source_duration_us - left_source_dur)

    # 关键帧按切点分配：左段保留 time <= at 的，右段保留 time > at 的（重新生成 ID）
    original_keyframes = raw.get("common_keyframes", [])
    left_keyframes = []
    right_keyframes = []
    for kf in original_keyframes:
        kf_time = int(kf.get("time", 0))
        if kf_time <= at:
            left_keyframes.append(kf)
        else:
            kf_copy = copy.deepcopy(kf)
            kf_copy["id"] = _new_id()
            right_keyframes.append(kf_copy)

    # 修改左段
    raw["target_timerange"] = TimeRange(segment.start_us, left_target_dur).to_dict()
    raw["source_timerange"] = TimeRange(segment.source_start_us, left_source_dur).to_dict()
    raw["common_keyframes"] = left_keyframes

    # 创建右段（深拷贝后更新关键字段）
    right = copy.deepcopy(raw)
    right["id"] = _new_id()
    right["target_timerange"] = TimeRange(at, right_target_dur).to_dict()
    right["source_timerange"] = TimeRange(
        segment.source_start_us + left_source_dur, right_source_dur
    ).to_dict()
    right["common_keyframes"] = right_keyframes
    # extra_material_refs 不应被复制到右段（特效作用域不应自动延续）
    right["extra_material_refs"] = []

    # 找到 track 并在原位置后插入右段
    for t in draft.tracks_raw:
        if t.get("id") == segment.track_id:
            segs = t.get("segments", [])
            for i, s in enumerate(segs):
                if s.get("id") == segment.id:
                    segs.insert(i + 1, right)
                    break
            break

    draft.extend_duration()
    return segment.id, right["id"]


def split_track_at(draft: Draft, track_id: str, at_us: Union[int, float, str],
                   unit: str = "us") -> list:
    """在 track 的 at_us 处切分所有跨过该时间点的 segment。

    返回 [(left_id, right_id), ...]
    """
    at = _us(at_us, unit)
    track = draft.get_track(track_id)
    results = []
    # 复制一份避免修改中迭代
    for seg in list(track.segments):
        if seg.start_us < at < seg.end_us:
            results.append(split_segment(draft, seg, at))
    return results


# ---------------------------------------------------------------------------
# Trim — 调整片段入点/出点
# ---------------------------------------------------------------------------

def trim_segment(draft: Draft, segment: Segment,
                 new_start_us: Optional[Union[int, float, str]] = None,
                 new_end_us: Optional[Union[int, float, str]] = None,
                 unit: str = "us") -> None:
    """调整片段的入点/出点。

    - new_start_us: 新入点（时间轴坐标）。None 表示不变。
    - new_end_us: 新出点。None 表示不变。
    - 只能"收缩"片段，不能扩展到素材范围外。

    入点变更会同步调整 source_timerange.start。
    """
    raw = draft.get_segment_raw(segment.id)
    if not raw:
        raise SegmentNotFoundError(segment.id)

    new_start = _us(new_start_us, unit) if new_start_us is not None else segment.start_us
    new_end = _us(new_end_us, unit) if new_end_us is not None else segment.end_us

    if new_start >= new_end:
        raise ValueError(f"new_start({new_start}) >= new_end({new_end})")

    # 计算新 source 入点
    speed = segment.speed or 1.0
    delta_start = new_start - segment.start_us
    # delta_start 可正可负：正=入点后移（source 入点也后移），负=入点前移（source 入点前移）
    new_source_start = segment.source_start_us + int(delta_start * speed)
    if new_source_start < 0:
        # source 入点不能为负，修正回 0 并同步调整 target 入点
        new_source_start = 0
    new_target_dur = new_end - new_start
    new_source_dur = int(new_target_dur * speed)
    if new_source_dur <= 0:
        raise ValueError(f"trim 后 source 时长为 0 或负数: {new_source_dur}")

    raw["target_timerange"] = TimeRange(new_start, new_target_dur).to_dict()
    raw["source_timerange"] = TimeRange(new_source_start, new_source_dur).to_dict()

    draft.extend_duration()


def trim_by_source(draft: Draft, segment: Segment,
                   source_in_us: Optional[int] = None,
                   source_out_us: Optional[int] = None) -> None:
    """按素材内部时间调整入点/出点。"""
    raw = draft.get_segment_raw(segment.id)
    if not raw:
        raise SegmentNotFoundError(segment.id)

    new_src_in = source_in_us if source_in_us is not None else segment.source_start_us
    new_src_out = source_out_us if source_out_us is not None else (
        segment.source_start_us + segment.source_duration_us
    )
    if new_src_in >= new_src_out:
        raise ValueError("source_in >= source_out")
    if new_src_in < 0:
        raise ValueError("source_in 不能为负")

    speed = segment.speed or 1.0
    new_source_dur = new_src_out - new_src_in
    new_target_dur = int(new_source_dur / speed)

    raw["source_timerange"] = TimeRange(new_src_in, new_source_dur).to_dict()
    raw["target_timerange"] = TimeRange(segment.start_us, new_target_dur).to_dict()
    draft.extend_duration()


# ---------------------------------------------------------------------------
# Remove / Ripple Delete
# ---------------------------------------------------------------------------

def remove_segment(draft: Draft, segment_id: str, ripple: bool = False) -> None:
    """删除片段。

    - ripple=False: 仅删除，后面片段不动（留下空隙）
    - ripple=True: 删除后把同 track 后面片段往前移，填补空隙，并同步移动关键帧
    """
    seg = draft.get_segment_raw(segment_id)
    if not seg:
        raise SegmentNotFoundError(segment_id)

    # 找 track
    target_track = None
    for t in draft.tracks_raw:
        if any(s.get("id") == segment_id for s in t.get("segments", [])):
            target_track = t
            break
    if not target_track:
        return

    segs = target_track["segments"]
    idx = next(i for i, s in enumerate(segs) if s.get("id") == segment_id)
    removed = segs.pop(idx)

    if ripple:
        removed_tt = removed.get("target_timerange", {})
        removed_start = int(removed_tt.get("start", 0))
        removed_dur = int(removed_tt.get("duration", 0))
        removed_end = removed_start + removed_dur
        shift = removed_dur

        # 只移动真正在 removed 之后的片段（start >= removed_end），避免误移重叠段
        for s in segs[idx:]:
            tt = s.get("target_timerange")
            if not tt:
                continue  # 无 target_timerange 的 segment 跳过，不静默修改
            s_start = int(tt.get("start", 0))
            if s_start >= removed_end:
                tt["start"] = s_start - shift
                # 同步移动关键帧时间
                for kf in s.get("common_keyframes", []):
                    kf["time"] = int(kf.get("time", 0)) - shift

    # 删除片段后用 recalc_duration（不是 extend_duration，后者只增不减）
    draft.recalc_duration()


# ---------------------------------------------------------------------------
# Move — 移动片段
# ---------------------------------------------------------------------------

def move_segment(draft: Draft, segment_id: str,
                 new_start_us: Optional[Union[int, float, str]] = None,
                 new_track_id: Optional[str] = None,
                 unit: str = "us") -> None:
    """移动片段到新位置/新轨道。

    若跨轨道移动，会更新 raw["track_id"] 字段。
    """
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise SegmentNotFoundError(segment_id)

    if new_start_us is not None:
        ns = _us(new_start_us, unit)
        tt = raw.get("target_timerange")
        if tt is None:
            tt = {}
            raw["target_timerange"] = tt
        tt["start"] = ns

    if new_track_id is not None and new_track_id != raw.get("track_id"):
        # 从原 track 移除
        for t in draft.tracks_raw:
            segs = t.get("segments", [])
            for i, s in enumerate(segs):
                if s.get("id") == segment_id:
                    segs.pop(i)
                    break
        # 加到新 track
        for t in draft.tracks_raw:
            if t.get("id") == new_track_id:
                t.setdefault("segments", []).append(raw)
                raw["track_id"] = new_track_id  # 更新 track_id 字段
                break

    draft.extend_duration()
