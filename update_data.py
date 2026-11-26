"""Fetch Lake Sawyer measurements and produce data.json for the dashboard."""
import json
import re
import time
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from http.client import HTTPException
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

SOURCE = 'https://www.lakesawyerweather.com/LEVEL3.TXT'
OUTPUT = Path(__file__).with_name('data.json')
DATE_LINE = re.compile(r'^\s*(\d{2}-\d{2}-\d{4})(?:\s+([+-]?\d+(?:\.\d+)?))?\s*$')

CACHE = Path(__file__).with_name('rain-cache.json')

def fetch(url, parse):
    for attempt in range(5):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'LakeSawyerDashboard/1.2'}), timeout=25) as response:
                return parse(response)
        except (URLError, TimeoutError, OSError, HTTPException, ValueError) as exc:
            if isinstance(exc, HTTPError) and exc.code < 500 and exc.code not in (408, 429):
                raise
            print(f'Attempt {attempt+1}/5 failed: {exc}', flush=True)
            if attempt == 4:
                raise
            time.sleep(5 * 2**attempt)


def fetch_json(base, params):
    return fetch(base + '?' + urlencode(params), json.load)


def get_rainfall(first_date):
    location = {'latitude': 47.34, 'longitude': -122.05,
                'daily': 'precipitation_sum', 'precipitation_unit': 'inch',
                'timezone': 'America/Los_Angeles'}
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date()
    archive_end = today - timedelta(days=8)
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    archive = cache.get('archive', {})
    recent = cache.get('recent', {})
    through = cache.get('archive_through')
    updated = cache.get('updated')
    errors = []
    start = first_date if not through else max(first_date, (datetime.fromisoformat(through).date()-timedelta(days=6)).isoformat())
    def extract(data):
        return {d: round(float(v), 3) for d,v in zip(data['daily']['time'], data['daily']['precipitation_sum']) if v is not None and d < today.isoformat()}
    if archive_end.isoformat() >= start and (not through or through < archive_end.isoformat()):
        try:
            archive.update(extract(fetch_json('https://archive-api.open-meteo.com/v1/archive', dict(location, start_date=start, end_date=archive_end.isoformat(), models='era5'))))
            through = archive_end.isoformat()
        except Exception as exc:
            errors.append(f'Archive: {exc}')
    try:
        recent.update(extract(fetch_json('https://api.open-meteo.com/v1/forecast', dict(location, past_days=10, forecast_days=1))))
        updated = datetime.now(timezone.utc).isoformat(timespec='seconds')
    except Exception as exc:
        errors.append(f'Recent: {exc}')
    for error in errors:
        print(f'::warning::Rainfall update failed: {error}')
    CACHE.write_text(json.dumps(dict(archive=archive, recent=recent, archive_through=through, updated=updated)))
    results = {**recent, **archive}
    return ([{'date': d, 'rain_in': results[d]} for d in sorted(results) if first_date <= d < today.isoformat()], updated, errors)


def main():
    text = fetch(SOURCE, lambda response: response.read().decode('utf-8-sig', errors='replace'))
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
    rainfall, rain_updated, rain_errors = get_rainfall(items[0]['date'])
    payload = {
        'source': SOURCE,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'measurement_unit': 'source units (not confirmed)',
        'readings': items,
        'rainfall': rainfall,
        'rainfall_updated_at_utc': rain_updated,
        'rainfall_status': 'partial or cached' if rain_errors else 'updated',
        'rainfall_source': 'Open-Meteo ERA5 reanalysis and recent forecast-model estimates',
        'rainfall_unit': 'inches',
    }
    OUTPUT.write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(items)} readings; latest: {items[-1]}')

if __name__ == '__main__':
    main()
