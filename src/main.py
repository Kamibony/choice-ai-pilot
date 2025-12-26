from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from src.scraper import scrape_site
from src.analyzer import analyze_content

app = FastAPI()

# --- Dátový Model ---
class AuditRequest(BaseModel):
    url: str
    client_name: str
    industry: str
    goals: str  # TOTO JE NOVÉ: Detailný popis identity

# --- FRONTEND ---
HTML_APP = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CHOICE AI | Reputation Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .gradient-text { background: linear-gradient(45deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .loader { border-top-color: #3b82f6; -webkit-animation: spinner 1.5s linear infinite; animation: spinner 1.5s linear infinite; }
        @keyframes spinner { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="min-h-screen flex flex-col items-center py-10 px-4">

    <div class="text-center mb-10">
        <h1 class="text-5xl font-bold mb-2"><span class="gradient-text">CHOICE AI</span> Perception</h1>
        <p class="text-slate-400">Ako vidí AI vašu značku?</p>
    </div>

    <div class="w-full max-w-5xl grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <div class="md:col-span-1 glass p-6 rounded-2xl h-fit">
            <h2 class="text-xl font-semibold mb-4 border-b border-slate-600 pb-2">Definícia Značky</h2>
            <form id="auditForm" class="space-y-4">
                <div>
                    <label class="block text-xs text-blue-400 uppercase font-bold mb-1">Meno Entity (Presne)</label>
                    <input type="text" id="client_name" required placeholder="Napr. Česká zemědělská univerzita" class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 outline-none text-white text-sm">
                    <p class="text-[10px] text-slate-500 mt-1">Musí byť presný názov, aby ho AI spoznala.</p>
                </div>
                <div>
                    <label class="block text-xs text-slate-400 uppercase font-bold mb-1">URL Webu</label>
                    <input type="url" id="url" required placeholder="https://..." class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 outline-none text-white text-sm">
                </div>
                <div>
                    <label class="block text-xs text-slate-400 uppercase font-bold mb-1">Segment</label>
                    <select id="industry" class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 text-sm text-white">
                        <option value="Education">Vzdelávanie / Univerzita</option>
                        <option value="E-commerce">E-commerce</option>
                        <option value="SaaS">SaaS / Tech</option>
                        <option value="Services">Služby</option>
                    </select>
                </div>
                
                <div>
                    <label class="block text-xs text-green-400 uppercase font-bold mb-1">Cieľová Identita (Čo chcete byť?)</label>
                    <textarea id="goals" rows="4" required placeholder="Napr: Sme moderná technologická univerzita zameraná na AI a inovácie. Nechceme byť vnímaní len ako 'hnojáreň'." class="w-full bg-slate-800 border border-slate-600 rounded-lg p-2 focus:ring-2 focus:ring-green-500 outline-none text-white text-sm"></textarea>
                </div>

                <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-bold py-3 rounded-xl transition transform hover:scale-105 shadow-lg mt-4">
                    <i class="fas fa-brain mr-2"></i> Zistiť názor AI
                </button>
            </form>
        </div>

        <div class="md:col-span-2 glass p-6 rounded-2xl min-h-[500px] relative">
            
            <div id="loader" class="hidden absolute inset-0 flex flex-col items-center justify-center bg-slate-900/90 rounded-2xl z-20">
                <div class="loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-12 w-12 mb-4"></div>
                <p class="text-blue-400 animate-pulse font-mono">Pýtam sa Gemini 2.5 Pro na vašu reputáciu...</p>
            </div>

            <div id="emptyState" class="flex flex-col items-center justify-center h-full text-slate-500">
                <i class="fas fa-robot text-6xl mb-4 opacity-50"></i>
                <p>Vyplňte formulár a zistite, či vás AI pozná.</p>
            </div>

            <div id="results" class="hidden space-y-6">
                <div class="flex justify-between items-start border-b border-slate-700 pb-4">
                    <div>
                        <h2 class="text-2xl font-bold text-white" id="res_title">--</h2>
                        <div class="text-sm text-slate-400 mt-1">Identita podľa AI (Gemini Memory)</div>
                    </div>
                    <div class="text-center bg-slate-800 p-3 rounded-lg border border-slate-600">
                        <span class="block text-[10px] text-slate-400 uppercase tracking-wider">AI Autorita</span>
                        <span class="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-blue-500" id="res_score">--</span>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-blue-900/20 p-4 rounded-xl border border-blue-500/30">
                        <div class="flex items-center mb-2">
                            <i class="fas fa-brain text-blue-400 mr-2"></i>
                            <span class="text-xs font-bold text-blue-400 uppercase">Aktuálne vnímanie AI</span>
                        </div>
                        <p class="text-sm text-slate-300" id="perception_text">--</p>
                    </div>
                    
                    <div class="bg-purple-900/20 p-4 rounded-xl border border-purple-500/30">
                         <div class="flex items-center mb-2">
                            <i class="fas fa-globe text-purple-400 mr-2"></i>
                            <span class="text-xs font-bold text-purple-400 uppercase">Web vs. Ciele</span>
                        </div>
                        <p class="text-sm text-slate-300" id="reality_text">--</p>
                    </div>
                </div>

                <div>
                    <h3 class="text-sm font-bold text-slate-400 uppercase mb-3">Detailné Postrehy</h3>
                    <div id="insights_list" class="space-y-3"></div>
                </div>

                <div class="bg-slate-800 p-4 rounded-xl border-l-4 border-green-500">
                    <h4 class="text-green-400 font-bold mb-1 text-sm"><i class="fas fa-magic mr-2"></i>AI Optimalizácia</h4>
                    <p class="text-sm text-slate-300 italic" id="res_rec">--</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('auditForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const loader = document.getElementById('loader');
            const emptyState = document.getElementById('emptyState');
            const results = document.getElementById('results');
            
            loader.classList.remove('hidden');
            emptyState.classList.add('hidden');
            results.classList.add('hidden');

            const payload = {
                url: document.getElementById('url').value,
                client_name: document.getElementById('client_name').value,
                industry: document.getElementById('industry').value,
                goals: document.getElementById('goals').value // Odosielame nový input
            };

            try {
                const response = await fetch('/audit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) throw new Error('Chyba komunikácie');

                const data = await response.json();
                renderResults(data);

            } catch (error) {
                alert("Chyba: " + error.message);
                emptyState.classList.remove('hidden');
            } finally {
                loader.classList.add('hidden');
            }
        });

        function renderResults(data) {
            const r = document.getElementById('results');
            r.classList.remove('hidden');

            document.getElementById('res_title').innerText = data.summary.page_title;
            document.getElementById('res_score').innerText = data.summary.overall_score + "/100";
            
            // Mapovanie špecifických polí z nového promptu
            // Prvý insight použijeme ako "Vnímanie AI"
            if(data.insights.length > 0) {
                document.getElementById('perception_text').innerText = data.insights[0].message;
            }
            // Druhý insight použijeme ako "Reality Check"
            if(data.insights.length > 1) {
                document.getElementById('reality_text').innerText = data.insights[1].message;
            }

            document.getElementById('res_rec').innerText = data.recommendation;

            const list = document.getElementById('insights_list');
            list.innerHTML = '';
            
            // Zobrazíme len 3. insight a ďalšie, aby sme neopakovali to isté
            data.insights.slice(2).forEach(insight => {
                let color = insight.type === 'warning' ? 'text-yellow-400' : 'text-blue-400';
                list.innerHTML += `
                    <div class="bg-slate-800/50 p-3 rounded border border-slate-700">
                        <div class="font-bold text-xs ${color} mb-1 uppercase">${insight.title}</div>
                        <div class="text-sm text-slate-300">${insight.message}</div>
                    </div>
                `;
            });
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTML_APP

@app.post("/audit")
async def perform_audit(request: AuditRequest):
    scraped_data = await scrape_site(request.url)
    if not scraped_data:
        raise HTTPException(status_code=400, detail="Could not scrape URL")
    
    result = analyze_content(scraped_data, request.dict())
    return result
