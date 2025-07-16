"""
OSC API Server - Multi-language Application with Language Switcher  
"""
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from datetime import datetime

from services.osc_client import OSCClientContext, MockOSCClient
from services.message_factory import message_factory
from services.language_service import language_service, get_request_language
from config.settings import settings
from endpoints.scene_endpoints import router as scene_router
from endpoints.palette_endpoints import router as palette_router
from endpoints.control_endpoints import router as control_router

osc_client = OSCClientContext(MockOSCClient())

def create_app():
    """Create FastAPI app with dynamic language support"""
    app = FastAPI(
        title="OSC LED Engine API",
        description="API server for LED Engine OSC control",
        version="1.0.0",
        docs_url=None,  
        redoc_url=None 
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize OSC client on startup"""
        global osc_client
        pass

    app.include_router(scene_router, prefix="/api/v1", tags=["Scene Management"])
    app.include_router(palette_router, prefix="/api/v1", tags=["Palette Control"])
    app.include_router(control_router, prefix="/api/v1", tags=["LED Control"])
    
    @app.middleware("http")
    async def language_middleware(request: Request, call_next):
        """Middleware to handle language switching"""
        request_lang = get_request_language(request)

        language_service.set_language(request_lang)
        
        response = await call_next(request)
        
        return response

    def custom_openapi(language: str = "en"):
        """Generate OpenAPI schema with localized content"""
        app_content = language_service.get_app_content(language)
        
        openapi_schema = get_openapi(
            title=app_content.get("title", "OSC LED Engine API"),
            version="1.0.0",
            description=app_content.get("description", "API server for LED Engine OSC control"),
            routes=app.routes,
        )
        
        openapi_schema["info"]["x-language"] = language
        
        tags = app_content.get("tags", {})
        endpoints = app_content.get("endpoints", {})
        
        if "tags" in openapi_schema and openapi_schema["tags"]:
            for tag in openapi_schema["tags"]:
                if tag["name"] == "Scene Management":
                    tag["name"] = tags.get("scene_management", "Scene Management")
                    tag["description"] = f"Scene management operations ({language})"
                elif tag["name"] == "Palette Control":
                    tag["name"] = tags.get("palette_control", "Palette Control")
                    tag["description"] = f"Palette control operations ({language})"
                elif tag["name"] == "LED Control":
                    tag["name"] = tags.get("led_control", "LED Control")
                    tag["description"] = f"LED control operations ({language})"
        
        if "paths" in openapi_schema:
            for path, methods in openapi_schema["paths"].items():
                for method, details in methods.items():
                    if method in ["post", "put", "get"]:
                        if "tags" in details:
                            updated_tags = []
                            for tag in details["tags"]:
                                if tag == "Scene Management":
                                    updated_tags.append(tags.get("scene_management", "Scene Management"))
                                elif tag == "Palette Control":
                                    updated_tags.append(tags.get("palette_control", "Palette Control"))
                                elif tag == "LED Control":
                                    updated_tags.append(tags.get("led_control", "LED Control"))
                                else:
                                    updated_tags.append(tag)
                            details["tags"] = updated_tags
                        
                        if "/load_json" in path:
                            endpoint_info = endpoints.get("load_json", {})
                        elif "/change_scene" in path:
                            endpoint_info = endpoints.get("change_scene", {})
                        elif "/change_palette" in path and "palette/{palette_id}" not in path:
                            endpoint_info = endpoints.get("change_palette", {})
                        elif "/palette/{palette_id}" in path:
                            endpoint_info = endpoints.get("palette_color", {})
                        elif "/change_effect" in path:
                            endpoint_info = endpoints.get("change_effect", {})
                        elif "/set_dissolve_time" in path:
                            endpoint_info = endpoints.get("set_dissolve_time", {})
                        elif "/set_speed_percent" in path:
                            endpoint_info = endpoints.get("set_speed_percent", {})
                        elif "/master_brightness" in path:
                            endpoint_info = endpoints.get("master_brightness", {})
                        else:
                            endpoint_info = {}
                        
                        if endpoint_info:
                            details["summary"] = endpoint_info.get("summary", details.get("summary", ""))
                            details["description"] = endpoint_info.get("description", details.get("description", ""))
        
        return openapi_schema

    def get_openapi_for_language(lang: str = "en"):
        """Get OpenAPI schema for specific language - always fresh"""
        return custom_openapi(lang)

    @app.get("/docs", response_class=HTMLResponse)
    async def custom_swagger_ui_html(request: Request, lang: str = Query("en")):
        """Custom Swagger UI with language switcher"""
        if not language_service.validate_language(lang):
            lang = "en"
        
        app.openapi_schema = None
        app.openapi = lambda: get_openapi_for_language(lang)
        
        app_content = language_service.get_app_content(lang)
        
        language_switcher = f"""
        <div style="position: fixed; top: 10px; right: 10px; z-index: 9999; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <label for="lang-select" style="font-weight: bold;">🌐 Language:</label>
            <select id="lang-select" onchange="switchLanguage(this.value)" style="margin-left: 5px; padding: 5px; border: 1px solid #ccc; border-radius: 3px;">
                <option value="vi" {'selected' if lang == 'vi' else ''}>🇻🇳 Tiếng Việt</option>
                <option value="en" {'selected' if lang == 'en' else ''}>🇺🇸 English</option>
                <option value="ja" {'selected' if lang == 'ja' else ''}>🇯🇵 日本語</option>
            </select>
        </div>
        <script>
            function switchLanguage(selectedLang) {{
                window.location.href = '/docs?lang=' + selectedLang;
            }}
        </script>
        """
        
        return get_swagger_ui_html(
            openapi_url=f"/openapi.json?lang={lang}",
            title=app_content.get("title", "OSC LED Engine API") + " - Documentation",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
            swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        ).body.decode() + language_switcher

    @app.get("/redoc", response_class=HTMLResponse)
    async def custom_redoc_html(request: Request, lang: str = Query("en")):
        """Custom ReDoc with language switcher"""
        # Validate language
        if not language_service.validate_language(lang):
            lang = "en"  # Default to Vietnamese
            
        # Clear OpenAPI cache and update for this language 
        app.openapi_schema = None
        app.openapi = lambda: get_openapi_for_language(lang)
        
        # Get localized content
        app_content = language_service.get_app_content(lang)
        
        # Language switcher HTML
        language_switcher = f"""
        <div style="position: fixed; top: 10px; right: 10px; z-index: 9999; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <label for="lang-select" style="font-weight: bold;">🌐 Language:</label>
            <select id="lang-select" onchange="switchLanguage(this.value)" style="margin-left: 5px; padding: 5px; border: 1px solid #ccc; border-radius: 3px;">
                <option value="vi" {'selected' if lang == 'vi' else ''}>🇻🇳 Tiếng Việt</option>
                <option value="en" {'selected' if lang == 'en' else ''}>🇺🇸 English</option>
                <option value="ja" {'selected' if lang == 'ja' else ''}>🇯🇵 日本語</option>
            </select>
        </div>
        <script>
            function switchLanguage(selectedLang) {{
                window.location.href = '/redoc?lang=' + selectedLang;
            }}
        </script>
        """
        
        return get_redoc_html(
            openapi_url=f"/openapi.json?lang={lang}",
            title=app_content.get("title", "OSC LED Engine API") + " - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
            redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        ).body.decode() + language_switcher

    @app.get("/openapi.json")
    async def get_openapi_endpoint(lang: str = Query("vi")):
        """Get OpenAPI schema with language support"""
        # Validate language
        if not language_service.validate_language(lang):
            lang = "en"
        
        # Clear cache and generate new schema for this language
        app.openapi_schema = None
        app.openapi = lambda: get_openapi_for_language(lang)
        
        return get_openapi_for_language(lang)

    @app.get("/")
    async def root(lang: str = Query("en")):
        """Root endpoint with language selector"""
        # Validate language
        if not language_service.validate_language(lang):
            lang = "en"
        app_content = language_service.get_app_content(lang)
        
        return {
            "message": app_content.get("welcome_message", "OSC LED Engine API Server"),
            "version": "1.0.0",
            "documentation": {
                "swagger_ui": f"/docs?lang={lang}",
                "redoc": f"/redoc?lang={lang}"
            },
            "endpoints": {
                "scene": ["/api/v1/load_json", "/api/v1/change_scene"],
                "palette": ["/api/v1/change_palette", "/api/v1/palette/{palette_id}/{color_id}"],
                "control": ["/api/v1/change_effect", "/api/v1/set_dissolve_time", "/api/v1/set_speed_percent", "/api/v1/master_brightness"]
            },
            "current_language": lang,
            "available_languages": {
                "vi": "🇻🇳 Tiếng Việt",
                "en": "🇺🇸 English", 
                "ja": "🇯🇵 日本語"
            }
        }

    @app.get("/health")
    async def health_check(lang: str = Query("en")):
        """Health check endpoint with localized status"""
        if not language_service.validate_language(lang):
            lang = "en"
        connection_status = await osc_client.check_connection()
        
        status_messages = language_service.language_data.get("status_messages", {}).get(lang, {})
        status_text = status_messages.get("healthy", "healthy") if connection_status else status_messages.get("degraded", "degraded")
        
        return {
            "status": status_text,
            "timestamp": datetime.now().isoformat(),
            "language": lang,
            "osc_server": {
                "host": settings.config.osc_server.host,
                "port": settings.config.osc_server.port,
                "connected": connection_status
            }
        }

    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
