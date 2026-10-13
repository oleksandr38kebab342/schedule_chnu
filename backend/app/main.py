from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(
    title="Система управління навчальним розкладом",
    description="API для формування, перевірки та відображення розкладу занять.",
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/health", tags=["service"])
def health() -> dict[str, str]:
    return {"status": "ok"}
