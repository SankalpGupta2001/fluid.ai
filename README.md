### AI Platform Engineer – Observability

An observable AI-powered backend service built with Python, FastAPI, Prometheus metrics, Python logging, and OpenTelemetry tracing.

This project was built for the AI Platform Engineer – Observability – 60-Minute Build Challenge. The goal is to demonstrate how an AI backend can be monitored, debugged, and troubleshot using logs, metrics, request correlation IDs, latency measurement, and distributed tracing.

# Assignment Overview

The assignment requires an AI-powered REST backend that:
- Uses Python/FastAPI.
- Exposes POST /ask.
- Accepts a question such as:
{
  "question": "Generate a company report"
}
- Processes the request using an LLM, agent, workflow, or mock AI logic.
- Performs at least one business action.
- Produces structured logs.
- Generates a request/correlation ID.
- Measures request latency.
- Tracks errors using metrics.
- Exposes Prometheus-compatible metrics.
- Provides a /health endpoint.
- Implements one real engineering improvement.
- Demonstrates one successful and one failing/invalid request.
- Shows how observability helps debug failures.

# Technology Stack

- Python
- FastAPI
- Uvicorn
- Pydantic
- Python logging
- ContextVar
- Prometheus Client
- OpenTelemetry
- python-dotenv
- python-docx
- JSON file
- asyncio

# Setup

1. Open the project in root folder fluid.ai
2. Run command cd fluid.ai and then run command source venv/Scripts/activate
3. Now check using command which python
4. It should point to something similar to: .../fluid.ai/venv/Scripts/python
5. Install dependencies: pip install -r requirements.txt
6. Create a .env file:
APP_NAME=Fluid.ai
APP_VERSION=1.0.0
APP_ENV=development
AI_TIMEOUT_SECONDS=2.0
7. Start the FastAPI server:
uvicorn index:app --reload
it will start server in http://localhost:8000

# API Endpoints
1. GET /
Returns basic service information.
{
  "service": "Fluid.ai",
  "version": "1.0.0",
  "status": "running"
}

2. GET /health
Used as a health check.
{
  "status": "healthy",
  "service": "Fluid.ai",
  "version": "1.0.0"
}

3. POST /ask
Main AI endpoint.
Request:
{
  "question": "Generate a company report"
}
Successful response:
{
  "request_id": "5f0db30c-0105-4be1-8aab-0c0c2743ca06",
  "answer": "The AI workflow processed the question successfully and generated a company report.",
  "report": {
    "company": "Acme AI",
    "sector": "Artificial Intelligence",
    "revenue": "$5M",
    "employees": 50,
    "status": "active",
    "summary": "Acme AI is an artificial intelligence company with a growing business operation."
  },
  "status": "success",
  "document": {
    "file_name": "report_<request_id>.docx",
    "file_path": "generated_reports/report_<request_id>.docx"
  }
}

4. GET /metrics
Exposes Prometheus-compatible metrics. The custom metrics includes:
ai_timeout_errors_total
ai_workflow_errors_total

# Request Validation
The /ask endpoint uses Pydantic validation. The question is required and has these constraints:
Minimum length: 3 characters
Maximum length: 2000 characters

For example, an invalid request such as:
{
  "question": ""
}
This will produces a validation error. The application returns HTTP 422.
{
  "success": false,
  "api_error": {
    "dev_msg": "Request validation failed.",
    "user_msg": "Please provide a valid question.",
    "user_msg_title": "Invalid Request!",
    "code": 42201
  },
  "request_id": "<request-id>",
  "details": []
}

# AI Processing
The challenge allows an LLM, agent, workflow, or mock AI logic. For this assignment for the code implementation, a deterministic used mock AI workflow is used instead of an external LLM API.

This keeps the demonstration: deterministic, reproducible, independent of API keys, easy to test, focused on observability rather than model setup.

The mock AI workflow:
1. Receive the Request: The client sends a POST /ask request to the FastAPI backend with a question in the request body, for example { "question": "Generate a company report" }.
2. Validate the Request: FastAPI validates the incoming request using the Pydantic AskRequest model. If the question is missing or invalid, the API returns a 422 Validation Error.
3. Generate Request ID: The request middleware generates a unique Request ID for every request. This ID is used to correlate the request across application logs, metrics, and OpenTelemetry traces.
4. Start AI Processing: The /ask endpoint starts the mock AI workflow and passes the user's question to the process_ai_request() function, which creates an OpenTelemetry AI Processing span.
5. Simulate AI Processing: The mock AI function receives the question and uses an artificial delay to simulate the latency of a real AI/LLM provider. It also has a timeout scenario to demonstrate how AI failures are handled.
6. Generate Company Report: After the simulated AI processing, the workflow generates structured company information:
{
  "company": "Acme AI",
  "sector": "Artificial Intelligence",
  "revenue": "$5M",
  "employees": 50,
  "status": "active",
  "summary": "Acme AI is an artificial intelligence company with a growing business operation."
}
7. Generate AI Answer: Along with the structured report, the mock AI generates a natural-language answer explaining that the AI workflow successfully processed the question and generated the company report.
8. Save and Generate Business Output: The backend saves the question, Request ID, and generated report into mock_db.json. It then generates a DOCX company report inside the generated_reports directory.
9. Return the Final API Response: The /ask endpoint returns the request_id, AI-generated answer, structured company report, success status, and generated document information to the client.
10. Complete Observability: After the workflow finishes, the middleware records the HTTP status code and request latency. Logs contain the Request ID, Prometheus records errors such as AI timeouts, and OpenTelemetry records the request flow and AI processing span for debugging and tracing.

# Business Action
The service performs two business actions after AI processing.

Action 1: Persist the report
The report is stored in: mock_db.json
{
  "request_id": "<request-id>",
  "question": "Generate a company report",
  "report": {
    "company": "Acme AI",
    "sector": "Artificial Intelligence",
    "revenue": "$5M",
    "employees": 50
  }
}
This represents persistence to a database in a real production system.

Action 2: Generate a company report (DOCX File)
The service creates: generated_reports/report_<request_id>.docx
The document contains: 
- Request ID
- Company information
- Report fields
This demonstrates a real business workflow after AI processing.

# Structured Logging
The application uses Python's built-in logging module with a custom formatter. The application also intercepts normal Python: print() and sends it through the logging system.
This allows application code to continue using simple print() calls while still producing structured log output.

Example:
[2026-09-25 10:43:30] INFO  ############# POST /ask #############  file: index.py  line: 230

The log structure provides:
Timestamp
Log level
Message
Filename
Line number
Request ID
Exception information when available

After this the all logs for all log level will store in the app.log file and it will rotate weekly to avoid storage issue.

# Request Correlation ID
Every request receives a unique request ID. The middleware first checks: X-Request-ID
If the client does not provide one, the application generates a UUID.
Example:
5f0db30c-0105-4be1-8aab-0c0c2743ca06
The ID is then available throughout the request.
It appears in: 
- Application logs
- OpenTelemetry spans
- API response
- Database record
- Generated report

# Request Latency
The FastAPI middleware records the time immediately before the request is processed.
After processing: duration_ms = elapsed_time * 1000
The response includes:
X-Request-ID
X-Response-Time-Ms

# Prometheus Metrics
The application uses: prometheus_client
Two custom error counters are implemented.
ai_timeout_errors_total
ai_workflow_errors_total

The Logs tell us what happened. Metrics tell us how often it happened.
Like : 
ai_timeout_errors_total 1.0
This tell that immediately tells us that an AI timeout has occurred.

# OpenTelemetry Tracing
OpenTelemetry is the main engineering improvement selected for this assignment.
I used trace in two place in POST /ask API, AI Processing.

The child span contains the parent span ID.

The child:

========== TRACE ==========
Span       : AI Processing
Trace ID   : 37025ab247e90e728e486319c87b8fd4
Span ID    : 7b11c3731fed6887
Parent ID  : 9c47ebd7c7b60998
Status     : OK
Duration   : 351.11 ms
Attributes :
  request_id: 5f0db30c-0105-4be1-8aab-0c0c2743ca06
===========================

The parent:

========== TRACE ==========
Span       : POST /ask
Trace ID   : 37025ab247e90e728e486319c87b8fd4
Span ID    : 9c47ebd7c7b60998
Parent ID  : None
Status     : OK
Duration   : 749.55 ms
Attributes :
  request_id: 5f0db30c-0105-4be1-8aab-0c0c2743ca06
===========================

# Error Handling
The application handles several types of failures.

1. Validation error

Invalid request:
HTTP 422

2. AI timeout
Please use the input in question as "trigger_failure" because this is mock code so failure occur in this case only.
When this value is received, the workflow raises: TimeoutError
The endpoint converts it into: HTTP 504 Gateway Timeout

3. Unexpected workflow error
Unexpected errors are converted into: HTTP 500

# Test Case 1 – Successful Request
Use:
{
  "question": "Generate a company report"
}

Expected result:
HTTP 200 OK
The response contains: 
- request ID
- AI answer
- report
- status
- generated DOCX path

So the process becomes like:
POST /ask -> Request Started -> AI Processing -> Generate reports in JSON format by AI  -> Report saved in db -> Company report generated (DOCX FILE) -> Request Completed


Terminal Logs and in the /docs dashobard:
Request:
{
  "question": "Generate a company report"
}
Response:
Status: 200
Response body:
{
  "request_id": "abd8f58e-9ca0-442f-a54e-d8236f391cc2",
  "answer": "The AI workflow processed the question successfully and generated a company report.",
  "report": {
    "company": "Acme AI",
    "sector": "Artificial Intelligence",
    "revenue": "$5M",
    "employees": 50,
    "status": "active",
    "summary": "Acme AI is an artificial intelligence company with a growing business operation."
  },
  "status": "success",
  "document": {
    "file_name": "report_abd8f58e-9ca0-442f-a54e-d8236f391cc2.docx",
    "file_path": "generated_reports\\report_abd8f58e-9ca0-442f-a54e-d8236f391cc2.docx"
  }
}
Response headers:
content-length: 533 
content-type: application/json 
date: Fri,25 Sep 2026 06:17:47 GMT 
server: uvicorn 
x-request-id: abd8f58e-9ca0-442f-a54e-d8236f391cc2 
x-response-time-ms: 717.53 

Terminal Logs:
2026-09-25 11:47:47:990 info: "############# Request POST /ask Started #############" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:207)
2026-09-25 11:47:47:991 info: "Request ID: abd8f58e-9ca0-442f-a54e-d8236f391cc2" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:208)
2026-09-25 11:47:47:994 info: "The ai request start processing" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:333)

========== TRACE ==========
Span       : AI Processing
Trace ID   : 5614cbeac14b203e6b62aa227ce0ef54
Span ID    : abca68fad9e7d8ff
Parent ID  : 0a076401ed5abb33
Status     : OK
Duration   : 354.77 ms
Attributes :
  request_id: abd8f58e-9ca0-442f-a54e-d8236f391cc2
===========================

2026-09-25 11:47:48:395 info: "The ai request get completed {'company': 'Acme AI', 'sector': 'Artificial Intelligence', 'revenue': '$5M', 'employees': 50, 'status': 'active', 'summary': 'Acme AI is an artificial intelligence company with a growing business operation.'}" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:340)
2026-09-25 11:47:48:508 info: "Saved data in db" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:348)
2026-09-25 11:47:48:695 info: "Generated the docx file generated_reports\report_abd8f58e-9ca0-442f-a54e-d8236f391cc2.docx" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:355)

========== TRACE ==========
Span       : POST /ask
Trace ID   : 5614cbeac14b203e6b62aa227ce0ef54
Span ID    : 0a076401ed5abb33
Parent ID  : None
Status     : OK
Duration   : 702.07 ms
Attributes :
  request_id: abd8f58e-9ca0-442f-a54e-d8236f391cc2
===========================

2026-09-25 11:47:48:708 info: "Status Code: 200" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:217)
2026-09-25 11:47:48:708 info: "Duration: 717.53 ms" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:218)
2026-09-25 11:47:48:708 info: "//////////// Request POST /ask Completed ////////////" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:220)
INFO:     127.0.0.1:53447 - "POST /ask HTTP/1.1" 200 OK

# Test Case 2 – Failing Request
Use:
{
  "question": "trigger_failure"
}
The mock AI workflow intentionally raises a timeout.

Expected result:
HTTP 504 Gateway Timeout

POST /ask -> Request Started -> AI Processing -> Error occur -> Request Completed

Expected metric:
ai_timeout_errors_total 1.0

Terminal Logs and in the /docs dashobard:
Request:
{
  "question": "trigger_failure"
}
Response:
Status: 504
Response body:
{
  "detail": {
    "success": false,
    "api_error": {
      "dev_msg": "AI provider timed out while processing the request.",
      "user_msg": "The AI service is taking too long to respond.",
      "user_msg_title": "AI Timeout!",
      "code": 50401
    },
    "request_id": "837557da-bae6-485e-9b85-60d93498947c"
  }
}
Response headers:
content-length: 261 
content-type: application/json 
date: Fri,25 Sep 2026 06:20:16 GMT 
server: uvicorn 
x-request-id: 837557da-bae6-485e-9b85-60d93498947c 
x-response-time-ms: 236.6 

Terminal Logs:
2026-09-25 11:50:17:322 info: "############# Request POST /ask Started #############" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:207)
2026-09-25 11:50:17:322 info: "Request ID: 837557da-bae6-485e-9b85-60d93498947c" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:208)
2026-09-25 11:50:17:324 info: "The ai request start processing" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:333)

========== TRACE ==========
Span       : AI Processing
Trace ID   : fe9c96c9772a7a95c6074b9cca1b7ca1
Span ID    : 55a97806741a86c1
Parent ID  : 459f833ebd1b0ec7
Status     : ERROR
Duration   : 209.80 ms
Attributes :
  request_id: 837557da-bae6-485e-9b85-60d93498947c
Events     :
  exception
  exception
===========================

2026-09-25 11:50:17:540 error: "The timeout error came in the ai processing" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:371)

========== TRACE ==========
Span       : POST /ask
Trace ID   : fe9c96c9772a7a95c6074b9cca1b7ca1
Span ID    : 459f833ebd1b0ec7
Parent ID  : None
Status     : ERROR
Duration   : 223.43 ms
Attributes :
  request_id: 837557da-bae6-485e-9b85-60d93498947c
Events     :
  exception
  exception
===========================

2026-09-25 11:50:17:558 info: "Status Code: 504" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:217)
2026-09-25 11:50:17:559 info: "Duration: 236.6 ms" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:218)
2026-09-25 11:50:17:559 info: "//////////// Request POST /ask Completed ////////////" (at file:///C:/Users/SANKALP/OneDrive/Desktop/web/fluid.ai/index.py:220)
INFO:     127.0.0.1:54521 - "POST /ask HTTP/1.1" 504 Gateway Timeout

# Debugging Demonstration

- Firstly we get api response as 504 Gateway Timeout
- Now in terminal we can check logs we got:
ERROR The timeout error came in the ai processing
which shows that time out error occurs
- In which request error occur that shown by request id 965b4280-809b-42ae-a817-ad49805baebe, fileName, lineNumber, log lovel.
- Then in Metrics we check by using /metrics api in that using  Prometheus we see ai_timeout_errors_total 1.0
- Finally, check the OpenTelemetry trace. The trace show everything how much time taken by function and what error came.


# Observability Signals
- Logs: What happened?
- Metrics: How often is it happening?
- Traces: Where did it happen and how did the request flow?

# Tradeoff Discussion

The main engineering tradeoff is:

1. Simplicity vs Observability
I have added the Observability signals as structured logging, request IDs, metrics, tracing, error handling without observability, an AI failure can be difficult to diagnose.
I have added very simple logs pattern which is simple to identify the issue happen and trace is also to identify the time required in the process.

2. Logging vs Performance
Detailed logs provide valuable debugging information but can: increase log volume consume storage, increase I/O, and can potentially affect application performance. But for this one solution is that we can use store logs in logs folder in application it self and for storage issue we can use daily rotate file logs so that previous logs automaticaly deleted.

3. Metrics vs Detail
Metrics are lightweight and useful for identifying trends.
Like:
ai_timeout_errors_total tells us that timeouts occurred.
But
The metric does not tell us the complete reason for an individual failure so for this logs and traces are useful.

4. Tracing vs Complexity
Tracing provides request-flow and latency information, but instrumentation and trace exporting add complexity and some overhead.
The production system could export OpenTelemetry traces to a proper backend such as Jaeger, Tempo, or another supported observability system.

# Future Improvements (In Production)
1. Real LLM or AI Agent (LangChain, LangGraph, OpenAI).
2. Replace mock_db.json with MySQL
3. Instead of generating reports as .docx file in the generated_reports/ we will use S3 bucket to store content in that and we send s3 bucket url to the frontend.
4. Security: We will use JWT, bcyrpt for authetication , authorization.
5. Deployment: We can use Docker because in AI service we will use RAG so have self hosted vector store also to store context so for hosting vector store in the AWS EC2 Server we  can use docker like Milvus so we will use docker to host service.

Video Link: https://drive.google.com/file/d/1GV5i4BumQc_M6aajpDugn5iN4ZHNimGK/view?usp=sharing
