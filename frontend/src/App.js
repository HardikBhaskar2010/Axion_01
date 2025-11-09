import React, { useEffect, useMemo, useRef, useState } from "react";
import "@/App.css";
import axios from "axios";
import { Toaster, toast } from "./components/ui/sonner";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Card } from "./components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Separator } from "./components/ui/separator";
import { Badge } from "./components/ui/badge";
import { Switch } from "./components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./components/ui/dialog";
import { Mic, MicOff, Send, CheckCircle2, XCircle, ActivitySquare, TerminalSquare, FolderOpen, Shield } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SR = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : undefined;
const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined;

const speak = (text) => { try { if (!synth) return; const u = new SpeechSynthesisUtterance(text); u.rate = 1; u.pitch = 1; synth.speak(u); } catch(_) {} };

const useWebSocket = (sessionId) => {
  const [status, setStatus] = useState("disconnected");
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);
  useEffect(() => { if (!sessionId) return; try { const wsUrl = BACKEND_URL.replace(/^http/, "ws") + `/api/ws/${sessionId}`; const ws = new WebSocket(wsUrl); wsRef.current = ws; ws.onopen = () => setStatus("connected"); ws.onclose = () => setStatus("disconnected"); ws.onerror = () => setStatus("error"); ws.onmessage = (ev) => { try { const msg = JSON.parse(ev.data); setEvents((prev) => [...prev, msg]); } catch (_) {} }; return () => ws.close(); } catch (_) { setStatus("error"); } }, [sessionId]);
  return { status, events };
};

function App() {
  const [session, setSession] = useState(null);
  const [mode, setMode] = useState("normal");
  const [utterance, setUtterance] = useState("");
  const [plans, setPlans] = useState([]);
  const [logs, setLogs] = useState([]);
  const [rootPath, setRootPath] = useState("");
  const [firstRun, setFirstRun] = useState(false);
  const [showRootModal, setShowRootModal] = useState(false);
  const [parserMode, setParserMode] = useState("rules");
  const [storageMode, setStorageMode] = useState("sqlite");
  const { status: wsStatus, events } = useWebSocket(session?.id);

  // Voice state
  const [wakeOn, setWakeOn] = useState(false);
  const [listening, setListening] = useState(false);
  const [awaitingCommand, setAwaitingCommand] = useState(false);
  const recognitionRef = useRef(null);
  const wakePhrase = "hey axion";

  const initRecognizer = (continuous = false) => {
    const SRImpl = SR; if (!SRImpl) { toast.error("Voice not supported in this browser"); return null; }
    const r = new SRImpl(); r.lang = "en-US"; r.interimResults = false; r.continuous = continuous; return r;
  };

  const startWake = () => { if (!SR) return toast.error("Voice not supported"); if (recognitionRef.current) recognitionRef.current.stop(); const r = initRecognizer(true); if (!r) return; recognitionRef.current = r; r.onstart = () => setListening(true); r.onend = () => { setListening(false); if (wakeOn) setTimeout(() => r.start(), 200); }; r.onerror = () => { setListening(false); if (wakeOn) setTimeout(() => r.start(), 800); }; r.onresult = (e) => { const text = Array.from(e.results).map(res => res[0].transcript).join(" ").toLowerCase(); if (!text) return; if (!awaitingCommand && text.includes(wakePhrase)) { speak("I'm listening"); setAwaitingCommand(true); return; } if (awaitingCommand) { setAwaitingCommand(false); handleVoiceCommand(text); } }; try { r.start(); } catch(_) {} };
  const stopWake = () => { setAwaitingCommand(false); if (recognitionRef.current) { try { recognitionRef.current.stop(); } catch(_) {} } };
  const pushToTalk = async () => { if (!SR) return toast.error("Voice not supported"); if (recognitionRef.current) { try { recognitionRef.current.stop(); } catch(_) {} } const r = initRecognizer(false); if (!r) return; recognitionRef.current = r; r.onstart = () => setListening(true); r.onend = () => setListening(false); r.onerror = () => setListening(false); r.onresult = (e) => { const text = Array.from(e.results).map(res => res[0].transcript).join(" "); if (!text) return; handleVoiceCommand(text); }; try { r.start(); } catch(_) {} };
  useEffect(() => { const onKey = (e) => { if (e.ctrlKey && e.code === 'Space') { e.preventDefault(); pushToTalk(); } }; window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, []);

  const handleVoiceCommand = (text) => { const cmd = text.trim(); setUtterance(cmd); speak(`Command: ${cmd}`); proposePlan(cmd); };

  useEffect(() => { (async () => { try { const { data } = await axios.post(`${API}/session/start`, { mode }); setSession(data); } catch (_) { toast.error("Unable to start session"); } })(); }, []);

  const loadRoot = async () => { try { const { data } = await axios.get(`${API}/settings/root`); setRootPath(data.root); setFirstRun(Boolean(data.first_run)); setShowRootModal(Boolean(data.first_run)); } catch(_) {} };
  useEffect(() => { loadRoot(); }, []);

  const setRootOnServer = async (value) => { try { const { data } = await axios.post(`${API}/settings/root`, { path: value }); setRootPath(data.root); setFirstRun(false); setShowRootModal(false); toast.success("Root folder set"); } catch (e) { toast.error(e?.response?.data?.detail || "Failed to set root"); } };

  const requestPrivilege = async (value) => {
    try {
      const { data } = await axios.post(`${API}/settings/privilege_request`, { need: ["files.write.outside_sandbox"], target_path: value, expires_minutes: 15, reason_brief: "set custom root" });
      const action = data.action; // add to local approvals
      setPlans((prev) => [...prev, action]);
      toast.message("Privilege request created. Approve it to proceed.");
    } catch (e) {
      toast.error("Failed to request privilege");
    }
  };

  useEffect(() => {
    if (!session?.id) return;
    const fetchLogs = async () => { try { const { data } = await axios.get(`${API}/logs`, { params: { session_id: session.id } }); setLogs(data.logs || []); } catch(_) {} };
    fetchLogs(); const id = setInterval(fetchLogs, 2000); return () => clearInterval(id);
  }, [session?.id]);

  useEffect(() => { const evt = events.at(-1); if (!evt) return; if (evt.event === "tool_result") { toast.success("Tool executed"); if (session?.id) { axios.get(`${API}/logs`, { params: { session_id: session.id } }).then(({ data }) => setLogs(data.logs || [])); } } }, [events, session?.id]);

  const proposePlan = async (maybeUtterance) => { const u = (maybeUtterance ?? utterance).trim(); if (!u) return toast.info("Enter a command"); if (!session?.id) return toast.error("No session"); try { const { data } = await axios.post(`${API}/plan`, { session_id: session.id, utterance: u }); setPlans(data.actions || []); if ((data.auto_results || []).length) toast.success("Executed non-risky actions"); } catch (_) { toast.error("Failed to propose plan"); } };

  const approve = async (action, decision) => { try { await axios.post(`${API}/action/approve`, { action_id: action.id, decision }); toast.message(decision === "allow" ? "Action approved" : "Action denied"); setPlans((prev) => prev.filter((a) => a.id !== action.id)); if (decision === 'allow' && action.tool === 'privilege.request') { await setRootOnServer(action.args.target_path); } } catch (_) { toast.error("Approval failed"); } };

  useEffect(() => { if (wakeOn) startWake(); else stopWake(); }, [wakeOn]);

  const wsOk = wsStatus === "connected";

  return (
    <div className="App" data-testid="ai-axion-app">
      <div className="header">
        <div className="brand">
          <span className="dot"/>
          <h1>AI Axion</h1>
        </div>
        <div className="mode-row">
          <span className="ws-indicator" data-testid="ws-status"><span className={`ws-dot ${wsOk ? 'ok' : 'bad'}`}></span>{wsOk ? 'Live' : 'Offline'}</span>
          <Badge variant="outline" className="badge" data-testid="agent-mode-badge">Agent Mode</Badge>
          <Select defaultValue={mode} onValueChange={(v)=> setMode(v)}>
            <SelectTrigger className="input" data-testid="mode-select"><SelectValue placeholder="Select mode" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="paranoid">paranoid</SelectItem>
              <SelectItem value="normal">normal</SelectItem>
              <SelectItem value="hands_free">hands_free</SelectItem>
            </SelectContent>
          </Select>
          <Separator style={{height:24, marginLeft:8, marginRight:8}} orientation="vertical"/>
          <Badge variant="outline" className="badge" data-testid="parser-mode-badge">Parser</Badge>
          <Select value={parserMode} onValueChange={(v)=> setParserMode(v)}>
            <SelectTrigger className="input" data-testid="parser-select" style={{width:100}}><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="rules">Rules</SelectItem>
              <SelectItem value="hybrid">Hybrid</SelectItem>
              <SelectItem value="llm">LLM</SelectItem>
            </SelectContent>
          </Select>
          <Badge variant="outline" className="badge" data-testid="storage-badge">{storageMode === 'sqlite' ? '💾 SQLite' : '⚡ Memory'}</Badge>
          <Separator style={{height:24, marginLeft:8, marginRight:8}} orientation="vertical"/>
          <div className="row" style={{gap:10}}>
            <div className="row" style={{gap:6, alignItems:'center'}}>
              <Switch checked={wakeOn} onCheckedChange={setWakeOn} data-testid="wake-toggle"/>
              <span className="small">Wake: "hey axion"</span>
            </div>
            <Button className="button" onClick={pushToTalk} data-testid="push-to-talk-button" aria-label="Push to talk">{listening ? <MicOff size={16} style={{marginRight:6}}/> : <Mic size={16} style={{marginRight:6}}/>}PTT</Button>
            <Button className="button ghost" data-testid="change-root-button" onClick={()=> setShowRootModal(true)}><FolderOpen size={16} style={{marginRight:6}}/>Change root</Button>
          </div>
        </div>
      </div>

      <Dialog open={showRootModal} onOpenChange={setShowRootModal}>
        <DialogContent data-testid="root-dialog">
          <DialogHeader>
            <DialogTitle className="row" style={{gap:8, alignItems:'center'}}><Shield size={16}/> Set file root (outside sandbox requires approval)</DialogTitle>
          </DialogHeader>
          <div className="col">
            <Input placeholder="Absolute path or folder name" className="input" data-testid="root-input" value={rootPath} onChange={(e)=> setRootPath(e.target.value)} />
            <div className="row" style={{gap:8, justifyContent:'flex-end'}}>
              <Button className="button ghost" data-testid="use-default-button" onClick={()=> setRootOnServer("")}>Use default</Button>
              <Button className="button" data-testid="request-privilege-button" onClick={()=> requestPrivilege(rootPath || "~/Desktop/Guardian")}>Request & Create</Button>
            </div>
          </div>
          <DialogFooter/>
        </DialogContent>
      </Dialog>

      <div className="app-shell">
        <aside className="sidebar">
          <Card className="card" data-testid="quick-actions">
            <div className="row" style={{justifyContent:'space-between'}}>
              <strong>Quick commands</strong>
            </div>
            <div className="col" style={{marginTop:12}}>
              <Button className="button" data-testid="quick-open-chrome" onClick={()=> setUtterance('open chrome')}>Open Chrome</Button>
              <Button className="button" data-testid="quick-what-time" onClick={()=> setUtterance('what time is it?')}>What time is it?</Button>
              <Button className="button" data-testid="quick-list-files" onClick={()=> setUtterance('list files')}>List files</Button>
              <Button className="button ghost" data-testid="quick-write-sample" onClick={()=> setUtterance('write file notes.txt: hello from guardian')}>Write sample file</Button>
              <Button className="button ghost" data-testid="quick-copy-sample" onClick={()=> setUtterance('copy file notes.txt to notes2.txt')}>Copy sample</Button>
              <Button className="button ghost" data-testid="quick-delete-sample" onClick={()=> setUtterance('delete file notes.txt')}>Delete sample</Button>
            </div>
          </Card>
        </aside>

        <main className="col">
          <Card className="card" data-testid="planner-card">
            <div className="row" style={{gap:12}}>
              <TerminalSquare size={18}/>
              <div style={{flex:1}}>
                <Input className="input" data-testid="command-input" placeholder="Type a command, e.g., 'write file notes.txt: hello'" value={utterance} onChange={(e)=> setUtterance(e.target.value)} />
              </div>
              <Button className="button" data-testid="propose-plan-button" onClick={()=> proposePlan()}><Send size={16} style={{marginRight:6}}/>Plan</Button>
            </div>
            <Separator style={{margin:'14px 0'}}/>
            <div className="plan-list" data-testid="plan-list">
              {plans.length === 0 && <div className="small">No pending approvals. Submit a command.</div>}
              {plans.map((a)=> (
                <div className="plan-item" key={a.id} data-testid={`plan-item-${a.id}`}>
                  <div className="row" style={{justifyContent:'space-between'}}>
                    <div>
                      <div className="title">{a.tool}</div>
                      <div className="small">risk: {a.risk} · reason: {a.reason_brief}</div>
                    </div>
                    {a.need_approval ? (
                      <div className="row" style={{gap:8}}>
                        <Button className="button" data-testid={`approve-action-${a.id}`} onClick={()=> approve(a, 'allow')}><CheckCircle2 size={16} style={{marginRight:6}}/>Approve</Button>
                        <Button className="button ghost" data-testid={`deny-action-${a.id}`} onClick={()=> approve(a, 'deny')}><XCircle size={16} style={{marginRight:6}}/>Deny</Button>
                      </div>
                    ) : (
                      <div className="badge" data-testid={`auto-exec-${a.id}`}>auto-executed</div>
                    )}
                  </div>
                  <div className="small" style={{marginTop:8}}>args: <code>{JSON.stringify(a.args)}</code></div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="card" data-testid="action-log-card">
            <div className="row" style={{alignItems:'center', gap:8}}>
              <ActivitySquare size={18}/>
              <strong>Action log</strong>
            </div>
            <div className="log-list" data-testid="action-log-list" style={{marginTop:12}}>
              {logs.length === 0 && <div className="small">No logs yet.</div>}
              {logs.map((l)=> (
                <div className="log-item" key={l.action_id} data-testid={`log-item-${l.action_id}`}>
                  <div className="row" style={{justifyContent:'space-between'}}>
                    <div className="row" style={{gap:8}}>
                      {l.success ? <CheckCircle2 size={16} color="#39d98a"/> : <XCircle size={16} color="#ff6b6b"/>}
                      <div>
                        <div className="title">{l.tool}</div>
                        <div className="small">{new Date(l.timestamp).toLocaleTimeString()} · id: {l.action_id}</div>
                      </div>
                    </div>
                    <div className="small">args: <code>{JSON.stringify(l.args)}</code></div>
                  </div>
                  {l.result && <div className="small" style={{marginTop:8}}>result: <code>{JSON.stringify(l.result)}</code></div>}
                  {l.error && <div className="small" style={{marginTop:8, color:'#ffb3b3'}}>error: {l.error}</div>}
                </div>
              ))}
            </div>
          </Card>
        </main>
      </div>

      <div className="footer" data-testid="footer">Backend: {String(BACKEND_URL)} — Root: {rootPath || 'default'} — Voice: {SR ? 'enabled' : 'unsupported'}</div>
      <Toaster richColors position="top-right"/>
    </div>
  );
}

export default App;
