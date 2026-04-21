/**
 * Smartphone Usage Analyzer - Frontend JavaScript
 * WITH User Authentication Support
 */

let chartInstances = {};
let currentSuggestions = null;
let currentUser = null;

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadFeatures();
    loadStats();
    loadHistory();
    loadUsageHistory();
    loadModelInfo();
    initUpload();
    initNavigation();
});

// ============ NAVIGATION ============
function initNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function() {
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// ============ LOAD CURRENT USER ============
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/auth/me');
        const data = await response.json();

        if (data.success && data.logged_in) {
            currentUser = data.user;
            document.getElementById('userName').textContent = data.user.full_name;

            // Show admin link if admin
            if (data.user.role === 'admin') {
                document.getElementById('adminLink').style.display = 'block';
            }

            // Setup profile link
            document.getElementById('profileLink').addEventListener('click', (e) => {
                e.preventDefault();
                showProfile();
            });
        } else {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error loading user:', error);
    }
}

// ============ PROFILE MODAL ============
function showProfile() {
    if (!currentUser) return;

    const modal = document.getElementById('profileModal');
    const content = document.getElementById('profileContent');

    const joined = new Date(currentUser.created_at).toLocaleDateString();
    const lastLogin = currentUser.last_login ?
        new Date(currentUser.last_login).toLocaleString() : 'Just now';

    content.innerHTML = `
        <div class="model-stat">
            <span class="model-stat-label">👤 Username</span>
            <span class="model-stat-value">${currentUser.username}</span>
        </div>
        <div class="model-stat">
            <span class="model-stat-label">📛 Full Name</span>
            <span class="model-stat-value">${currentUser.full_name}</span>
        </div>
        <div class="model-stat">
            <span class="model-stat-label">📧 Email</span>
            <span class="model-stat-value">${currentUser.email}</span>
        </div>
        <div class="model-stat">
            <span class="model-stat-label">🛡️ Role</span>
            <span class="model-stat-value">${currentUser.role.toUpperCase()}</span>
        </div>
        <div class="model-stat">
            <span class="model-stat-label">📊 Total Predictions</span>
            <span class="model-stat-value">${currentUser.total_predictions}</span>
        </div>
        <div class="model-stat">
            <span class="model-stat-label">📅 Joined</span>
            <span class="model-stat-value">${joined}</span>
        </div>
        <div class="model-stat">
            <span class="model-stat-label">🕐 Last Login</span>
            <span class="model-stat-value">${lastLogin}</span>
        </div>
    `;

    modal.style.display = 'flex';
}

function closeProfile() {
    document.getElementById('profileModal').style.display = 'none';
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.id === 'profileModal') {
        closeProfile();
    }
});

// ============ TOAST ============
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const icons = { success: '✅', error: '❌', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || '📌'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);
    setTimeout(() => { if (toast.parentElement) { toast.style.opacity='0'; toast.style.transform='translateX(100px)'; setTimeout(()=>toast.remove(),300); } }, 4000);
}

// ============ HANDLE AUTH ERRORS ============
function handleAuthError(data) {
    if (data.redirect === '/login' || data.message === 'Login required') {
        window.location.href = '/login';
        return true;
    }
    return false;
}

// ============ LOAD FEATURES ============
async function loadFeatures() {
    const container = document.getElementById('dynamicFields');
    try {
        const response = await fetch('/api/features');
        const data = await response.json();

        if (!data.success && handleAuthError(data)) return;

        if (data.success && data.features.length > 0) {
            let html = '<div class="form-row">';
            data.features.forEach((feature, index) => {
                if (index > 0 && index % 2 === 0) html += '</div><div class="form-row">';
                html += `
                    <div class="form-group">
                        <label for="${feature.name}">${feature.display_name}</label>
                        <input type="${feature.type}" id="${feature.name}" name="${feature.name}"
                               placeholder="Enter ${feature.display_name.toLowerCase()}"
                               ${feature.step ? 'step="'+feature.step+'"' : ''} ${feature.type==='number'?'min="0"':''} required>
                    </div>`;
            });
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="loading-fields"><p>⚠️ No model trained yet.</p></div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="loading-fields"><p>❌ Error loading form.</p></div>';
    }
    document.getElementById('usageForm').addEventListener('submit', handleAnalyze);
}

// ============ ANALYZE ============
async function handleAnalyze(e) {
    e.preventDefault();
    const btn = document.getElementById('analyzeBtn');
    const form = document.getElementById('usageForm');
    const resultsCard = document.getElementById('resultsCard');

    const formData = new FormData(form);
    const inputData = {};
    formData.forEach((value, key) => { inputData[key] = value; });

    if (!Object.values(inputData).some(v => v !== '' && v !== null)) {
        showToast('Please fill in at least one field', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> Analyzing...';

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inputData)
        });
        const data = await response.json();

        if (!data.success && handleAuthError(data)) return;

        if (data.success) {
            displayResults(data);
            resultsCard.style.display = 'block';
            resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            showToast('Analysis complete!', 'success');
            loadStats();
            loadHistory();
            loadUsageHistory();
        } else {
            showToast(data.message || 'Analysis failed', 'error');
        }
    } catch (error) {
        showToast('Server error.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🔍</span> Analyze My Usage';
    }
}

// ============ DISPLAY RESULTS ============
function displayResults(data) {
    const { prediction, risk, suggestions, probabilities } = data;
    const score = Math.round(risk.score);
    const color = risk.color;
    const degree = (score / 100) * 360;

    document.getElementById('gaugeCircle').style.background = `conic-gradient(${color} ${degree}deg, rgba(255,255,255,0.05) ${degree}deg)`;
    animateNumber('gaugeScore', 0, score, '%', 1000);
    document.getElementById('gaugeLabel').textContent = 'Risk Score';
    document.getElementById('riskLevel').textContent = risk.level;
    document.getElementById('riskLevel').style.color = color;
    document.getElementById('predictionText').textContent = `Model Prediction: ${prediction}`;

    const probaContainer = document.getElementById('probaChartContainer');
    if (probabilities && probabilities.values && probabilities.values.length > 0) {
        probaContainer.style.display = 'block';
        renderProbaChart(probabilities);
    } else { probaContainer.style.display = 'none'; }

    currentSuggestions = suggestions;
    document.getElementById('suggestionsSection').style.display = 'block';

    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            showSuggestionTab(this.dataset.tab);
        });
    });
    showSuggestionTab('immediate');
}

function animateNumber(elementId, start, end, suffix = '', duration = 1000) {
    const element = document.getElementById(elementId);
    const range = end - start;
    const startTime = performance.now();
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        element.textContent = Math.round(start + range * eased) + suffix;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function showSuggestionTab(tabName) {
    if (!currentSuggestions) return;
    const container = document.getElementById('tabContent');
    let items = [];
    switch(tabName) {
        case 'immediate': items = currentSuggestions.immediate_actions || []; break;
        case 'daily': items = currentSuggestions.daily_habits || []; break;
        case 'longterm': items = currentSuggestions.long_term_goals || []; break;
        case 'apps': items = currentSuggestions.apps_recommended || []; break;
        case 'health': items = currentSuggestions.health_tips || []; break;
    }
    if (tabName === 'immediate' && currentSuggestions.personalized) {
        items = [...items, ...currentSuggestions.personalized];
    }
    if (items.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;">No suggestions.</p>';
        return;
    }
    container.innerHTML = items.map((item, i) =>
        `<div class="suggestion-item" style="animation:fadeInUp 0.3s ease ${i*0.05}s both">${item}</div>`
    ).join('');
}

function renderProbaChart(probabilities) {
    const ctx = document.getElementById('probaChart').getContext('2d');
    if (chartInstances['proba']) chartInstances['proba'].destroy();
    const labels = probabilities.labels.length > 0 ? probabilities.labels : probabilities.values.map((_,i) => `Class ${i}`);
    const colors = ['#27ae60','#f39c12','#e74c3c','#3498db','#9b59b6','#1abc9c'];
    chartInstances['proba'] = new Chart(ctx, {
        type:'bar',
        data: { labels, datasets: [{ label:'Probability', data:probabilities.values.map(v=>(v*100).toFixed(1)), backgroundColor:colors.slice(0,labels.length).map(c=>c+'40'), borderColor:colors.slice(0,labels.length), borderWidth:2, borderRadius:8 }] },
        options: { responsive:true, plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>ctx.parsed.y+'%'}}}, scales:{ y:{beginAtZero:true,max:100,ticks:{color:'#a0a0cc',callback:v=>v+'%'},grid:{color:'rgba(51,51,102,0.3)'}}, x:{ticks:{color:'#a0a0cc'},grid:{display:false}} } }
    });
}

// ============ STATS ============
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        if (!data.success && handleAuthError(data)) return;
        if (data.success) {
            document.getElementById('totalPredictions').textContent = data.stats.total_predictions;
            document.getElementById('avgRisk').textContent = data.stats.average_risk_score + '%';
            const modelRes = await fetch('/api/model-info');
            const modelData = await modelRes.json();
            if (modelData.success && modelData.model_info) {
                const score = modelData.model_info.best_score;
                document.getElementById('modelAccuracy').textContent = (typeof score==='number' && score>1) ? score+'%' : (score*100).toFixed(1)+'%';
            }
            renderRiskDistChart(data.stats.risk_distribution);
        }
    } catch(e) { console.error(e); }
}

// ============ USAGE HISTORY ============
async function loadUsageHistory() {
    try {
        const response = await fetch('/api/usage-history?days=30');
        const data = await response.json();
        if (!data.success && handleAuthError(data)) return;
        if (data.success && data.history.length > 0) {
            renderScreenTimeChart(data.history);
            renderUsageDistChart(data.history);
            renderActivityChart(data.history);
        } else { renderPlaceholderCharts(); }
    } catch(e) { renderPlaceholderCharts(); }
}

function renderScreenTimeChart(history) {
    const ctx = document.getElementById('screenTimeChart').getContext('2d');
    if (chartInstances['screenTime']) chartInstances['screenTime'].destroy();
    chartInstances['screenTime'] = new Chart(ctx, {
        type:'line',
        data: { labels:history.map(h=>h.date), datasets:[
            { label:'Screen Time', data:history.map(h=>h.screen_time), borderColor:'#6c5ce7', backgroundColor:'rgba(108,92,231,0.1)', fill:true, tension:0.4, pointRadius:4 },
            { label:'Social Media', data:history.map(h=>h.social_media), borderColor:'#e74c3c', backgroundColor:'rgba(231,76,60,0.1)', fill:true, tension:0.4, pointRadius:4 },
            { label:'Gaming', data:history.map(h=>h.gaming), borderColor:'#f39c12', backgroundColor:'rgba(243,156,18,0.1)', fill:true, tension:0.4, pointRadius:4 }
        ]},
        options: { responsive:true, plugins:{legend:{labels:{color:'#a0a0cc',usePointStyle:true}}}, scales:{ y:{beginAtZero:true,ticks:{color:'#a0a0cc',callback:v=>v+'h'},grid:{color:'rgba(51,51,102,0.3)'}}, x:{ticks:{color:'#a0a0cc',maxRotation:45},grid:{display:false}} } }
    });
}

function renderUsageDistChart(history) {
    const ctx = document.getElementById('usageDistChart').getContext('2d');
    if (chartInstances['usageDist']) chartInstances['usageDist'].destroy();
    const avg = {'Screen Time':0,'Social Media':0,'Gaming':0,'Productivity':0};
    const n = history.length||1;
    history.forEach(h=>{ avg['Screen Time']+=h.screen_time; avg['Social Media']+=h.social_media; avg['Gaming']+=h.gaming; avg['Productivity']+=h.productivity; });
    Object.keys(avg).forEach(k=>avg[k]=(avg[k]/n).toFixed(1));
    chartInstances['usageDist'] = new Chart(ctx, {
        type:'doughnut',
        data: { labels:Object.keys(avg), datasets:[{ data:Object.values(avg), backgroundColor:['rgba(108,92,231,0.8)','rgba(231,76,60,0.8)','rgba(243,156,18,0.8)','rgba(39,174,96,0.8)'], borderColor:'#222244', borderWidth:3, hoverOffset:10 }] },
        options: { responsive:true, plugins:{ legend:{position:'bottom',labels:{color:'#a0a0cc',padding:15,usePointStyle:true}}, tooltip:{callbacks:{label:ctx=>ctx.label+': '+ctx.parsed+' hrs avg'}} } }
    });
}

function renderRiskDistChart(riskDist) {
    const ctx = document.getElementById('riskDistChart').getContext('2d');
    if (chartInstances['riskDist']) chartInstances['riskDist'].destroy();
    const labels = Object.keys(riskDist).length>0 ? Object.keys(riskDist) : ['No Data'];
    const values = Object.keys(riskDist).length>0 ? Object.values(riskDist) : [0];
    const colorMap = {'High Risk':'rgba(231,76,60,0.8)','Medium Risk':'rgba(243,156,18,0.8)','Low Risk':'rgba(39,174,96,0.8)'};
    chartInstances['riskDist'] = new Chart(ctx, {
        type:'pie',
        data: { labels, datasets:[{ data:values, backgroundColor:labels.map(l=>colorMap[l]||'rgba(108,92,231,0.8)'), borderColor:'#222244', borderWidth:3, hoverOffset:10 }] },
        options: { responsive:true, plugins:{ legend:{position:'bottom',labels:{color:'#a0a0cc',padding:15,usePointStyle:true}} } }
    });
}

function renderActivityChart(history) {
    const ctx = document.getElementById('activityChart').getContext('2d');
    if (chartInstances['activity']) chartInstances['activity'].destroy();
    chartInstances['activity'] = new Chart(ctx, {
        type:'bar',
        data: { labels:history.map(h=>h.date), datasets:[
            { label:'App Opens', data:history.map(h=>h.app_opens), backgroundColor:'rgba(108,92,231,0.6)', borderColor:'#6c5ce7', borderWidth:1, borderRadius:4 },
            { label:'Notifications', data:history.map(h=>h.notifications), backgroundColor:'rgba(0,206,201,0.6)', borderColor:'#00cec9', borderWidth:1, borderRadius:4 }
        ]},
        options: { responsive:true, plugins:{legend:{labels:{color:'#a0a0cc',usePointStyle:true}}}, scales:{ y:{beginAtZero:true,ticks:{color:'#a0a0cc'},grid:{color:'rgba(51,51,102,0.3)'}}, x:{ticks:{color:'#a0a0cc',maxRotation:45},grid:{display:false}} } }
    });
}

function renderPlaceholderCharts() {
    const s = [
        {date:'Day 1',screen_time:5.2,social_media:2.1,gaming:1.5,productivity:0.8,app_opens:65,notifications:90},
        {date:'Day 2',screen_time:6.1,social_media:3.0,gaming:1.2,productivity:0.5,app_opens:80,notifications:110},
        {date:'Day 3',screen_time:4.5,social_media:1.8,gaming:0.8,productivity:1.2,app_opens:50,notifications:75},
        {date:'Day 4',screen_time:7.3,social_media:3.5,gaming:2.0,productivity:0.3,app_opens:95,notifications:140},
        {date:'Day 5',screen_time:3.8,social_media:1.5,gaming:0.5,productivity:1.5,app_opens:40,notifications:60}
    ];
    renderScreenTimeChart(s); renderUsageDistChart(s); renderActivityChart(s);
    renderRiskDistChart({'Low Risk':2,'Medium Risk':2,'High Risk':1});
}

// ============ HISTORY ============
async function loadHistory() {
    try {
        const response = await fetch('/api/history?limit=50');
        const data = await response.json();
        if (!data.success && handleAuthError(data)) return;
        const tbody = document.getElementById('historyBody');
        if (data.success && data.history.length > 0) {
            tbody.innerHTML = data.history.map((item,i) => {
                const date = new Date(item.timestamp).toLocaleString();
                const riskClass = item.risk_level.toLowerCase().includes('high')?'risk-high':item.risk_level.toLowerCase().includes('medium')?'risk-medium':'risk-low';
                return `<tr><td>${data.history.length-i}</td><td>${date}</td><td><strong>${item.prediction}</strong></td><td><span class="risk-badge ${riskClass}">${item.risk_level}</span></td><td>${item.risk_score.toFixed(1)}%</td><td>${item.model_name||'-'}</td></tr>`;
            }).join('');
        } else { tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No history yet. Make your first analysis! 📊</td></tr>'; }
    } catch(e) { console.error(e); }
}

async function clearHistory() {
    if (!confirm('Clear all your history?')) return;
    try {
        const response = await fetch('/api/clear-history', {method:'DELETE'});
        const data = await response.json();
        if (data.success) { showToast('History cleared','success'); loadHistory(); loadStats(); loadUsageHistory(); }
        else showToast('Failed','error');
    } catch(e) { showToast('Error','error'); }
}

// ============ MODEL INFO ============
async function loadModelInfo() {
    try {
        const response = await fetch('/api/model-info');
        const data = await response.json();
        if (!data.success && handleAuthError(data)) return;
        const container = document.getElementById('currentModelInfo');
        if (data.success && data.model_info) {
            const info = data.model_info;
            let html = `
                <div class="model-stat"><span class="model-stat-label">Model</span><span class="model-stat-value">${info.model_name}</span></div>
                <div class="model-stat"><span class="model-stat-label">Type</span><span class="model-stat-value">${info.problem_type}</span></div>
                <div class="model-stat"><span class="model-stat-label">Score</span><span class="model-stat-value">${typeof info.best_score==='number'&&info.best_score>1?info.best_score+'%':info.best_score}</span></div>
                <div class="model-stat"><span class="model-stat-label">Features</span><span class="model-stat-value">${info.features?info.features.length:'?'}</span></div>
                <div class="model-stat"><span class="model-stat-label">Target</span><span class="model-stat-value">${info.target||'-'}</span></div>`;
            if (info.total_training_time) html += `<div class="model-stat"><span class="model-stat-label">Training Time</span><span class="model-stat-value">${info.total_training_time}</span></div>`;
            if (info.results) {
                html += '<h4 style="margin-top:20px;margin-bottom:10px;font-size:1rem;">📊 All Models:</h4>';
                for (const [name,metrics] of Object.entries(info.results)) {
                    const isWinner = name===info.model_name;
                    html += `<div class="model-stat" style="${isWinner?'background:rgba(108,92,231,0.1);padding:8px;border-radius:8px;':''}"><span class="model-stat-label">${isWinner?'🏆 ':''}${name}</span><span class="model-stat-value">${metrics.accuracy?metrics.accuracy+'%':metrics.r2_score?'R²: '+metrics.r2_score:'-'}${metrics.training_time?' ('+metrics.training_time+')':''}</span></div>`;
                }
            }
            if (info.features && info.features.length>0) {
                html += '<h4 style="margin-top:20px;margin-bottom:10px;font-size:1rem;">📋 Features:</h4><div style="display:flex;flex-wrap:wrap;gap:6px;">';
                info.features.forEach(f => { html += `<span style="background:var(--darker);padding:4px 10px;border-radius:20px;font-size:0.8rem;color:var(--text-secondary)">${f.replace(/_/g,' ')}</span>`; });
                html += '</div>';
            }
            container.innerHTML = html;
        } else { container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;">No model trained yet.</p>'; }
    } catch(e) { console.error(e); }
}

// ============ FILE UPLOAD ============
function initUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('datasetFile');
    const fileName = document.getElementById('fileName');

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault(); uploadArea.classList.remove('drag-over');
        if (e.dataTransfer.files.length>0) { fileInput.files=e.dataTransfer.files; fileName.textContent='📄 '+e.dataTransfer.files[0].name; }
    });
    fileInput.addEventListener('change', () => { if (fileInput.files.length>0) fileName.textContent='📄 '+fileInput.files[0].name; });

    document.getElementById('trainForm').addEventListener('submit', handleTrain);
}

async function handleTrain(e) {
    e.preventDefault();
    const fileInput = document.getElementById('datasetFile');
    const trainBtn = document.getElementById('trainBtn');
    const status = document.getElementById('trainingStatus');
    const results = document.getElementById('modelResults');

    if (!fileInput.files || fileInput.files.length===0) { showToast('Select a CSV file first','warning'); return; }

    const formData = new FormData();
    formData.append('dataset', fileInput.files[0]);
    const targetCol = document.getElementById('targetColumn').value;
    if (targetCol) formData.append('target_column', targetCol);

    trainBtn.disabled = true; status.style.display='block'; results.style.display='none';

    try {
        const response = await fetch('/api/train', { method:'POST', body:formData });
        const data = await response.json();
        if (data.success) {
            showToast('Model trained! 🎉','success');
            results.style.display = 'block';
            const info = data.model_info;
            document.getElementById('modelResultsContent').innerHTML = `
                <div class="model-stat"><span class="model-stat-label">Best Model</span><span class="model-stat-value">${info.model_name}</span></div>
                <div class="model-stat"><span class="model-stat-label">Score</span><span class="model-stat-value">${typeof info.best_score==='number'&&info.best_score>1?info.best_score+'%':info.best_score}</span></div>
                <div class="model-stat"><span class="model-stat-label">Time</span><span class="model-stat-value">${info.total_training_time||'-'}</span></div>
                <div class="model-stat"><span class="model-stat-label">Features</span><span class="model-stat-value">${info.features?info.features.length:'?'}</span></div>`;
            loadFeatures(); loadModelInfo(); loadStats();
        } else showToast(data.message||'Training failed','error');
    } catch(e) { showToast('Error training model','error'); }
    finally { trainBtn.disabled=false; status.style.display='none'; }
}