# Interview Copilot AI

Interview Copilot AI is a production-grade, ultra-low latency cross-platform desktop assistant designed to listen to live conversations, automatically extract questions, semantic-search context from your resume, capture active screen code challenges, and stream real-time bullet answer recommendations with sub-second feedback loops.

---

## 🏗️ Architecture Overview

```
                      +-----------------------------+
                      |     Desktop Client UI       |
                      |   (React / Zustand / TS)    |
                      +--------------+--------------+
                                     |
                PCM Audio Websocket  |  HTTP Form OCR Upload
                                     v
                      +-----------------------------+
                      |   FastAPI Service Gateway   |
                      +---+-------+-------+------+--+
                          |       |       |      |
        Question Detector |       |       |      | RAG Queries
                          v       v       v      v
                    +-----+---+ +-+---+ +-+---+ +-----+---+
                    | Gemini  | |Gemini| | PIL | | Qdrant  |
                    |  Flash  | | Pro  | | OCR | |Vector DB|
                    +---------+ +------+ +-----+ +---------+
```

### Key Performance Targets:
- **Speech-to-Text latency:** `< 500 ms` via Deepgram PCM Audio streaming.
- **Answer suggest streaming:** `< 2.0 s` utilizing parallel reasoning models (Gemini Flash & Gemini Pro).
- **RAG personalize support:** Context injection using local PDF text embeddings stored in Qdrant.

---

## 📂 Folder Layout

```
stealthai/
├── desktop-app/              # React + TS + Tailwind (Bundled with Vite/Tauri)
│   ├── src/
│   │   ├── components/       # Premium Glassmorphic Overlay & Dashboard views
│   │   ├── store/            # Zustand state containers
│   │   ├── App.tsx           # Environment routing selectors
│   │   └── index.css         # Styling, premium gradients and layout anims
│   ├── package.json
│   └── vite.config.ts
├── backend-service/          # FastAPI Python Server
│   ├── app/
│   │   ├── api/              # Routers (Auth sync, Sessions websocket, Resume)
│   │   ├── services/         # Audio pipe, NLP detector, RAG embedding, OCR screenshot
│   │   ├── core/             # Configuration & Database connection managers
│   │   └── main.py           # FastAPI lifecycle hooks and app starter
│   ├── requirements.txt
│   └── Dockerfile
├── database/                 # Prisma DB models
│   └── schema.prisma
├── docker-compose.yml        # PostgreSQL & Qdrant vector containers
├── deploy.sh                 # Environment setup and run automation script
└── README.md                 # Exhaustive instruction guide
```

---

## ⚙️ Environment Configurations

Create a `.env` file in the `backend-service/` folder with the following variables:

```env
# Database Credentials
DATABASE_URL="postgresql://postgres:postgrespassword@localhost:5432/interview_copilot"

# Vector Database Mappings
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_COLLECTION="resume_embeddings"

# AI Models Keys (Add keys for full live API support)
GEMINI_API_KEY="your-gemini-key"
DEEPGRAM_API_KEY="your-deepgram-key"
OPENAI_API_KEY="your-openai-key"
```

---

## 🚀 Setup & Execution Guide

### 1. Auto-Boot Infrastructure (Recommended)
You can run our customized deployment automation script directly from the root workspace folder:
```bash
chmod +x deploy.sh
./deploy.sh
```

### 2. Manual Startup

#### Step A: Boot Databases via Docker
Ensure Docker Desktop is active, then spin up the backend dependencies:
```bash
docker-compose up -d
```

#### Step B: Start FastAPI Backend Service
```bash
cd backend-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
You can view the active OpenAPI schemas directly at http://localhost:8000/docs.

#### Step C: Start React Desktop Client
```bash
cd desktop-app
npm install
npm run dev
```
Open http://localhost:3000 in your browser to run the premium dashboard panel.

---

## 💡 Key Features Walkthrough

1. **Draggable Transparent Overlay Widget:** Open the view selector in the bottom right corner and toggle into the **Copilot Widget**. Tap Alt + R to start audio capture.
2. **Resume RAG Semantic Synchronization:** Navigate to the **Resume RAG** workspace panel, browse a PDF layout, and hit upload. The text chunks will instantly prepare dynamic responses matching your credentials.
3. **Screen OCR Problem Recognition:** Snap active screenshots inside the **Screen OCR** overlay tab. Our system automatically reviews standard coding dynamic scripts and displays structured advice.
4. **Mock Interview Arena:** Experience interactive practice boards against AI. Pick roles/companies, submit your answers, and receive detailed coaching evaluations.
5. **Speech analytics:** Get comprehensive clarity percentages, speaking pace reports, filler-word counts, and gap indices.
