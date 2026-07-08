"""Stereotax vernier reader — Stage 1 still-image prototype.

Pipeline (see CLAUDE.md steps 1-5):
  imaging  -> load, deskew, extract the main / vernier bands
  profile  -> collapse each band to a 1-D intensity profile (ticks = dips)
  ticks    -> sub-pixel tick centres (parabolic vertex)
  read     -> coarse (which division) + fine (global line fit) + combine
  debug    -> matplotlib overlays of every intermediate signal
"""
