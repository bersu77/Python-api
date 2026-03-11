import utils.session
import os
from app import create_app, db
from app.config import config_map

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_map.get(config_name, config_map["default"]))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
