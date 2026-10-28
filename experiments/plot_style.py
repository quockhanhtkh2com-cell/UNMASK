"""Khuôn vẽ chung UNMASK: nền trắng, 300 dpi, màu cố định theo gate."""
from pathlib import Path

import matplotlib as mpl
from cycler import cycler


GATE_ORDER = ["F0", "F1", "F2", "F3a", "F3"]

GATE_LABELS = {
    "F0": "F0 (baseline)",
    "F1": "F1 (DiE)",
    "F2": "F2 (entropy rule)",
    "F3a": "F3a (ablation)",
    "F3": "F3 (UNMASK)",
}

# Giữ bảng màu 5 cổng đang dùng trong bản dev.
GATE_COLOR = {
    "F0": "#9e9e9e",
    "F1": "#ef5350",
    "F2": "#ff9800",
    "F3a": "#42a5f5",
    "F3": "#26c6da",
}

GATE_MARKER = {
    "F0": "s",
    "F1": "^",
    "F2": "D",
    "F3a": "o",
    "F3": "*",
}

GATE_SIZE = {
    "F0": 80,
    "F1": 80,
    "F2": 80,
    "F3a": 80,
    "F3": 140,
}

DPI = 300
TEXT_COLOR = "#222222"
GRID_COLOR = "#dddddd"


def apply_style():
    """Áp dụng font, màu nền và định dạng chung trước khi tạo figure."""
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "legend.title_fontsize": 10,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.edgecolor": "white",
        "savefig.transparent": False,
        "savefig.dpi": DPI,
        "text.color": TEXT_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "axes.edgecolor": "#666666",
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "grid.color": GRID_COLOR,
        "grid.alpha": 0.7,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "legend.facecolor": "white",
        "legend.edgecolor": "#cccccc",
        "legend.labelcolor": TEXT_COLOR,
        "axes.prop_cycle": cycler(
            color=[GATE_COLOR[gate] for gate in GATE_ORDER]
        ),
    })


def save_figure(fig, path):
    """Xuất hình nền trắng ở 300 dpi."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        dpi=DPI,
        facecolor="white",
        edgecolor="white",
        transparent=False,
        bbox_inches="tight",
    )
    return path