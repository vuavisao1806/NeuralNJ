import os
import subprocess
import glob
import re
import csv

raxml_exec = "/workspace/standard-RAxML/raxmlHPC-PTHREADS"
cal_rf_script = "/workspace/NeuralNJ/examples/cal_rf_distance.py"

def parse_rf_output(output: str) -> tuple[float, float]:
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

def solve_dataset(dataset: str) -> None:
	input_dir = f"/workspace/NeuralNJ/empirical/{dataset}"
	output_dir = f"/workspace/RAxML_8_cores_{dataset}_Results"
	abs_output_dir = os.path.abspath(output_dir)
	special_dataset = dataset[0:-1] if dataset == "JarvD5a" else dataset
	ref_tree_path = f"/workspace/concatenation_species_trees/{special_dataset}/{dataset}.IQ-TREE.concatenation.tre"

	if not os.path.exists(abs_output_dir):
		os.makedirs(abs_output_dir)

	gene_files = glob.glob(os.path.join(input_dir, "*.phy")) + glob.glob(os.path.join(input_dir, "*.fasta")) + glob.glob(os.path.join(input_dir, "*.aln"))

	if not gene_files:
		print(f"{input_dir} is empty")
		exit(1)

	print(f"Find {len(gene_files)} file gen. Start running RAxML...")

	for i, msa_path in enumerate(gene_files, 1):
		# Lấy tên file gốc làm tiền tố (ví dụ: "gene_001.phy" -> "gene_001")
		file_name = os.path.basename(msa_path)
		base_name = os.path.splitext(file_name)[0]
		best_tree = os.path.join(abs_output_dir, f"RAxML_bestTree.{base_name}")
		if os.path.exists(best_tree):
			print(f"[{i}/{len(gene_files)}] Skipping (already done): {file_name}")
			continue
		print(f"[{i}/{len(gene_files)}] Running: {file_name}...")
		
		command = [
			raxml_exec,
			"-T", "8",
			"-m", "GTRGAMMA",      # Mô hình GTR+G cho DNA
			"-p", "2201",         # Random seed cho cây Parsimony khởi tạo
			"--no-bfgs",           # Tắt BFGS cho DNA theo yêu cầu của bài báo
			"-s", msa_path,        # File đầu vào
			"-n", base_name,       # Tên tiền tố đầu ra
			"-w", abs_output_dir   # Thư mục đầu ra (đường dẫn tuyệt đối)
		]
		
		try:
			# Chạy RAxML (ẩn output dài dòng của RAxML trên terminal)
			#print("Just comment")
			subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
		except subprocess.CalledProcessError as e:
			print(f"Error when running RAxML for {file_name}")

	print("\nFinish run RAxML for all instances!")

	print("Start calc average RF and nRF")
	rows: list[dict[str, object]] = []
	inferred_trees = sorted(glob.glob(os.path.join(abs_output_dir, "RAxML_bestTree.*")))

	for inf_tree_path in inferred_trees:
		tree_name = os.path.basename(inf_tree_path)
		gene_name = tree_name.replace("RAxML_bestTree.", "", 1)

		rf_cmd = [
			"python", cal_rf_script,
			"--reftree", os.path.abspath(ref_tree_path),
			"--inftree", inf_tree_path,
		]

		try:
			result = subprocess.run(rf_cmd, capture_output=True, text=True, check=True)
			parsed = parse_rf_output(result.stdout.strip())

			if parsed is None:
				print(f"Không parse được RF/nRF cho cây {tree_name}. Output: {result.stdout.strip()}")
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
			print(f"Lỗi tính RF/nRF cho cây {tree_name}: {e}")

	if not rows:
		print(f"Không có dữ liệu RF/nRF hợp lệ cho bộ {dataset}.")
		return []

	rf_distances = [float(row["rf"]) for row in rows]
	nrf_distances = [float(row["nrf"]) for row in rows]
	avg_rf = sum(rf_distances) / len(rf_distances)
	avg_nrf = sum(nrf_distances) / len(nrf_distances)

	# TSV riêng cho từng dataset. File này dùng được ngay với script R.
	dataset_tsv = os.path.join(abs_output_dir, f"{dataset}_rf_nrf_results.tsv")
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
		f"KẾT QUẢ ĐÁNH GIÁ TRÊN BỘ {dataset}",
		f"Số lượng gen hợp lệ: {len(rows)}/{len(gene_files)}",
		f"Khoảng cách RF trung bình: {avg_rf:.4f}",
		f"Khoảng cách nRF trung bình: {avg_nrf:.4f}",
		f"File RF/nRF từng gene: {dataset_tsv}",
		"=" * 50,
	]

	summary_text = "\n".join(summary_lines)
	print("\n" + summary_text)

	summary_file = os.path.join(abs_output_dir, f"{dataset}_summary.txt")
	with open(summary_file, "w", encoding="utf-8") as f:
		f.write(summary_text + "\n")

	print(f"Đã ghi summary vào: {summary_file}")
	print(f"Đã ghi RF/nRF từng gene vào: {dataset_tsv}")

	return rows

if __name__ == "__main__":
	datasets = ["SongD1", "JarvD5a", "TarvD7", "WickD3b"]

	all_rows: list[dict[str, object]] = []
	all_nrf_distances: dict[str, list[float]] = {}

	for dataset in datasets:
		rows = solve_dataset(dataset=dataset)
		all_rows.extend(rows)
		all_nrf_distances[dataset] = [float(row["nrf"]) for row in rows]

	# TSV tổng hợp cho tất cả dataset. Đây là file tiện nhất để đưa cho R.
	combined_tsv = "/workspace/RAxML_8_cores_rf_nrf_results_all_datasets.tsv"
	if all_rows:
		with open(combined_tsv, "w", encoding="utf-8", newline="") as f:
			writer = csv.DictWriter(
				f,
				fieldnames=["dataset", "gene", "tree_file", "rf", "nrf"],
				delimiter="\t",
			)
			writer.writeheader()
			writer.writerows(all_rows)
		print(f"Đã ghi RF/nRF tổng hợp vào: {combined_tsv}")
	else:
		print("Không có dữ liệu RF/nRF nào để ghi file tổng hợp.")
