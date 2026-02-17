#  Quick Start Guide

Get the Agentic Compliance Auditor running in 5 minutes!

## Prerequisites

1. **Python 3.11+** installed
2. **Ollama** installed and running
   - Download: https://ollama.ai
   - Start: `ollama serve`
   - Pull model: `ollama pull llama3.2`

## Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/BalajiV21/AI_Compliance_Auditor.git
cd AI_Compliance_Auditor

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Initialize Database

```bash
# Run the setup script
python setup.py
```

This will:
- Load sample regulatory documents (GDPR, HIPAA, SOC2)
- Create embeddings
- Store in ChromaDB vector database
- Takes ~2-3 minutes

## Step 3: Start the Application

### Option A: Use the batch file (Windows)

```bash
run_all.bat
```

This starts both API and UI automatically.

### Option B: Manual start

**Terminal 1 - API Server**:
```bash
cd src/api
python main.py
```

**Terminal 2 - Streamlit UI**:
```bash
cd ui
streamlit run streamlit_app.py
```

## Step 4: Access the Application

- **UI**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Test It Out!

Try these sample questions in the UI:

1. "What are the requirements for data retention under GDPR Article 17?"
2. "How does HIPAA define Protected Health Information?"
3. "What are the security safeguards required by SOC2?"
4. "Compare data breach notification requirements in GDPR and HIPAA"

## Common Issues

### Ollama not running
```
Error: Could not connect to Ollama
Fix: Run 'ollama serve' in a separate terminal
```

### Port already in use
```
Error: Address already in use
Fix: Change ports in .env file or kill existing process
```

### No documents loaded
```
Error: No relevant information found
Fix: Run 'python setup.py' to initialize database
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Add your own regulatory documents to `data/raw/` and run setup again
- Configure Redis and Neo4j for enhanced memory capabilities

## Optional Components

For full functionality, install and start:

**Redis** (for session memory):
```bash
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# Linux/Mac:
brew install redis  # Mac
apt-get install redis-server  # Ubuntu
redis-server
```

**Neo4j** (for knowledge graph):
```bash
# Download from https://neo4j.com/download/
# Or use Docker:
docker run -p 7474:7474 -p 7687:7687 neo4j
```

> The system works without Redis/Neo4j using in-memory fallbacks!

---

**That's it!** You now have a fully functional compliance auditor running locally.

For questions, check the logs in `logs/app.log` or see the full README.
