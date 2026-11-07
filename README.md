# Lake Sawyer iPhone dashboard

Automatically reads https://www.lakesawyerweather.com/LEVEL3.TXT and publishes an interactive year-over-year dashboard via GitHub Pages.

## Setup

1. Create a **public** GitHub repository named `lake-sawyer-dashboard`.
2. Upload `index.html`, `icon.svg`, `manifest.webmanifest`, `update_data.py`, and the `.github/workflows/publish.yml` workflow **preserving the folder path**. GitHub's web upload may not preserve an empty directory; this one contains the workflow file.
3. Open repository **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
4. Open **Actions → Update and publish dashboard → Run workflow**. If prompted, enable Actions for the repository.
5. After the green successful run, visit `https://YOUR_GITHUB_USERNAME.github.io/lake-sawyer-dashboard/`. It may take a few minutes to become available.
6. On iPhone open the URL in **Safari**, choose **Share → Add to Home Screen** (enable **Open as Web App** if shown), and tap **Add**.

## Daily operation

The workflow runs every hour at 15 mins past the hour, subject to GitHub Actions scheduling delays. This UTC schedule does **not** stay at exactly 7:15 AM local time year-round. The webpage fetches `data.json` with a cache-busting query each time it opens, and the Refresh button checks again. If the source is unchanged, the dashboard shows the latest available observation date rather than claiming today's data exists.

To update immediately, open **Actions → Update and publish dashboard → Run workflow**. Wait for the deployment to finish, then tap Refresh in the dashboard.

## Notes

- Measurements in `LEVEL3.TXT` are signed numbers with some blank dates. The script parses only valid dated lines with numeric readings, retaining missing-day gaps in the chart.
- The source's units and reference datum are **not verified**, so the dashboard labels them as *source units*.
- Historical average and range compare the same calendar date in all years before the latest year. Leap day may have fewer samples.
- The chart uses Plotly loaded from a CDN, so the iPhone needs internet access.
- GitHub Pages is publicly accessible. Do not store passwords or other secrets in the repository.
- This uses GitHub's official Pages deployment workflow and does not need a commit on every run.
