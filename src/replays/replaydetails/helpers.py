def seconds_to_human(seconds: int, *, sep: str = ":", full: bool = True) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if full:
        return f"{h}{sep}{m:02}{sep}{s:02}"
    return f"{h}h{sep}{m:02}m{sep}{s:02}s" if h else f"{m}m{sep}{s:02}s" if m else f"{s}s"
