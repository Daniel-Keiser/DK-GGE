from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
import pandas as pd
import time
import os

app = FastAPI()

# Serve static files (like HTML, CSS, JS) from the "static" directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Path for the CSV file
csv_file_path = 'static/output.csv'

def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve data from {url}. Error: {e}")
        return None

def process_data(data):
    content = data.get('content', {})
    L_array = content.get('L', [])
    results = []
    for item in L_array:
        player_id = item[1]  # ID is the loot value
        alliance_name = item[2].get('AN', '')
        loot_value = int(item[2].get('CF', 0))
        if alliance_name == 'Soft Kittens':
            results.append((player_id, item[2].get('N'), loot_value))
    return results

def format_sv_value(index):
    if index == 0:
        return '225'
    else:
        return f"22{15 + 10 * (index - 1)}"

def fetch_data_for_looting(base_url, loot_limit, collected_data):
    current_index = 0
    valid_players_found = False
    
    while True:
        formatted_value = format_sv_value(current_index)
        url = f"{base_url}%22LT%22:2,%22LID%22:1,%22SV%22:%{formatted_value}%22"
        print(f"Fetching data from {url}")
        data = fetch_data(url)
        if data:
            results = process_data(data)
            if results:
                for result in results:
                    player_id, name, loot_value = result
                    if player_id >= loot_limit:
                        collected_data.append((player_id, name))
                        valid_players_found = True
                        print(f"Found player from 'Soft Kittens': loot={player_id}, Name={name}")
                    else:
                        if valid_players_found:
                            print(f"Stopping as loot value {player_id} is less than or equal to the limit.")
                            return
            else:
                print("No relevant data found in this batch, continuing...")
            current_index += 1
            time.sleep(1)
        else:
            print("No more data to fetch from the current index.")
            break

def generate_csv():
    loot_limit = 5000000  # Example limit
    base_url = 'https://empire-api.fly.dev/EmpireEx_21/hgh/'
    all_data = []

    fetch_data_for_looting(base_url, loot_limit, all_data)
    df = pd.DataFrame(all_data, columns=['Loot ID', 'Name'])
    df.to_csv(csv_file_path, index=False, sep=',', encoding='utf-8')

@app.on_event("startup")
async def startup_event():
    # Generate the CSV file when the server starts
    if not os.path.exists(csv_file_path):
        generate_csv()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    file_path = "static/index.html"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return HTMLResponse(content=file.read())
    return HTMLResponse(content="<h1>Index file not found</h1>", status_code=404)

@app.get("/download-csv/")
async def download_csv():
    if os.path.exists(csv_file_path):
        return FileResponse(csv_file_path, media_type='text/csv', filename='output.csv')
    else:
        return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
