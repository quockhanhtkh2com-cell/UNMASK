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
from split_data import check_no_leak  # noqa: E402


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
    all_ok &= _ok("group hợp lệ", set(df["group"]) <= S.VALID_GROUPS)
    all_ok &= _ok("variant hợp lệ", set(df["variant"]) <= S.VALID_VARIANTS)
    all_ok &= _ok("packer hợp lệ", set(df["packer"]) <= S.VALID_PACKERS)

    # 2. không rò rỉ
    errs = check_no_leak(df)
    all_ok &= _ok("Không rò rỉ split", not errs, errs[0] if errs else "")

    # 3. P-low entropy thấp hơn pack thường
    low = df[df["variant"] == "P-low"]["entropy_max_section"]
    hi = df[df["variant"].isin(["P-seen", "P-unseen"])]["entropy_max_section"]
    if len(low) and len(hi):
        all_ok &= _ok("P-low entropy < pack thường",
                      low.mean() < hi.mean(),
                      f"P-low={low.mean():.2f} vs pack={hi.mean():.2f}")
    else:
        _ok("P-low entropy (bỏ qua, thiếu mẫu)", True)

    # 4. G1 bị DiE nhận packed (cần manifest)
    man_path = manifest or dataset.replace("dataset", "manifest")
    if os.path.exists(man_path):
        man = pd.read_csv(man_path)
        g1 = man[man["group"] == "G1"]
        if len(g1):
            frac = (g1["die_result"].isin(["packed", "protected"])).mean()
            all_ok &= _ok("DiE nhận G1 là packed (>80%)", frac > 0.8, f"{frac:.0%}")
    else:
        _ok("manifest (bỏ qua, không tìm thấy)", True, man_path)

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
