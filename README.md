# Switch Impact Simulator

A portfolio-first decision tool for mutual fund investors.

## Project Structure
*   `frontend/`: Next.js (App Router) application.
*   `backend/`: Python FastAPI application.

## Getting Started

### Prerequisites
*   Node.js 18+
*   Python 3.11+
*   Docker (optional)

### Running Locally (Manual)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Running with Docker Compose
```bash
docker-compose up --build
```
