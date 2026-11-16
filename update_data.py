"""Fetch Lake Sawyer measurements and produce data.json for the dashboard."""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

SOURCE = 'https://www.lakesawyerweather.com/LEVEL3.TXT'
OUTPUT = Path(__file__).with_name('data.json')
DATE_LINE = re.compile(r'^\s*(\d{2}-\d{2}-\d{4})(?:\s+([+-]?\d+(?:\.\d+)?))?\s*$')

def fetch_json(base, params):
    url = base + '?' + urlencode(params)
    with urlopen(Request(url, headers={'User-Agent': 'LakeSawyerDashboard/1.1'}), timeout=75) as response:
        return json.load(response)


def get_rainfall(first_date):
    # Lake Sawyer approximate center; Open-Meteo gridded estimates, not station observations.
    location = {'latitude': 47.34, 'longitude': -122.05,
                'daily': 'precipitation_sum', 'precipitation_unit': 'inch',
                'timezone': 'America/Los_Angeles'}
    today = datetime.now(timezone.utc).date()
    # Archive can lag several days. Supplement its last week with forecast API history.
    archive_end = today - timedelta(days=8)
    results = {}
    if archive_end.isoformat() >= first_date:
        params = dict(location, start_date=first_date, end_date=archive_end.isoformat(), models='era5')
        data = fetch_json('https://archive-api.open-meteo.com/v1/archive', params)
        for day, amount in zip(data['daily']['time'], data['daily']['precipitation_sum']):
            if amount is not None:
                results[day] = round(float(amount), 3)
    recent = fetch_json('https://api.open-meteo.com/v1/forecast', dict(location, past_days=10, forecast_days=1))
    for day, amount in zip(recent['daily']['time'], recent['daily']['precipitation_sum']):
        if amount is not None and day <= today.isoformat():
            results[day] = round(float(amount), 3)
    return [{'date': day, 'rain_in': results[day]} for day in sorted(results)]


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
        'rainfall': get_rainfall(items[0]['date']),
        'rainfall_source': 'Open-Meteo ERA5 reanalysis and recent forecast-model estimates',
        'rainfall_unit': 'inches',
    }
    OUTPUT.write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(items)} readings; latest: {items[-1]}')

if __name__ == '__main__':
    main()
