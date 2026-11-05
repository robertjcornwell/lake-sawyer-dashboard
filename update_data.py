"""Fetch Lake Sawyer measurements and produce data.json for the dashboard."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = 'https://www.lakesawyerweather.com/LEVEL3.TXT'
OUTPUT = Path(__file__).with_name('data.json')
DATE_LINE = re.compile(r'^\s*(\d{2}-\d{2}-\d{4})(?:\s+([+-]?\d+(?:\.\d+)?))?\s*$')

def main():
    request = Request(SOURCE, headers={'User-Agent': 'LakeSawyerDashboard/1.0'})
    with urlopen(request, timeout=45) as response:
        text = response.read().decode('utf-8-sig', errors='replace')
    readings = {}
    dates_seen = 0
    for line in text.splitlines():
        match = DATE_LINE.match(line)
        if not match:
            continue
        date = datetime.strptime(match.group(1), '%m-%d-%Y').date().isoformat()
        dates_seen += 1
        if match.group(2) is not None:
            readings[date] = float(match.group(2))
    if dates_seen < 100 or len(readings) < 100:
        raise ValueError(f'Unexpected data: {dates_seen} dated lines, {len(readings)} measurements')
    items = [{'date': date, 'level': readings[date]} for date in sorted(readings)]
    payload = {
        'source': SOURCE,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'measurement_unit': 'source units (not confirmed)',
        'readings': items,
    }
    OUTPUT.write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(items)} readings; latest: {items[-1]}')

if __name__ == '__main__':
    main()
