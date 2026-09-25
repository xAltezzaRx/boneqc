import base64

from fastapi import FastAPI, HTTPException

from app.contracts import (
    AnalyzeRequest,
    AnalyzeResponse,
    ModelInfoResponse,
)
from app.inference import (
    create_inference_engine,
)


app = FastAPI(
    title="BoneQC AI Engine",
    version="0.2.0",
)

engine = create_inference_engine()


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get(
    "/v1/model",
    response_model=ModelInfoResponse,
)
async def model_info() -> ModelInfoResponse:
    return engine.model_info()


@app.post(
    "/v1/analyze",
    response_model=AnalyzeResponse,
)
async def analyze(
    request: AnalyzeRequest,
) -> AnalyzeResponse:
    try:
        preview = base64.b64decode(
            request.preview_png_base64,
            validate=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid preview_png_base64"
            ),
        ) from exc

    if not preview:
        raise HTTPException(
            status_code=422,
            detail="Preview image is empty",
        )

    return await engine.analyze(
        request,
        preview,
    )
