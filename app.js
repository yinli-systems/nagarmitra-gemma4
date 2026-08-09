const state = { caseId: "garbage_overflow", language: "hi", data: null, running: false };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const fallback = {
  garbage_overflow: {
    issue: "Overflowing waste", issue_hi: "कूड़ा जमा है", confidence: .94, urgency: "today",
    department: "Municipal sanitation", department_hi: "नगर सफाई विभाग",
    summary: "Overflowing mixed waste beside a public lane near a school boundary.", summary_hi: "स्कूल की सीमा के पास सार्वजनिक रास्ते के किनारे मिला-जुला कूड़ा जमा है।",
    reason: "Standing waste can attract pests and contaminate nearby drains.", reason_hi: "जमा कूड़ा कीटों को आकर्षित कर सकता है और नालियों को दूषित कर सकता है।",
    ticket_id: "NM-PRY-2026-0809-0042", checklist: ["Photograph the full location and one close-up", "Record the nearest landmark without exposing a person's face", "Do not touch unknown waste or sharps"],
    sources: [{title: "Swachh Bharat Mission — Urban", url: "https://mohua.gov.in/cms/swachh-bharat-mission.php"}, {title: "Prayagraj Municipal Corporation", url: "https://prayagrajmc.gov.in/"}],
    steps: [{tool:"classify_issue",label:"Classifying the report",detail:"Gemma 4 · text + image understanding"},{tool:"lookup_department",label:"Finding a responsible desk",detail:"Local knowledge base · 2 source records"},{tool:"draft_complaint",label:"Drafting a bilingual action card",detail:"Gemma 4 · Hindi + English"},{tool:"safety_review",label:"Applying safety and privacy checks",detail:"No diagnosis · no fabricated contact · human review"}]
  }
};

async function loadData() {
  try {
    const [trace, knowledge] = await Promise.all([fetch("data/demo_trace.json").then(r => r.json()), fetch("data/knowledge.json").then(r => r.json())]);
    state.data = trace;
    state.knowledge = knowledge;
  } catch (error) {
    state.data = fallback;
    state.knowledge = {};
  }
  renderCard();
  renderTrace(false);
}

function currentCase() { return state.data?.[state.caseId] || fallback.garbage_overflow; }
function localized(item, key) { return state.language === "hi" && item[`${key}_hi`] ? item[`${key}_hi`] : item[key]; }
function urgencyLabel(value) { return state.language === "hi" ? ({today:"आज", "this week":"इस सप्ताह", "immediate review":"तुरंत जांच"}[value] || value) : value[0].toUpperCase() + value.slice(1); }

function renderCard() {
  const item = currentCase();
  $("#issueLabel").textContent = localized(item, "issue");
  $("#confidenceValue").textContent = `${Math.round(item.confidence * 100)}%`;
  $("#urgencyValue").textContent = urgencyLabel(item.urgency);
  $("#summaryText").textContent = localized(item, "summary");
  $("#reasonText").textContent = localized(item, "reason");
  $("#departmentValue").textContent = state.language === "hi" ? item.department_hi : item.department;
  $("#departmentHindi").textContent = state.language === "hi" ? item.department : item.department_hi;
  $("#checklist").innerHTML = item.checklist.map(x => `<li>${x}</li>`).join("");
  $("#sourceList").innerHTML = item.sources.map(x => `<a class="source-link" href="${x.url}" target="_blank" rel="noreferrer">${x.title}</a>`).join("");
}

function renderTrace(running, completed = true) {
  const item = currentCase();
  const steps = item.steps || fallback.garbage_overflow.steps;
  $("#traceSteps").innerHTML = steps.map((step, index) => `<div class="trace-step ${running && index === 0 ? "active" : ""}" data-step="${index}"><span class="step-index">${index + 1}</span><span><b>${step.label}</b><small>${step.detail}</small></span><span class="step-state">${completed ? "✓" : "…"}</span></div>`).join("");
}

function selectCase(id) {
  state.caseId = id;
  $$(".case-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.case === id));
  const prompts = {
    garbage_overflow: "कूड़ा तीन दिन से नहीं उठा है और नाली बंद हो रही है।",
    broken_streetlight: "यह स्ट्रीट लाइट कई रातों से बंद है, बाजार लौटने वाले लोग अंधेरे में चलते हैं।",
    unsafe_water: "साझे नल के पानी का रंग और गंध आज अलग लग रही है।"
  };
  $("#reportText").value = prompts[id];
  renderCard(); renderTrace(false);
  $("#runStatus").textContent = "READY";
  $("#traceIntro").textContent = "Gemma 4 is ready to inspect the report and call only approved local tools.";
  $("#queueMessage").textContent = "";
}

async function analyze() {
  if (state.running) return;
  state.running = true;
  const button = $("#analyzeButton");
  button.disabled = true; button.querySelector("span:nth-child(2)").textContent = "Running approved tools…";
  $("#runStatus").textContent = "RUNNING";
  $("#traceIntro").textContent = "Gemma 4 is reading the report, then routing through the allow-listed civic tools.";
  renderTrace(true, false);
  const steps = $$(".trace-step");
  for (let i = 0; i < steps.length; i++) {
    steps.forEach((el, j) => el.classList.toggle("active", j === i));
    steps[i].querySelector(".step-state").textContent = "…";
    await new Promise(resolve => setTimeout(resolve, 460));
    steps[i].querySelector(".step-state").textContent = "✓";
  }
  steps.forEach(el => el.classList.remove("active"));
  renderCard();
  $("#runStatus").textContent = "COMPLETE";
  $("#traceIntro").textContent = "Action card prepared. The final handoff stays with the resident.";
  $("#queueMessage").textContent = `Draft ${currentCase().ticket_id} is ready for review.`;
  button.disabled = false; button.querySelector("span:nth-child(2)").textContent = "Analyze with Gemma 4";
  state.running = false;
}

function downloadDraft() {
  const item = currentCase();
  const draft = { ticket_id: item.ticket_id, issue: localized(item, "issue"), report: $("#reportText").value, place: $("#placeInput").value, department: state.language === "hi" ? item.department_hi : item.department, urgency: urgencyLabel(item.urgency), sources: item.sources, human_review_required: true };
  const blob = new Blob([JSON.stringify(draft, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `${item.ticket_id}.json`; link.click(); URL.revokeObjectURL(url);
  $("#queueMessage").textContent = "A local JSON copy was downloaded — no network request was made.";
}

function saveQueue() {
  const count = Number($("#queueCount").textContent || 0) + 1;
  $("#queueCount").textContent = count;
  $("#queueMessage").textContent = `Saved ${currentCase().ticket_id} to the device queue. Submit only after checking it yourself.`;
}

$$(".case-btn").forEach(btn => btn.addEventListener("click", () => selectCase(btn.dataset.case)));
$$(".lang-btn").forEach(btn => btn.addEventListener("click", () => { state.language = btn.dataset.language; $$(".lang-btn").forEach(x => x.classList.toggle("active", x === btn)); renderCard(); }));
$("#analyzeButton").addEventListener("click", analyze);
$("#downloadButton").addEventListener("click", downloadDraft);
$("#queueButton").addEventListener("click", saveQueue);
$("#reviewCheck").addEventListener("change", (event) => { $("#queueButton").disabled = !event.target.checked; });
$("#photoInput").addEventListener("change", (event) => { const file = event.target.files?.[0]; if (file) { $("#photoPreview").src = URL.createObjectURL(file); $(".upload-overlay b").textContent = file.name; $(".upload-overlay small").textContent = "Local evidence selected"; } });
loadData();
