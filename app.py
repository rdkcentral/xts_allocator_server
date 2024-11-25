from sanic import Sanic
from routes.allocation_routes import allocation_routes
from routes.device_routes import device_routes
from config import Config

app = Sanic("XTS_Allocator_Server")

# register routes
app.blueprint(allocation_routes)
app.blueprint(device_routes)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    # what port
