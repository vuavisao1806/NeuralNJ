import os
import glob
import re
import csv
import argparse
import subprocess
from typing import Optional

# Script tính RF/nRF từ các cây đã inference sẵn.
# Không chạy IQ-TREE, không chạy RAxML.
# Input chính:
#   1. Folder chứa inferred trees
#   2. Reference tree / concatenation tree
# Output:
#   1. TSV chứa RF/nRF từng cây
#   2. Summary txt chứa average RF/nRF

DEFAULT_CAL_RF_SCRIPT = "/workspace/NeuralNJ/examples/cal_rf_distance.py"


def parse_rf_output(output: str) -> Optional[tuple[float, float]]:
	"""
	Parse output từ cal_rf_distance.py.

	Expected output:
		RF distance: 12, Normalized RF distance: 0.3157894736842105
	"""
	match = re.search(
		r"RF distance:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*"
		r"Normalized RF distance:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
		output,
	)
	if not match:
		return None

	return float(match.group(1)), float(match.group(2))


def collect_tree_files(tree_dir: str, pattern: str) -> list[str]:
	"""Lấy danh sách cây trong folder theo pattern."""
	tree_files = sorted(glob.glob(os.path.join(tree_dir, pattern)))
	return [path for path in tree_files if os.path.isfile(path)]


def infer_gene_name(tree_path: str, strip_prefix: str = "", strip_suffix: str = "") -> str:
	"""
	Tạo gene/tree name từ tên file.

	Ví dụ:
		RAxML_bestTree.gene1 -> gene1 nếu strip_prefix="RAxML_bestTree."
		gene1.treefile       -> gene1 nếu strip_suffix=".treefile"
	"""
	name = os.path.basename(tree_path)

	if strip_prefix and name.startswith(strip_prefix):
		name = name[len(strip_prefix):]

	if strip_suffix and name.endswith(strip_suffix):
		name = name[:-len(strip_suffix)]
	else:
		# Nếu không truyền strip_suffix, bỏ extension cuối cùng cho gọn.
		name = os.path.splitext(name)[0]

	return name


def calculate_for_existing_trees(
	dataset: str,
	tree_dir: str,
	ref_tree_path: str,
	output_dir: str,
	cal_rf_script: str,
	pattern: str,
	strip_prefix: str,
	strip_suffix: str,
) -> list[dict[str, object]]:
	abs_tree_dir = os.path.abspath(tree_dir)
	abs_ref_tree_path = os.path.abspath(ref_tree_path)
	abs_output_dir = os.path.abspath(output_dir)
	os.makedirs(abs_output_dir, exist_ok=True)

	if not os.path.isdir(abs_tree_dir):
		raise FileNotFoundError(f"Tree folder does not exist: {abs_tree_dir}")

	if not os.path.exists(abs_ref_tree_path):
		raise FileNotFoundError(f"Reference tree does not exist: {abs_ref_tree_path}")

	tree_files = collect_tree_files(abs_tree_dir, pattern)
	if not tree_files:
		print(f"No tree files found in {abs_tree_dir} with pattern: {pattern}")
		return []

	print(f"Dataset: {dataset}")
	print(f"Reference tree: {abs_ref_tree_path}")
	print(f"Tree folder: {abs_tree_dir}")
	print(f"Found {len(tree_files)} inferred tree files. Start calculating RF/nRF...")

	rows: list[dict[str, object]] = []

	for i, inf_tree_path in enumerate(tree_files, 1):
		tree_file = os.path.basename(inf_tree_path)
		gene_name = infer_gene_name(tree_file, strip_prefix=strip_prefix, strip_suffix=strip_suffix)

		print(f"[{i}/{len(tree_files)}] Calculating: {tree_file}")

		rf_cmd = [
			"python",
			cal_rf_script,
			"--reftree",
			abs_ref_tree_path,
			"--inftree",
			inf_tree_path,
		]

		try:
			result = subprocess.run(rf_cmd, capture_output=True, text=True, check=True)
			parsed = parse_rf_output(result.stdout.strip())

			if parsed is None:
				print(f"Cannot parse RF/nRF for {tree_file}. Output: {result.stdout.strip()}")
				continue

			rf, nrf = parsed
			rows.append({
				"dataset": dataset,
				"gene": gene_name,
				"tree_file": tree_file,
				"rf": rf,
				"nrf": nrf,
			})

		except subprocess.CalledProcessError as e:
			print(f"Error calculating RF/nRF for {tree_file}")
			if e.stderr:
				print(e.stderr.strip())
		except Exception as e:
			print(f"Error calculating RF/nRF for {tree_file}: {e}")

	if not rows:
		print(f"No valid RF/nRF results for dataset {dataset}.")
		return []

	rf_distances = [float(row["rf"]) for row in rows]
	nrf_distances = [float(row["nrf"]) for row in rows]
	avg_rf = sum(rf_distances) / len(rf_distances)
	avg_nrf = sum(nrf_distances) / len(nrf_distances)

	result_tsv = os.path.join(abs_output_dir, f"{dataset}_rf_nrf_results.tsv")
	with open(result_tsv, "w", encoding="utf-8", newline="") as f:
		writer = csv.DictWriter(
			f,
			fieldnames=["dataset", "gene", "tree_file", "rf", "nrf"],
			delimiter="\t",
		)
		writer.writeheader()
		writer.writerows(rows)

	summary_lines = [
		"=" * 50,
		f"KẾT QUẢ ĐÁNH GIÁ TRÊN BỘ {dataset}",
		f"Số lượng cây hợp lệ: {len(rows)}/{len(tree_files)}",
		f"Khoảng cách RF trung bình: {avg_rf:.4f}",
		f"Khoảng cách nRF trung bình: {avg_nrf:.4f}",
		f"File RF/nRF từng cây: {result_tsv}",
		"=" * 50,
	]

	summary_text = "\n".join(summary_lines)
	print("\n" + summary_text)

	summary_file = os.path.join(abs_output_dir, f"{dataset}_summary.txt")
	with open(summary_file, "w", encoding="utf-8") as f:
		f.write(summary_text + "\n")

	print(f"Saved summary to: {summary_file}")
	print(f"Saved RF/nRF TSV to: {result_tsv}")

	return rows


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Calculate RF/nRF from an existing folder of inferred trees. No IQ-TREE/RAxML run step."
	)
	parser.add_argument("--dataset", required=True, help="Dataset name, e.g. SongD1")
	parser.add_argument("--tree-dir", required=True, help="Folder containing inferred tree files")
	parser.add_argument("--ref-tree", required=True, help="Reference/concatenation tree file")
	parser.add_argument("--output-dir", required=True, help="Folder to write TSV and summary")
	parser.add_argument("--cal-rf-script", default=DEFAULT_CAL_RF_SCRIPT, help="Path to cal_rf_distance.py")
	parser.add_argument(
		"--pattern",
		default="*.treefile",
		help="Glob pattern for inferred trees inside --tree-dir. Examples: '*.treefile', 'RAxML_bestTree.*', '*.nwk', '*.tre'",
	)
	parser.add_argument(
		"--strip-prefix",
		default="",
		help="Optional filename prefix to remove when creating gene names, e.g. 'RAxML_bestTree.'",
	)
	parser.add_argument(
		"--strip-suffix",
		default="",
		help="Optional filename suffix to remove when creating gene names, e.g. '.treefile'",
	)

	args = parser.parse_args()

	calculate_for_existing_trees(
		dataset=args.dataset,
		tree_dir=args.tree_dir,
		ref_tree_path=args.ref_tree,
		output_dir=args.output_dir,
		cal_rf_script=args.cal_rf_script,
		pattern=args.pattern,
		strip_prefix=args.strip_prefix,
		strip_suffix=args.strip_suffix,
	)


if __name__ == "__main__":
	main()