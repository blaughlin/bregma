"""Debug rendering — the primary debugging surface (CLAUDE.md).

Three panels: the deskewed crop with both band boxes; each 1-D profile with
detected tick centres overlaid; and the step-4 offset-vs-index scatter with the
fitted line and zero crossing.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def render(out_path, gray, main_rows, vernier_rows, main_cols, vernier_cols,
           main_prof, main_ticks, vernier_prof, vernier_ticks,
           fine, result, title=""):
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 3)

    # (a) deskewed crop with band boxes
    ax0 = fig.add_subplot(gs[:, 0])
    ax0.imshow(gray, cmap="gray", aspect="auto")
    for rows, cols, color, name in [(main_rows, main_cols, "lime", "main"),
                                    (vernier_rows, vernier_cols, "cyan", "vernier")]:
        (r0, r1), (c0, c1) = rows, cols
        ax0.add_patch(Rectangle((c0, r0), c1 - c0, r1 - r0,
                                fill=False, edgecolor=color, lw=1.5, label=name))
    ax0.legend(loc="upper right", fontsize=8)
    ax0.set_title("deskewed crop + bands")

    # (b) main profile with ticks
    ax1 = fig.add_subplot(gs[0, 1:])
    _plot_profile(ax1, main_prof, main_ticks, main_rows[0], "main scale profile", "lime")

    # (c) vernier profile with ticks
    ax2 = fig.add_subplot(gs[1, 1])
    _plot_profile(ax2, vernier_prof, vernier_ticks, vernier_rows[0], "vernier profile", "cyan")

    # (d) step-4 offset-vs-number global fit
    ax3 = fig.add_subplot(gs[1, 2])
    n = fine["number"]
    inl = fine["inliers"]
    ax3.scatter(n[inl], fine["offset_u"][inl], c="k", s=18, label="offset (inlier)")
    if (~inl).any():
        ax3.scatter(n[~inl], fine["offset_u"][~inl], c="red", s=18, marker="x", label="rejected")
    line = fine["slope"] * n + fine["intercept"]
    ax3.plot(n, line, "r-", lw=1.2, label=f"fit (rms={fine['resid_rms']:.2f}px)")
    ax3.axhline(0, color="gray", lw=0.6)
    ax3.axvline(fine["n_star"], color="orange", ls="--",
                label=f"n*={fine['n_star']:.2f}")
    ax3.set_xlabel("vernier number"); ax3.set_ylabel("offset to main grid (px)")
    ax3.set_title("step 4: global fit"); ax3.legend(fontsize=7)

    sup = title or f"reading = {result['reading_mm']:.3f} mm " \
                    f"(coarse {result['coarse_mm']:.2f} + fine {result['fine_mm']:.3f})"
    fig.suptitle(sup, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def _plot_profile(ax, prof, ticks, row_offset, title, color):
    x = range(row_offset, row_offset + len(prof))
    ax.plot(x, prof, "k-", lw=0.8)
    for t in ticks:
        ax.axvline(t + row_offset, color=color, lw=0.7, alpha=0.8)
    ax.set_title(f"{title} ({len(ticks)} ticks)")
    ax.set_xlabel("row (px)"); ax.set_ylabel("intensity")
