#!/usr/bin/env python3
"""
Filter alignment instances by number of nucleotide sites using Biopython.

Install dependency if needed:
    pip install biopython

Examples:
    python filter_instances_by_sites_biopython.py \
        --input-dir /workspace/NeuralNJ/empirical/SongD1 \
        --max-sites 17000 \
        --output-tsv SongD1_le_17000.tsv \
        --copy-to /workspace/NeuralNJ/empirical_filtered/SongD1_le_17000

    python filter_instances_by_sites_biopython.py \
        --input-dir /workspace/NeuralNJ/empirical/WickD3b \
        --max-sites 4400 \
        --format fasta
"""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path
from typing import Iterable

from Bio import AlignIO


SUPPORTED_EXTENSIONS = (".phy", ".phylip", ".fasta", ".fa", ".fas", ".aln")


def guess_formats(path: Path, forced_format: str | None = None) -> list[str]:
    """
    Return candidate Biopython AlignIO formats.

    Biopython format names:
        fasta
        phylip
        phylip-relaxed
    """
    if forced_format:
        return [forced_format]

    suffix = path.suffix.lower()

    if suffix in {".fasta", ".fa", ".fas", ".aln"}:
        # Many .aln files in your datasets are FASTA-like.
        return ["fasta", "phylip-relaxed", "phylip"]

    if suffix in {".phy", ".phylip"}:
        return ["phylip-relaxed", "phylip", "fasta"]

    return ["fasta", "phylip-relaxed", "phylip"]


def read_alignment(path: Path, forced_format: str | None = None):
    errors: list[str] = []

    for fmt in guess_formats(path, forced_format):
        try:
            alignment = AlignIO.read(str(path), fmt)
            return fmt, alignment
        except Exception as e:
            errors.append(f"{fmt}: {e}")

    raise ValueError("Cannot read alignment. Tried formats: " + " | ".join(errors))


def count_sites(path: Path, forced_format: str | None = None) -> tuple[str, int, int]:
    """
    Return:
        format_used, num_taxa, num_sites

    In Biopython MultipleSeqAlignment:
        len(alignment) = number of sequences/taxa
        alignment.get_alignment_length() = number of sites/columns
    """
    fmt, alignment = read_alignment(path, forced_format)

    num_taxa = len(alignment)
    num_sites = alignment.get_alignment_length()

    if num_taxa <= 0:
        raise ValueError("Alignment has no sequences")

    if num_sites <= 0:
        raise ValueError("Alignment has zero sites")

    return fmt, num_taxa, num_sites


def iter_alignment_files(input_dir: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for path in input_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path
    else:
        for path in input_dir.iterdir():
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter alignment instances by number of nucleotide sites using Biopython."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Folder containing alignment instances.",
    )
    parser.add_argument(
        "--max-sites",
        required=True,
        type=int,
        help="Keep instances with number of sites <= this value.",
    )
    parser.add_argument(
        "--output-tsv",
        default=None,
        help="Output TSV file. Default: <input_dir.name>_le_<max_sites>_sites.tsv",
    )
    parser.add_argument(
        "--copy-to",
        default=None,
        help="Optional folder. If set, copy accepted instances into this folder.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan input directory recursively.",
    )
    parser.add_argument(
        "--format",
        choices=["fasta", "phylip", "phylip-relaxed"],
        default=None,
        help="Force input format. If omitted, the script tries to auto-detect.",
    )
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Also write failed/unreadable files into the TSV.",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    if args.output_tsv:
        output_tsv = Path(args.output_tsv).resolve()
    else:
        output_tsv = Path(f"{input_dir.name}_le_{args.max_sites}_sites.tsv").resolve()

    copy_to = Path(args.copy_to).resolve() if args.copy_to else None
    if copy_to:
        copy_to.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    accepted = 0
    rejected = 0
    failed = 0

    files = sorted(iter_alignment_files(input_dir, args.recursive))

    for path in files:
        try:
            fmt, num_taxa, num_sites = count_sites(path, args.format)
            keep = num_sites <= args.max_sites

            if keep:
                accepted += 1
                if copy_to:
                    relative_path = path.relative_to(input_dir)
                    destination = copy_to / relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
            else:
                rejected += 1

            rows.append({
                "file": str(path),
                "filename": path.name,
                "format_used": fmt,
                "num_taxa": num_taxa,
                "num_sites": num_sites,
                "max_sites": args.max_sites,
                "keep": "yes" if keep else "no",
                "reason": "" if keep else f"num_sites > {args.max_sites}",
            })

        except Exception as e:
            failed += 1
            if args.include_failed:
                rows.append({
                    "file": str(path),
                    "filename": path.name,
                    "format_used": "",
                    "num_taxa": "",
                    "num_sites": "",
                    "max_sites": args.max_sites,
                    "keep": "failed",
                    "reason": str(e),
                })

    fieldnames = [
        "file",
        "filename",
        "format_used",
        "num_taxa",
        "num_sites",
        "max_sites",
        "keep",
        "reason",
    ]

    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with output_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 60)
    print("FILTER ALIGNMENT INSTANCES BY NUMBER OF SITES")
    print(f"Input folder       : {input_dir}")
    print(f"Max sites          : {args.max_sites}")
    print(f"Total files scanned: {len(files)}")
    print(f"Accepted           : {accepted}")
    print(f"Rejected           : {rejected}")
    print(f"Failed             : {failed}")
    print(f"Output TSV         : {output_tsv}")
    if copy_to:
        print(f"Copied accepted to : {copy_to}")
    print("=" * 60)


if __name__ == "__main__":
    main()
