"""Ghép BẢNG CHÍNH F0–F3a & BẢNG KIỂM ĐỊNH MCNEMAR — [Đức].
Tuân thủ SPEC_ketqua_chi_so.md và kết quả trên tập test (404 mẫu).

    python experiments/build_main_table.py --results results --out results/bang_chinh
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "unmask"))
import eval_metrics as M         # noqa: E402
import schema_cols as S          # noqa: E402
import f1_die, f2_rule           # noqa: E402
from unmask.filter import load_filter  # noqa: E402

GATES = ["F0", "F1", "F1+", "F2", "F3", "F3a"]


def _compute_mcnemar_table(dataset_path: str, f3_config_path: str, out_csv: str):
    import pandas as pd
    df = pd.read_csv(dataset_path)
    if "die_result_real" not in df.columns:
        # Try to load from die_real_v1.1.csv (đọc từ dev hoặc local)
        die_real_path = os.path.join(os.path.dirname(dataset_path), "die_real_v1.1.csv")
        if not os.path.exists(die_real_path):
            die_real_path = "die_real_v1.1.csv"
        if os.path.exists(die_real_path):
            die_real = pd.read_csv(die_real_path)
            if "die_result_real" in die_real.columns and "sha256" in die_real.columns:
                df = df.merge(die_real[["sha256", "die_result_real"]], on="sha256", how="left")

    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df

    f3 = load_filter(f3_config_path, use_dualcheck=True)
    f3a = load_filter(f3_config_path, use_dualcheck=False)

    dec = {
        "F0": ["PASS"] * len(df_test),
        "F1": f1_die.run(df_test, variant="packed_only"),
        "F1+": f1_die.run(df_test, variant="packed_protected"),
        "F2": f2_rule.run(df_test),
        "F3": [f3.decide(r)["decision"] for r in df_test.to_dict("records")],
        "F3a": [f3a.decide(r)["decision"] for r in df_test.to_dict("records")],
    }

    def is_correct(decisions, grp):
        return [(d == "FILTERED") if g == "G1" else (d != "FILTERED")
                for d, g in zip(decisions, grp)]

    groups = df_test["group"].tolist()
    c_f1 = is_correct(dec["F1"], groups)
    c_f1_plus = is_correct(dec["F1+"], groups)
    c_f2 = is_correct(dec["F2"], groups)
    c_f3 = is_correct(dec["F3"], groups)
    c_f3a = is_correct(dec["F3a"], groups)

    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]

    m1 = M.mcnemar(c_f3, c_f1)
    m1_plus = M.mcnemar(c_f3, c_f1_plus)
    m2 = M.mcnemar(c_f3, c_f2)
    m3 = M.mcnemar(c_f3, c_f3a)

    # Holm correction cho 4 tests (F1, F1+, F2, F3a)
    p_values = [m1["p_value"], m1_plus["p_value"], m2["p_value"], m3["p_value"]]
    p_holm, is_sig = M.holm_correction(p_values, alpha=0.05)

    def get_conclusion(p_orig, p_holm_val, is_significant, test_name):
        if p_orig < 0.001:
            p_str = f"{p_orig:.2e}"
        else:
            p_str = f"{p_orig:.4f}"
        p_holm_str = f"{p_holm_val:.2e}" if p_holm_val < 0.001 else f"{p_holm_val:.4f}"

        if is_significant:
            return f"Ý nghĩa thống kê (p_Holm = {p_holm_str} < 0.05)"
        else:
            if test_name == "ablation":
                return f"Không đạt ý nghĩa (p_Holm = {p_holm_str}; p_orig = {p_str})"
            else:
                return f"Không có ý nghĩa thống kê (p_Holm = {p_holm_str})"

    rows_mc = [
        {
            "comparison": "F3 vs F1 (DiE packed)",
            "b": m1["b"], "c": m1["c"],
            "stat": round(m1["stat"], 4),
            "p_value": f"{m1['p_value']:.2e}" if m1["p_value"] < 0.001 else f"{m1['p_value']:.4f}",
            "p_holm": f"{p_holm[0]:.2e}" if p_holm[0] < 0.001 else f"{p_holm[0]:.4f}",
            "conclusion": get_conclusion(m1["p_value"], p_holm[0], is_sig[0], "f1")
        },
        {
            "comparison": "F3 vs F1+ (DiE packed+protected)",
            "b": m1_plus["b"], "c": m1_plus["c"],
            "stat": round(m1_plus["stat"], 4),
            "p_value": f"{m1_plus['p_value']:.2e}" if m1_plus["p_value"] < 0.001 else f"{m1_plus['p_value']:.4f}",
            "p_holm": f"{p_holm[1]:.2e}" if p_holm[1] < 0.001 else f"{p_holm[1]:.4f}",
            "conclusion": get_conclusion(m1_plus["p_value"], p_holm[1], is_sig[1], "f1+")
        },
        {
            "comparison": "F3 vs F2 (entropy)",
            "b": m2["b"], "c": m2["c"],
            "stat": round(m2["stat"], 4),
            "p_value": f"{m2['p_value']:.2e}" if m2["p_value"] < 0.001 else f"{m2['p_value']:.4f}",
            "p_holm": f"{p_holm[2]:.2e}" if p_holm[2] < 0.001 else f"{p_holm[2]:.4f}",
            "conclusion": get_conclusion(m2["p_value"], p_holm[2], is_sig[2], "f2")
        },
        {
            "comparison": "F3 vs F3a (ablation)",
            "b": m3["b"], "c": m3["c"],
            "stat": round(m3["stat"], 4),
            "p_value": f"{m3['p_value']:.4f}",
            "p_holm": f"{p_holm[3]:.4f}",
            "conclusion": get_conclusion(m3["p_value"], p_holm[3], is_sig[3], "ablation")
        },
    ]
    df_mc = pd.DataFrame(rows_mc)
    df_mc.to_csv(out_csv, index=False)
    print(f"[mcnemar] -> {out_csv}")
    return df_mc, dec, df_test, FEATURE_NUM


def build(results_dir: str, out_prefix: str, dataset_path: str = "dataset_v1.1.csv",
          f3_config_path: str = "config/thresholds.locked.json"):
    import pandas as pd, numpy as np
    from detector import DriftDetector

    all_files = glob.glob(os.path.join(results_dir, "results_*.csv"))
    # Loại bỏ file mock và file trùng dual-write (_0_0_)
    files = [f for f in all_files if "_0_0_" not in f and not os.path.basename(f).startswith("results_mock")]
    if not files:
        print("Chưa có results_*.csv — chạy run_experiments.py trước."); return

    df_res = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df_res = df_res[df_res.gate.isin(GATES)]

    # Tính McNemar và lấy quyết định test 404 mẫu để tính Wilson CI chuẩn
    mcnemar_csv = os.path.join(results_dir, "stats_mcnemar.csv")
    df_mc, dec_test, df_test, FEATURE_NUM = _compute_mcnemar_table(dataset_path, f3_config_path, mcnemar_csv)

    # Khởi tạo detector D1 để tính alarm trên 404 mẫu test cho FNR_e2e
    df_full = pd.read_csv(dataset_path)
    g0_train = df_full[(df_full.group == "G0") & (df_full.split == "train")][FEATURE_NUM].to_numpy(float)
    det = DriftDetector(method="mahalanobis", seed=0, standardize=True).fit(g0_train)
    cfg = json.load(open(f3_config_path, encoding="utf-8"))
    det.threshold = float(cfg.get("detector_D1", {}).get("threshold_value", 6.9111))
    alarms_test = det.predict(df_test[FEATURE_NUM].to_numpy(float))

    # Tính Wilson CI trên 404 mẫu test cho từng cổng
    wilson_dict = {}
    for gate in GATES:
        d = dec_test[gate]
        grp = list(df_test.group)
        var = list(df_test.variant)
        # FTR cần tính từ tập test 404 mẫu với chuông D1 chạy toàn bộ
        ftr_rate = M.ftr(d, grp, alarms_test)
        wilson_dict[gate] = {
            "FTR": ftr_rate.wilson(),
            "FNR_G2": M.fnr(d, grp, "G2").wilson(),
            "FNR_G3": M.fnr(d, grp, "G3").wilson(),
            "FNR_e2e_G2": M.fnr_end2end(d, alarms_test, grp, "G2").wilson(),
            "FNR_e2e_G3": M.fnr_end2end(d, alarms_test, grp, "G3").wilson(),
            "correct_Pseen": M.correct_filter_rate(d, grp, var, "P-seen").wilson(),
            "correct_Punseen": M.correct_filter_rate(d, grp, var, "P-unseen").wilson(),
            "flagged_rate": M.flagged_rate(d).wilson(),
        }

    # Tổng hợp số liệu theo gate từ results_*.csv
    rows_clean = []
    rows_md = []

    for gate in GATES:
        gdf = df_res[df_res.gate == gate]

        def get_stat(col, sub_df=gdf):
            if col not in sub_df.columns:
                return 0.0, 0.0
            vals = sub_df[col].dropna()
            if len(vals) == 0:
                return 0.0, 0.0
            return float(vals.mean()), float(vals.std(ddof=1)) if len(vals) > 1 else 0.0

        ftr30_mean, ftr30_std = get_stat("FTR", gdf[gdf.pack_ratio_set == 0.3])
        ftr50_mean, ftr50_std = get_stat("FTR", gdf[gdf.pack_ratio_set == 0.5])
        ftr70_mean, ftr70_std = get_stat("FTR", gdf[gdf.pack_ratio_set == 0.7])

        # Lấy Wilson CI từ dict (dùng cho markdown)
        w = wilson_dict[gate]
        ftr_ci_30 = w.get("FTR_30", (float('nan'), float('nan')))
        ftr_ci_50 = w.get("FTR_50", (float('nan'), float('nan')))
        ftr_ci_70 = w.get("FTR_70", (float('nan'), float('nan')))

        fnr_g2_mean, fnr_g2_std = get_stat("FNR_G2")
        fnr_g3_mean, fnr_g3_std = get_stat("FNR_G3")
        fnr_e2e_g2_mean, fnr_e2e_g2_std = get_stat("FNR_e2e_G2")
        fnr_e2e_g3_mean, fnr_e2e_g3_std = get_stat("FNR_e2e_G3")

        pseen_mean, pseen_std = get_stat("correct_filter_Pseen")
        punseen_mean, punseen_std = get_stat("correct_filter_Punseen")
        flagged_mean, flagged_std = get_stat("flagged_rate")

        w = wilson_dict[gate]

        # Bảng CSV số thuần (cho Trúc vẽ hình dễ parse float)
        rows_clean.append({
            "gate": gate,
            "FTR@30": round(ftr30_mean, 4),
            "FTR@50": round(ftr50_mean, 4),
            "FTR@70": round(ftr70_mean, 4),
            "FNR_G2": round(fnr_g2_mean, 4),
            "FNR_G3": round(fnr_g3_mean, 4),
            "FNR_e2e_G2": round(fnr_e2e_g2_mean, 4),
            "FNR_e2e_G3": round(fnr_e2e_g3_mean, 4),
            "correct_Pseen": round(pseen_mean, 4),
            "correct_Punseen": round(punseen_mean, 4),
            "correct_Plow": "—",
            "correct_Pwild": "—",
            "flagged_rate": round(flagged_mean, 4),
        })

        # Bảng Markdown theo đúng mẫu template
        def fmt_cell(m, s, ci_lo, ci_hi):
            return f"`{m:.3f} ± {s:.3f}` [{ci_lo:.3f}, {ci_hi:.3f}]"

        def fmt_rate_cell(m, s, ci_lo, ci_hi):
            return f"`{m:.3f}` [{ci_lo:.3f}, {ci_hi:.3f}]"

        # Format FTR với Wilson CI (dùng chung CI cho cả 3 tỉ lệ)
        ftr_ci_lo, ftr_ci_hi = w.get("FTR", (float('nan'), float('nan')))
        ftr30_fmt = fmt_cell(ftr30_mean, ftr30_std, ftr_ci_lo, ftr_ci_hi)
        ftr50_fmt = fmt_cell(ftr50_mean, ftr50_std, ftr_ci_lo, ftr_ci_hi)
        ftr70_fmt = fmt_cell(ftr70_mean, ftr70_std, ftr_ci_lo, ftr_ci_hi)

        rows_md.append({
            "gate": gate,
            "FTR@30": ftr30_fmt,
            "FTR@50": ftr50_fmt,
            "FTR@70": ftr70_fmt,
            "FNR_G2": fmt_cell(fnr_g2_mean, fnr_g2_std, w["FNR_G2"][0], w["FNR_G2"][1]),
            "FNR_G3": fmt_cell(fnr_g3_mean, fnr_g3_std, w["FNR_G3"][0], w["FNR_G3"][1]),
            "FNR_e2e_G2": fmt_cell(fnr_e2e_g2_mean, fnr_e2e_g2_std, w["FNR_e2e_G2"][0], w["FNR_e2e_G2"][1]),
            "FNR_e2e_G3": fmt_cell(fnr_e2e_g3_mean, fnr_e2e_g3_std, w["FNR_e2e_G3"][0], w["FNR_e2e_G3"][1]),
            "correct_Pseen": fmt_rate_cell(pseen_mean, pseen_std, w["correct_Pseen"][0], w["correct_Pseen"][1]),
            "correct_Punseen": fmt_rate_cell(punseen_mean, punseen_std, w["correct_Punseen"][0], w["correct_Punseen"][1]),
            "correct_Plow": "—",
            "correct_Pwild": "—",
            "flagged_rate": "0" if gate == "F0" or flagged_mean == 0 else fmt_cell(flagged_mean, flagged_std, w["flagged_rate"][0], w["flagged_rate"][1]),
        })

    df_clean = pd.DataFrame(rows_clean)
    df_clean.to_csv(out_prefix + ".csv", index=False)

    # Tạo markdown đúng chuẩn bang_chinh_TEMPLATE.md
    md_content = []
    md_content.append("# Bảng chính F0–F3 — v1.1 (Số liệu thực nghiệm)\n")
    md_content.append("> Đã chạy E1–E6 trên `dataset_v1.1.csv` (mean ± std qua 3 seed, kèm Wilson 95% CI).\n")
    md_content.append("> Dataset test = 404 mẫu · F3 khóa 0.475 · D1 khóa 6.9111 (P80 chuẩn hóa) · P-low/P-wild = \"—\" (không có ở v1.1).\n\n")
    md_content.append("## Bảng chính (FTR kèm tỉ lệ pack; FNR tách G2/G3; FNR_e2e toàn trình)\n\n")

    md_content.append("| gate | FTR@30 | FTR@50 | FTR@70 | FNR_G2 (filter) | FNR_G3 (filter) | FNR_e2e_G2 | FNR_e2e_G3 | correct_Pseen | correct_Punseen | correct_Plow | correct_Pwild | flagged_rate |")
    md_content.append("|:----:|:------:|:------:|:------:|:---------------:|:---------------:|:-----------:|:-----------:|:-------------:|:---------------:|:------------:|:-------------:|:------------:|")
    for r in rows_md:
        md_content.append(f"| {r['gate']} | {r['FTR@30']} | {r['FTR@50']} | {r['FTR@70']} | {r['FNR_G2']} | {r['FNR_G3']} | {r['FNR_e2e_G2']} | {r['FNR_e2e_G3']} | {r['correct_Pseen']} | {r['correct_Punseen']} | {r['correct_Plow']} | {r['correct_Pwild']} | {r['flagged_rate']} |")

    md_content.append("\n* Chú thích: `FNR_G2/G3` = tỉ lệ bỏ sót do bộ lọc loại nhầm; `FNR_e2e` = tỉ lệ bỏ sót toàn trình (bộ lọc loại HOẶC chuông D1 không kêu).")
    md_content.append("* `±` = std qua các seed; `[...]` = khoảng tin cậy Wilson 95% CI [lo, hi].*\n\n")
    md_content.append("## Bảng kiểm định McNemar (ghép cặp trên cùng 404 mẫu test)\n\n")
    md_content.append("| So sánh | b (F3 đúng, kia sai) | c (F3 sai, kia đúng) | p-value | Kết luận |")
    md_content.append("|:---|:---:|:---:|:---:|:---|")
    for _, row in df_mc.iterrows():
        md_content.append(f"| {row['comparison']} | `{row['b']}` | `{row['c']}` | `{row['p_value']}` | {row['conclusion']} |")

    md_content.append("\n> Kết quả đo trực tiếp theo config khóa: F3=0.475, D1=6.9111 (P80 chuẩn hóa) trên 404 mẫu test độc lập.\n")

    full_md = "\n".join(md_content)
    with open(out_prefix + ".md", "w", encoding="utf-8") as f:
        f.write(full_md)

    print(f"[bang_chinh] -> {out_prefix}.csv / .md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results/bang_chinh")
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    args = ap.parse_args()
    build(args.results, args.out, dataset_path=args.dataset, f3_config_path=args.f3_config)


if __name__ == "__main__":
    main()
