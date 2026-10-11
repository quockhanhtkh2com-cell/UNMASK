"""Metric cho UNMASK — [Trúc]. ĐÃ IMPLEMENT ĐẦY ĐỦ (có unit test trong tests/).

Định nghĩa (bám hướng dẫn):
- FTR  = số lần detector báo drift do mẫu CHỈ đổi vỏ (G1) / tổng số lần báo drift.
         LUÔN kèm tỉ lệ mẫu pack trong dữ liệu.
- FNR  = mẫu G2 (hoặc G3) bị bộ lọc loại (FILTERED) / tổng mẫu nhóm đó.
         Báo RIÊNG G2 và G3.
- tỉ lệ lọc đúng = mẫu G1 bị FILTERED / tổng G1, theo từng biến thể packer.
- %FLAGGED = mẫu được gắn cờ thay vì loại.
- Wilson CI cho mọi tỉ lệ; McNemar so 2 cổng trên cùng mẫu.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass
class Rate:
    num: int
    den: int

    @property
    def value(self) -> float:
        return self.num / self.den if self.den else float("nan")

    def wilson(self, z: float = 1.96) -> tuple[float, float]:
        """Khoảng tin cậy Wilson (mặc định 95%)."""
        n = self.den
        if n == 0:
            return (float("nan"), float("nan"))
        p = self.num / n
        denom = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denom
        half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
        return (max(0.0, center - half), min(1.0, center + half))

    def __repr__(self):
        lo, hi = self.wilson()
        return f"{self.value:.3f} [{lo:.3f},{hi:.3f}] (n={self.den})"


def ftr(decisions: list[str], groups: list[str], drift_alarm: list[bool]) -> Rate:
    """FTR: trong các lần BÁO DRIFT (drift_alarm=True trên mẫu được đưa vào chuông),
    bao nhiêu là mẫu G1 (chỉ đổi vỏ = false trigger).

    decisions: PASS/FILTERED/FLAGGED của cổng. Chỉ mẫu KHÔNG bị FILTERED mới vào chuông.
    """
    alarms = 0
    false_alarms = 0
    for dec, g, alarm in zip(decisions, groups, drift_alarm):
        if dec == "FILTERED":
            continue  # bị lọc, không vào chuông
        if alarm:
            alarms += 1
            if g == "G1":
                false_alarms += 1
    return Rate(false_alarms, alarms)


def fnr(decisions: list[str], groups: list[str], target_group: str) -> Rate:
    """FNR trên 1 nhóm drift thật (G2 hoặc G3): bị FILTERED = bỏ sót."""
    total = sum(1 for g in groups if g == target_group)
    missed = sum(1 for dec, g in zip(decisions, groups)
                 if g == target_group and dec == "FILTERED")
    return Rate(missed, total)


def correct_filter_rate(decisions: list[str], groups: list[str], variants: list[str],
                        variant: str | None = None) -> Rate:
    """Tỉ lệ lọc đúng: G1 bị FILTERED / tổng G1 (lọc theo biến thể nếu truyền variant)."""
    idx = [i for i, g in enumerate(groups) if g == "G1"
           and (variant is None or variants[i] == variant)]
    total = len(idx)
    filtered = sum(1 for i in idx if decisions[i] == "FILTERED")
    return Rate(filtered, total)


def flagged_rate(decisions: list[str]) -> Rate:
    return Rate(sum(1 for d in decisions if d == "FLAGGED"), len(decisions))


def pack_ratio(groups: list[str], variants: list[str]) -> float:
    """Tỉ lệ mẫu bị pack trong dữ liệu (để đính kèm mọi FTR)."""
    packed = sum(1 for g, v in zip(groups, variants)
                 if g in ("G1", "G3") or v in ("P-low", "P-wild"))
    return packed / len(groups) if groups else float("nan")


def mcnemar(a_correct: list[bool], b_correct: list[bool]) -> dict:
    """McNemar trên cùng mẫu, dùng chi-square 1 dof có hiệu chỉnh liên tục."""
    if len(a_correct) != len(b_correct):
        raise ValueError("Hai danh sách phải có cùng số mẫu.")

    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if not x and y)

    if b + c == 0:
        return {"b": b, "c": c, "stat": 0.0, "p_value": 1.0}

    stat = max(0, abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(stat / 2))

    return {"b": b, "c": c, "stat": stat, "p_value": p}


if __name__ == "__main__":
    # demo nhanh
    dec = ["PASS", "FILTERED", "FLAGGED", "PASS"]
    grp = ["G2", "G1", "G3", "G1"]
    alarm = [True, True, True, True]
    print("FTR:", ftr(dec, grp, alarm))
    print("FNR G2:", fnr(dec, grp, "G2"))
    print("FNR G3:", fnr(dec, grp, "G3"))
