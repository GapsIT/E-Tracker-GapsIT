Put the actual GapsSight installer files in this folder, using exactly
these filenames (this project can't ship the real 30+ MB .rar binaries,
only the code that serves them):

  GapsSight_Windows_0.1.rar
  GapsSight_Linux_0.1.rar

This is what apps/releases/views.py reads from -- see
GAPSIGHT_RELEASES_DIR / GAPSIGHT_RELEASES in core/settings.py if you'd
rather rename the files or point this at a different folder (e.g. one
outside the project, via the GAPSIGHT_RELEASES_DIR env var).
