"""Entry point for the speech-to-text desktop helper."""
from __future__ import annotations

import argparse
import logging
from typing import List

from app.gui import run_app
from app.transcriber import WhisperXTranscriber


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Speech to text helper using WhisperX")
    parser.add_argument(
        "--whisperx-cmd",
        default="whisperx",
        help="Name or path of the WhisperX executable (default: whisperx)",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        help="Device passed to WhisperX, e.g. cuda or cpu (default: cuda)",
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        help="Model passed to WhisperX (default: large-v3)",
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        help="Optional compute type such as float16 or int8",
    )
    parser.add_argument(
        "--extra-args",
        nargs=argparse.REMAINDER,
        default=None,
        help="Additional parameters forwarded verbatim to WhisperX",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    transcriber = WhisperXTranscriber(
        whisperx_command=args.whisperx_cmd,
        device=args.device,
        model=args.model,
        compute_type=args.compute_type,
        extra_args=args.extra_args,
    )

    run_app(transcriber)


if __name__ == "__main__":
    main()
