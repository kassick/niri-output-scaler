#!/usr/bin/env python3

from dataclasses import dataclass
from functools import cache, cached_property, partial
import itertools
import sys
import json
import subprocess
import argparse
from typing import (
    Any,
    Mapping,
    NotRequired,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    TypedDict,
)

OutType = TypeVar("OutType")


def niri_json_from_msg_raw(*msg: str, type: Type[OutType] = list) -> OutType:
    proc = subprocess.Popen(["niri", "msg", "--json", *msg], stdout=subprocess.PIPE)
    proc.wait()
    if proc.returncode != 0:
        raise Exception(f"niri returned non-zero status {proc.returncode}")

    if not proc.stdout:
        raise Exception("No output from niri")

    output = json.loads(proc.stdout.read())

    return output


@cache
def _niri_json_from_msg_cached(*msg: str, type: Type[OutType] = list) -> OutType:
    return niri_json_from_msg_raw(*msg, type=type)


def niri_json_from_msg(*msg: str, type: Type[OutType] = list) -> OutType:
    """Simple wrapper, just to avoid typing information being lost with cache"""
    return _niri_json_from_msg_cached(*msg, type=type)


class WorkspaceEntryDict(TypedDict):
    id: int
    idx: int
    name: NotRequired[str]
    output: NotRequired[str]
    is_active: bool
    is_focused: bool
    active_window_id: int

class OutputLogicalEntryDict(TypedDict):
    x: int
    y: int
    width: int
    height: int
    scale: float
    transform: str

class OutputEntryDict(TypedDict):
    name: str
    make: str
    model: str
    serial: str
    physical_size: Tuple[int, int]
    modes: Sequence[Mapping]
    current_mode: int
    vrr_supported: bool
    vrr_enabled: bool
    logical: OutputLogicalEntryDict

@dataclass
class NiriState:
    workspaces: Sequence[WorkspaceEntryDict]
    outputs: Mapping[str, OutputEntryDict]

    @classmethod
    def new(cls):
        workspaces = niri_json_from_msg(
            "workspaces", type=Sequence[WorkspaceEntryDict]
        )

        outputs = niri_json_from_msg(
            "outputs", type=Mapping[str, OutputEntryDict]
        )

        return cls(workspaces=workspaces, outputs=outputs)

    @cached_property
    def focused_workspace(self) -> WorkspaceEntryDict | None:
        return next((w for w in self.workspaces if w["is_focused"]), None)

    @cached_property
    def active_workspaces(self) -> Sequence[WorkspaceEntryDict]:
        return [w for w in self.workspaces if w["is_active"]]

    @cached_property
    def focused_output(self) -> OutputEntryDict | None:
        if (focused := self.focused_workspace) and (output_name := focused.get("output")):
            return self.outputs.get(output_name)


def main():
    parser = argparse.ArgumentParser(description="Niri Output Scaler")

    parser.add_argument(
        "--scale", "-s", action="append", type=float, help="Target output scale. Can be defined multiple times"
    )

    parser.add_argument(
        "--output", "-o", action="store", type=str, help="The target output. A value of @current will scale the current output",
        default="@current"
    )

    parser.add_argument(
        "--direction", action="store", choices=["forwards", "backwards"], default="forwards"
    )

    args = parser.parse_args()

    niri = NiriState.new()

    if args.output == '@current':
        if not niri.focused_output:
            print("No focused output!", file=sys.stderr)
            sys.exit(1)
        target_output = niri.focused_output
    elif args.output in niri.outputs:
        target_output = niri.outputs[args.output]
    else:
        print(f"Could not find an output named {args.output}", file=sys.stderr)
        sys.exit(1)

    output_name = target_output["name"]
    current_scale = float(target_output["logical"]["scale"])
    target_scales: Sequence[float] = sorted(args.scale)

    next_scale = find_next_scale(current_scale, target_scales, direction=args.direction)
    if next_scale:
        print(f"Scaling {output_name} to {next_scale}")
        result = subprocess.run(["niri", "msg", "output", output_name, "scale", str(next_scale)])
        if result.returncode != 0:
            print("Could not switch to next scale!")
    else:
        print("Did not find a next scale WAT")

def find_next_scale(
    current_scale: float,
    target_scales: Sequence[float],
    direction: str
) -> float | None:


    if not target_scales:
        return None

    target_scale_value = None

    match direction:
        case "forwards":
            for s in target_scales:
                if s > current_scale:
                    target_scale_value = s
                    break
            target_scale_value = target_scale_value or target_scales[0]
        case "backwards":
            for s in reversed(target_scales):
                if s < current_scale:
                    target_scale_value = s
                    break
            target_scale_value = target_scale_value or target_scales[-1]

        case _:
            raise ValueError(f"Invalid Direction {direction}")

    return target_scale_value


if __name__ == "__main__":
    main()
