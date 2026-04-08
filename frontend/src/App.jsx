import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import Globe from './components/Globe';
import './App.css';

const API_BASE = "http://localhost:8000";

function App() {
  // ── Core state ─────────────────────────────────────────────────
  const [command,     setCommand]     = useState("");
  const [response,    setResponse]    = useState("Systems Online. Ready to assist, Sir.");
  const [isThinking,  setIsThinking]  = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isAsleep,    setIsAsleep]    = useState(false);
  const [mode,        setMode]        = useState("speech"); // 'speech' | 'text'
  const [stats,       setStats]       = useState({ cpu: 0, ram: 0 });
  const [history,     setHistory]     = useState([]);
  const [wakeFlash,   setWakeFlash]   = useState(false);
  const [ollamaOk,    setOllamaOk]    = useState(true);

  // ── Widget / view state ────────────────────────────────────────
  const queryParams = new URLSearchParams(window.location.search);
  const isWidget    = queryParams.get("mode") === "widget";
  const [view,       setView]       = useState("home");     // ✅ Fixed: was no-op ternary
  const [shortcuts,  setShortcuts]  = useState({});
  const [newShortcut, setNewShortcut] = useState({ key: "", action: "OPEN_APP", value: "" });

  // ── Refs: keep stable references for callbacks ─────────────────
  const isThinkingRef  = useRef(false);
  const isListeningRef = useRef(false);
  const isAsleepRef    = useRef(false);

  // Keep refs in sync with state
  useEffect(() => { isThinkingRef.current  = isThinking;  }, [isThinking]);
  useEffect(() => { isListeningRef.current = isListening; }, [isListening]);
  useEffect(() => { isAsleepRef.current    = isAsleep;    }, [isAsleep]);

  // ── Load stats + shortcuts + health ───────────────────────────
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, commandsRes, healthRes] = await Promise.all([
          axios.get(`${API_BASE}/stats`),
          axios.get(`${API_BASE}/commands`),
          axios.get(`${API_BASE}/health`),
          axios.get(`${API_BASE}/settings/mode`),
        ]);

        // Parse stats
        const statsStr = statsRes.data.stats;
        const cpuMatch = statsStr.match(/CPU Usage: ([\d.]+)/);
        const ramMatch = statsStr.match(/RAM Usage: ([\d.]+)/);
        if (cpuMatch && ramMatch) setStats({ cpu: cpuMatch[1], ram: ramMatch[1] });

        // Shortcuts
        setShortcuts(commandsRes.data);

        // Mode
        setMode(modeRes.data.mode);

        // Ollama status
        setOllamaOk(healthRes.data.ollama === "online");
        setIsAsleep(!healthRes.data.jarvis_awake);
      } catch (err) {
        console.warn("Fetch error:", err.message);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  // ── Wake-word SSE listener ─────────────────────────────────────
  useEffect(() => {
    console.log("📡 Connecting to wake-word SSE stream...");
    const evtSource = new EventSource(`${API_BASE}/wake-stream`);

    evtSource.onmessage = (e) => {
      if (e.data === "wake") {
        // Ignore wake events if in text mode (Issue 16: Strictness)
        if (mode === 'text') return;

        console.log("🚨 Wake word detected by server!");
        if (isListeningRef.current || isThinkingRef.current) return;
        setWakeFlash(true);
        setIsAsleep(false);
        setResponse("WAKE WORD DETECTED — Listening...");
        setTimeout(() => setWakeFlash(false), 2000);
        setTimeout(() => triggerListen(), 800);
      } else if (e.data.startsWith("mode:")) {
        const newMode = e.data.split(":")[1];
        setMode(newMode);
        console.log("📡 Mode Sync:", newMode);
      }
    };

    evtSource.onerror = () => {
      // SSE will auto-reconnect — ignore transient errors
    };

    return () => evtSource.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Command processing ─────────────────────────────────────────
  const processCommand = useCallback(async (cmdText) => {
    setIsListening(false);
    setIsThinking(true);
    setResponse("Analyzing...");

    try {
      const res = await axios.post(`${API_BASE}/command`, { command: cmdText });

      if (res.data.asleep) {
        setIsAsleep(true);
        setResponse(res.data.response);
        setIsThinking(false);
        return;
      }

      setIsAsleep(false);
      setResponse(res.data.response);
      setHistory(prev => [
        ...prev,
        { type: 'user',   text: cmdText },
        { type: 'jarvis', text: res.data.response },
      ]);
      setIsThinking(false);

    } catch (err) {
      setResponse("System core communication failure. Check server status.");
      setIsThinking(false);
    }
  }, []);

  const triggerListen = useCallback(async () => {
    if (isThinkingRef.current || isListeningRef.current) return;
    setIsListening(true);
    setResponse("Listening...");
    try {
      const res = await axios.get(`${API_BASE}/listen`);
      const text = res.data.text?.trim();
      if (text && text !== "STT model not found") {
        processCommand(text);
      } else {
        setResponse("I didn't catch that. Please try again.");
        setIsListening(false);
      }
    } catch (err) {
      setResponse("Microphone system error.");
      setIsListening(false);
    }
  }, [processCommand]);

  const handleModeChange = async (newMode) => {
    try {
      const res = await axios.post(`${API_BASE}/settings/mode`, { mode: newMode });
      setMode(res.data.mode);
      setResponse(`INTERACTION MODE: ${newMode.toUpperCase()}`);
    } catch (err) {
      console.error("Failed to update mode:", err);
    }
  };
   /* eslint-disable no-undef */
   /* ... existing handleSendCommand ... */

  const handleSendCommand = (e) => {
    if (e) e.preventDefault();
    if (!command.trim()) return;
    processCommand(command);
    setCommand("");
  };

  const onGlobeClick = () => {
    if (view !== 'home') return;
    if (isAsleep) {
      // Wake up on globe click
      setIsAsleep(false);
      setResponse("Systems reactivated. How can I assist you, Sir?");
      return;
    }
    const nextMode = mode === "speech" ? "text" : "speech";
    setMode(nextMode);
    setResponse(`Switching to ${nextMode.toUpperCase()} mode.`);
    if (nextMode === "speech") setTimeout(triggerListen, 800);
  };

  // ── Shortcut management ────────────────────────────────────────
  const handleAddShortcut = async (e) => {
    if (e) e.preventDefault();
    if (!newShortcut.key || !newShortcut.value) return;
    const updated = { ...shortcuts, [newShortcut.key.toLowerCase()]: `${newShortcut.action}(${newShortcut.value})` };
    try {
      await axios.post(`${API_BASE}/commands`, updated);
      setShortcuts(updated);
      setNewShortcut({ key: "", action: "OPEN_APP", value: "" });
    } catch { alert("Failed to save shortcut"); }
  };

  const removeShortcut = async (key) => {
    const updated = { ...shortcuts };
    delete updated[key];
    try {
      await axios.post(`${API_BASE}/commands`, updated);
      setShortcuts(updated);
    } catch { alert("Failed to delete shortcut"); }
  };

  const handleClearHistory = async () => {
    try {
      await axios.get(`${API_BASE}/clear-history`);
      setHistory([]);
      setResponse("Conversation memory cleared, Sir.");
    } catch { alert("Failed to clear history"); }
  };

  // ── Status label ───────────────────────────────────────────────
  const statusLabel = isAsleep
    ? "STANDBY"
    : isThinking ? "PROCESSING"
    : isListening ? "LISTENING"
    : "ACTIVE";

  const statusColor = isAsleep ? "#ff6b00" : wakeFlash ? "#ff0066" : "#00f2ff";

  // ─────────────────────────────────────────────────────────────────
  // WIDGET MODE
  // ─────────────────────────────────────────────────────────────────
  if (isWidget) {
    return (
      <div className="widget-container" style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
        <div
          className={`globe-wrapper ${wakeFlash ? 'pulse-wake' : 'pulse-aura'}`}
          onClick={onGlobeClick}
          style={{ cursor: 'pointer' }}
        >
          <Globe />
        </div>
        <div className="widget-ui">
          {mode === "speech" ? (
             <div className="response-bubble mini-bubble" style={{ cursor: 'pointer' }}>
                {(isThinking || isListening || wakeFlash) && (
                  <div className="listening-pulse" style={{ background: statusColor }} />
                )}
                <span className="response-text mini-text" style={{ color: statusColor }}>
                  {response}
                </span>
              </div>
          ) : (
            <div className="response-bubble mini-bubble text-mode-bubble">
                <span className="response-text mini-text" style={{ opacity: 0.6 }}>TEXT_MODE_ACTIVE</span>
            </div>
          )}

          {mode === "text" && !isAsleep && (
            <form className="input-group mini-input" onSubmit={handleSendCommand} style={{ pointerEvents: 'auto' }}>
              <input
                autoFocus
                type="text"
                placeholder="TYPE COMMAND..."
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: `1px solid ${statusColor}` }}
              />
            </form>
          )}

          {mode === "speech" && (
            <div className="widget-status" style={{ fontSize: '0.65rem', opacity: 0.5, marginTop: '5px' }}>
                {isListening ? "LISTENING..." : "SAY 'JARVIS'"}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────
  // FULL UI MODE
  // ─────────────────────────────────────────────────────────────────
  return (
    <div className="jarvis-container">
      {/* Navigation */}
      <div className="nav-bar">
        <button className="nav-btn" onClick={() => setView('home')}
          style={{ opacity: view === 'home' ? 1 : 0.5 }}>
          CORE_INTEL
        </button>
        <button className="nav-btn" onClick={() => setView('settings')}
          style={{ opacity: view === 'settings' ? 1 : 0.5 }}>
          COMMAND_CENTER
        </button>
        <button className="nav-btn" onClick={handleClearHistory}
          style={{ opacity: 0.5, borderColor: 'rgba(255,100,100,0.3)', color: '#ff8888' }}>
          CLEAR_MEM
        </button>
      </div>

      {/* Globe (only on home) */}
      {view === 'home' && (
        <div className="globe-wrapper" onClick={onGlobeClick} style={{ cursor: 'pointer' }}>
          <Globe />
        </div>
      )}

      {/* UI Overlay */}
      <div className="ui-overlay">
        {/* Header */}
        <header className="header">
          <div className="title-group">
            <h1 style={{ color: statusColor }}>JARVIS</h1>
            <p>ADVANCED SYSTEM INTERFACE v3.0</p>
          </div>
          <div className="stats-panel">
            <div className="stat-row">
              CPU_LOAD: <span className="neon-val">{stats.cpu}%</span>
            </div>
            <div className="stat-row">
              RAM_USAGE: <span className="neon-val">{stats.ram}%</span>
            </div>
            <div style={{ marginTop: '5px', fontSize: '0.7rem' }}>
              CORE_STATUS: <span style={{ color: statusColor, fontWeight: 600 }}>{statusLabel}</span>
            </div>
            {!ollamaOk && (
              <div style={{ marginTop: '5px', fontSize: '0.65rem', color: '#ff4444' }}>
                ⚠ OLLAMA OFFLINE — Start with: ollama serve
              </div>
            )}
          </div>
        </header>

        {view === 'home' ? (
          <div className="chat-section">
            <div style={{ marginBottom: '8px', fontSize: '0.7rem', color: statusColor, letterSpacing: '2px' }}>
              MODE: {mode.toUpperCase()} · MEMORY: {history.length / 2 | 0} EXCHANGES
            </div>

            {response && (
              <div className={`response-bubble ${wakeFlash ? 'wake-flash' : ''}`}>
                {(isThinking || isListening || wakeFlash) && (
                  <div className="listening-pulse" style={{ background: statusColor }} />
                )}
                <span className="response-text">{response}</span>
              </div>
            )}

            {mode === "text" ? (
              <form className="input-group" onSubmit={handleSendCommand}>
                <input
                  type="text"
                  placeholder={isThinking ? "PROCESSING..." : "TRANSMIT COMMAND..."}
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  disabled={isThinking}
                />
                <button type="submit" disabled={isThinking}>SEND</button>
              </form>
            ) : (
              <div className="input-group" style={{ justifyContent: 'center', opacity: isListening ? 1 : 0.5 }}>
                <div style={{ padding: '12px', fontSize: '0.9rem', color: statusColor }}>
                  {isListening
                    ? "JARVIS IS LISTENING..."
                    : isAsleep
                    ? "CLICK GLOBE OR SAY 'HEY JARVIS' TO WAKE"
                    : "CLICK GLOBE TO TALK · OR SAY 'HEY JARVIS'"}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ── COMMAND CENTER ── */
          <div className="settings-section" style={{ pointerEvents: 'auto' }}>
            <div className="flex-header">
                <h2 style={{ color: '#00f2ff', fontWeight: 200, letterSpacing: '3px' }}>SYSTEM SETTINGS</h2>
            </div>
            
            <div className="system-settings-card">
              <div className="setting-control">
                <span className="setting-label">INTERACTION_MODE</span>
                <div className="mode-toggle">
                  <button 
                    className={`toggle-btn ${mode === 'text' ? 'active' : ''}`}
                    onClick={() => handleModeChange('text')}
                  >TEXT_ONLY</button>
                  <button 
                    className={`toggle-btn ${mode === 'speech' ? 'active' : ''}`}
                    onClick={() => handleModeChange('speech')}
                  >LIVE_SPEECH</button>
                </div>
              </div>
            </div>

            <h2 style={{ color: '#00f2ff', fontWeight: 200, letterSpacing: '3px', marginTop: '40px' }}>PERSONAL SHORTCUTS</h2>

            <div className="shortcuts-table">
              {Object.keys(shortcuts).length === 0 ? (
                <div style={{ padding: '20px', opacity: 0.4, textAlign: 'center', fontSize: '0.85rem' }}>
                  No shortcuts defined yet.
                </div>
              ) : (
                Object.entries(shortcuts).map(([k, v]) => (
                  <div key={k} className="shortcut-row">
                    <span className="sc-key">{k}</span>
                    <span className="sc-arrow">→</span>
                    <span className="sc-val">{v}</span>
                    <button onClick={() => removeShortcut(k)} className="sc-del">DEL</button>
                  </div>
                ))
              )}
            </div>

            <form className="shortcut-form" onSubmit={handleAddShortcut}>
              <input
                type="text"
                placeholder="KEYWORD (e.g. play)"
                value={newShortcut.key}
                onChange={e => setNewShortcut({ ...newShortcut, key: e.target.value })}
              />
              <select
                value={newShortcut.action}
                onChange={e => setNewShortcut({ ...newShortcut, action: e.target.value })}
              >
                <option value="OPEN_APP">OPEN_APP</option>
                <option value="OPEN_FOLDER">OPEN_FOLDER</option>
                <option value="OPEN_URL">OPEN_URL</option>
              </select>
              <input
                type="text"
                placeholder="VALUE (e.g. steam)"
                value={newShortcut.value}
                onChange={e => setNewShortcut({ ...newShortcut, value: e.target.value })}
              />
              <button type="submit">ADD_SHORTCUT</button>
            </form>
          </div>
        )}
      </div>
      <footer className="dashboard-footer">
        <div className="footer-content">
          <p className="made-with">Made with <span className="heart">❤️</span> by <strong>Rudra Kumar Gupta</strong></p>
          <div className="social-links">
            <a href="https://rudra-gupta.vercel.app/" target="_blank" rel="noopener noreferrer" className="social-icon" title="Portfolio">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
            </a>
            <a href="https://www.linkedin.com/in/rudra-kumar-gupta/" target="_blank" rel="noopener noreferrer" className="social-icon" title="LinkedIn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>
            </a>
            <a href="https://github.com/Rudra-Gupta15" target="_blank" rel="noopener noreferrer" className="social-icon" title="GitHub">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
