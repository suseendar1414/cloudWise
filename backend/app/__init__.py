"""CloudWise Backend Application"""

from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI()
    
    from app.api.routes.query import router as query_router
    app.include_router(query_router)
    
    @app.get("/test")
    def test():
        return {"message": "test endpoint working"}
    
    @app.get("/health")
    def health_check():
        return {"status": "healthy"}
    
    return app
