from __future__ import annotations

import asyncio
import builtins
import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from docx import Document
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, make_asgi_app
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from logging.handlers import TimedRotatingFileHandler

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Fluid.ai")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("APP_ENV", "development")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "2.0"))
request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

MOCK_DB_FILE = Path("mock_db.json")
REPORTS_DIR = Path("generated_reports")
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

AI_TIMEOUT_ERRORS = Counter(
    "ai_timeout_errors_total",
    "Total number of AI timeout errors",
)

AI_WORKFLOW_ERRORS = Counter(
    "ai_workflow_errors_total",
    "Total number of unexpected AI workflow errors",
)

AI_REQUESTS_TOTAL = Counter(
    "ai_requests_total",
    "Total number of AI requests.",
    ["status"],
)

def get_request_id() -> str:
    return request_id_context.get()

class JsonFormatter(logging.Formatter):

    def format(self, record):
        now = time.localtime(record.created)

        milliseconds = int(
            (record.created - int(record.created)) * 1000
        )

        timestamp = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S', now)}"
            f":{milliseconds:03d}"
        )

        message = record.getMessage()

        file_path = record.pathname.replace("\\", "/")
        file_url = f"file:///{file_path}"

        return (
            f'{timestamp} '
            f'{record.levelname.lower()}: '
            f'"{message}" '
            f'(at {file_url}:{record.lineno})'
        )

logger = logging.getLogger("fluid_ai")
logger.setLevel(logging.DEBUG)
logger.handlers.clear()
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(JsonFormatter())
file_handler = TimedRotatingFileHandler(
    LOGS_DIR / "app.log",
    when="W0",
    interval=1,
    backupCount=2,
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(JsonFormatter())
logger.addHandler(console_handler)
logger.addHandler(file_handler)
_original_print = builtins.print

def structured_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    logger.info(message, stacklevel=2)

def print_debug(*args):
    message = " ".join(str(arg) for arg in args)
    logger.debug(message, stacklevel=2)

def print_warning(*args):
    message = " ".join(str(arg) for arg in args)
    logger.warning(message, stacklevel=2)

def print_error(*args):
    message = " ".join(str(arg) for arg in args)
    logger.error(message, stacklevel=2)

builtins.print = structured_print

class SimpleConsoleExporter(SpanExporter):

    def export(self, spans):
        for span in spans:
            duration_ms = (
                span.end_time - span.start_time
            ) / 1_000_000

            _original_print()
            _original_print("========== TRACE ==========")
            _original_print(f"Span       : {span.name}")
            _original_print(f"Trace ID   : {span.context.trace_id:032x}")
            _original_print(f"Span ID    : {span.context.span_id:016x}")

            if span.parent:
                _original_print(
                    f"Parent ID  : {span.parent.span_id:016x}"
                )
            else:
                _original_print("Parent ID  : None")

            _original_print(
                f"Status     : {span.status.status_code.name}"
            )
            _original_print(
                f"Duration   : {duration_ms:.2f} ms"
            )

            if span.attributes:
                _original_print("Attributes :")
                for key, value in span.attributes.items():
                    _original_print(f"  {key}: {value}")

            if span.events:
                _original_print("Events     :")
                for event in span.events:
                    _original_print(f"  {event.name}")

            _original_print("===========================")
            _original_print()

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(SimpleConsoleExporter()))
tracer = trace.get_tracer("fluid-ai")

app = FastAPI(title="AI Platform Service", version=APP_VERSION, description="AI backend with request correlation and error handling.",)

class AskRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=2000,
        description="Question to send to the AI workflow.",
    )

class AskResponse(BaseModel):
    request_id: str
    answer: str
    report: dict[str, Any]
    status: str
    document: dict[str, str]

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = get_request_id()
    print("request_validation_failed")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "api_error": {
                "dev_msg": "Request validation failed.",
                "user_msg": "Please provide a valid question.",
                "user_msg_title": "Invalid Request!",
                "code": 42201,
            },
            "request_id": request_id,
            "details": exc.errors(),
        },
    )

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    incoming_request_id = request.headers.get("X-Request-ID")
    request_id = (
        incoming_request_id
        if incoming_request_id
        else str(uuid.uuid4())
    )
    request_id_context.set(request_id)
    start_time = time.perf_counter()
    response = None
    request_name = f"{request.method} {request.url.path}"

    print(f"############# Request {request_name} Started #############")
    print(f"Request ID: {request_id}")

    try:
        response = await call_next(request)
        return response
    finally:
        duration = (time.perf_counter() - start_time)
        duration_ms = round(duration * 1000, 2)
        status_code = response.status_code if response else 500
        print(f"Status Code: {status_code}")
        print(f"Duration: {duration_ms} ms")

        print(f"//////////// Request {request_name} Completed ////////////")
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(duration_ms)

async def run_ai_model(question: str) -> dict[str, Any]:
    if question.strip().lower() == "trigger_failure":
        await asyncio.sleep(0.2)
        raise TimeoutError(
            "AI provider timed out while processing the request."
        )
    await asyncio.sleep(0.35)
    report = {
        "company": "Acme AI",
        "sector": "Artificial Intelligence",
        "revenue": "$5M",
        "employees": 50,
        "status": "active",
        "summary": (
            "Acme AI is an artificial intelligence company "
            "with a growing business operation."
        ),
    }
    answer = "The AI workflow processed the question successfully and generated a company report."
    return {
        "answer": answer,
        "report": report,
    }

async def process_ai_request(question: str) -> dict[str, Any]:
    with tracer.start_as_current_span("AI Processing") as span:
        span.set_attribute("request_id", get_request_id())

        try:
            result = await asyncio.wait_for(
                run_ai_model(question),
                timeout=AI_TIMEOUT_SECONDS,
            )

            span.set_status(Status(StatusCode.OK))
            return result

        except Exception as error:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(error)
            raise

async def save_report_to_mock_db(request_id: str, question: str, report: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(0.1)
    if MOCK_DB_FILE.exists():
        with open(MOCK_DB_FILE, "r", encoding="utf-8") as file:
            database = json.load(file)
    else:
        database = {
            "reports": []
        }
    report_record = {
        "request_id": request_id,
        "question": question,
        "report": report,
    }
    database["reports"].append(report_record)
    with open(MOCK_DB_FILE, "w", encoding="utf-8") as file:
        json.dump(database, file, indent=2)
    return {
        "saved": True,
        "request_id": request_id,
    }

async def generate_report_docx(request_id: str, report: dict[str, Any]) -> str:
    await asyncio.sleep(0.1)
    document = Document()
    document.add_heading("AI Company Report", level=1)
    document.add_paragraph(f"Request ID: {request_id}")
    document.add_heading("Company Information", level=2)

    for key, value in report.items():
        document.add_paragraph(f"{key.replace('_', ' ').title()}: {value}")
    file_path = REPORTS_DIR / f"report_{request_id}.docx"
    document.save(file_path)
    return str(file_path)

@app.get("/")
async def index():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
    }

metrics_app = make_asgi_app()

app.mount(
    "/metrics",
    metrics_app,
)

@app.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    request_id = get_request_id()

    with tracer.start_as_current_span("POST /ask") as span:
        span.set_attribute("request_id", request_id)

        try:
            print("The ai request start processing")

            ai_result = await process_ai_request(payload.question)

            answer = ai_result["answer"]
            report = ai_result["report"]

            print("The ai request get completed", report)

            AI_REQUESTS_TOTAL.labels(status="success").inc()

            await save_report_to_mock_db(
                request_id=request_id,
                question=payload.question,
                report=report,
            )

            print("Saved data in db")

            docx_path = await generate_report_docx(
                request_id=request_id,
                report=report,
            )

            print("Generated the docx file", docx_path)
            span.set_status(Status(StatusCode.OK))
            return {
                "request_id": request_id,
                "answer": answer,
                "report": report,
                "status": "success",
                "document": {
                    "file_name": f"report_{request_id}.docx",
                    "file_path": docx_path,
                },
            }

        except TimeoutError as error:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(error)
            print_error("The timeout error came in the ai processing")
            AI_REQUESTS_TOTAL.labels(status="error").inc()
            AI_TIMEOUT_ERRORS.inc()

            raise HTTPException(
                status_code=504,
                detail={
                    "success": False,
                    "api_error": {
                        "dev_msg": "AI provider timed out while processing the request.",
                        "user_msg": "The AI service is taking too long to respond.",
                        "user_msg_title": "AI Timeout!",
                        "code": 50401,
                    },
                    "request_id": request_id,
                },
            )

        except Exception as error:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(error)
            print_error("The error occur in the ai processing")
            AI_REQUESTS_TOTAL.labels(status="error").inc()
            AI_WORKFLOW_ERRORS.inc()

            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "api_error": {
                        "dev_msg": "Unexpected error occurred during AI workflow.",
                        "user_msg": "Something went wrong while processing your request.",
                        "user_msg_title": "Something Went Wrong!",
                        "code": 50001,
                    },
                    "request_id": request_id,
                },
            )

if __name__ == "__main__":
    uvicorn.run(
        "index:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
