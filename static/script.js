/* ===========================================================
   JARVIS HUD — Controller Script
   Deep Integration: State sync, telemetry, voice reactivity
   =========================================================== */

const socket = io();

// === DOM REFS ===
const transcript   = document.getElementById('transcript');
const userInput     = document.getElementById('user-input');
const sendBtn       = document.getElementById('send-btn');
const thinking      = document.getElementById('thinking-indicator');
const neuralState   = document.getElementById('neural-state');
const coreStateLabel = document.getElementById('core-state-label');
const coreStateSub  = document.getElementById('core-state-sub');

// === STATE ===
let cmdHistory = [];
let historyIdx = -1;
let processingStartTs = null;
const startTime = Date.now();

// =============================================================
//  1. CLOCK / UPTIME
// =============================================================
setInterval(() => {
    const now = new Date();
    const el = document.getElementById('live-time');
    const ms = document.getElementById('live-millis');
    if (el) el.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    if (ms) ms.textContent = '.' + now.getMilliseconds().toString().padStart(3, '0');

    const d = Date.now() - startTime;
    const h = String(Math.floor(d / 3600000)).padStart(2, '0');
    const m = String(Math.floor((d % 3600000) / 60000)).padStart(2, '0');
    const s = String(Math.floor((d % 60000) / 1000)).padStart(2, '0');
    const u = document.getElementById('uptime-val');
    if (u) u.textContent = `${h}:${m}:${s}`;
}, 200);

// =============================================================
//  2. TRANSCRIPT HELPERS
// =============================================================
function typeMessage(text, className) {
    const p = document.createElement('p');
    p.className = className;
    transcript.appendChild(p);

    let i = 0;
    const speed = Math.max(8, Math.min(20, 800 / text.length)); // Adaptive speed
    const interval = setInterval(() => {
        p.textContent = text.slice(0, i);
        i++;
        transcript.scrollTop = transcript.scrollHeight;
        if (i > text.length) clearInterval(interval);
    }, speed);
}

function addUser(text) {
    const p = document.createElement('p');
    p.className = 'user-msg';
    p.textContent = `> ${text}`;
    transcript.appendChild(p);
    transcript.scrollTop = transcript.scrollHeight;
}

function addSystemLog(msg) {
    const p = document.createElement('p');
    p.className = 'system-msg';
    const t = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    p.innerHTML = `<span class="log-time">[${t}]</span> <span class="log-tag">SYS//</span> ${msg}`;
    transcript.appendChild(p);
    transcript.scrollTop = transcript.scrollHeight;
}

// =============================================================
//  3. SEND / INPUT HANDLING
// =============================================================
function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    thinking.classList.remove('hidden');
    socket.emit('ui_command', text);

    cmdHistory.push(text);
    historyIdx = cmdHistory.length;
    userInput.value = '';
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { sendMessage(); return; }
    if (e.key === 'ArrowUp') {
        if (historyIdx > 0) { historyIdx--; userInput.value = cmdHistory[historyIdx]; }
        e.preventDefault();
    }
    if (e.key === 'ArrowDown') {
        if (historyIdx < cmdHistory.length - 1) { historyIdx++; userInput.value = cmdHistory[historyIdx]; }
        else { historyIdx = cmdHistory.length; userInput.value = ''; }
        e.preventDefault();
    }
});

// --- Brain Selector ---
const brainSelector = document.getElementById('brain-selector');
if (brainSelector) {
    const COLOR_MAP = {
        auto:       { accent: 'var(--accent-cyan)', h: 'var(--h-cyan)' },
        gemini:     { accent: 'var(--accent-blue)', h: 'var(--h-blue)' },
        groq:       { accent: 'var(--accent-gold)', h: 'var(--h-gold)' }
    };

    brainSelector.addEventListener('change', () => {
        const provider = brainSelector.value;
        socket.emit('update_brain_provider', { provider: provider });
        
        // Visual Feedback: Change Arc Reactor & HUD theme
        const theme = COLOR_MAP[provider] || COLOR_MAP.auto;
        document.documentElement.style.setProperty('--state-accent', theme.accent);
        document.documentElement.style.setProperty('--state-h', theme.h);

        if (coreStateSub) {
            coreStateSub.textContent = (provider === 'auto') ? 'FAILOVER MODE // ACTIVE' : `${provider.toUpperCase()} // FORCED`;
        }
        
        addSystemLog(`Neural Link recalibrated: ${provider.toUpperCase()} engaged.`);
    });
}

// =============================================================
//  4. CORE STATE MANAGEMENT (Deep HUD Integration)
// =============================================================
const STATE_MAP = {
    processing: { label: 'PROCESSING',  sub: 'Neural pathway active...', neural: 'THINK_CYCLE ACTIVE', bodyClass: 'state-thinking' },
    action:     { label: 'EXECUTING',   sub: 'Skill dispatch in progress', neural: 'EXECUTOR ENGAGED', bodyClass: 'state-action' },
    speaking:   { label: 'SPEAKING',    sub: 'Audio synthesis active', neural: 'VOICE OUTPUT ACTIVE', bodyClass: 'state-speaking' },
    listening:  { label: 'LISTENING',   sub: 'Wake word detected — awaiting command', neural: 'SENSORY INPUT ACTIVE', bodyClass: 'state-listening' },
    idle:       { label: 'STANDBY',     sub: 'GEMINI-2.5-FLASH-LITE // READY', neural: 'NEURAL LINK ESTABLISHED', bodyClass: '' },
};

function setHUDState(state) {
    const cfg = STATE_MAP[state] || STATE_MAP.idle;
    const body = document.body;

    Object.values(STATE_MAP).forEach(s => { if (s.bodyClass) body.classList.remove(s.bodyClass); });

    if (cfg.bodyClass) body.classList.add(cfg.bodyClass);
    if (coreStateLabel) coreStateLabel.textContent = cfg.label;
    if (coreStateSub) coreStateSub.textContent = cfg.sub;
    if (neuralState) neuralState.textContent = cfg.neural;

    if (state === 'processing') {
        thinking.classList.remove('hidden');
    } else {
        thinking.classList.add('hidden');
    }

    if (window.__reactorSetState) window.__reactorSetState(state);
}

// =============================================================
//  5. SOCKET EVENT HANDLERS
// =============================================================

// --- Connection Status ---
socket.on('disconnect', () => {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    if (statusDot) statusDot.style.background = '#ff4444';
    if (statusText) statusText.textContent = 'DISCONNECTED';
    console.warn('[HUD] Socket disconnected');
});

socket.on('reconnect', () => {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    if (statusDot) statusDot.style.background = '#00ff88';
    if (statusText) statusText.textContent = 'ONLINE';
    console.log('[HUD] Socket reconnected');
});

socket.on('connect', () => {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    if (statusDot) statusDot.style.background = '#00ff88';
    if (statusText) statusText.textContent = 'ONLINE';
});

// --- Messages ---
socket.on('new_message', (data) => {
    if (data.sender === 'jarvis') {
        setHUDState('idle');
        typeMessage(`JARVIS >> ${data.text}`, 'jarvis-msg');
    } else if (data.sender === 'user') {
        addUser(data.text);
    }
});

socket.on('system_log', (msg) => {
    addSystemLog(msg);
});

// --- State Changes ---
socket.on('state_change', (state) => {
    if (state === 'processing') {
        processingStartTs = Date.now();
        setHUDState('processing');
    } else if (state === 'action') {
        setHUDState('action');
    } else if (state === 'listening') {
        setHUDState('listening');
    } else {
        if (processingStartTs) {
            const ms = Date.now() - processingStartTs;
            const el = document.getElementById('latency-val');
            if (el) el.textContent = `${ms}ms`;
            processingStartTs = null;
        }
        setHUDState('idle');
    }
});

// --- System Metrics ---
function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }

socket.on('system_status', (data) => {
    const s = data && data.status ? data.status : null;
    if (!s) return;

    const cpu = clamp(Number(s.cpu || 0), 0, 100);
    const ram = clamp(Number(s.ram || 0), 0, 100);

    const cpuBar = document.getElementById('cpu-bar');
    const memBar = document.getElementById('mem-bar');
    const cpuVal = document.getElementById('cpu-val');
    const memVal = document.getElementById('mem-val');

    if (cpuBar) {
        cpuBar.style.width = `${cpu}%`;
        cpuBar.className = `fill ${cpu > 90 ? 'critical' : cpu > 70 ? 'warning' : ''}`;
    }
    if (memBar) {
        memBar.style.width = `${ram}%`;
        memBar.className = `fill ${ram > 90 ? 'critical' : ram > 70 ? 'warning' : ''}`;
    }
    if (cpuVal) cpuVal.textContent = `${cpu}%`;
    if (memVal) memVal.textContent = `${ram}%`;

    // Battery
    if (s.battery) {
        const b = s.battery;
        const battBar = document.getElementById('batt-bar');
        const battVal = document.getElementById('batt-val');
        if (battBar) battBar.style.width = `${b.percent}%`;
        if (battVal) battVal.textContent = `${b.percent}%${b.power_plugged ? ' AC' : ''}`;
    }

    // Overall status
    const statusEl = document.getElementById('status-text');
    if (statusEl) {
        if (cpu > 90 || ram > 90) {
            statusEl.textContent = 'CRITICAL';
            statusEl.style.color = 'var(--accent-pink)';
        } else {
            statusEl.textContent = 'ONLINE';
            statusEl.style.color = '';
        }
    }
});

// --- Voice Level (Arc Reactor + Three.js Particle Reactivity) ---
socket.on('voice_level', (data) => {
    const level = data.level || 0;
    const core = document.querySelector('.core-circle');
    const glow = document.getElementById('core-glow');
    const rings = document.querySelectorAll('.ring');

    if (level > 5) setHUDState('speaking');

    if (core) {
        const r = 28 + (level / 8);
        core.setAttribute('r', r);
    }

    if (glow) {
        glow.style.opacity = 0.3 + (level / 150);
        glow.style.filter = `blur(${30 + level / 4}px)`;
    }

    rings.forEach((ring, i) => {
        const extra = level / (250 + i * 60);
        ring.style.opacity = 0.25 + extra;
    });

    if (window.__reactorSetVoice) window.__reactorSetVoice(level);
});

// --- Visual Awareness ---
socket.on('visual_awareness', (data) => {
    const img = document.getElementById('last-scan-img');
    const ctx = document.getElementById('observer-context');
    if (img && data.image_path) img.src = data.image_path + '?t=' + Date.now();
    if (ctx && data.context) ctx.textContent = data.context;
});

// --- Gesture Status ---
socket.on('gesture_status', (data) => {
    const dot = document.getElementById('gesture-dot');
    if (!dot) return;
    if (data.status === 'TRACKING') {
        dot.classList.add('online');
    } else {
        dot.classList.remove('online');
    }
});

// --- Agent Status ---
socket.on('agent_status', (data) => {
    const li = document.querySelector(`li[data-agent="${data.agent}"]`);
    if (!li) return;
    const dot = li.querySelector('.status-dot');
    const isActive = data.status.toLowerCase().includes('active') || data.status.toLowerCase().includes('new goal');
    if (isActive) {
        dot.classList.add('online');
        li.classList.add('active');
    } else {
        dot.classList.remove('online');
        li.classList.remove('active');
    }
});

// --- Auth: PIN + Face Verification ---
(function initAuth() {
    const overlay      = document.getElementById('auth-overlay');
    const pinStage     = document.getElementById('auth-pin-stage');
    const faceStage    = document.getElementById('auth-face-stage');
    const successStage = document.getElementById('auth-success-stage');
    const pinInput     = document.getElementById('auth-pin-input');
    const pinBtn       = document.getElementById('auth-pin-submit');
    const pinError     = document.getElementById('auth-pin-error');
    const faceVideo    = document.getElementById('auth-face-video');
    const faceCanvas   = document.getElementById('auth-face-canvas');
    const faceStatus   = document.getElementById('auth-face-status');
    const welcomeName  = document.getElementById('auth-welcome-name');
    if (!overlay) return;

    let faceStream = null;
    let scanTimer  = null;
    let scanCount  = 0;
    const MAX_SCANS = 5;

    function authSpeak(text) {
        socket.emit('auth_speak', { text });
    }

    socket.on('force_reauth', () => {
        sessionStorage.removeItem('jarvis_auth');
        overlay.style.display = '';
        overlay.classList.remove('fade-out');
        showStage(pinStage);
        pinInput.value = '';
        pinInput.focus();
        if (!sessionStorage.getItem('jarvis_auth_greeted')) {
            sessionStorage.setItem('jarvis_auth_greeted', 'true');
            authSpeak('Starting verification. Please enter your access code.');
        }
    });

    if (sessionStorage.getItem('jarvis_auth') === 'true') {
        overlay.style.display = 'none';
        return;
    }

    function showStage(stage) {
        [pinStage, faceStage, successStage].forEach(s => s.classList.add('hidden'));
        stage.classList.remove('hidden');
    }

    // PIN submit
    function submitPin() {
        const pin = pinInput.value.trim();
        if (!pin) return;
        pinBtn.disabled = true;
        pinBtn.textContent = 'VERIFYING...';
        socket.emit('verify_pin', { pin });
    }
    pinBtn.addEventListener('click', submitPin);
    pinInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') submitPin(); });
    pinInput.focus();

    // PIN accepted → open face scan
    socket.on('pin_accepted', () => {
        authSpeak('Access code accepted. Step two. Initiating facial recognition.');
        showStage(faceStage);
        startFaceScan();
    });

    socket.on('auth_failure', () => {
        authSpeak('Access denied. Invalid code.');
        pinBtn.disabled = false;
        pinBtn.textContent = 'VERIFY';
        pinError.classList.remove('hidden');
        pinInput.value = '';
        pinInput.focus();
        setTimeout(() => pinError.classList.add('hidden'), 3000);
    });

    const retryBtn = document.getElementById('auth-face-retry');

    function showRetryBtn() {
        if (retryBtn) retryBtn.classList.remove('hidden');
    }
    function hideRetryBtn() {
        if (retryBtn) retryBtn.classList.add('hidden');
    }

    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            hideRetryBtn();
            if (faceStatus) {
                faceStatus.textContent = 'Scanning... hold still';
                faceStatus.className = 'auth-face-status';
            }
            scanTimer = setTimeout(captureAndVerify, 1500);
        });
    }

    function startFaceScan() {
        if (faceStatus) faceStatus.textContent = 'Activating facial scanner...';
        faceStatus.className = 'auth-face-status';
        scanCount = 0;
        hideRetryBtn();

        navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
        }).then(stream => {
            faceStream = stream;
            faceVideo.srcObject = stream;
            faceVideo.play();
            if (faceStatus) faceStatus.textContent = 'Scanning... hold still';
            authSpeak('Look at the camera, please.');

            scanTimer = setTimeout(captureAndVerify, 2000);
        }).catch(err => {
            console.error('[auth] Camera failed:', err);
            authSpeak('Access denied. Camera unavailable. Biometric scan required.');
            if (faceStatus) {
                faceStatus.textContent = 'ACCESS DENIED — Camera unavailable. Biometric scan required.';
                faceStatus.className = 'auth-face-status error';
            }
        });
    }

    function captureAndVerify() {
        if (!faceStream) return;
        scanCount++;

        faceCanvas.width = faceVideo.videoWidth;
        faceCanvas.height = faceVideo.videoHeight;
        const ctx = faceCanvas.getContext('2d');
        ctx.drawImage(faceVideo, 0, 0);
        const dataUrl = faceCanvas.toDataURL('image/jpeg', 0.85);

        if (faceStatus) faceStatus.textContent = `Scanning... attempt ${scanCount}/${MAX_SCANS}`;
        socket.emit('face_verify', { image: dataUrl });
    }

    socket.on('face_result', (data) => {
        if (data.status === 'success') {
            if (faceStatus) {
                faceStatus.textContent = 'IDENTITY CONFIRMED';
                faceStatus.className = 'auth-face-status success';
            }
            authSpeak(`Identity confirmed. Welcome back, ${data.name || 'Sir'}.`);
            setTimeout(() => grantAccess(data.name || 'Sir'), 1500);

        } else if (data.status === 'registered') {
            if (faceStatus) {
                faceStatus.textContent = 'FACE REGISTERED — WELCOME';
                faceStatus.className = 'auth-face-status success';
            }
            authSpeak(`Face registered successfully. Welcome, ${data.name || 'Sir'}.`);
            setTimeout(() => grantAccess(data.name || 'Sir'), 1500);

        } else if (data.status === 'no_faces') {
            if (faceStatus) faceStatus.textContent = 'First time setup — registering your face...';
            authSpeak('No biometric data on file. Registering your face now. Hold still.');
            setTimeout(() => {
                faceCanvas.width = faceVideo.videoWidth;
                faceCanvas.height = faceVideo.videoHeight;
                faceCanvas.getContext('2d').drawImage(faceVideo, 0, 0);
                const dataUrl = faceCanvas.toDataURL('image/jpeg', 0.85);
                socket.emit('face_register', { image: dataUrl, name: 'Sir' });
            }, 2000);

        } else if (data.status === 'no_face_detected') {
            if (faceStatus) {
                faceStatus.textContent = 'NO FACE DETECTED — Position yourself in front of the camera.';
                faceStatus.className = 'auth-face-status error';
            }
            authSpeak('No face detected.');
            showRetryBtn();

        } else if (data.status === 'denied') {
            if (faceStatus) {
                faceStatus.textContent = 'FACE NOT RECOGNIZED';
                faceStatus.className = 'auth-face-status error';
            }
            authSpeak('Face not recognized.');
            showRetryBtn();

        } else {
            if (faceStatus) {
                faceStatus.textContent = data.message || 'Verification error';
                faceStatus.className = 'auth-face-status error';
            }
        }
    });

    function grantAccess(name) {
        stopFaceStream();
        showStage(successStage);
        if (welcomeName) welcomeName.textContent = `Welcome, ${name}`;
        sessionStorage.setItem('jarvis_auth', 'true');
        sessionStorage.removeItem('jarvis_auth_greeted');

        setTimeout(() => {
            overlay.classList.add('fade-out');
            setTimeout(() => { overlay.style.display = 'none'; }, 900);
        }, 2000);
    }

    function stopFaceStream() {
        if (scanTimer) { clearTimeout(scanTimer); scanTimer = null; }
        if (faceStream) {
            faceStream.getTracks().forEach(t => t.stop());
            faceStream = null;
        }
        faceVideo.srcObject = null;
    }

    // Voice enrollment prompt (shown in HUD after login if no voice print)
    socket.on('voice_enroll_needed', () => {
        if (overlay.style.display === 'none' || overlay.classList.contains('fade-out')) {
            addSystemLog('VOICE ENROLLMENT REQUIRED — Click the enrollment banner to begin.');
            const banner = document.createElement('div');
            banner.id = 'voice-enroll-banner';
            banner.className = 'voice-enroll-banner';
            banner.innerHTML = '<span class="enroll-icon">🎙</span> Voice print not found — <strong>Click here</strong> to enroll your voice for secure confirmations';
            banner.addEventListener('click', () => {
                banner.innerHTML = '<span class="enroll-icon">🎙</span> Recording... speak naturally for ~12 seconds';
                banner.classList.add('recording');
                socket.emit('voice_enroll', {});
            });
            document.body.appendChild(banner);
        }
    });

    socket.on('voice_enroll_status', (data) => {
        const banner = document.getElementById('voice-enroll-banner');
        if (!banner) return;
        if (data.status === 'recording') {
            banner.innerHTML = `<span class="enroll-icon">🎙</span> ${data.message}`;
        } else if (data.status === 'success') {
            banner.innerHTML = '<span class="enroll-icon">✓</span> Voice print enrolled — speaker verification active';
            banner.classList.remove('recording');
            banner.classList.add('success');
            addSystemLog('Voice print enrolled successfully. Speaker verification is now active.');
            setTimeout(() => banner.remove(), 4000);
        } else if (data.status === 'error') {
            banner.innerHTML = `<span class="enroll-icon">✗</span> ${data.message} — click to retry`;
            banner.classList.remove('recording');
            banner.classList.add('error');
        }
    });
})();

// =============================================================
//  6. SIMULATED DATA STREAM (Makes HUD feel alive)
// =============================================================
const DATA_STREAM_LINES = [
    'ACK >> Neural handshake verified',
    'SYNC >> Memory buffer: 12.4MB / 128MB',
    'PING >> Gemini endpoint latency: 42ms',
    'SCAN >> Filesystem watcher: 3 active hooks',
    'CORE >> Priority queue depth: 0',
    'AUTH >> Session token valid [exp: 23:59]',
    'VOSK >> Recognition model: en-IN-16kHz',
    'AUDIO >> edge-tts voice: en-GB-RyanNeural',
    'SAFE >> Environment: DEVELOPMENT',
    'SKILL >> 26 modules loaded (0 errors)',
    'SYNC >> Episodic memory: 847 entries',
    'NET >> Network interface: connected',
    'GPU >> Compute: integrated (MediaPipe ready)',
    'TICK >> Autonomous loop: 1.2s interval',
];

function startDataStream() {
    const el = document.getElementById('data-stream');
    if (!el) return;

    let lines = [];
    setInterval(() => {
        const line = DATA_STREAM_LINES[Math.floor(Math.random() * DATA_STREAM_LINES.length)];
        const t = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        lines.push(`[${t}] ${line}`);
        if (lines.length > 6) lines.shift();
        el.textContent = lines.join('\n');
    }, 3000);
}

startDataStream();

// =============================================================
//  7. UTILITY FUNCTIONS
// =============================================================
function hapticFeedback(ms = 50) {
    if (window.navigator && window.navigator.vibrate) {
        window.navigator.vibrate(ms);
    }
}

function emergencyHalt() {
    if (confirm('INITIATE_SYSTEM_HALT? All active tasks will be terminated.')) {
        socket.emit('ui_command', 'Emergency Halt: Shutdown all processes');
        hapticFeedback(200);
    }
}

// =============================================================
//  8. THREE.JS ARC REACTOR PARTICLE FIELD
// =============================================================
(function initReactorParticles() {
    const canvas = document.getElementById('reactor-particles');
    if (!canvas || typeof THREE === 'undefined') return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
    camera.position.z = 3;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const PARTICLE_COUNT = 600;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const velocities = new Float32Array(PARTICLE_COUNT * 3);
    const baseDist = new Float32Array(PARTICLE_COUNT);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 0.6 + Math.random() * 1.8;
        positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = (Math.random() - 0.5) * 0.8;
        velocities[i * 3]     = (Math.random() - 0.5) * 0.002;
        velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.002;
        velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.001;
        baseDist[i] = r;
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
        size: 0.018,
        color: 0x00e5ff,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    let _voiceLevel = 0;
    let _currentState = 'idle';

    const STATE_COLORS = {
        idle:       0x00e5ff,
        processing: 0xffb300,
        action:     0xff4081,
        speaking:   0x00e676,
        listening:  0x40c4ff,
    };

    window.__reactorSetVoice = (level) => { _voiceLevel = level; };
    window.__reactorSetState = (state) => {
        _currentState = state;
        const c = STATE_COLORS[state] || STATE_COLORS.idle;
        material.color.setHex(c);
    };

    function resize() {
        const panel = canvas.parentElement;
        if (!panel) return;
        const w = panel.clientWidth;
        const h = panel.clientHeight;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }

    resize();
    window.addEventListener('resize', resize);

    function animate() {
        requestAnimationFrame(animate);
        const pos = geometry.attributes.position.array;
        const pulse = 1 + (_voiceLevel / 200);
        const time = performance.now() * 0.0003;

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const i3 = i * 3;
            pos[i3]     += velocities[i3] * pulse;
            pos[i3 + 1] += velocities[i3 + 1] * pulse;
            pos[i3 + 2] += velocities[i3 + 2];

            const dist = Math.sqrt(pos[i3] ** 2 + pos[i3 + 1] ** 2);
            if (dist > baseDist[i] * 1.3 || dist < baseDist[i] * 0.5) {
                velocities[i3]     *= -0.9;
                velocities[i3 + 1] *= -0.9;
            }
        }

        geometry.attributes.position.needsUpdate = true;
        material.opacity = 0.35 + (_voiceLevel / 300);
        particles.rotation.z = time * 0.3;
        renderer.render(scene, camera);
    }

    animate();
})();

// =============================================================
//  9. IMAGE DRAG & DROP — Visual Analysis
// =============================================================
(function initImageDrop() {
    const dropZone = document.getElementById('drop-zone');
    const dropOverlay = document.getElementById('drop-overlay');
    const observerCtx = document.getElementById('observer-context');
    const scanImg = document.getElementById('last-scan-img');
    if (!dropZone) return;

    // Show overlay on drag-enter
    dropZone.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dropOverlay.classList.add('active');
    });
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropOverlay.classList.add('active');
    });
    dropZone.addEventListener('dragleave', (e) => {
        if (!dropZone.contains(e.relatedTarget)) {
            dropOverlay.classList.remove('active');
        }
    });

    dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropOverlay.classList.remove('active');

        const file = e.dataTransfer.files[0];
        if (!file || !file.type.startsWith('image/')) {
            addSystemLog('Drop rejected: not an image file.');
            return;
        }

        // Preview immediately
        const localUrl = URL.createObjectURL(file);
        if (scanImg) { scanImg.src = localUrl; scanImg.style.display = 'block'; }

        // Show scanning state
        if (observerCtx) observerCtx.textContent = 'SCANNING... Neural optics processing image...';
        setHUDState('processing');
        addSystemLog(`Image received: ${file.name} (${(file.size / 1024).toFixed(1)} KB) — dispatching to vision core...`);

        try {
            const formData = new FormData();
            formData.append('image', file, file.name);

            const res = await fetch('/api/analyse_image', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (data.error) {
                if (observerCtx) observerCtx.textContent = `Error: ${data.error}`;
                addSystemLog(`Vision Error: ${data.error}`);
                setHUDState('idle');
            }
            // Success is handled by the socket event ('visual_awareness' + 'new_message')
            // which main.py broadcasts after analysis completes
        } catch (err) {
            if (observerCtx) observerCtx.textContent = `Network Error: ${err.message}`;
            addSystemLog(`Image upload failed: ${err.message}`);
            setHUDState('idle');
        }
    });
})();

// =============================================================
//  10. CAMERA PREVIEW PANEL
// =============================================================
(function initCameraPreview() {
    const overlay = document.getElementById('camera-overlay');
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    const captureBtn = document.getElementById('camera-capture-btn');
    const cancelBtn = document.getElementById('camera-cancel');
    const statusEl = document.getElementById('camera-status');
    if (!overlay || !video) return;

    let mediaStream = null;

    function openCamera() {
        overlay.classList.remove('hidden');
        if (statusEl) statusEl.textContent = 'Requesting camera access...';
        captureBtn.disabled = true;

        navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' }
        }).then(stream => {
            mediaStream = stream;
            video.srcObject = stream;
            video.play();
            captureBtn.disabled = false;
            if (statusEl) statusEl.textContent = 'Position your camera and click CAPTURE when ready';
            addSystemLog('Camera feed active — awaiting capture.');
        }).catch(err => {
            console.error('[camera] getUserMedia failed:', err);
            if (statusEl) statusEl.textContent = 'Camera access denied. Falling back to server capture...';
            addSystemLog('Browser camera denied — falling back to server capture.');
            socket.emit('camera_preview_failed', {});
            setTimeout(closeCamera, 1500);
        });
    }

    function closeCamera() {
        overlay.classList.add('hidden');
        if (mediaStream) {
            mediaStream.getTracks().forEach(t => t.stop());
            mediaStream = null;
        }
        video.srcObject = null;
    }

    function captureFrame() {
        if (!mediaStream) return;
        captureBtn.disabled = true;
        if (statusEl) statusEl.textContent = 'CAPTURING...';

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
        socket.emit('camera_captured', { image: dataUrl });

        if (statusEl) statusEl.textContent = 'Captured — sending to JARVIS...';
        addSystemLog('Camera frame captured — transmitting to neural core.');

        setTimeout(closeCamera, 800);
    }

    captureBtn.addEventListener('click', captureFrame);
    cancelBtn.addEventListener('click', () => {
        socket.emit('camera_preview_cancelled', {});
        closeCamera();
    });

    socket.on('camera_preview_start', () => {
        console.log('[JARVIS] camera_preview_start received');
        openCamera();
    });
    socket.on('camera_preview_stop', () => closeCamera());

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !overlay.classList.contains('hidden')) {
            socket.emit('camera_preview_cancelled', {});
            closeCamera();
        }
    });
})();

// =============================================================
//  11. VISUAL GENERATION PANEL
// =============================================================
(function initVisualPanel() {
    const overlay = document.getElementById('visual-overlay');
    const content = document.getElementById('visual-content');
    const titleEl = document.getElementById('visual-title');
    const statusEl = document.getElementById('visual-status');
    const closeBtn = document.getElementById('visual-close');
    const zoomInBtn = document.getElementById('visual-zoom-in');
    const zoomOutBtn = document.getElementById('visual-zoom-out');
    const resetBtn = document.getElementById('visual-reset');
    const saveBtn = document.getElementById('visual-save');

    if (!overlay || !content) return;

    let panZoomInstance = null;
    let currentContent = null;

    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({ startOnLoad: false, theme: 'dark' });
    }

    function openPanel(title) {
        overlay.classList.remove('hidden');
        if (titleEl) titleEl.textContent = title || 'VISUAL_OUTPUT';
        addSystemLog('Visual output received — displaying on HUD.');
    }

    function closePanel() {
        overlay.classList.add('hidden');
        if (panZoomInstance) {
            panZoomInstance.destroy();
            panZoomInstance = null;
        }
    }

    closeBtn.addEventListener('click', closePanel);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !overlay.classList.contains('hidden')) {
            closePanel();
        }
    });

    function renderSvg(svgContent) {
        const clean = (typeof DOMPurify !== 'undefined')
            ? DOMPurify.sanitize(svgContent, { USE_PROFILES: { svg: true, svgFilters: true } })
            : svgContent;
        content.innerHTML = clean;
        const svgEl = content.querySelector('svg');
        if (svgEl && typeof svgPanZoom !== 'undefined') {
            svgEl.style.width = '100%';
            svgEl.style.height = '100%';
            setTimeout(() => {
                panZoomInstance = svgPanZoom(svgEl, {
                    controlIconsEnabled: false,
                    fit: true,
                    center: true,
                    zoomScaleSensitivity: 0.3,
                    minZoom: 0.3,
                    maxZoom: 10
                });
            }, 100);
        }
    }

    socket.on('visual_panel', (data) => {
        content.innerHTML = '';
        if (panZoomInstance) { panZoomInstance.destroy(); panZoomInstance = null; }
        currentContent = data;

        if (data.type === 'photo_overlay') {
            const container = document.createElement('div');
            container.className = 'photo-overlay-container';

            const photo = document.createElement('img');
            photo.className = 'photo-bg';
            photo.src = data.photo_url + '?t=' + Date.now();
            container.appendChild(photo);

            if (data.svg_overlay) {
                const svgDiv = document.createElement('div');
                svgDiv.className = 'svg-overlay';
                const clean = (typeof DOMPurify !== 'undefined')
                    ? DOMPurify.sanitize(data.svg_overlay, { USE_PROFILES: { svg: true, svgFilters: true } })
                    : data.svg_overlay;
                svgDiv.innerHTML = clean;
                container.appendChild(svgDiv);
            }

            content.appendChild(container);
            if (statusEl) statusEl.textContent = 'AR OVERLAY — BLUEPRINT ON PHOTO';

        } else if (data.type === 'ai_composite') {
            const container = document.createElement('div');
            container.className = 'ai-composite-container';
            const img = document.createElement('img');
            if (data.image_base64) {
                img.src = 'data:image/jpeg;base64,' + data.image_base64;
            } else if (data.image_url) {
                img.src = data.image_url + '?t=' + Date.now();
            }
            container.appendChild(img);
            content.appendChild(container);
            if (statusEl) statusEl.textContent = 'AI COMPOSITE — REALISTIC RENDER';

        } else if (data.type === 'assembly_3d') {
            if (window.__startAssembly) {
                window.__startAssembly(data, content, overlay);
            }
            if (statusEl) statusEl.textContent = 'ASSEMBLING 3D MODEL...';
            openPanel(data.title);
            return;

        } else if (data.type === 'svg') {
            renderSvg(data.content);
            if (statusEl) statusEl.textContent = 'SVG BLUEPRINT LOADED';

        } else if (data.type === 'mermaid') {
            const pre = document.createElement('pre');
            pre.className = 'mermaid';
            pre.textContent = data.content;
            content.appendChild(pre);
            if (typeof mermaid !== 'undefined') {
                mermaid.run({ nodes: [pre] });
            }
            if (statusEl) statusEl.textContent = 'MERMAID DIAGRAM RENDERED';

        } else {
            const clean = (typeof DOMPurify !== 'undefined')
                ? DOMPurify.sanitize(data.content)
                : data.content;
            content.innerHTML = clean;
            if (statusEl) statusEl.textContent = 'HTML VISUAL LOADED';
        }

        openPanel(data.title);
    });

    if (zoomInBtn) zoomInBtn.addEventListener('click', () => { if (panZoomInstance) panZoomInstance.zoomIn(); });
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => { if (panZoomInstance) panZoomInstance.zoomOut(); });
    if (resetBtn) resetBtn.addEventListener('click', () => { if (panZoomInstance) { panZoomInstance.resetZoom(); panZoomInstance.center(); } });

    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            if (!currentContent) return;
            if (currentContent.type === 'ai_composite' && currentContent.image_base64) {
                const byteChars = atob(currentContent.image_base64);
                const byteNumbers = new Array(byteChars.length);
                for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i);
                const blob = new Blob([new Uint8Array(byteNumbers)], { type: 'image/jpeg' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `jarvis_composite_${Date.now()}.jpg`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } else {
                const saveContent = currentContent.svg_overlay || currentContent.content || '';
                const blob = new Blob([saveContent], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `jarvis_visual_${Date.now()}.${currentContent.type === 'svg' ? 'svg' : 'html'}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
            if (statusEl) statusEl.textContent = 'SAVED TO DOWNLOADS';
        });
    }
})();

// =============================================================
//  12. THREE.JS 3D ASSEMBLY VIEWER — Iron Man Style
// =============================================================
(function initAssemblyViewer() {
    if (typeof THREE === 'undefined') return;

    const CYAN    = 0x00e5ff;
    const DARK_BG = 0x06060f;
    const PART_DELAY = 800;
    const FLY_DURATION = 1000;
    const SCALE_FACTOR = 0.01;

    let scene, camera, renderer, css2Renderer, controls;
    let animFrameId = null;
    let autoOrbitActive = false;
    let autoOrbitAngle = 0;
    let assemblyData = null;
    let phaseEl = null;
    let infoEl = null;

    function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

    function dispose() {
        if (animFrameId) { cancelAnimationFrame(animFrameId); animFrameId = null; }
        autoOrbitActive = false;
        if (controls) { controls.dispose(); controls = null; }
        if (renderer) { renderer.dispose(); renderer = null; }
        if (css2Renderer) { css2Renderer = null; }
        if (scene) {
            scene.traverse(obj => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {
                    if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                    else obj.material.dispose();
                }
            });
            scene = null;
        }
        camera = null;
        assemblyData = null;
    }

    function createPartMesh(part) {
        const s = SCALE_FACTOR;
        let geo;
        if (part.shape === 'cylinder') {
            geo = new THREE.CylinderGeometry(part.w * s / 2, part.w * s / 2, part.h * s, 24);
        } else if (part.shape === 'sphere') {
            geo = new THREE.SphereGeometry(part.w * s / 2, 20, 16);
        } else {
            geo = new THREE.BoxGeometry(part.w * s, part.h * s, part.d * s);
        }

        const col = new THREE.Color(part.color || '#a0845c');
        const solidMat = new THREE.MeshPhongMaterial({
            color: col,
            transparent: true,
            opacity: 0,
            emissive: col,
            emissiveIntensity: 0.08,
            shininess: 60,
        });

        const mesh = new THREE.Mesh(geo, solidMat);

        const edges = new THREE.EdgesGeometry(geo);
        const wireMat = new THREE.LineBasicMaterial({ color: CYAN, transparent: true, opacity: 0.9 });
        const wireframe = new THREE.LineSegments(edges, wireMat);
        mesh.add(wireframe);
        mesh.userData.wireframe = wireframe;

        mesh.userData.targetPos = new THREE.Vector3(part.x * s, part.y * s, part.z * s);
        mesh.userData.partName = part.name;
        mesh.userData.dims = { w: part.w, h: part.h, d: part.d };

        return mesh;
    }

    function randomSpawnPos(targetPos) {
        const directions = [
            new THREE.Vector3(0, 4, 0),
            new THREE.Vector3(-4, 2, 0),
            new THREE.Vector3(4, 2, 0),
            new THREE.Vector3(0, 2, -4),
            new THREE.Vector3(0, 2, 4),
            new THREE.Vector3(-3, 3, -2),
            new THREE.Vector3(3, 3, 2),
        ];
        const dir = directions[Math.floor(Math.random() * directions.length)];
        return new THREE.Vector3(
            targetPos.x + dir.x + (Math.random() - 0.5),
            targetPos.y + dir.y + (Math.random() - 0.5),
            targetPos.z + dir.z + (Math.random() - 0.5)
        );
    }

    function createDimLabel(text) {
        if (typeof THREE.CSS2DObject === 'undefined') return null;
        const div = document.createElement('div');
        div.className = 'assembly-label';
        div.textContent = text;
        const obj = new THREE.CSS2DObject(div);
        return obj;
    }

    function snapFlash(mesh) {
        const flashGeo = new THREE.SphereGeometry(0.15, 8, 8);
        const flashMat = new THREE.MeshBasicMaterial({
            color: CYAN,
            transparent: true,
            opacity: 0.7,
            blending: THREE.AdditiveBlending,
        });
        const flash = new THREE.Mesh(flashGeo, flashMat);
        flash.position.copy(mesh.position);
        scene.add(flash);

        let t = 0;
        function animateFlash() {
            t += 0.05;
            flash.scale.setScalar(1 + t * 3);
            flashMat.opacity = 0.7 * (1 - t);
            if (t < 1) {
                requestAnimationFrame(animateFlash);
            } else {
                scene.remove(flash);
                flashGeo.dispose();
                flashMat.dispose();
            }
        }
        animateFlash();
    }

    function buildScene(container, data) {
        dispose();
        assemblyData = data;
        container.innerHTML = '';

        const width = container.clientWidth || 800;
        const height = container.clientHeight || 500;

        scene = new THREE.Scene();
        scene.background = new THREE.Color(DARK_BG);
        scene.fog = new THREE.FogExp2(DARK_BG, 0.3);

        camera = new THREE.PerspectiveCamera(50, width / height, 0.01, 100);

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.domElement.className = 'assembly-canvas';
        container.appendChild(renderer.domElement);

        if (typeof THREE.CSS2DRenderer !== 'undefined') {
            css2Renderer = new THREE.CSS2DRenderer();
            css2Renderer.setSize(width, height);
            css2Renderer.domElement.className = 'assembly-labels-layer';
            container.appendChild(css2Renderer.domElement);
        }

        controls = new THREE.OrbitControls(camera, css2Renderer ? css2Renderer.domElement : renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.enablePan = true;
        controls.minDistance = 0.5;
        controls.maxDistance = 10;
        controls.addEventListener('start', () => { autoOrbitActive = false; });

        const ambientLight = new THREE.AmbientLight(0x334466, 0.6);
        scene.add(ambientLight);
        const pointLight = new THREE.PointLight(0x00e5ff, 0.4, 15);
        pointLight.position.set(2, 4, 2);
        scene.add(pointLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.5);
        dirLight.position.set(-2, 3, 4);
        scene.add(dirLight);

        const gridColor = new THREE.Color(0x00e5ff);
        const grid = new THREE.GridHelper(4, 40, gridColor, gridColor);
        grid.material.transparent = true;
        grid.material.opacity = 0.12;
        scene.add(grid);

        phaseEl = document.createElement('div');
        phaseEl.className = 'assembly-phase';
        phaseEl.textContent = 'INITIALIZING...';
        container.appendChild(phaseEl);

        infoEl = document.createElement('div');
        infoEl.className = 'assembly-info';
        container.appendChild(infoEl);

        let bbox = new THREE.Box3();
        data.parts.forEach(p => {
            const s = SCALE_FACTOR;
            const half = new THREE.Vector3(p.w * s / 2, p.h * s / 2, p.d * s / 2);
            const center = new THREE.Vector3(p.x * s, p.y * s, p.z * s);
            bbox.expandByPoint(center.clone().sub(half));
            bbox.expandByPoint(center.clone().add(half));
        });
        const bCenter = new THREE.Vector3();
        bbox.getCenter(bCenter);
        const bSize = new THREE.Vector3();
        bbox.getSize(bSize);
        const maxDim = Math.max(bSize.x, bSize.y, bSize.z);
        const dist = maxDim * 2.2;
        camera.position.set(bCenter.x + dist * 0.5, bCenter.y + dist * 0.5, bCenter.z + dist);
        controls.target.copy(bCenter);
        controls.update();

        const parts = data.parts;
        const meshes = [];

        parts.forEach((p, i) => {
            const mesh = createPartMesh(p);
            const spawnPos = randomSpawnPos(mesh.userData.targetPos);
            mesh.position.copy(spawnPos);
            mesh.userData.spawnPos = spawnPos.clone();
            mesh.userData.spawnRotation = new THREE.Euler(
                (Math.random() - 0.5) * Math.PI * 2,
                (Math.random() - 0.5) * Math.PI * 2,
                (Math.random() - 0.5) * Math.PI * 2
            );
            mesh.rotation.copy(mesh.userData.spawnRotation);
            mesh.visible = false;
            scene.add(mesh);
            meshes.push(mesh);
        });

        let currentPartIdx = 0;
        let partStartTime = 0;
        let assemblyPhase = 'grid';
        let gridFadeStart = performance.now();
        let allDone = false;

        function updatePhaseText() {
            if (!phaseEl) return;
            if (assemblyPhase === 'grid') {
                phaseEl.textContent = 'SCANNING WORKSPACE...';
            } else if (assemblyPhase === 'flying') {
                phaseEl.textContent = `ASSEMBLING... ${currentPartIdx + 1}/${parts.length} parts`;
            } else if (assemblyPhase === 'labels') {
                phaseEl.textContent = 'RENDERING DIMENSIONS...';
            } else if (assemblyPhase === 'done') {
                phaseEl.textContent = 'ASSEMBLY COMPLETE';
                if (infoEl && data.summary) {
                    infoEl.innerHTML = `<strong>${data.title || ''}</strong><br>${data.summary}` +
                        (data.build_time ? `<br>Est. build time: ${data.build_time}` : '');
                }
            }
        }

        function animate() {
            animFrameId = requestAnimationFrame(animate);
            const now = performance.now();

            if (assemblyPhase === 'grid') {
                const elapsed = now - gridFadeStart;
                const gridOpacity = Math.min(elapsed / 600, 0.12);
                grid.material.opacity = gridOpacity;
                if (elapsed > 500) {
                    assemblyPhase = 'flying';
                    partStartTime = now;
                    if (meshes[0]) meshes[0].visible = true;
                    updatePhaseText();
                }
            }

            if (assemblyPhase === 'flying') {
                const totalElapsed = now - partStartTime;
                const expectedPart = Math.floor(totalElapsed / PART_DELAY);

                if (expectedPart > currentPartIdx && currentPartIdx < meshes.length - 1) {
                    currentPartIdx = Math.min(expectedPart, meshes.length - 1);
                    if (meshes[currentPartIdx]) meshes[currentPartIdx].visible = true;
                    updatePhaseText();
                }

                for (let i = 0; i <= Math.min(currentPartIdx, meshes.length - 1); i++) {
                    const m = meshes[i];
                    if (!m.visible) continue;
                    const myStart = i * PART_DELAY;
                    const t = Math.min((totalElapsed - myStart) / FLY_DURATION, 1);
                    if (t < 0) continue;

                    const e = easeOutCubic(t);
                    m.position.lerpVectors(m.userData.spawnPos, m.userData.targetPos, e);

                    const sr = m.userData.spawnRotation;
                    m.rotation.x = sr.x * (1 - e);
                    m.rotation.y = sr.y * (1 - e);
                    m.rotation.z = sr.z * (1 - e);

                    const wire = m.userData.wireframe;
                    if (t >= 1 && !m.userData.landed) {
                        m.userData.landed = true;
                        m.material.opacity = 0.75;
                        if (wire) wire.material.opacity = 0.4;
                        snapFlash(m);
                    } else if (t < 1) {
                        m.material.opacity = t * 0.3;
                        if (wire) wire.material.opacity = 0.9 - t * 0.5;
                    }
                }

                const allLanded = meshes.every(m => m.userData.landed);
                if (allLanded && !allDone) {
                    allDone = true;
                    setTimeout(() => {
                        assemblyPhase = 'labels';
                        updatePhaseText();
                        addDimensionLabels(meshes);
                        setTimeout(() => {
                            assemblyPhase = 'done';
                            updatePhaseText();
                            autoOrbitActive = true;
                        }, 800);
                    }, 400);
                }
            }

            if (autoOrbitActive) {
                autoOrbitAngle += 0.003;
                const r = dist;
                camera.position.x = bCenter.x + r * 0.5 * Math.cos(autoOrbitAngle);
                camera.position.z = bCenter.z + r * Math.sin(autoOrbitAngle);
                camera.lookAt(bCenter);
            }

            controls.update();
            renderer.render(scene, camera);
            if (css2Renderer) css2Renderer.render(scene, camera);
        }

        updatePhaseText();
        animate();

        function onResize() {
            if (!renderer || !container) return;
            const w = container.clientWidth;
            const h = container.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
            if (css2Renderer) css2Renderer.setSize(w, h);
        }
        window.addEventListener('resize', onResize);
    }

    function addDimensionLabels(meshes) {
        meshes.forEach(m => {
            const d = m.userData.dims;
            const name = m.userData.partName;
            const text = `${name} (${d.w}×${d.h}×${d.d} cm)`;
            const label = createDimLabel(text);
            if (label) {
                label.position.copy(m.userData.targetPos);
                label.position.y += (d.h * SCALE_FACTOR / 2) + 0.06;
                scene.add(label);
            }
        });
    }

    window.__startAssembly = function(data, container, overlay) {
        if (!data || !data.data || !data.data.parts) return;
        buildScene(container, data.data);
    };

    window.addEventListener('beforeunload', dispose);
})();