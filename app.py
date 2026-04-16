from flask import Flask, g
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Register blueprints ──────────────────────────────
    from routes.users          import users_bp
    from routes.listings       import listings_bp
    from routes.orders         import orders_bp
    from routes.transactions   import transactions_bp
    from routes.wallet         import wallet_bp
    from routes.meters         import meters_bp
    from routes.zones          import zones_bp
    from routes.stats          import stats_bp
    from routes.notifications  import notifications_bp
    from routes.disputes       import disputes_bp
    from routes.ratings        import ratings_bp
    from routes.energy_sources import sources_bp

    app.register_blueprint(users_bp,         url_prefix="/api/users")
    app.register_blueprint(listings_bp,      url_prefix="/api/listings")
    app.register_blueprint(orders_bp,        url_prefix="/api/orders")
    app.register_blueprint(transactions_bp,  url_prefix="/api/transactions")
    app.register_blueprint(wallet_bp,        url_prefix="/api/wallet")
    app.register_blueprint(meters_bp,        url_prefix="/api/meters")
    app.register_blueprint(zones_bp,         url_prefix="/api/zones")
    app.register_blueprint(stats_bp,         url_prefix="/api/stats")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(disputes_bp,      url_prefix="/api/disputes")
    app.register_blueprint(ratings_bp,       url_prefix="/api/ratings")
    app.register_blueprint(sources_bp,       url_prefix="/api/energy-sources")

    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "VoltShare P2P Energy API"}

    return app

if __name__ == "__main__":
    app = create_app()
    PORT = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=PORT, debug=True)
