# utils.py
def safe_float(value):
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return 0.0
    value = str(value).strip()
    value = value.replace('%', '').replace(',', '').strip()
    if not value or value == '—' or value == '-':
        return 0.0
    try:
        return float(value)
    except:
        return 0.0

def safe_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is None:
        return 0
    value = str(value).strip()
    value = value.replace('%', '').replace(',', '').strip()
    if not value or value == '—' or value == '-':
        return 0
    try:
        return int(float(value))
    except:
        return 0

def safe_elo(value):
    val = safe_float(value)
    return val if val > 0 else 1.0

def get_color_icon(value, stat_type, limits):
    if stat_type not in limits:
        return "⚪", "❓"
    lim = limits[stat_type]
    if value >= lim['purple']:
        return "🟣", "👑"
    elif value >= lim['red']:
        return "🔴", "💀"
    elif value >= lim['orange']:
        return "🟠", "⚔️"
    elif value >= lim['yellow']:
        return "🟡", "🥚"
    else:
        return "🟢", "🐑"
        # utils.py — добавить в конец
import math

def player_confidence(matches: int):
    """Возвращает (вес, уровень_доверия)."""
    if matches <= 0:
        return 0.1, "very_low"
    if matches < 5:
        return 0.2, "very_low"
    if matches < 10:
        return 0.5, "low"
    w = min(1.0, math.sqrt(matches) / 10.0)
    return w, "high"

def weighted_mean(values, weights):
    """Взвешенное среднее."""
    total_w = sum(weights) or 1.0
    return sum(v * w for v, w in zip(values, weights)) / total_w

def confidence_emoji(conf: str) -> str:
    return {"very_low": "⚠️", "low": "⚠️", "high": "✅"}.get(conf, "❓")