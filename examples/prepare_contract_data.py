"""
Convert raw contracts dataset, into Dataset format.
Runs rust-code-analysis-cli to generate code metrics.
"""

import zipfile
import os
import urllib.request
import tarfile
import subprocess
import re
import time

from datasets import Dataset

from nearai.dataset import get_dataset
from nearai.registry import dataset
from nearai.config import DATA_FOLDER

COLUMNS = [
    "filename",
    "code",
    "function_names",
    "struct_names",
    "metrics",
]

tools_dir = DATA_FOLDER / "tools"
analyzer_name = "rust-code-analysis-cli"
analyzer = tools_dir / analyzer_name / analyzer_name
analyzer_url = (
    "https://github.com/mozilla/rust-code-analysis/releases/download/v0.0.25/rust-code-analysis-linux-cli-x86_64.tar.gz"
)


def extract_code_element(code, code_element):
    lines = code.split("\n")
    items = ""

    type_expr = r".*\s*" + re.escape(code_element) + r"\s+\w+"
    type_expr2 = re.escape(code_element) + r"\s+(\w+)"
    for line in lines:
        if re.match(type_expr, line):  # Use regular expression to find " fn " function declarations
            function_name = re.findall(type_expr2, line)[0]  # Extract the function name using capture group
            items += function_name
            items += ", "

    return items


def main():
    dataset_name = "rust_contracts_20240529"
    dataset_base_dir = DATA_FOLDER / "datasets" / dataset_name

    # Download the raw dataset. This will download the zip file
    dataset_path = get_dataset(f"{dataset_name}/raw/v0")

    uncompressed = dataset_base_dir / "uncompressed"
    processed_dataset = dataset_base_dir / "processed"

    if not uncompressed.exists():
        with zipfile.ZipFile(str(dataset_path) + f"/{dataset_name}.zip", "r") as zip_ref:
            zip_ref.extractall(uncompressed)

    if not os.path.exists(tools_dir):
        os.makedirs(tools_dir)
    if not analyzer.exists():
        print("Downloading rust-code-analysis")
        archive = analyzer_name + ".tar.gz"
        urllib.request.urlretrieve(analyzer_url, tools_dir / archive)
        with tarfile.open(tools_dir / archive) as f:
            f.extractall(tools_dir / analyzer_name)
        subprocess.check_call(["chmod", "+x", analyzer])

    if not processed_dataset.exists():
        ds = {col: [] for col in COLUMNS}
        code_hashes = set()
        duplicates = 0
        empty = 0
        errors = 0
        processed_count = 0

        for file in uncompressed.glob("*/*/*/*.rs"):
            if processed_count % 100 == 0 and processed_count > 0:
                print(f"Processed {processed_count} files, at time: {time.time()}")
            processed_count += 1
            try:
                code = file.read_text()
                if not code:
                    empty += 1
                    continue
                # remove duplicates based on code hash
                code_hash = hash(code)
                if code_hash in code_hashes:
                    duplicates += 1
                    continue
                code_hashes.add(code_hash)

                function_names = extract_code_element(code, "fn")
                struct_names = extract_code_element(code, "struct")

                result = subprocess.run([analyzer, "-m", "-O", "json", "-p", str(file)], capture_output=True, text=True)
            except Exception as e:
                print(f"Error processing {file}: {e}")
                errors += 1
                continue

            ds["filename"].append(file.name)
            ds["code"].append(code)
            ds["function_names"].append(function_names)
            ds["struct_names"].append(struct_names)
            ds["metrics"].append(result.stdout)

        print(f"Removed {duplicates} duplicates")
        print(f"Encountered {empty} empty files and {errors} errors")
        ds = Dataset.from_dict(ds)
        ds.save_to_disk(str(processed_dataset))

    dataset.upload(
        path=processed_dataset,
        s3_path=f"{dataset_name}/transformed/v0",
        author="prepare_contract_data.py",
        description="NEAR Protocol contracts dataset with code metrics, function and struct names.",
        name="rust_contracts",
        details=None,
        show_entry=True,
        tags=["dataset", "contracts", "near", "rust"],
    )


if __name__ == "__main__":
    main()
