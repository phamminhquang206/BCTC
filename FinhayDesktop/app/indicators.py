"""Close-based SMA, population-standard-deviation BB, and Wilder RSI.

Missing/nonpositive closes break the sequence; warm-up starts again afterwards.
All output lists align with the original input, before any viewport filtering.
"""
from math import sqrt
from .finance import number


def calculate_indicators(rows, ma_periods=(), bb_period=None, bb_deviation=2.0, rsi_period=None):
    periods = list(ma_periods) + ([bb_period] if bb_period else []) + ([rsi_period] if rsi_period else [])
    if any(not isinstance(p, int) or isinstance(p, bool) or p < 2 for p in periods):
        raise ValueError('Chu kỳ phải là số nguyên từ 2 trở lên.')
    deviation = number(bb_deviation)
    if deviation is None or deviation <= 0:
        raise ValueError('Độ lệch BB phải lớn hơn 0.')
    result = {f'MA{p}': [None] * len(rows) for p in ma_periods}
    if bb_period:
        result.update({key: [None] * len(rows) for key in ('BB giữa', 'BB trên', 'BB dưới')})
    if rsi_period:
        result[f'RSI{rsi_period}'] = [None] * len(rows)
    segment, gains, losses = [], [], []
    avg_gain = avg_loss = None
    for i, row in enumerate(rows):
        close = number(row.get('c'))
        if close is None or close <= 0:
            segment, gains, losses = [], [], []
            avg_gain = avg_loss = None
            continue
        previous = segment[-1] if segment else None
        segment.append(close)
        for period in ma_periods:
            if len(segment) >= period:
                result[f'MA{period}'][i] = sum(segment[-period:]) / period
        if bb_period and len(segment) >= bb_period:
            window = segment[-bb_period:]
            mean = sum(window) / bb_period
            std = sqrt(sum((value - mean) ** 2 for value in window) / bb_period)
            for key, value in [('BB giữa', mean), ('BB trên', mean + deviation * std), ('BB dưới', mean - deviation * std)]:
                result[key][i] = value
        if rsi_period and previous is not None:
            gain, loss = max(close - previous, 0), max(previous - close, 0)
            if avg_gain is None:
                gains.append(gain)
                losses.append(loss)
                if len(gains) < rsi_period:
                    continue
                avg_gain, avg_loss = sum(gains) / rsi_period, sum(losses) / rsi_period
            else:
                avg_gain = (avg_gain * (rsi_period - 1) + gain) / rsi_period
                avg_loss = (avg_loss * (rsi_period - 1) + loss) / rsi_period
            result[f'RSI{rsi_period}'][i] = (50 if avg_gain == avg_loss == 0 else
                100 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss))
    return result
