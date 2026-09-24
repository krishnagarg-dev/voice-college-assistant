# KIET AI Assistant

> **Voice-Based College Information Assistant Using RAG and Tool
> Calling**

A production-style academic project that provides a voice-first
interface for answering student questions using information available
from official KIET sources.

**Live Frontend:** https://voice-college-assistant.vercel.app\
**Backend API:** https://voice-college-assistant.onrender.com\
**API Docs:** https://voice-college-assistant.onrender.com/docs

------------------------------------------------------------------------

## 1. Project Overview

KIET AI Assistant is a college information assistant designed around
four core ideas:

1.  **Voice-first interaction** --- students can ask questions using
    browser speech recognition and hear answers using speech synthesis.
2.  **Grounded AI answers** --- the assistant retrieves relevant
    information from a curated KIET knowledge base before generating an
    answer.
3.  **Official source citations** --- supported answers provide
    clickable KIET source links.
4.  **Safe fallback and human handoff** --- when the available KIET
    knowledge does not verify an answer, the assistant avoids inventing
    information and can offer human/WhatsApp escalation.

The project is designed as an MCA CA1 academic project while keeping the
architecture suitable for future institutional integration.

------------------------------------------------------------------------

## 2. Key Features

### Voice Assistant

-   Browser-based speech-to-text.
-   Text-to-speech for assistant responses.
-   Voice states:
    -   `LISTENING`
    -   `THINKING`
    -   `SPEAKING`
    -   `ERROR`
-   Microphone recognition is paused while the assistant speaks.
-   Starting a voice session provides a welcome message after the user's
    click, avoiding browser autoplay restrictions.
-   Stop Conversation cancels active speech and recognition.

### Text Chat

-   Typed questions are supported alongside voice input.
-   Conversation history appears after interaction.
-   The same backend grounding pipeline is used for typed and voice
    questions.

### RAG Knowledge Base

-   Curated official KIET web sources.
-   TXT/PDF document ingestion support.
-   Chunking and local embeddings.
-   ChromaDB vector storage.
-   Metadata-aware retrieval.
-   Relevance filtering.
-   Deterministic chunk identifiers and content checks to reduce
    duplicate ingestion.
-   MCA-specific programme metadata where applicable.
-   Safe no-context/no-information behavior.

### Tool Calling

The backend contains a deterministic query-routing layer and tool
registry for:

-   Latest notices/circulars
-   Upcoming events
-   Academic calendar
-   Timetable

Live providers are restricted to approved KIET HTTPS sources. If an
official source does not provide the requested information, the
assistant does not fabricate it.

### Grounded Answers and Citations

Answers are generated from retrieved/verified context.

Examples of supported information include: - Admissions - MCA
eligibility - MCA admission information - Curriculum - Rules and
discipline - Scholarships - Placement information - Placement training /
CRPC information - Other indexed official KIET information

### Safe Unknown-Question Handling

For questions outside the verified knowledge base, the assistant can
return:

> I don't have enough verified information to answer that accurately.

The system is designed not to turn unrelated or unsupported content into
a confident KIET answer.

### Human Escalation

When verified information is insufficient, the interface can provide: -
Contact the KIET team - Continue on WhatsApp

The WhatsApp workflow: - Shows a preview before opening WhatsApp. -
Allows the message to be reviewed/edited. - Includes the current
question and assistant response by default. - Can include relevant
official source links. - Does not expose internal prompts, RAG metadata,
vector IDs, API information, browser/IP data, or backend diagnostics. -
Opens WhatsApp with a draft; the user decides whether to send it. -
Never claims that the message has already been sent.

------------------------------------------------------------------------

## 3. Architecture

``` text
Student
   |
   v
KIET AI Assistant UI
   |
   +----------------------+
   |                      |
Voice Input            Typed Input
   |                      |
Speech Recognition        |
   +----------+-----------+
              |
              v
        FastAPI /api/chat
              |
              v
        Query Router
          /       \
         /         \
        v           v
      RAG          Tools
       |             |
       v             v
   ChromaDB      Official KIET
   Knowledge      Live Sources
       \             /
        \           /
         v         v
             Gemini
                |
                v
       Grounded Response
        + Citations
                |
          +-----+-----+
          |           |
          v           v
       Chat UI    Text-to-Speech
```

------------------------------------------------------------------------

## 4. Technology Stack

### Frontend

-   React
-   Vite
-   CSS
-   Browser Web Speech APIs
-   Responsive UI
-   Safe answer rendering

### Backend

-   Python
-   FastAPI
-   Uvicorn
-   Pydantic
-   Modular service architecture

### AI

-   Gemini
-   Official Google GenAI SDK

### RAG

-   ChromaDB
-   Local embedding model
-   Document chunking
-   Metadata-aware retrieval

### Deployment

-   Vercel --- frontend
-   Render --- backend
-   GitHub --- source control

------------------------------------------------------------------------

## 5. Repository Structure

``` text
voice-college-assistant/
│
├── backend/
│   ├── app/
│   │   ├── config/
│   │   ├── rag/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── tools/
│   │   └── main.py
│   │
│   ├── data/
│   │   └── source_registry.json
│   │
│   ├── tests/
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── .python-version
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── App.css
│   │
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

------------------------------------------------------------------------

## 6. Backend API

### Health

``` http
GET /health
```

Expected response:

``` json
{
  "status": "ok"
}
```

### Chat

``` http
POST /api/chat
```

Example request:

``` json
{
  "message": "What is the admission process of MCA?"
}
```

The response contains the grounded assistant answer and relevant source
information.

### Tools

``` http
GET /api/tools
```

Returns the available tool registry information intended for the
application architecture.

### API Documentation

FastAPI automatically exposes:

``` text
/docs
/openapi.json
```

Production docs:

https://voice-college-assistant.onrender.com/docs

------------------------------------------------------------------------

## 7. Environment Variables

### Backend

Create:

``` text
backend/.env
```

Use `backend/.env.example` as the template.

Typical production configuration includes:

``` env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
CORS_ORIGINS=https://voice-college-assistant.vercel.app
VECTOR_DB_PATH=./chroma_db
```

Do **not** commit real credentials.

Gemini credentials remain backend-side and are never placed in the React
application.

### Frontend

Create:

``` text
frontend/.env
```

Example:

``` env
VITE_API_URL=http://localhost:8000
```

For production:

``` env
VITE_API_URL=https://voice-college-assistant.onrender.com
```

WhatsApp configuration:

``` env
VITE_ADMISSIONS_WHATSAPP_NUMBER=918588811998
```

The WhatsApp number should only be configured when the institutional
contact is authorized for the intended use.

------------------------------------------------------------------------

## 8. Local Development

### Prerequisites

Install:

-   Python 3.12
-   Node.js
-   npm
-   Git

### Backend

From the project root:

``` bash
cd backend
python -m venv .venv
```

Windows PowerShell:

``` powershell
.venv\Scripts\activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Create environment file:

``` powershell
Copy-Item .env.example .env
```

Fill in the required environment values.

Start FastAPI:

``` bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend:

``` text
http://localhost:8000
```

Health check:

``` text
http://localhost:8000/health
```

### Frontend

Open another terminal:

``` bash
cd frontend
npm install
npm run dev
```

The Vite development server normally runs at:

``` text
http://localhost:5173
```

Make sure `VITE_API_URL` points to the local backend.

------------------------------------------------------------------------

## 9. RAG Data and Ingestion

The project uses a curated source registry:

``` text
backend/data/source_registry.json
```

The registry identifies approved KIET sources for ingestion.

The RAG layer supports: - Official web content - TXT documents - PDF
documents - Source metadata - Page metadata where available - Programme
metadata - Chunking - Embeddings - ChromaDB storage

### Startup Bootstrap

The deployed free Render environment does not rely on a permanent paid
disk.

At startup: 1. The application checks the Chroma collection. 2. If the
collection is populated, existing content is reused. 3. If the
collection is missing or empty, the curated KIET source registry is used
to rebuild the index. 4. Existing content-hash and deterministic
chunk-ID checks reduce duplicate ingestion. 5. The embedding model is
downloaded at runtime when required.

This makes the deployment resilient to the ephemeral filesystem of a
free Render service.

------------------------------------------------------------------------

## 10. Official KIET Information Coverage

The indexed knowledge base has been built around official KIET sources
covering areas such as:

-   Institution overview
-   Postgraduate programmes
-   MCA programme
-   Curriculum
-   Admission procedure
-   Fees
-   Scholarships
-   Student handbook
-   Anti-ragging information
-   Discipline/rules
-   Placement overview
-   Placement training
-   Corporate Relations and Placement Centre
-   Other approved KIET information sources

Placement-specific information is distinguished from claims about an
exact placement policy. If an exact policy cannot be verified from the
available official sources, the assistant says so instead of inventing
one.

------------------------------------------------------------------------

## 11. Example Verified MCA Outputs

The assistant has been tested with MCA-specific questions.

Examples:

### Highest placement package

Question:

``` text
What was the highest placement package of MCA in 2024 to 2025?
```

Verified answer:

``` text
16.42 LPA
```

### Average placement package

``` text
3.66 LPA
```

### Placed percentage

``` text
83.58%
```

The answers are accompanied by relevant official KIET source citations.

------------------------------------------------------------------------

## 12. Safety and Privacy

The application is designed to minimize unnecessary exposure of internal
information.

### Never expose to the frontend

-   Gemini API keys
-   Backend environment variables
-   Internal prompts
-   Vector database identifiers
-   Retrieval metadata that is not intended for users
-   Internal routing diagnostics
-   Server-side debugging information
-   Browser/IP information
-   Internal provider credentials

### Safe answer behavior

The assistant should not manufacture a KIET answer when the knowledge
base does not support it.

For example:

``` text
User:
Who is Narnia?

Assistant:
I don't have enough verified information to answer that accurately.
```

For an unsupported exact policy:

``` text
User:
What is the exact MCA placement policy at KIET?

Assistant:
I couldn't verify a specific MCA placement policy in the official KIET sources currently available.
```

This behavior is intentional.

------------------------------------------------------------------------

## 13. Voice Interaction Flow

``` text
START CONVERSATION
       |
       v
   WELCOME TTS
       |
       v
   LISTENING
       |
       v
   THINKING
       |
       v
   SPEAKING
       |
       v
   LISTENING
       |
       +------> repeat
```

During `SPEAKING`, browser recognition is paused so the assistant does
not hear its own response.

`Stop Conversation`: - Cancels speech synthesis. - Stops speech
recognition. - Ends the active voice session. - Returns the UI to the
idle/welcome state.

### Browser Compatibility

Voice input depends on browser support for:

``` javascript
window.SpeechRecognition ||
window.webkitSpeechRecognition
```

Chrome/Edge are the intended browsers for testing the voice workflow.

------------------------------------------------------------------------

## 14. WhatsApp Handoff Flow

``` text
Insufficient verified information
             |
             v
       Need more help?
             |
             v
   Continue on WhatsApp
             |
             v
       Message Preview
             |
       +-----+-----+
       |           |
     Cancel     Open Draft
                     |
                     v
                  WhatsApp
                     |
                     v
              User chooses
               whether to send
```

The assistant does not automatically send WhatsApp messages.

The preview is intentionally visible so the user can inspect and edit
the message before opening WhatsApp.

------------------------------------------------------------------------

## 15. Deployment

### Frontend --- Vercel

Project settings:

``` text
Framework: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

Production environment variable:

``` env
VITE_API_URL=https://voice-college-assistant.onrender.com
```

### Backend --- Render

The backend runs FastAPI/Uvicorn.

The production server binds to:

``` text
0.0.0.0:$PORT
```

Health endpoint:

``` text
/health
```

The service is configured to use Python 3.12.

### Production URLs

Frontend:

https://voice-college-assistant.vercel.app

Backend:

https://voice-college-assistant.onrender.com

API documentation:

https://voice-college-assistant.onrender.com/docs

------------------------------------------------------------------------

## 16. Free Render Considerations

The current deployment is designed without requiring a paid persistent
disk.

Because the free service filesystem is ephemeral: - Chroma data may
disappear after restart/redeploy/spin-down. - The embedding model may
need to download again. - Startup bootstrap can rebuild the curated
knowledge base. - The first request after inactivity may be slower
because the service can cold-start.

For institutional production, a durable vector/database layer would be
preferable.

------------------------------------------------------------------------

## 17. Testing

The project includes backend tests for areas such as:

-   API regression
-   Tool routing
-   RAG behavior
-   RAG startup/bootstrap
-   Source handling
-   No-information behavior

Frontend validation includes:

``` bash
npm run build
```

The production application has also been manually tested for:

-   Admission questions
-   MCA admission questions
-   MCA placement questions
-   Placement figures
-   Unknown questions
-   Unsupported policy questions
-   Voice input/output
-   Voice state transitions
-   WhatsApp preview
-   Official source citations

------------------------------------------------------------------------

## 18. Example Test Questions

### Admissions

``` text
What is the admission procedure of KIET?
```

``` text
What is the admission process of MCA?
```

### MCA

``` text
What is the eligibility criteria for MCA?
```

``` text
What is the MCA fee structure?
```

### Placements

``` text
What was the highest placement package of MCA in 2024-2025?
```

``` text
What was the average MCA placement package in 2024-2025?
```

``` text
What percentage of MCA students were placed in 2024-2025?
```

### Safety

``` text
Who is Narnia?
```

``` text
What is the exact MCA placement policy at KIET?
```

The last two are useful for checking that the assistant does not
hallucinate unsupported information.

------------------------------------------------------------------------

## 19. Security Checklist

Before production use:

-   [ ] Real `.env` files are not committed.
-   [ ] Gemini credentials exist only on the backend.
-   [ ] `VITE_*` variables contain only values safe for client-side
    exposure.
-   [ ] CORS contains explicit trusted frontend origins.
-   [ ] No `Access-Control-Allow-Origin: *` is used for production.
-   [ ] WhatsApp contact is institutionally authorized.
-   [ ] API error responses do not expose stack traces or internal
    diagnostics.
-   [ ] Source URLs are restricted to approved KIET sources.
-   [ ] RAG/vector metadata is not unnecessarily returned to clients.
-   [ ] Human escalation does not automatically transmit messages.
-   [ ] Production secrets are configured through hosting-provider
    environment variables.

------------------------------------------------------------------------

## 20. Limitations

1.  Browser speech recognition can vary between browsers and may
    interpret pauses differently.
2.  Free Render services can spin down after inactivity, producing
    cold-start delays.
3.  The timetable feature depends on an approved official KIET source
    being available.
4.  The counsellor form currently provides the interface/validation but
    is not connected to a live institutional CRM.
5.  WhatsApp handoff depends on the configured institutional contact and
    the user's WhatsApp environment.
6.  The current knowledge base only covers information that has been
    deliberately indexed from approved sources.
7.  Information that is not available or verifiable from those sources
    should be treated as unsupported.

------------------------------------------------------------------------

## 21. Future Institutional Integration

Possible next-stage institutional capabilities include:

-   Authorized student portal integration
-   Live admission-status services
-   Authenticated student-specific information
-   Official timetable/attendance APIs
-   Institutional CRM/helpdesk integration
-   Automated official-source refresh
-   Knowledge-base monitoring
-   Durable managed vector storage
-   Role-based administration
-   Institutional analytics with appropriate privacy controls
-   Multilingual voice support

These integrations should only be implemented using authorized
institutional APIs/data sources and appropriate access controls.

------------------------------------------------------------------------

## 22. Why RAG Instead of a General Chatbot?

A general-purpose LLM can generate fluent answers, but fluency does not
guarantee that an answer is based on current or official college
information.

This project uses RAG so that:

``` text
Official KIET Information
        ↓
Retrieval
        ↓
Relevant Context
        ↓
Gemini
        ↓
Grounded Response
        ↓
Official Citations
```

The goal is to make the assistant answer from the college's verified
information rather than relying only on the model's general training
knowledge.

------------------------------------------------------------------------

## 23. Project Status

### Completed

-   [x] React/Vite KIET assistant interface
-   [x] FastAPI backend
-   [x] RAG pipeline
-   [x] ChromaDB integration
-   [x] Official KIET source ingestion
-   [x] MCA-specific retrieval
-   [x] Tool routing
-   [x] Live official-source providers
-   [x] Gemini integration
-   [x] Source citations
-   [x] Voice input
-   [x] Voice output
-   [x] Voice session controls
-   [x] Safe no-information behavior
-   [x] Human escalation
-   [x] WhatsApp preview/draft handoff
-   [x] Vercel deployment
-   [x] Render deployment
-   [x] Production environment configuration
-   [x] Backend regression/RAG/tool tests
-   [x] Frontend production build

### Current project direction

The application is feature-complete for the academic prototype. Further
work should focus on institutional validation, authorized integrations,
durable production infrastructure, monitoring and governance rather than
adding unnecessary demo features.

------------------------------------------------------------------------

## 24. License / Institutional Use

This repository is an academic project. Any institutional deployment,
branding, data integration, official communication channel, or
student-specific service should be used only with appropriate
authorization from KIET.

------------------------------------------------------------------------

## 25. Author

**Krishna Garg**\
MCA --- KIET\
Project: **KIET AI Assistant**
