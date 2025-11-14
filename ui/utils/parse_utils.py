import re
from typing import Optional


_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_leading_float(value) -> Optional[float]:
    """Extract the first floating-point number from `value`.

    Returns a float when a number is found, otherwise None.
    Works on numbers embedded in strings like '123.4 kPa', '-12.3C', '1.23e-2', etc.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.upper() in ("N/A", "NA"):
        return None
    m = _NUM_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None
