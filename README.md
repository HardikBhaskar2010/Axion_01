# AI Axion — Local Jarvis-Style Desktop Assistant

AI Axion is a **local-first desktop agent** that turns natural language into safe, auditable actions on your computer. It handles file operations, system queries, and application management through an intelligent approval workflow that puts you in control.

**Rules are offline and instant** — an optional LLM fallback handles fuzzy commands. **High-risk actions always require your approval**, ensuring safety without sacrificing functionality.

---

## ✨ Features

- 🎤 **Voice Control** - Wake word activation ("hey axion") or push-to-talk (Ctrl+Space)
- 🧠 **Hybrid Command Parser** - Rule-based patterns (instant, offline) with optional LLM fallback for fuzzy queries
- 📁 **File Operations** - Read, write, delete, copy, move files with sandbox protection
- 🛡️ **Security First** - Risk assessment and approval workflow for every action
- 💾 **Persistent Storage** - SQLite database with in-memory cache for performance
- 📊 **Action Logging** - Complete audit trail of all executed commands
- 🔌 **Real-time Updates** - WebSocket support for live notifications
- 🎛️ **Three Security Modes**:
  - **Paranoid** - Approve everything (even system time queries)
  - **Normal** - Approve medium/high risk actions (default)
  - **Hands-free** - Only approve high-risk actions

---

## 🏗️ Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  React Frontend │◄────────┤  FastAPI Backend│
│  (Voice + UI)   │         │  (Parser + Tools)│
└─────────────────┘         └─────────────────┘
        │                            │
        │                            ▼
        │                    ┌───────────────┐
        └────────────────────┤  SQLite + Cache│
                             │  (Sessions/Logs)│
                             └───────────────┘

Parser Flow: Utterance → Rules Engine → [LLM Fallback] → Action → Approval → Execution
```

**Stack**: React 19 + FastAPI + SQLite + WebSockets

---

## 🚀 Quickstart

### Prerequisites

- **Python 3.11+** with pip and virtualenv
- **Node.js 18+** with Yarn
- **Operating System**: Linux, macOS, or Windows with WSL

### Installation

#### 1. Clone & Setup Backend

```bash
cd /app/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set PARSER_MODE, STORAGE_MODE, etc.
```

#### 2. Setup Frontend

```bash
cd /app/frontend

# Install dependencies
yarn install

# Configure environment
# Create .env file with REACT_APP_BACKEND_URL
```

#### 3. Run Services

**Backend:**
```bash
cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend:**
```bash
cd /app/frontend
yarn start
```

**Access:** Open `http://localhost:3000` in your browser

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in `/app/backend/`:

```bash
# Server
HOST=0.0.0.0
PORT=8001

# Storage Mode (memory = demo, sqlite = production)
STORAGE_MODE=sqlite
DB_PATH=./axion.db

# Parser Mode (rules = offline, hybrid = rules + LLM fallback, llm = always LLM)
PARSER_MODE=rules
CONFIDENCE_LOW=0.55
CONFIDENCE_HIGH=0.80

# LLM Configuration (optional - for hybrid/llm mode)
# LLM_API_KEY=your_openai_key_here
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4

# Security
SANDBOX_PATH=~/Desktop/Axion
MAX_SESSION_MINUTES=60

# CORS
CORS_ORIGINS=*
```

### Parser Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **rules** | Offline pattern matching only | Fast, deterministic, no API costs |
| **hybrid** | Rules first, LLM fallback if confidence < threshold | Best balance of speed and flexibility |
| **llm** | Always use LLM | Maximum flexibility, requires API key |

### Storage Modes

| Mode | Persistence | Use Case |
|------|-------------|----------|
| **sqlite** | Persistent to disk | Production, keeps session/log history |
| **memory** | Lost on restart | Quick demos, testing |

---

## 🛡️ Safety & Permissions

### Sandbox Protection

All file operations are **sandboxed** to the path defined in `SANDBOX_PATH` (default: `~/Desktop/Axion`).

To access files outside the sandbox:
1. Request privilege via the UI
2. Approve the high-risk action
3. Set new root path

### Risk Levels

| Risk | Examples | Approval Needed |
|------|----------|----------------|
| **Low** | System time, list files | Paranoid mode only |
| **Medium** | Read/write files in sandbox | Normal + Paranoid modes |
| **High** | Delete files, outside-sandbox access | All modes |

### Security Modes

- **Paranoid**: Approve every single action (including "what time is it?")
- **Normal**: Auto-execute low-risk, approve medium/high risk (recommended)
- **Hands-free**: Auto-execute low/medium risk, approve only high risk

---

## 🎯 Tool/Intent Registry

### Supported Commands

| Command | Intent | Risk | Example |
|---------|--------|------|---------|
| What time is it? | `system.time` | Low | `what time is it?` |
| Write file | `files.write` | Medium | `write file notes.txt: hello world` |
| Read file | `files.read` | Medium | `read file notes.txt` |
| Delete file | `files.delete` | High | `delete file notes.txt` |
| Copy file | `files.copy` | Medium | `copy file a.txt to b.txt` |
| Move file | `files.move` | Medium | `move file a.txt to b.txt` |
| List files | `files.list` | Low | `list files` |
| Open app | `apps.open` | Low | `open chrome` |

### Adding New Commands

Edit `/app/backend/app/parser.py` and add patterns to the `RULES` list:

```python
RULES = [
    # Pattern, intent, args_extractor, confidence
    (r'^your pattern here$', 
     'tool.name', 
     lambda m: {'arg': m.group(1)}, 
     0.95),
]
```

Then implement the tool in `/app/backend/app/tools.py`:

```python
async def your_tool(self, arg: str) -> Dict[str, Any]:
    # Implementation
    return {"result": "success"}
```

---

## 🔧 Development

### Project Structure

```
/app/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── parser.py         # Command parser (hybrid logic)
│   │   ├── tools.py          # Tool execution layer
│   │   ├── storage.py        # SQLite + cache storage
│   │   ├── models.py         # Pydantic data models
│   │   └── config.py         # Configuration management
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Environment configuration
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── App.css           # Styling
│   │   └── components/       # UI components (Radix UI)
│   ├── package.json          # Node dependencies
│   └── .env                  # Frontend config
└── README.md                 # This file
```

### Running Tests

**Backend API Tests:**
```bash
cd /app
python backend_test.py
```

This runs a comprehensive test suite covering:
- Session management
- Command parsing and planning
- File operations (write, read, delete, copy, move)
- Approval workflow
- Privilege requests
- Logs and settings

**Expected Result:** `10/10 tests passed 🎉`

### Hot Reload

Both backend and frontend support hot reload:
- **Backend**: Uvicorn watches for file changes
- **Frontend**: React Fast Refresh

### Adding Dependencies

**Backend:**
```bash
cd /app/backend
source .venv/bin/activate
pip install package-name
pip freeze > requirements.txt
```

**Frontend:**
```bash
cd /app/frontend
yarn add package-name
```

---

## 🐛 Troubleshooting

### Backend won't start

**Check logs:**
```bash
tail -f /var/log/supervisor/backend.err.log
```

**Common issues:**
- Missing dependencies: `pip install -r requirements.txt`
- Port already in use: Change `PORT` in `.env`
- SQLite permissions: Ensure write access to `DB_PATH` directory

### Microphone not working

**Browser permissions:**
- Chrome/Edge: Click the lock icon in address bar → Allow microphone
- Firefox: Click the camera icon → Allow
- Safari: Preferences → Websites → Microphone → Allow

**System permissions:**
- macOS: System Preferences → Security & Privacy → Microphone → Allow browser
- Windows: Settings → Privacy → Microphone → Allow apps
- Linux: Check PulseAudio/ALSA configuration

### WebSocket shows "Offline"

This is expected if the WebSocket library isn't installed on the frontend. The app uses HTTP polling as a fallback, so all functionality works correctly.

To enable WebSockets, ensure the backend is running and accessible at the configured `REACT_APP_BACKEND_URL`.

### File operations fail

**Check sandbox path:**
```bash
# Verify the path exists
ls -la ~/Desktop/Axion

# Create if missing
mkdir -p ~/Desktop/Axion
```

**Outside-sandbox access:**
Request privilege via UI: Settings → Change Root → Request & Create

### Database locked (SQLite)

Another process is accessing the database. Stop all Axion instances:
```bash
sudo supervisorctl stop backend
rm axion.db  # Only if you want to reset
sudo supervisorctl start backend
```

---

## 🗺️ Roadmap

### In Progress
- [ ] LLM integration for hybrid parser mode
- [ ] Browser automation with Playwright
- [ ] Screen OCR and visual command understanding

### Planned
- [ ] Persistent wake word (always listening)
- [ ] Multi-session support
- [ ] Plugin system for custom tools
- [ ] Natural language to cron scheduling
- [ ] Cross-platform app launcher improvements
- [ ] Voice feedback customization
- [ ] Multi-language support

### Community Requested
- [ ] Docker containerization
- [ ] Cloud sync for action history
- [ ] Mobile companion app
- [ ] Team collaboration features

---

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🙏 Credits

**Built with:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React 19](https://react.dev/) - Frontend UI library
- [Radix UI](https://www.radix-ui.com/) - Accessible component primitives
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first styling
- [Uvicorn](https://www.uvicorn.org/) - ASGI server
- [SQLite](https://www.sqlite.org/) - Embedded database

**Inspired by:**
- J.A.R.V.I.S. from Iron Man
- [Talon Voice](https://talonvoice.com/)
- [Serenade](https://serenade.ai/)

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

**Development Guidelines:**
1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Test in all three security modes

---

## 📧 Support

- **Issues**: [GitHub Issues](#)
- **Discussions**: [GitHub Discussions](#)
- **Email**: support@aiaxion.dev

---

**Made with ❤️ for the local-first AI community**
