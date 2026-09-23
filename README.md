# KIET Voice-Based College Information Assistant

## Deployment preparation

The frontend and backend are separate services. The backend has been deployed on Render at [voice-college-assistant.onrender.com](https://voice-college-assistant.onrender.com); the frontend deployment remains separate.

### Frontend — Vercel

1. Import the repository into Vercel and set the **Root Directory** to `frontend`.
2. Use `npm run build` as the build command and `dist` as the output directory (Vercel detects Vite automatically).
3. Set `VITE_API_URL` to the public HTTPS origin of the Render backend, for example `https://your-service.onrender.com` (no `/api` suffix).
4. `VITE_*` values are included in the browser bundle. Set only public values here; never add `GEMINI_API_KEY` or another secret.

For local frontend development, copy `frontend/.env.example` to `frontend/.env.local`, then run:

```powershell
cd frontend
npm install
npm run dev
```

### Backend — Render

Create a Python web service with `backend` as its **Root Directory**. The checked-in `backend/.python-version` pins Python 3.12.14. Configure:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

Set these service environment variables in Render:

| Variable | Value |
| --- | --- |
| `GEMINI_API_KEY` | Required secret, entered in Render's environment settings only |
| `GEMINI_MODEL` | Optional; defaults to the model configured by the application |
| `CORS_ORIGINS` | Required for browser access; set to the exact Vercel origin, such as `https://your-project.vercel.app` |
| `VECTOR_DB_PATH` | Optional; defaults to `data/chroma` inside the service filesystem |
| `DOCUMENTS_PATH` | Optional; defaults to `data/documents` |
| `RAG_CHUNK_SIZE` | Optional; defaults to `800` |
| `RAG_CHUNK_OVERLAP` | Optional; defaults to `150` |
| `RAG_TOP_K` | Optional; defaults to `4` |
| `RAG_MAX_DISTANCE` | Optional; defaults to `0.60` |

#### Free Render Chroma initialization

No persistent disk is used for the free-tier demonstration. Render Free has an ephemeral filesystem: Chroma data and the model cache can disappear on redeploy, restart, or spin-down. The application checks the Chroma collection at startup. If it already contains chunks, it reuses the index and does not fetch the websites again. If the collection is missing or empty, it ingests enabled entries from the curated `backend/data/source_registry.json` list of official KIET URLs before serving the app. This does not guarantee that the index will survive a later restart.

First initialization can take longer while the configured official sources are fetched and Chroma downloads the local all-MiniLM-L6-v2 ONNX embedding model into `VECTOR_DB_PATH/embedding-model` (about 90 MB). These files are generated at runtime and are not committed to Git. Subsequent starts reuse them only while Render retains that instance's filesystem. If ingestion or model download fails, the API still starts and `/health` remains available; server logs report initialization status, and RAG may return its existing no-context answer until a later startup successfully initializes the index. No exact startup duration is promised.

The free setup is suitable for an academic/product demonstration, not a guarantee of durable RAG storage. Persistent Chroma data across restarts requires storage outside Render Free's ephemeral filesystem or a paid Render service with a persistent disk. See [Render's Free instance limitations](https://render.com/docs/free).

`backend/data/source_registry.json` and `backend/data/documents/` are source-controlled inputs. The sample MCA text file is a test fixture and is not production KIET knowledge. Do not treat it as official content.

Production `CORS_ORIGINS` must contain explicit origins, separated by commas if more than one is required. Do not use `*`. Add the final Vercel origin after Vercel assigns it; it is intentionally not guessed or hardcoded in this repository. Local development origins are present in `backend/.env.example` and should not be copied into production unless needed.

### Local backend development

From the repository root, activate/create a virtual environment, install the backend requirements, copy `backend/.env.example` to `backend/.env`, and enter a Gemini key in that ignored local file. Then:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

The health endpoint is `GET http://localhost:8000/health`. The chat endpoint is `POST http://localhost:8000/api/chat`.

### Environment templates

`backend/.env.example` lists backend settings and contains no credentials. `frontend/.env.example` contains only public frontend configuration. Keep real secrets in Render's environment settings or ignored local `.env` files, never in Git or Vercel `VITE_*` variables.
