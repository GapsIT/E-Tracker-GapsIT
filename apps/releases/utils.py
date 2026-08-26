def detect_platform(request):
    """
    Best-effort detection of the visitor's OS from their User-Agent, used
    only to decide which download button to highlight first.

    Falls back to "windows" for macOS, mobile, unknown, or missing
    User-Agent strings, per spec ("if no linux or windows then default
    windows").
    """
    ua = request.META.get("HTTP_USER_AGENT", "").lower()

    # "Linux" also shows up inside Android User-Agent strings
    # (e.g. "Linux; Android 14") -- don't treat those as desktop Linux.
    if "linux" in ua and "android" not in ua:
        return "linux"

    if "windows" in ua or "win64" in ua or "win32" in ua:
        return "windows"

    return "windows"
