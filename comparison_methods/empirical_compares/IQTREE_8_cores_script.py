import os
import subprocess
import glob
import re
import csv
from typing import Optional

iqtree_exec = "/workspace/iqtree-3.1.2-Linux/bin/iqtree3"
cal_rf_script = "/workspace/NeuralNJ/examples/cal_rf_distance.py"

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

	rf = float(match.group(1))
	nrf = float(match.group(2))
	return rf, nrf


def collect_gene_files(input_dir: str) -> list[str]:
	patterns = ["*.phy", "*.phylip", "*.fasta", "*.fa", "*.fas", "*.aln"]
	gene_files: list[str] = []
	for pattern in patterns:
		gene_files.extend(glob.glob(os.path.join(input_dir, pattern)))
	return sorted(gene_files)


def solve_dataset(dataset: str) -> list[dict[str, object]]:
	input_dir = f"/workspace/NeuralNJ/empirical/{dataset}"
	output_dir = f"/workspace/IQTree_8_cores_{dataset}_Results"
	abs_output_dir = os.path.abspath(output_dir)
	special_dataset = dataset[0:-1] if dataset == "JarvD5a" else dataset
	ref_tree_path = f"/workspace/concatenation_species_trees/{special_dataset}/{dataset}.IQ-TREE.concatenation.tre"


	os.makedirs(abs_output_dir, exist_ok=True)

	gene_files = collect_gene_files(input_dir)
	if not gene_files:
		print(f"{input_dir} is empty")
		return []

	if not os.path.exists(ref_tree_path):
		print(f"Reference tree does not exist: {ref_tree_path}")
		return []

	print(f"Find {len(gene_files)} gene files. Start running IQ-TREE...")

	for i, msa_path in enumerate(gene_files, 1):
		file_name = os.path.basename(msa_path)
		base_name = os.path.splitext(file_name)[0]
		prefix = os.path.join(abs_output_dir, base_name)
		treefile = prefix + ".treefile"
		if os.path.exists(treefile):
			print(f"[{i}/{len(gene_files)}] Skipping (already done): {file_name}")
			continue

		print(f"[{i}/{len(gene_files)}] Running IQ-TREE: {file_name}...")

		command = [
			iqtree_exec,
			"-s", msa_path,
			"-st", "DNA",
			"-m", "GTR+G",
			"-T", "8",
			"-seed", "2201",
			"-pre", prefix,
			"-quiet",
		]

		try:
			subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
		except subprocess.CalledProcessError as e:
			print(f"Error when running IQ-TREE for {file_name}: {e}")
		except FileNotFoundError:
			print(f"Cannot find IQ-TREE executable: {iqtree_exec}")
			print("Please edit iqtree_exec, for example: iqtree_exec = 'iqtree2' or '/path/to/iqtree3'")
			return []

	print("\nFinish running IQ-TREE for all gene files!")
	print("Start calculating RF and nRF...")

	rows: list[dict[str, object]] = []
	inferred_trees = sorted(glob.glob(os.path.join(abs_output_dir, "*.treefile")))

	for inf_tree_path in inferred_trees:
		tree_name = os.path.basename(inf_tree_path)
		gene_name = tree_name.removesuffix(".treefile")

		rf_cmd = [
			"python", cal_rf_script,
			"--reftree", os.path.abspath(ref_tree_path),
			"--inftree", inf_tree_path,
		]

		try:
			result = subprocess.run(rf_cmd, capture_output=True, text=True, check=True)
			parsed = parse_rf_output(result.stdout.strip())

			if parsed is None:
				print(f"Cannot parse RF/nRF for tree {tree_name}. Output: {result.stdout.strip()}")
				continue

			rf, nrf = parsed
			rows.append({
				"dataset": dataset,
				"gene": gene_name,
				"tree_file": tree_name,
				"rf": rf,
				"nrf": nrf,
			})

		except Exception as e:
			print(f"Error when calculating RF/nRF for tree {tree_name}: {e}")

	if not rows:
		print(f"No valid RF/nRF data for dataset {dataset}.")
		return []

	rf_distances = [float(row["rf"]) for row in rows]
	nrf_distances = [float(row["nrf"]) for row in rows]
	avg_rf = sum(rf_distances) / len(rf_distances)
	avg_nrf = sum(nrf_distances) / len(nrf_distances)

	dataset_tsv = os.path.join(abs_output_dir, f"{dataset}_iqtree_rf_nrf_results.tsv")
	with open(dataset_tsv, "w", encoding="utf-8", newline="") as f:
		writer = csv.DictWriter(
			f,
			fieldnames=["dataset", "gene", "tree_file", "rf", "nrf"],
			delimiter="\t",
		)
		writer.writeheader()
		writer.writerows(rows)

	summary_lines = [
		"=" * 50,
		f"KẾT QUẢ ĐÁNH GIÁ IQ-TREE TRÊN BỘ {dataset}",
		f"Số lượng gen hợp lệ: {len(rows)}/{len(gene_files)}",
		f"Khoảng cách RF trung bình: {avg_rf:.4f}",
		f"Khoảng cách nRF trung bình: {avg_nrf:.4f}",
		f"File RF/nRF từng gene: {dataset_tsv}",
		"=" * 50,
	]

	summary_text = "\n".join(summary_lines)
	print("\n" + summary_text)

	summary_file = os.path.join(abs_output_dir, f"{dataset}_iqtree_summary.txt")
	with open(summary_file, "w", encoding="utf-8") as f:
		f.write(summary_text + "\n")

	print(f"Wrote summary to: {summary_file}")
	print(f"Wrote RF/nRF per gene to: {dataset_tsv}")

	return rows


if __name__ == "__main__":
	datasets = ["SongD1", "JarvD5a", "TarvD7", "WickD3b"]

	all_rows: list[dict[str, object]] = []

	for dataset in datasets:
		rows = solve_dataset(dataset=dataset)
		all_rows.extend(rows)

	combined_tsv = "/workspace/IQTree_8_cores_rf_nrf_results_all_datasets.tsv"
	if all_rows:
		with open(combined_tsv, "w", encoding="utf-8", newline="") as f:
			writer = csv.DictWriter(
				f,
				fieldnames=["dataset", "gene", "tree_file", "rf", "nrf"],
				delimiter="\t",
			)
			writer.writeheader()
			writer.writerows(all_rows)
		print(f"Wrote combined RF/nRF results to: {combined_tsv}")
	else:
		print("No RF/nRF data to write combined TSV.")
