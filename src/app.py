import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

from mcp_server.server import MCPServer

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

server = MCPServer()
server.start()

app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>MCP Tools</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; margin: 2rem; }
    button { padding: 0.5rem 1rem; font-size: 1rem; margin-right: 0.5rem; }
    ul { margin-top: 1rem; }
    li { margin: 0.25rem 0; }
    .container { margin-top: 2rem; }
    .card { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin-top: 1rem; }
    input { padding: 0.5rem; font-size: 1rem; margin-right: 0.5rem; width: 200px; }
    .weather-data { margin-top: 1rem; }
    .weather-data p { margin: 0.5rem 0; }
    .error { color: red; }
  </style>
</head>
<body>
  <h1>MCP Server Tools</h1>
  <button id=\"load\">List Tools</button>
  <ul id=\"tools\"></ul>
  
  <div class="container">
    <h2>Weather Tool</h2>
    <div>
      <input type="text" id="location" placeholder="Enter city (e.g. London)" />
      <select id="units">
        <option value="metric">Celsius</option>
        <option value="imperial">Fahrenheit</option>
      </select>
      <button id="getWeather">Get Weather</button>
    </div>
    <div id="weatherResult" class="card weather-data" style="display: none;"></div>
  </div>
  
  <script>
    document.getElementById('load').onclick = async () => {
      const res = await fetch('/api/tools');
      const data = await res.json();
      const ul = document.getElementById('tools');
      ul.innerHTML = '';
      (data.tools || []).forEach(t => {
        const li = document.createElement('li');
        const desc = t.description ? ` - ${t.description}` : '';
        const ver = t.version ? ` (${t.version})` : '';
        li.textContent = `${t.name}${ver}${desc}`;
        ul.appendChild(li);
      });
    };
    
    document.getElementById('getWeather').onclick = async () => {
      const location = document.getElementById('location').value;
      const units = document.getElementById('units').value;
      const resultDiv = document.getElementById('weatherResult');
      
      if (!location) {
        resultDiv.innerHTML = '<p class="error">Please enter a location</p>';
        resultDiv.style.display = 'block';
        return;
      }
      
      resultDiv.innerHTML = '<p>Loading weather data...</p>';
      resultDiv.style.display = 'block';
      
      try {
        const res = await fetch(`/api/weather?location=${encodeURIComponent(location)}&units=${units}`);
        const data = await res.json();
        
        if (data.status === 'success') {
          const weather = data.data;
          resultDiv.innerHTML = `
            <h3>${weather.location}</h3>
            <p><strong>Description:</strong> ${weather.description}</p>
            <p><strong>Temperature:</strong> ${weather.temperature}</p>
            <p><strong>Feels like:</strong> ${weather.feels_like}</p>
            <p><strong>Humidity:</strong> ${weather.humidity}</p>
            <p><strong>Wind:</strong> ${weather.wind}</p>
          `;
        } else {
          resultDiv.innerHTML = `<p class="error">Error: ${data.message}</p>`;
        }
      } catch (e) {
        resultDiv.innerHTML = `<p class="error">Error fetching weather data: ${e.message}</p>`;
      }
    };
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/tools")
def api_tools():
    tools_list = []
    try:
        names = server.get_registered_tools()
        for name in names:
            meta = server.get_tool(name)
            if meta is not None:
                tools_list.append(
                    {
                        "name": getattr(meta, "name", name),
                        "description": getattr(meta, "description", ""),
                        "version": getattr(meta, "version", ""),
                    }
                )
            else:
                tools_list.append({"name": name})
    except Exception as e:
        logging.exception("Failed to list tools: %s", e)
    return jsonify({"tools": tools_list})


@app.route("/api/weather")
def api_weather():
    location = request.args.get("location")
    units = request.args.get("units", "metric")

    if not location:
        return jsonify({"status": "error", "message": "Location parameter is required"})

    try:
        weather_tool = server.get_tool_instance("WeatherTool")
        if not weather_tool:
            return jsonify({"status": "error", "message": "Weather tool not available"})

        result = weather_tool.get_weather(location, units)
        return jsonify(result)
    except Exception as e:
        logging.exception("Weather API error: %s", e)
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
