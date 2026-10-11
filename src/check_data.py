"""E0 — kiểm tra dữ liệu — [Trúc]. ĐÃ IMPLEMENT. Báo PASS/FAIL từng mục.

Kiểm:
  1. Đúng schema (đủ cột, giá trị hợp lệ).
  2. Không rò rỉ split (origin không ở cả train/val lẫn test).
  3. P-low entropy thực sự thấp hơn P-seen/unseen cùng là pack.
  4. DiE xác nhận G1 bị nhận là packed (tiền đề).
  5. is_drift_truth khớp group.

    python src/check_data.py --dataset mock/mock_dataset.csv
"""
from __future__ import annotations
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import schema_cols as S  # noqa: E402


def _ok(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def run(dataset: str, manifest: str | None = None) -> bool:
    import pandas as pd
    df = pd.read_csv(dataset)
    all_ok = True
    print(f"E0 kiểm tra: {dataset}  ({len(df)} dòng)")

    # 1. schema
    missing = [c for c in S.DATASET_COLS if c not in df.columns]
    all_ok &= _ok("Đủ cột dataset", not missing, f"thiếu {missing}" if missing else "")
    if missing:
        print("\nKẾT QUẢ: CÓ MỤC FAIL")
        return False

    all_ok &= _ok("Dataset có dữ liệu", not df.empty)
    if df.empty:
        print("\nKẾT QUẢ: CÓ MỤC FAIL")
        return False

    all_ok &= _ok(
        "Không thiếu giá trị bắt buộc",
        not df[list(S.DATASET_COLS)].isna().any().any(),
    )
    all_ok &= _ok(
        "split hợp lệ",
        set(df["split"]) <= S.VALID_SPLIT,
    )
    all_ok &= _ok(
        "sha256 không trùng",
        not df["sha256"].duplicated().any(),
    )
    all_ok &= _ok("group hợp lệ", set(df["group"]) <= S.VALID_GROUPS)
    all_ok &= _ok("variant hợp lệ", set(df["variant"]) <= S.VALID_VARIANTS)
    all_ok &= _ok("packer hợp lệ", set(df["packer"]) <= S.VALID_PACKERS)
    all_ok &= _ok(
        "section_name_class hợp lệ",
        set(df["section_name_class"]) <= S.VALID_SECTION_CLASS,
    )

    # Feature phải là số, không được NaN hoặc vô cực.
    numeric_cols = [
        c for c in S.FEATURE_COLS if c != "section_name_class"
    ] + ["is_drift_truth"]

    numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    bad_numeric = (
        numeric.isna()
        | numeric.isin([float("inf"), float("-inf")])
    )
    numeric_ok = not bad_numeric.any().any()

    all_ok &= _ok(
        "Các cột số hợp lệ và hữu hạn",
        numeric_ok,
        f"{int(bad_numeric.sum().sum())} ô không hợp lệ",
    )

    if not numeric_ok:
        print("\nKẾT QUẢ: CÓ MỤC FAIL")
        return False

    # Dùng giá trị đã chuyển sang số cho các kiểm tra tiếp theo.
    df[numeric_cols] = numeric

    int_cols = [
        "num_sections", "ep_section_writable", "num_dll", "num_api",
        "only_dynamic_loader_imports", "file_size", "size_of_headers",
        "checksum_valid", "compile_timestamp", "has_overlay",
        "overlay_size", "is_dotnet", "is_drift_truth",
    ]
    all_ok &= _ok(
        "Các cột int không có phần thập phân",
        (numeric[int_cols] % 1 == 0).all().all(),
    )

    binary_cols = [
        "ep_section_writable", "only_dynamic_loader_imports",
        "checksum_valid", "has_overlay", "is_dotnet", "is_drift_truth",
    ]
    all_ok &= _ok(
        "Các cột nhị phân chỉ có 0/1",
        numeric[binary_cols].isin([0, 1]).all().all(),
    )

    entropy_cols = [
        "entropy_file", "entropy_max_section", "entropy_mean_section",
    ]
    all_ok &= _ok(
        "Entropy trong khoảng 0–8",
        ((numeric[entropy_cols] >= 0)
         & (numeric[entropy_cols] <= 8)).all().all(),
    )

    all_ok &= _ok(
        "high_entropy_byte_ratio trong khoảng 0–1",
        numeric["high_entropy_byte_ratio"].between(0, 1).all(),
    )

    # 2. Mỗi origin chỉ được nằm trong một tập.
    split_counts = df.groupby("origin_sha256")["split"].nunique()
    leaked_origins = split_counts[split_counts > 1]

    all_ok &= _ok(
        "Không rò rỉ split (train/val/test)",
        leaked_origins.empty,
        f"{len(leaked_origins)} origin nằm ở nhiều tập",
    )

    # 3. P-low entropy thấp hơn pack thường
    low = df[df["variant"] == "P-low"]["entropy_max_section"]
    hi = df[df["variant"].isin(["P-seen", "P-unseen"])]["entropy_max_section"]
    if len(low) and len(hi):
        all_ok &= _ok("P-low entropy < pack thường",
                      low.mean() < hi.mean(),
                      f"P-low={low.mean():.2f} vs pack={hi.mean():.2f}")
    else:
        _ok("P-low entropy (bỏ qua, thiếu mẫu)", True)

    # 4. Kiểm tra manifest và đối chiếu với dataset.
    man_path = manifest or dataset.replace("dataset", "manifest")

    if not os.path.isfile(man_path):
        _ok("Manifest tồn tại", False, man_path)
        print("\nKẾT QUẢ: CÓ MỤC FAIL")
        return False

    man = pd.read_csv(man_path)
    missing_man = [c for c in S.MANIFEST_COLS if c not in man.columns]
    all_ok &= _ok(
        "Đủ cột manifest",
        not missing_man,
        f"thiếu {missing_man}" if missing_man else "",
    )

    if missing_man:
        print("\nKẾT QUẢ: CÓ MỤC FAIL")
        return False

    # note là ghi chú tự do, được phép để trống.
    required_man = [c for c in S.MANIFEST_COLS if c != "note"]
    all_ok &= _ok(
        "Manifest không thiếu giá trị bắt buộc",
        not man[required_man].isna().any().any(),
    )

    unique_hash = not man["sha256"].duplicated().any()
    all_ok &= _ok("sha256 manifest không trùng", unique_hash)

    all_ok &= _ok(
        "die_result hợp lệ",
        set(man["die_result"]) <= S.VALID_DIE,
    )

    for col in ["removed_prepacked", "pack_failed"]:
        values = pd.to_numeric(man[col], errors="coerce")
        all_ok &= _ok(
            f"{col} chỉ có 0/1",
            values.isin([0, 1]).all(),
        )

    covered = df["sha256"].isin(man["sha256"]).all()
    all_ok &= _ok(
        "Mọi mẫu dataset có trong manifest",
        covered,
    )

    # Manifest có thể chứa thêm mẫu đã bị loại.
    # Chỉ đối chiếu những mẫu thực sự có trong dataset.
    if unique_hash and covered:
        matched = (
            man.set_index("sha256")
            .loc[df["sha256"]]
            .reset_index()
        )

        ids_match = (
            df[S.ID_COLS].reset_index(drop=True)
            .eq(matched[S.ID_COLS])
            .all().all()
        )
        all_ok &= _ok(
            "Định danh dataset khớp manifest",
            ids_match,
        )

        g1 = matched.loc[
            df["group"].reset_index(drop=True) == "G1"
        ]
        if not g1.empty:
            frac = g1["die_result"].isin(
                ["packed", "protected"]
            ).mean()
            all_ok &= _ok(
                "DiE nhận G1 là packed (>80%)",
                frac > 0.8,
                f"{frac:.0%}",
            )
        else:
            all_ok &= _ok(
                "Có mẫu G1 để kiểm tra DiE",
                False,
                "không có mẫu G1",
            )
    # 5. nhãn khớp group
    bad = df[df["is_drift_truth"] != df["group"].map(S.GROUP_IS_DRIFT)]
    all_ok &= _ok("is_drift_truth khớp group", len(bad) == 0, f"{len(bad)} dòng sai")

    print(f"\nKẾT QUẢ: {'PASS toàn bộ' if all_ok else 'CÓ MỤC FAIL'}")
    return all_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()
    sys.exit(0 if run(args.dataset, args.manifest) else 1)


if __name__ == "__main__":
    main()
