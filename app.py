from sanic import Sanic, response
from routes.allocation_routes import allocation_routes
from routes.device_routes import device_routes
from config import Config
import os

app = Sanic("XTS_Allocator_Server")

# Register routes
app.blueprint(allocation_routes)
app.blueprint(device_routes)
app.static('/logo.png', './logo.png')

# Serve the main page
@app.route("/")
async def main_page(request):
    return await response.file(os.path.join(os.path.dirname(__file__), "templates", "index.html"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
