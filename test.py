import requests

params = {
    'key': 'AIzaSyD_G5I4QCRCZHy8-5vrljX6fB1LH5FdRLk',
    'cx': 'd4523cb7fe42a4075',
    'q': 'test',
    'num': 1
}

r = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")