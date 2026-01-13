"""
Flow Trials - FastAPI Backend
Wires together platform, search, and AI modules
"""
from fastapi import FastAPI

from platform_module import configure_cors, register_health_route, register_startup_handler
from search_module import register_search_routes
from ai_module import register_ai_routes

# ======================================================================
# APP INITIALIZATION
# ======================================================================

app = FastAPI(title="Clinical Trials Search API")

# Configure CORS
configure_cors(app)

# Register routes
register_health_route(app)
register_search_routes(app)
register_ai_routes(app)

# Register startup handler
register_startup_handler(app)
