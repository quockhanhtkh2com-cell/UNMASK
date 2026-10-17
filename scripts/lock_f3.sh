#!/usr/bin/env bash
# Khoa nguong F3 tren dataset. T5: doi duong dan sang dataset v1.0 la xong.
#   scripts/lock_f3.sh <dataset.csv> [out.json]
# Thu tren v0.1 (khong dung config repo):  scripts/lock_f3.sh dataset_v0.1_pilot.csv /tmp/lock_v01.json
set -euo pipefail
DS="${1:?can duong dan dataset.csv}"
OUT="${2:-config/thresholds.locked.json}"
PY="${PYTHON:-python}"
echo "[lock] dataset: $DS"
echo "[lock] sha256 : $(sha256sum "$DS" | cut -d' ' -f1)"
$PY -m pytest -q
$PY unmask/train.py --dataset "$DS" --out "$OUT"
for flag in "" "--no-dualcheck"; do
  UNMASK_CONFIG="$OUT" $PY -m unmask.filter --dataset "$DS" $flag 2>&1 | grep -E "phân bố"
done
echo "[lock] da khoa -> $OUT"
if [ "$OUT" = "config/thresholds.locked.json" ]; then
  echo "[lock] BUOC TIEP: git add $OUT && git commit (TRUOC khi chay E3-E5). Dong bo voi Duc/Khanh: file nay dung chung."
fi
