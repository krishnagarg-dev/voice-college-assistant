# KIET Voice-Based College Information Assistant

## Deployment preparation

The frontend and backend are separate services. This repository is prepared for a Vercel frontend and a Render Python web service; no service has been deployed or connected to GitHub.

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
| `VECTOR_DB_PATH` | Path on the persistent disk, recommended `/var/data/chroma` |
| `DOCUMENTS_PATH` | Optional; defaults to `data/documents` |
| `RAG_CHUNK_SIZE` | Optional; defaults to `800` |
| `RAG_CHUNK_OVERLAP` | Optional; defaults to `150` |
| `RAG_TOP_K` | Optional; defaults to `4` |
| `RAG_MAX_DISTANCE` | Optional; defaults to `0.60` |

Attach a Render persistent disk mounted at `/var/data` before relying on indexed RAG data. Then set `VECTOR_DB_PATH=/var/data/chroma`. After the service and disk are available, run `python -m app.rag.web_ingest` once from the Render service shell to populate the index from the curated official-source registry. Review the ingestion summary and resolve failed sources before using the assistant. Repeat this command when you intentionally refresh the knowledge base.

Render's service filesystem is ephemeral outside a persistent disk. The local `backend/data/chroma` index and its cached embedding model are ignored by Git, so neither is included in a clean deployment. The backend stores Chroma locally at `VECTOR_DB_PATH`; Chroma also downloads its ONNX embedding model into that directory when first needed. A new Render disk starts empty and must be seeded. Without a persistent disk, the index can disappear on restart or redeploy. The persistent disk is an operational requirement for a reliable RAG deployment; review Render plan/cost requirements before attaching one.

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
