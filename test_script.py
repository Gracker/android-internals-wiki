import urllib.request
url = "https://developer.android.com/reference/androidx/metrics/performance/JankStats"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    print("Fetched AndroidX JankStats")
except Exception as e:
    print(f"Error: {e}")
