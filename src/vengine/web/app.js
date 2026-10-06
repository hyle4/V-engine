const main = document.querySelector("#main");
const state = {
  view: "practice",
  items: [],
  dueItems: [],
  hasMore: false,
  mode: "all",
  index: 0,
  item: null,
  selected: null,
  submitted: false,
  bookletId: "",
  bookletTitle: "",
  catalogId: "",
  indexOpen: false,
  libraryYear: "",
  libraryFilters: [],
  review: [],
  reviewIndex: 0,
  reviewPage: 0,
  reviewCollection: "",
  reviewTotal: 0,
  reviewQueueOpen: false,
  collections: [],
  providers: { gemini: false, agy: false },
  projectInfo: { configured: false, editable: false, project: null },
  projectOptions: { formats: [], proposers: ["builtin"] },
};
const COPY = {
  en: {
    navPractice: "Practice", navLibrary: "Library", navReview: "Review", navImport: "Import", navProject: "Project",
    appearance: "Appearance", font: "Font", size: "Size", width: "Width", readingDefault: "Default",
    theme: "Theme", goTo: "Go to", examInstructions: "Exam instructions",
    narrow: "Narrow", standard: "Standard", years: "Years", provas: "Exams", allFilters: "All",
    noBooklets: "No exams in this year.", backToExams: "Exams", chooseFileNamed: "Choose a file",
    unsolved: "Unsolved", wrong: "Wrong", starred: "Saved", correctCount: "correct",
    chooseProva: "Choose an exam", index: "Index", light: "Light", dark: "Dark",
    projectSettings: "Project settings", projectConfigure: "Start V-engine with --project to configure this workspace.",
    project: "Project", setupProject: "Set up your project", name: "Name", language: "Language", saveProject: "Save project",
    nothingDue: "Nothing due", allExercises: "All exercises", awaitingReview: "awaiting review",
    noExercises: "No exercises yet", importSource: "Import a source", all: "All", due: "Due",
    answerChoices: "Answer choices", checkAnswer: "Check answer", next: "Next", save: "Save", saved: "Saved",
    hideSource: "Hide source text", showSource: "Show source text", editShared: "Edit question and shared text",
    openSource: "Open source", page: "page", sourceReference: "Source reference",
    library: "Library", searchExercises: "Search exercises", createExercise: "Create exercise",
    importSourceBtn: "Import source", noExercisesFound: "No exercises found.", loadMore: "Load more exercises",
    subject: "Subject", prompt: "Prompt", interaction: "Interaction", choice: "Choice", shortText: "Short text",
    openResponse: "Open response", sendReview: "Send to review", optionsLine: "Options, one per line",
    answerOrQuery: "Answer or reference query", writePrompt: "Write a prompt first", twoOptions: "Add at least two options",
    exerciseCreated: "Exercise created for review", collection: "Collection", allCollections: "All collections",
    noProposals: "No proposals here", reviewClear: "Review is clear", queue: "Queue", discardSelected: "Discard selected",
    options: "Options", answerKey: "Answer key", source: "Source", noCitation: "No citation",
    sharedText: "Shared text", title: "Title", text: "Text", saveText: "Save text", approveText: "Approve text",
    saveChanges: "Save changes", approvePractice: "Approve for practice", reviewExercise: "Review exercise",
    sourcePage: "Source page", sharedSaved: "Shared text saved for review", sharedApproved: "Shared text approved",
    newRevision: "New revision saved", saveBeforeApproval: "Save changes before approval",
    approvedPractice: "Approved for practice", useCE: "Use C, E, true, or false.",
    importTitle: "Import", type: "Type", originalExam: "Original exam", studySource: "Study source",
    sourceFile: "Source file", answerKeyFile: "Answer key", generateAI: "Generate with AI", provider: "Provider",
    importForReview: "Import for review", chooseFile: "Choose a file first", importing: "Importing source…",
    importFailed: "Import failed", cancel: "Cancel", importCancelled: "Import cancelled",
    sentToReview: "sent to review.", openReview: "Open review", sourceSaved: "Source saved. No exercises proposed.",
    importComplete: "Import complete", chooseAnswer: "Choose or enter an answer first", attemptSaved: "Attempt saved",
    sampleAnswer: "Sample answer", howWell: "How well did you do?", again: "Again", hard: "Hard", good: "Good", easy: "Easy",
    reviewScheduled: "Review scheduled", yourAnswer: "Your answer", writeAnswer: "Write your answer",
    choose: "Choose", chooseMatch: "Choose a match", part: "Part",
    zoomImage: "Zoom image", zoomIn: "Zoom in", zoomOut: "Zoom out", close: "Close",
  },
  "pt-BR": {
    navPractice: "Praticar", navLibrary: "Acervo", navReview: "Revisão", navImport: "Importar", navProject: "Projeto",
    appearance: "Aparência", font: "Fonte", size: "Tamanho", width: "Largura", readingDefault: "Padrão",
    theme: "Tema", goTo: "Ir para", examInstructions: "Instruções da prova",
    narrow: "Estreita", standard: "Padrão", years: "Anos", provas: "Provas", allFilters: "Todas",
    noBooklets: "Nenhuma prova neste ano.", backToExams: "Provas", chooseFileNamed: "Escolher arquivo",
    unsolved: "Não feitas", wrong: "Erros", starred: "Salvas", correctCount: "corretas",
    chooseProva: "Escolher prova", index: "Índice", light: "Claro", dark: "Escuro",
    projectSettings: "Projeto", projectConfigure: "Inicie o V-engine com --project para configurar este espaço.",
    project: "Projeto", setupProject: "Configure o projeto", name: "Nome", language: "Idioma", saveProject: "Salvar projeto",
    nothingDue: "Nada pendente", allExercises: "Todos os exercícios", awaitingReview: "aguardando revisão",
    noExercises: "Nenhum exercício", importSource: "Importar uma fonte", all: "Tudo", due: "Devidos",
    answerChoices: "Alternativas", checkAnswer: "Conferir", next: "Próxima", save: "Salvar", saved: "Salvo",
    hideSource: "Ocultar texto", showSource: "Mostrar texto", editShared: "Editar questão e texto compartilhado",
    openSource: "Abrir fonte", page: "página", sourceReference: "Referência da fonte",
    library: "Acervo", searchExercises: "Buscar exercícios", createExercise: "Criar exercício",
    importSourceBtn: "Importar fonte", noExercisesFound: "Nenhum exercício encontrado.", loadMore: "Carregar mais",
    subject: "Matéria", prompt: "Enunciado", interaction: "Interação", choice: "Escolha", shortText: "Texto curto",
    openResponse: "Resposta aberta", sendReview: "Enviar para revisão", optionsLine: "Alternativas, uma por linha",
    answerOrQuery: "Resposta ou consulta de referência", writePrompt: "Escreva um enunciado", twoOptions: "Inclua ao menos duas alternativas",
    exerciseCreated: "Exercício enviado para revisão", collection: "Coleção", allCollections: "Todas as coleções",
    noProposals: "Nada nesta coleção", reviewClear: "Revisão em dia", queue: "Fila", discardSelected: "Descartar seleção",
    options: "Alternativas", answerKey: "Gabarito", source: "Fonte", noCitation: "Sem citação",
    sharedText: "Texto compartilhado", title: "Título", text: "Texto", saveText: "Salvar texto", approveText: "Aprovar texto",
    saveChanges: "Salvar alterações", approvePractice: "Aprovar para prática", reviewExercise: "Revisar exercício",
    sourcePage: "Página original", sharedSaved: "Texto salvo para revisão", sharedApproved: "Texto aprovado",
    newRevision: "Nova revisão salva", saveBeforeApproval: "Salve as alterações antes de aprovar",
    approvedPractice: "Aprovado para prática", useCE: "Use C, E, true ou false.",
    importTitle: "Importar", type: "Tipo", originalExam: "Prova original", studySource: "Fonte de estudo",
    sourceFile: "Arquivo", answerKeyFile: "Gabarito", generateAI: "Gerar com IA", provider: "Provedor",
    importForReview: "Importar para revisão", chooseFile: "Escolha um arquivo", importing: "Importando…",
    importFailed: "Falha na importação", cancel: "Cancelar", importCancelled: "Importação cancelada",
    sentToReview: "enviados para revisão.", openReview: "Abrir revisão", sourceSaved: "Fonte salva. Nenhum exercício proposto.",
    importComplete: "Importação concluída", chooseAnswer: "Escolha ou escreva uma resposta", attemptSaved: "Tentativa salva",
    sampleAnswer: "Resposta modelo", howWell: "Como você se saiu?", again: "De novo", hard: "Difícil", good: "Bom", easy: "Fácil",
    reviewScheduled: "Revisão agendada", yourAnswer: "Sua resposta", writeAnswer: "Escreva a resposta",
    choose: "Escolha", chooseMatch: "Escolha o par", part: "Parte",
    zoomImage: "Ampliar imagem", zoomIn: "Aumentar", zoomOut: "Diminuir", close: "Fechar",
  },
};
function locale() {
  const value = state.projectInfo.project?.locale;
  return COPY[value] ? value : "en";
}
function t(key) {
  return COPY[locale()][key] || COPY.en[key] || key;
}
const READING_FONTS = ["", "JetBrainsMono Nerd Font", "iA Writer Mono S", "Adwaita Mono", "Liberation Sans"];
function applyChrome() {
  document.documentElement.lang = locale();
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-label]").forEach((node) => {
    const label = [...node.childNodes].find((child) => child.nodeType === Node.TEXT_NODE);
    if (label) label.textContent = t(node.dataset.i18nLabel);
  });
  document.querySelectorAll("[data-aria]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.aria));
  });
  const configured = Boolean(state.projectInfo.configured && state.projectInfo.project);
  const study = studyShell();
  document.querySelector("#nav-project").hidden = study || (configured && state.projectInfo.project.show_project === false);
  for (const view of ["practice", "library", "review", "import"]) {
    document.querySelector(`[data-view="${view}"]`).hidden = study;
  }
  if (study && state.view === "settings") state.view = "practice";
  updateProva();
  applyAppearance();
}
function studyShell() {
  return state.projectInfo.project?.show_project === false;
}
function updateProva() {
  const button = document.querySelector("#prova");
  button.hidden = !studyShell();
  button.textContent = state.bookletTitle || t("chooseProva");
}
function storedAppearance() {
  try {
    return JSON.parse(localStorage.getItem("vengine-appearance") || "null");
  } catch {
    return null;
  }
}
function appearanceChoice() {
  const project = state.projectInfo.project || {};
  const stored = storedAppearance() || {};
  return {
    font: stored.font ?? project.font ?? "",
    text_size: stored.text_size || project.text_size || "md",
    reading_width: stored.reading_width || project.reading_width || "standard",
  };
}
function applyAppearance() {
  const choice = appearanceChoice();
  const font = READING_FONTS.includes(choice.font) ? choice.font : "";
  document.documentElement.dataset.font = font;
  document.documentElement.dataset.size = ["xs", "sm", "md", "lg"].includes(choice.text_size) ? choice.text_size : "md";
  document.documentElement.dataset.reading = choice.reading_width === "narrow" ? "narrow" : "standard";
}
async function saveAppearance(partial) {
  const next = { ...appearanceChoice(), ...partial };
  localStorage.setItem("vengine-appearance", JSON.stringify(next));
  applyAppearance();
  const project = state.projectInfo.project;
  if (!state.projectInfo.editable || !project) return;
  const updated = {
    ...project,
    font: next.font,
    text_size: next.text_size,
    reading_width: next.reading_width,
    locale: partial.locale || project.locale,
  };
  state.projectInfo = await request("PUT", "/project", updated);
  applyChrome();
}
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
const text = (blocks) => (blocks || []).map((b) => b.text || "").join("\n\n");
function imageSource(block) {
  if (block.kind !== "image") return "";
  if (block.asset_id)
    return `/api/sources/${encodeURIComponent(block.asset_id)}/file`;
  if (block.source?.source_id && block.source.page)
    return `/api/sources/${encodeURIComponent(block.source.source_id)}/render/${block.source.page}`;
  return "";
}
function isScoreNote(value) {
  const line = String(value || "").replace(/\s+/g, " ").trim();
  if (!line) return false;
  return /^(?:extens[aã]o (?:m[aá]xima|do texto)|maximum length|\[valor\s*:|\[value\s*:)/i.test(line);
}
function reflowLines(value) {
  const lines = String(value || "").split(/\n/).map((line) => line.trim()).filter(Boolean);
  const merged = [];
  for (const line of lines) {
    const previous = merged[merged.length - 1];
    const numbered = /^\d{1,2}\s+\S/.test(line);
    const bullet = /^[•]/.test(line);
    const continues = previous && !numbered && !bullet && /^[a-záàâãéêíóôõúüç]/.test(line) && !/[.!?:;]$/.test(previous);
    if (continues) merged[merged.length - 1] = `${previous} ${line}`;
    else merged.push(line);
  }
  return merged;
}
function peelScore(line) {
  const match = String(line || "").match(/\s*(\[(?:valor|value)\s*:[^\]]+\])\s*$/i);
  if (!match) return { text: line, note: "" };
  const text = line.slice(0, match.index).trim();
  if (!text) return { text: "", note: match[1] };
  return { text, note: match[1] };
}
function isCommandLine(value) {
  const line = String(value || "").replace(/\s+/g, " ").trim();
  if (!line || line.length > 220) return false;
  return /^(texto para|espa[cç]o livre|about the previous|quest[aã]o\b|acerca d|sabendo que|em economias|em relação ao|considerando |relativamente |no que se refere|a respeito d|tendo em vista|a partir do texto|julgue os itens)/i.test(line);
}
function renderPromptText(value) {
  const chunks = [];
  let paragraph = [];
  const flush = () => {
    const line = paragraph.join(" ").trim();
    paragraph = [];
    if (!line) return;
    const peeled = peelScore(line);
    if (peeled.text) chunks.push(`<p class="prompt-part">${esc(peeled.text)}</p>`);
    if (peeled.note) chunks.push(`<p class="prompt-note">${esc(peeled.note)}</p>`);
  };
  for (const line of reflowLines(value)) {
    if (isScoreNote(line)) {
      flush();
      chunks.push(`<p class="prompt-note">${esc(line)}</p>`);
      continue;
    }
    if (/^[•]/.test(line) || /^\d{1,2}\s+\S/.test(line)) flush();
    paragraph.push(line);
  }
  flush();
  return chunks.join("");
}
function renderQuestion(item) {
  const parts = Array.isArray(item.organization)
    ? item.organization.filter((part) => String(part.text || "").trim())
    : [];
  const task = parts.filter((part) => part.role === "task");
  if (!task.length || parts.length < 2) return content(item.prompt);
  const instructions = parts.filter((part) => part.role === "instructions");
  const scoring = parts.filter((part) => part.role === "scoring");
  const shortScore = (part) => String(part.text || "").replace(/\s+/g, " ").trim().length <= 220;
  const notes = [...instructions, ...scoring.filter((part) => !shortScore(part))];
  const banners = parts.filter((part) => part.role === "banner" || part.role === "heading");
  const stimulus = parts.filter((part) => part.role === "stimulus");
  const note = notes.length
    ? `<details class="prompt-instructions"><summary>${esc(t("examInstructions"))}</summary>${notes.map((part) => renderPromptText(part.text)).join("")}</details>`
    : "";
  const banner = banners.map((part) => `<p class="prompt-banner">${esc(part.text.replace(/\s+/g, " ").trim())}</p>`).join("");
  const quote = stimulus.map((part) => `<blockquote class="prompt-stimulus">${renderPromptText(part.text)}</blockquote>`).join("");
  const limits = scoring.filter(shortScore).map((part) => renderPromptText(part.text)).join("");
  return `${note}${banner}${quote}${task.map((part) => renderPromptText(part.text)).join("")}${limits}`;
}
const content = (blocks) =>
  (blocks || [])
    .map((b) => {
      const image = imageSource(b);
      if (image)
        return `<button type="button" class="figure" aria-label="${esc(t("zoomImage"))}"><img class="source-image" src="${image}" alt="${esc(b.text || t("sourcePage"))}"></button>`;
      if (b.kind === "code") return `<pre class="code-block">${esc(b.text)}</pre>`;
      return renderPromptText(b.text);
    })
    .join("");
const sourceLink = (source) =>
  source && !source.source_id.startsWith("legacy:")
    ? `<a href="/api/sources/${encodeURIComponent(source.source_id)}/file${source.page ? "#page=" + encodeURIComponent(source.page) : ""}">${t("openSource")}${source.page ? " · " + t("page") + " " + esc(source.page) : ""}</a>`
    : t("sourceReference");
const setStatus = (value) =>
  (document.querySelector("#status").textContent = value);

// --- Route 2, 4, 5: Math, Inline Tokens & Problem Statement Parser ---
function formatMathTokens(str) {
  return (str || "")
    .replace(/(?<!\d)10\^?(\d+)/g, "10<sup>$1</sup>")
    .replace(/(?<!\d)2\^?(\d+)/g, (m, p) => (["31", "16", "63", "32"].includes(p) ? `2<sup>${p}</sup>` : m))
    .replace(/\bO\(n\^?(\d+)\)/g, '<code class="inline-code">O(n<sup>$1</sup>)</code>')
    .replace(/\bO\((1|n|log\s*n|n\s*log\s*n|n!)\)/gi, '<code class="inline-code">O($1)</code>');
}

function formatInlineVariables(str) {
  const varPattern = /\b(nums|target|prices|matrix|board|grid|words|word|intervals|interval|head|root|nodes|node|edges|candidates|coins|stones|pile|cost|height|heights|capacity|amount|width|memo|dp|ans|res|val|val1|val2|left|right|mid|low|high|start|end|diff|count|curr|prev|slow|fast)\b(?![^<]*>)/g;
  const indexPattern = /\b([a-zA-Z_]\w*\[(?:i|j|k|mid|start|end|\d+)\])(?![^<]*>)/g;
  const lenPattern = /\b([a-zA-Z_]\w*\.length)(?![^<]*>)/g;
  const constPattern = /\b(true|false|null|None|True|False)\b(?![^<]*>)/g;

  return formatMathTokens(str || "")
    .replace(varPattern, '<code class="inline-code">$1</code>')
    .replace(indexPattern, '<code class="inline-code">$1</code>')
    .replace(lenPattern, '<code class="inline-code">$1</code>')
    .replace(constPattern, '<code class="inline-code">$1</code>');
}

function parseProblemPrompt(raw, title = "") {
  let text = (raw || "").trim();
  const lines = text.split("\n").map((l) => l.trim());
  const cleanTitle = (title || "").replace(/^\d+\.\s*/, "").trim().toLowerCase();
  if (lines.length && cleanTitle && (cleanTitle === lines[0].toLowerCase() || lines[0].toLowerCase().includes(cleanTitle))) {
    text = lines.slice(1).join("\n").trim();
  }

  let followUp = "";
  let constraints = [];
  const examples = [];
  let desc = "";

  const followUpMatch = text.match(/(?:Follow-up|Follow up|Note):\s*([\s\S]+)$/i);
  if (followUpMatch) {
    followUp = followUpMatch[1].trim();
    text = text.slice(0, followUpMatch.index).trim();
  }

  const constMatch = text.match(/Constraints:\s*([\s\S]+)$/i);
  if (constMatch) {
    const rawConst = constMatch[1].trim();
    constraints = rawConst
      .split("\n")
      .map((l) => l.replace(/^([•*]|\s*-\s+)\s*/, "").trim())
      .filter((l) => l.length > 0 && l !== "•");
    text = text.slice(0, constMatch.index).trim();
  }

  const exRegex = /Example\s+(\d+)\s*:\s*([\s\S]*?)(?=(?:Example\s+\d+\s*:|$))/gi;
  let exMatch;
  let firstExIndex = -1;

  while ((exMatch = exRegex.exec(text)) !== null) {
    if (firstExIndex === -1) firstExIndex = exMatch.index;
    const exNum = exMatch[1];
    const exBody = exMatch[2].trim();

    let input = "";
    let output = "";
    let explanation = "";

    const inMatch = exBody.match(/Input:\s*([\s\S]*?)(?=(?:Output:|Explanation:|$))/i);
    const outMatch = exBody.match(/Output:\s*([\s\S]*?)(?=(?:Explanation:|Output:|$))/i);
    const explMatch = exBody.match(/(?:Explanation|Output(?=.*Because)):\s*([\s\S]*?)$/i);

    if (inMatch) input = inMatch[1].trim();
    if (outMatch) output = outMatch[1].trim();
    if (explMatch && explMatch[0].toLowerCase().includes("explanation")) {
      explanation = explMatch[1].trim();
    } else if (exBody.includes("Because ") && !explanation) {
      explanation = exBody.slice(exBody.indexOf("Because ")).trim();
    }

    examples.push({ num: exNum, input, output, explanation });
  }

  if (firstExIndex !== -1) {
    desc = text.slice(0, firstExIndex).trim();
  } else {
    desc = text;
  }

  return { desc, examples, constraints, followUp };
}

// --- Route 7: Multi-Language Regex Syntax Tokenizer ---
function tokenizeCode(code, lang = "python") {
  lang = (lang || "python").toLowerCase();
  let tokenRegex;
  if (lang === "javascript" || lang === "js" || lang === "typescript" || lang === "ts") {
    tokenRegex = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)|(`(?:\\.|[^`])*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b(?:function|class|const|let|var|return|if|else|for|while|do|switch|case|break|continue|new|this|typeof|instanceof|async|await|import|export|from|default|try|catch|finally|throw|yield|in|of)\b)|(\b(?:true|false|null|undefined|NaN|Infinity)\b)|(\b(?:console|Math|Object|Array|String|Number|Boolean|Map|Set|Promise|JSON)\b)|(\b[a-zA-Z_$][\w$]*(?=\s*\())|(\b\d+(?:\.\d+)?\b)|(=>|[+\-*/%=<>!&|^~:]+)|([()[\]{},;])/g;
  } else if (lang === "sql") {
    tokenRegex = /(--[^\n]*|\/\*[\s\S]*?\*\/)|("(?:\\[\s\S]|[^"])*"|'(?:''|[^'])*')|(\b(?:SELECT|FROM|WHERE|INSERT|INTO|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET|UNION|ALL|DISTINCT|AS|AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|CREATE|TABLE|DROP|ALTER|INDEX|VIEW|PRIMARY\s+KEY|FOREIGN\s+KEY|CASCADE|SET|VALUES|COUNT|AVG|SUM|MIN|MAX)\b)/gi;
  } else {
    tokenRegex = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b(?:def|class|return|if|elif|else|while|for|in|try|except|finally|with|as|import|from|lambda|yield|raise|pass|continue|break|assert|async|await|global|nonlocal|is|not|and|or)\b)|(\b(?:True|False|None)\b)|(\b(?:self|cls)\b)|(\b(?:int|str|float|bool|list|dict|set|tuple|Optional|Any|Union|ListNode|TreeNode|print|len|range|enumerate|zip|min|max|sum|sorted|map|filter)\b)|(\b[a-zA-Z_]\w*(?=\s*\())|(\b\d+(?:\.\d+)?\b)|(->|[+\-*/%=<>!&|^~:]+)|([()[\]{},;])/g;
  }

  let lastIndex = 0;
  let out = "";
  let match;

  while ((match = tokenRegex.exec(code)) !== null) {
    if (match.index > lastIndex) {
      out += esc(code.slice(lastIndex, match.index));
    }
    const [full, comm, str, kw, bool, selfOrType, typeOrFn, fnOrNum, numOrOp, opOrPunct, punct] = match;
    if (comm) out += `<span class="tok-comm">${esc(comm)}</span>`;
    else if (str) out += `<span class="tok-str">${esc(str)}</span>`;
    else if (kw) out += `<span class="tok-kw">${esc(kw)}</span>`;
    else if (bool) out += `<span class="tok-bool">${esc(bool)}</span>`;
    else if (selfOrType) out += `<span class="tok-self">${esc(selfOrType)}</span>`;
    else if (typeOrFn) out += `<span class="tok-type">${esc(typeOrFn)}</span>`;
    else if (fnOrNum) out += `<span class="tok-fn">${esc(fnOrNum)}</span>`;
    else if (numOrOp) out += `<span class="tok-num">${esc(numOrOp)}</span>`;
    else if (opOrPunct) out += `<span class="tok-op">${esc(opOrPunct)}</span>`;
    else if (punct) out += `<span class="tok-punct">${esc(punct)}</span>`;
    lastIndex = tokenRegex.lastIndex;
  }
  if (lastIndex < code.length) {
    out += esc(code.slice(lastIndex));
  }
  return out;
}

// --- Route 9: Live Dual-Layer Code Editor with Line Numbers & Auto-Indent ---
function setupLiveEditor(wrapper, language = "python") {
  if (!wrapper) return;
  const textarea = wrapper.querySelector(".editor-input");
  const highlight = wrapper.querySelector("#highlight-layer");
  const gutter = wrapper.querySelector(".line-numbers-gutter");
  if (!textarea || !highlight) return;

  function update() {
    const val = textarea.value;
    highlight.innerHTML = tokenizeCode(val, language) + (val.endsWith("\n") ? " " : "");
    if (gutter) {
      const lines = val.split("\n").length;
      let gutterHtml = "";
      for (let i = 1; i <= lines; i++) {
        gutterHtml += i + "<br>";
      }
      gutter.innerHTML = gutterHtml;
    }
    textarea.style.height = "auto";
    const scrollH = Math.max(380, textarea.scrollHeight);
    textarea.style.height = scrollH + "px";
  }

  function syncScroll() {
    const backdrop = wrapper.querySelector(".editor-backdrop");
    if (backdrop) {
      backdrop.scrollTop = textarea.scrollTop;
      backdrop.scrollLeft = textarea.scrollLeft;
    }
    if (gutter) {
      gutter.scrollTop = textarea.scrollTop;
    }
  }

  textarea.addEventListener("input", update);
  textarea.addEventListener("scroll", syncScroll);

  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      if (e.shiftKey) {
        const before = textarea.value.substring(0, start);
        const lineStart = before.lastIndexOf("\n") + 1;
        if (textarea.value.substring(lineStart, lineStart + 4) === "    ") {
          textarea.value = textarea.value.substring(0, lineStart) + textarea.value.substring(lineStart + 4);
          textarea.selectionStart = Math.max(lineStart, start - 4);
          textarea.selectionEnd = Math.max(lineStart, end - 4);
          update();
        }
      } else {
        textarea.value = textarea.value.substring(0, start) + "    " + textarea.value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + 4;
        update();
      }
    } else if (e.key === "Enter") {
      const start = textarea.selectionStart;
      const beforeCursor = textarea.value.substring(0, start);
      const lastLine = beforeCursor.split("\n").pop();
      const match = lastLine.match(/^(\s*)/);
      let indent = match ? match[1] : "";
      if (lastLine.trim().endsWith(":")) {
        indent += "    ";
      }
      if (indent.length > 0) {
        e.preventDefault();
        const end = textarea.selectionEnd;
        textarea.value = beforeCursor + "\n" + indent + textarea.value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + 1 + indent.length;
        update();
      }
    }
  });

  update();
}

function renderProblemPane(item) {
  const spec = item.interaction;
  const rawPrompt = (item.prompt || []).map((b) => b.text || "").join("\n\n");
  const parsed = parseProblemPrompt(rawPrompt, item.title);

  const descParagraphs = parsed.desc
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${formatInlineVariables(esc(p))}</p>`)
    .join("");

  let examplesHtml = "";
  if (parsed.examples.length) {
    examplesHtml = parsed.examples
      .map(
        (ex) => `
      <div class="example-card">
        <span class="example-badge">Example ${esc(ex.num)}</span>
        ${ex.input ? `<div class="example-row"><span class="example-label">Input:</span><code class="example-code">${esc(ex.input)}</code></div>` : ""}
        ${ex.output ? `<div class="example-row"><span class="example-label">Output:</span><code class="example-code">${esc(ex.output)}</code></div>` : ""}
        ${ex.explanation ? `<div class="example-row"><span class="example-label">Explanation:</span><span class="example-explanation">${formatInlineVariables(esc(ex.explanation))}</span></div>` : ""}
      </div>
    `,
      )
      .join("");
  }

  let constraintsHtml = "";
  const constraintsList = (parsed.constraints && parsed.constraints.length)
    ? parsed.constraints
    : (spec.constraints || []);
  if (constraintsList.length) {
    constraintsHtml = `
      <div class="constraints-section">
        <div class="constraints-title">Constraints</div>
        <ul class="constraints-list">
          ${constraintsList.map((c) => `<li>${formatInlineVariables(formatMathTokens(esc(c)))}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  let followUpHtml = "";
  if (parsed.followUp) {
    followUpHtml = `
      <div class="followup-card">
        <strong>Follow up:</strong> ${formatInlineVariables(formatMathTokens(esc(parsed.followUp)))}
      </div>
    `;
  }

  return `
    <div class="problem-pane">
      <div class="problem-desc">
        ${descParagraphs || renderQuestion(item)}
      </div>
      ${examplesHtml}
      ${constraintsHtml}
      ${followUpHtml}
      ${item.sources.length ? `<p class="source" style="margin-top:20px;">${sourceLink(item.sources[0])}<br><span class="small">${esc(item.sources[0].quote || "")}</span></p>` : ""}
    </div>
  `;
}

function renderEditorPane(item) {
  const spec = item.interaction;
  const lang = (spec.language || "python").toLowerCase();
  const langDisplay = lang === "javascript" ? "JavaScript" : lang === "sql" ? "SQL" : "Python 3";

  return `
    <div class="editor-pane">
      <div class="code-editor-wrapper">
        <div class="code-editor-header">
          <div class="lang-pill">
            <span class="lang-dot ${esc(lang)}"></span>
            <span>${esc(langDisplay)}</span>
          </div>
        </div>
        <div class="code-editor-shell">
          <div class="line-numbers-gutter" aria-hidden="true">1</div>
          <div class="editor-stage">
            <pre class="editor-backdrop" aria-hidden="true"><code id="highlight-layer"></code></pre>
            <textarea id="response" class="editor-input code" aria-label="Your code solution" spellcheck="false" placeholder="Write your solution here">${esc(spec.starter_code || "")}</textarea>
          </div>
        </div>
      </div>
      <div class="actions" style="margin-top:0; justify-content:space-between;">
        <div style="display:flex; gap:12px; align-items:center;">
          <button class="btn-run" id="run-code">Run code</button>
          <button class="primary" id="commit">Submit Solution</button>
        </div>
        <div style="display:flex; gap:14px; align-items:center;">
          <button class="link" id="next">Next →</button>
          <button class="link" id="star">☆ Save</button>
        </div>
      </div>
      <div id="test-console" class="test-console" style="display:none;" aria-live="polite"></div>
      <div id="feedback" aria-live="polite"></div>
    </div>
  `;
}

async function api(path, options = {}) {
  const res = await fetch("/api" + path, options);
  const body = await res.json();
  if (!res.ok) throw Error(body.detail || `Request failed (${res.status})`);
  return body;
}
function request(method, path, data) {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
function error(err) {
  setStatus(err.message);
  main.insertAdjacentHTML(
    "afterbegin",
    `<p role="alert" class="error-text">${esc(err.message)}</p>`,
  );
}
function nav(view, focus = true) {
  if (state.projectInfo.editable && !state.projectInfo.configured) view = "settings";
  state.view = view;
  document.querySelectorAll(".topbar .nav").forEach((b) => {
    const active = b.dataset.view === view;
    b.classList.toggle("active", active);
    if (active) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  render();
  if (focus) main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
async function refresh() {
  try {
    const reviewQuery = `/exercises?status=needs_review&limit=100&offset=${state.reviewPage * 100}${state.reviewCollection ? "&collection_id=" + encodeURIComponent(state.reviewCollection) : ""}`;
    const [items, dueItems, review, collections, health, projectInfo, projectOptions] = await Promise.all([
      api("/exercises?status=approved&limit=100"),
      api("/exercises?status=approved&due=true&limit=100"),
      api(reviewQuery),
      api("/collections"),
      api("/health"),
      api("/project"),
      api("/project/options"),
    ]);
    state.items = items;
    state.dueItems = dueItems;
    state.hasMore = items.length === 100;
    state.review = review;
    state.reviewTotal = health.stats.review;
    state.collections = collections;
    state.providers = health.providers;
    if (!state.projectInfo.configured && projectInfo.project)
      state.mode = projectInfo.project.practice_mode;
    state.projectInfo = projectInfo;
    state.projectOptions = projectOptions;
    if (projectInfo.project) {
      document.querySelector("#project-name").textContent = projectInfo.project.name;
      document.title = projectInfo.project.name;
    }
    if (studyShell() && !state.bookletId) {
      const saved = localStorage.getItem("vengine-booklet") || "";
      if (collections.some((item) => item.id === saved)) state.bookletId = saved;
    }
    if (state.bookletId) {
      const booklet = await api(`/exercises?status=approved&collection_id=${encodeURIComponent(state.bookletId)}&limit=500`);
      state.items = booklet.sort((a, b) => compareLabels(a.label, b.label));
      const chosen = collections.find((item) => item.id === state.bookletId);
      const year = collectionYear(chosen?.name || "");
      state.bookletTitle = chosen ? bookletTitle(chosen.name, year) : state.bookletTitle;
    }
    applyChrome();
    if (projectInfo.editable && !projectInfo.configured) state.view = "settings";
    document.querySelector("#review-count").textContent =
      health.stats.review || "";
    nav(state.view, false);
  } catch (err) {
    error(err);
  }
}
function render() {
  main.classList.remove("review-active");
  main.classList.remove("practice-with-passage");
  ({ practice, library, review, import: importView, settings })[state.view]();
}
function settings() {
  const info = state.projectInfo;
  const config = info.project || {
    schema_version: 1,
    name: "",
    subject: "General",
    ai_provider: "auto",
    ai_count: 8,
    proposer: "builtin",
    practice_mode: "all",
    locale: "en",
  };
  if (!info.editable) {
    main.innerHTML = `<h1>${t("projectSettings")}</h1><p>${esc(t("projectConfigure"))}</p>`;
    return;
  }
  main.innerHTML = `<h1>${info.configured ? t("project") : t("setupProject")}</h1>
    <form id="project-form" class="project-form">
      <label>${t("name")}<input class="input" name="name" maxlength="80" required value="${esc(config.name)}"></label>
      <label>${t("language")}<select class="input" name="locale"><option value="en">English</option><option value="pt-BR">Português</option></select></label>
      <div class="actions"><button class="primary" type="submit">${t("saveProject")}</button></div>
    </form>`;
  const form = main.querySelector("#project-form");
  form.elements.locale.value = config.locale || "en";
  form.onsubmit = async (event) => {
    event.preventDefault();
    try {
      const updated = { ...config, name: form.elements.name.value.trim(), locale: form.elements.locale.value };
      state.projectInfo = await request("PUT", "/project", updated);
      state.mode = updated.practice_mode;
      document.querySelector("#project-name").textContent = updated.name;
      applyChrome();
      nav("practice");
    } catch (err) {
      error(err);
    }
  };
}
function activeItems() {
  if (state.mode === "due") return state.dueItems;
  if (state.mode === "unsolved") return state.items.filter((item) => !item.last_outcome);
  if (state.mode === "wrong") return state.items.filter((item) => item.last_outcome === "incorrect");
  if (state.mode === "starred") return state.items.filter((item) => item.starred);
  return state.items;
}
function compositeControls(spec, prefix = "p") {
  return (spec.parts || []).map((part, index) => {
    const child = part.interaction || part;
    const key = `${prefix}${index}`;
    const label = part.prompt || `${t("part")} ${index + 1}`;
    let input;
    if (child.kind === "composite") input = compositeControls(child, `${key}-`);
    else if (child.kind === "choice") input = (child.options || []).map((option) =>
      `<label><input type="${child.multiple ? "checkbox" : "radio"}" name="${key}" value="${esc(option.id)}"> ${content(option.blocks)}</label>`).join("");
    else if (child.kind === "boolean") input = `<select data-value><option value="">${t("choose")}</option><option value="true">True</option><option value="false">False</option></select>`;
    else if (child.kind === "cloze") input = (child.gaps || []).map((gap) =>
      `<label>${esc(gap.id)}<input class="input" data-gap="${esc(gap.id)}"></label>`).join("");
    else if (child.kind === "matching") input = (child.left || []).map((left) =>
      `<label>${esc(left)}<select data-match="${esc(left)}">${(child.right || []).map((right) => `<option value="${esc(right)}">${esc(right)}</option>`).join("")}</select></label>`).join("");
    else if (["rubric", "code", "sql"].includes(child.kind)) input = `<textarea data-value aria-label="${t("yourAnswer")}"></textarea>`;
    else input = `<input class="input" data-value aria-label="${t("yourAnswer")}" ${child.kind === "numeric" ? 'type="number" step="any"' : ""}>`;
    return `<fieldset class="composite-part" data-composite="${key}"><legend>${esc(typeof label === "string" ? label : text(label))}</legend>${input}</fieldset>`;
  }).join("");
}
function compositeResponse(spec, prefix = "p") {
  return (spec.parts || []).map((part, index) => {
    const child = part.interaction || part;
    const key = `${prefix}${index}`;
    const root = main.querySelector(`[data-composite="${key}"]`);
    if (child.kind === "composite") return compositeResponse(child, `${key}-`);
    if (child.kind === "choice") {
      const selected = [...root.querySelectorAll("input:checked")].map((input) => input.value);
      return child.multiple ? selected : selected[0] || null;
    }
    if (child.kind === "cloze") return Object.fromEntries(
      [...root.querySelectorAll("[data-gap]")].map((input) => [input.dataset.gap, input.value]));
    if (child.kind === "matching") return Object.fromEntries(
      [...root.querySelectorAll("[data-match]")].map((input) => [input.dataset.match, input.value]));
    const value = root.querySelector("[data-value]")?.value || "";
    if (child.kind === "boolean") return value === "" ? null : value === "true";
    if (child.kind === "numeric") return value === "" ? null : Number(value);
    if (child.kind === "ordering") return value.split(",").map((x) => x.trim()).filter(Boolean);
    return value;
  });
}
function practice() {
  main.classList.remove("practice-with-passage", "passage-hidden");
  if (studyShell() && !state.bookletId) {
    state.item = null;
    main.innerHTML = `<button class="link" id="open-prova">${t("chooseProva")}</button>`;
    main.querySelector("#open-prova").onclick = () => openPicker();
    return;
  }
  const items = activeItems();
  const item = items[state.index];
  state.item = item;
  if (!item) {
    if (studyShell() && state.bookletId) {
      main.innerHTML = `<h1>${t("nothingDue")}</h1><button class="link" id="show-all">${t("allFilters")}</button>`;
      main.querySelector("#show-all").onclick = () => {
        state.mode = "all";
        state.index = 0;
        practice();
      };
      return;
    }
    main.innerHTML = state.mode === "due" && state.items.length
      ? `<h1>${t("nothingDue")}</h1><button class="secondary" id="show-all">${t("allExercises")}</button>`
      : state.reviewTotal
        ? `<h1>${esc(state.reviewTotal)} ${t("awaitingReview")}</h1><button class="link" id="begin-review">✦ ${t("navReview")}</button>`
        : `<h1>${t("noExercises")}</h1><button class="link" id="begin-import">✦ ${t("importSource")}</button>`;
    const button = main.querySelector("button");
    button.onclick = () => {
      if (state.mode === "due") {
        state.mode = "all";
        practice();
      } else nav(state.reviewTotal ? "review" : "import");
    };
    return;
  }
  const spec = item.interaction;
  const kind = spec.kind;
  const isCode = kind === "code";
  main.classList.toggle("playground-active", isCode);

  const diffBadge = spec.difficulty ? `<span class="badge-${esc(spec.difficulty)}">${esc(spec.difficulty)}</span> ` : "";
  const tags = (spec.tags || item.topics || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("");

  if (isCode) {
    main.innerHTML = `
      <div class="split">
        <div>
          <span class="eyebrow">${esc(item.subject)}</span>
          <h1 style="margin:6px 0 8px;">${esc(item.title)}</h1>
          <div class="tags-row">${diffBadge}${tags}</div>
        </div>
        <div style="text-align:right;">
          <span class="small">${state.index + 1} / ${items.length}</span>
          <div class="toolbar" style="margin-top:8px;">
            <button class="nav ${state.mode === "all" ? "active" : ""}" data-mode="all">${t("all")}</button>
            <button class="nav ${state.mode === "due" ? "active" : ""}" data-mode="due">${t("due")} ${state.dueItems.length}</button>
          </div>
        </div>
      </div>
      <div class="divider" style="margin:16px 0 24px;"></div>
      <div class="playground-layout">
        ${renderProblemPane(item)}
        ${renderEditorPane(item)}
      </div>
    `;

    setupLiveEditor(main.querySelector(".code-editor-wrapper"), spec.language || "python");

    const runBtn = main.querySelector("#run-code");
    if (runBtn) {
      runBtn.onclick = async () => {
        const code = main.querySelector("#response")?.value || "";
        if (!code.trim()) {
          setStatus("Write your solution first");
          return;
        }
        runBtn.disabled = true;
        runBtn.textContent = "Running...";
        try {
          const data = await request("POST", `/exercises/${item.exercise_id}/run`, { response: code });
          renderTestConsole(data.result);
          setStatus("Sample test run finished");
        } catch (err) {
          error(err);
        } finally {
          runBtn.disabled = false;
          runBtn.textContent = "Run code";
        }
      };
    }
  } else {
    let controls = "";
    if (kind === "choice")
      controls = `<div class="options" role="group" aria-label="${t("answerChoices")}">${spec.options.map((o) => `<button class="option" data-answer="${esc(o.id)}"><span class="key">${esc(o.id)}</span><span>${content(o.blocks)}</span></button>`).join("")}</div>`;
    else if (kind === "boolean")
      controls = `<div class="options"><button class="option" data-answer="true">${esc(item.metadata?.boolean_labels?.true || "True")}</button><button class="option" data-answer="false">${esc(item.metadata?.boolean_labels?.false || "False")}</button></div>`;
    else if (kind === "sql")
      controls = `<textarea id="response" class="code" aria-label="${t("yourAnswer")}" spellcheck="false" placeholder="SELECT ...">${esc(spec.starter_code || "")}</textarea>`;
    else if (kind === "cloze")
      controls = spec.gaps
        .map(
          (g) =>
            `<label>${esc(g.id)}<input class="input gap" data-gap="${esc(g.id)}"></label>`,
        )
        .join("");
    else if (kind === "matching")
      controls = (spec.left || [])
        .map(
          (key) =>
            `<label>${esc(key)}<select class="match" data-key="${esc(key)}"><option value="">${t("chooseMatch")}</option>${(spec.right || []).map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join("")}</select></label>`,
        )
        .join("");
    else if (kind === "composite")
      controls = compositeControls(spec);
    else if (kind === "ordering")
      controls = `<input id="response" class="input" placeholder="Enter IDs in order, separated by commas">`;
    else
      controls = `<textarea id="response" aria-label="${t("yourAnswer")}" placeholder="${t("writeAnswer")}"></textarea>`;

    const actionsHtml = `<div class="actions"><button class="primary" id="commit">${t("checkAnswer")}</button><button class="link" id="next">${t("next")} →</button><button class="link" id="star">${item.starred ? "★" : "☆"} ${item.starred ? t("saved") : t("save")}</button></div>`;
    const modeButtons = (studyShell() && state.bookletId
      ? [["all", t("allFilters")], ["unsolved", t("unsolved")], ["wrong", t("wrong")], ["starred", t("starred")]]
      : [["all", t("all")], ["due", `${t("due")} ${state.dueItems.length}`]])
      .map(([mode, label]) => `<button class="nav ${state.mode === mode ? "active" : ""}" data-mode="${mode}">${label}</button>`).join("");
    const hasPassage = item.contexts.length > 0;
    if (hasPassage) main.classList.add("practice-with-passage");
    const passageSurface = hasPassage ? `<aside id="practice-passage" class="practice-passage" aria-label="Source text">${content(item.contexts)}</aside>` : "";
    const questionSurface = `<section class="practice-question"><div class="question">${renderQuestion(item)}</div>${controls}<div id="feedback" aria-live="polite"></div>${actionsHtml}${item.sources.length ? `<p class="source">${sourceLink(item.sources[0])}</p>` : ""}</section>`;
    const place = state.bookletTitle ? `${esc(state.bookletTitle)} · ` : "";
    const editControl = !studyShell() && hasPassage ? `<button id="edit-question" class="quiet" aria-label="${t("editShared")}">✎</button>` : "";
    const passageControl = hasPassage ? `<button id="toggle-passage" class="quiet passage-toggle" aria-label="${t("hideSource")}" aria-controls="practice-passage" aria-expanded="true">◧</button>` : "";
    const indexControl = studyShell() && state.bookletId ? `<button id="index-toggle" class="quiet" aria-expanded="${state.indexOpen ? "true" : "false"}" aria-controls="label-index">${t("index")}</button>` : "";
    const indexPanel = studyShell() && state.bookletId && state.indexOpen
      ? `<div id="label-index" class="label-index">${state.items.map((entry) => `<button class="menu-choice" data-jump="${esc(entry.exercise_id)}" ${entry.exercise_id === item.exercise_id ? 'aria-current="true"' : ""}>${esc(entry.label || "·")}</button>`).join("")}</div>`
      : "";
    main.innerHTML = `<div class="split"><span class="eyebrow">${diffBadge}${place}${esc(item.label)}</span><span class="small">${state.index + 1} / ${items.length}</span></div><div class="toolbar">${modeButtons}${editControl}${passageControl}${indexControl}</div>${indexPanel}<div class="divider"></div><div class="practice-grid">${passageSurface}${questionSurface}</div>`;
  }

  state.selected = null;
  state.submitted = false;

  main.querySelectorAll("[data-answer]").forEach(
    (button) =>
      (button.onclick = () => {
        if (state.submitted) return;
        const id = button.dataset.answer;
        if (spec.multiple) {
          state.selected = Array.isArray(state.selected) ? state.selected : [];
          state.selected = state.selected.includes(id)
            ? state.selected.filter((x) => x !== id)
            : [...state.selected, id];
        } else state.selected = id;
        main
          .querySelectorAll("[data-answer]")
          .forEach((b) =>
            b.classList.toggle(
              "selected",
              Array.isArray(state.selected)
                ? state.selected.includes(b.dataset.answer)
                : state.selected === b.dataset.answer,
            ),
          );
      }),
  );
  const commitBtn = main.querySelector("#commit");
  if (commitBtn) commitBtn.onclick = commit;
  const nextBtn = main.querySelector("#next");
  if (nextBtn) nextBtn.onclick = next;
  const starBtn = main.querySelector("#star");
  const passageToggle = main.querySelector("#toggle-passage");
  const editQuestion = main.querySelector("#edit-question");
  if (editQuestion) editQuestion.onclick = async () => {
    try {
      const latest = await api(`/exercises/${item.exercise_id}?review=true`);
      if (latest.status === "approved")
        await request("PATCH", `/review/${item.exercise_id}`, {
          changes: { review_notes: ["Review question and shared text before approval."] },
        });
      state.reviewCollection = item.collection_id || "";
      state.reviewPage = 0;
      await refresh();
      state.reviewIndex = Math.max(0, state.review.findIndex((draft) => draft.exercise_id === item.exercise_id));
      nav("review");
    } catch (err) { error(err); }
  };
  if (passageToggle) passageToggle.onclick = () => {
    const pane = main.querySelector("#practice-passage");
    pane.hidden = !pane.hidden;
    passageToggle.setAttribute("aria-expanded", String(!pane.hidden));
    passageToggle.setAttribute("aria-label", pane.hidden ? t("showSource") : t("hideSource"));
    main.classList.toggle("passage-hidden", pane.hidden);
  };
  if (starBtn) {
    starBtn.onclick = async () => {
      const starred = !item.starred;
      await request("PUT", `/exercises/${item.exercise_id}/mark`, { starred });
      item.starred = starred;
      starBtn.textContent = `${starred ? "★" : "☆"} ${starred ? t("saved") : t("save")}`;
      setStatus(starred ? t("saved") : t("save"));
    };
  }
  const indexToggle = main.querySelector("#index-toggle");
  if (indexToggle) indexToggle.onclick = () => {
    state.indexOpen = !state.indexOpen;
    practice();
  };
  main.querySelectorAll("[data-jump]").forEach((button) => {
    button.onclick = () => {
      state.mode = "all";
      state.index = state.items.findIndex((entry) => entry.exercise_id === button.dataset.jump);
      if (state.index < 0) state.index = 0;
      state.indexOpen = true;
      practice();
    };
  });
  main.querySelectorAll("[data-mode]").forEach(
    (button) =>
      (button.onclick = () => {
        state.mode = button.dataset.mode;
        state.index = 0;
        practice();
      }),
  );
}

function renderTestConsole(result) {
  const consoleEl = main.querySelector("#test-console");
  if (!consoleEl) return;
  consoleEl.style.display = "block";
  const visible = result.details?.visible_cases || [];
  const statusClass = result.outcome === "correct" ? "case-status-passed" : "case-status-failed";
  const statusIcon = result.outcome === "correct" ? "✓" : "✗";
  const statusLabel = result.outcome === "correct"
    ? "All Sample Cases Passed"
    : result.outcome === "partial"
      ? "Some Test Cases Failed"
      : (result.feedback || "Run Failed");

  let tabsHtml = "";
  let cardsHtml = "";
  if (visible.length) {
    tabsHtml = `<div class="testcase-tabs">${visible.map((c, i) => `
      <button class="testcase-tab ${i === 0 ? "active" : ""} ${c.passed ? "pass" : "fail"}" data-tab="${i}">
        <span class="tab-icon">${c.passed ? "✓" : "✗"}</span>
        <span>${esc(c.name || `Case ${i + 1}`)}</span>
        ${c.duration_ms !== undefined ? `<span class="duration-chip">${c.duration_ms}ms</span>` : ""}
      </button>`).join("")}</div>`;

    cardsHtml = visible.map((c, i) => `
      <div class="testcase-card" id="testcase-card-${i}" style="${i === 0 ? "" : "display:none;"}">
        <div class="case-field">
          <span class="case-field-label">Input</span>
          <div class="case-field-val">${esc(JSON.stringify(c.input))}</div>
        </div>
        ${c.passed ? `
          <div class="case-field">
            <span class="case-field-label">Output</span>
            <div class="case-field-val">${esc(JSON.stringify(c.actual))}</div>
          </div>
        ` : `
          <div class="diff-box">
            <div class="diff-col diff-expected">
              <span class="diff-label">Expected Output</span>
              <div class="diff-val">${esc(JSON.stringify(c.expected))}</div>
            </div>
            <div class="diff-col diff-actual">
              <span class="diff-label">Your Output</span>
              <div class="diff-val">${c.error ? `<span class="case-status-failed">${esc(c.error)}</span>` : esc(JSON.stringify(c.actual))}</div>
            </div>
          </div>
        `}
        ${c.stdout ? `<div class="case-field"><span class="case-field-label">Stdout</span><pre class="console-stdout">${esc(c.stdout)}</pre></div>` : ""}
      </div>
    `).join("");
  }

  consoleEl.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <span class="${statusClass}"><span>${statusIcon}</span> <span>${esc(statusLabel)}</span></span>
      <span class="small">${result.score !== null ? Math.round(result.score * 100) + "% passed" : ""}</span>
    </div>
    ${tabsHtml}
    ${cardsHtml}
  `;

  consoleEl.querySelectorAll(".testcase-tab").forEach((tab) => {
    tab.onclick = () => {
      const idx = tab.dataset.tab;
      consoleEl.querySelectorAll(".testcase-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      consoleEl.querySelectorAll(".testcase-card").forEach((card, i) => {
        card.style.display = String(i) === idx ? "flex" : "none";
      });
    };
  });
}
function responseFor(spec) {
  if (spec.kind === "composite") return compositeResponse(spec);
  if (["choice", "boolean"].includes(spec.kind))
    return spec.kind === "boolean"
      ? state.selected === null
        ? null
        : state.selected === "true"
      : state.selected;
  if (spec.kind === "cloze")
    return Object.fromEntries(
      [...main.querySelectorAll(".gap")].map((input) => [
        input.dataset.gap,
        input.value,
      ]),
    );
  if (spec.kind === "matching")
    return Object.fromEntries(
      [...main.querySelectorAll(".match")].map((input) => [
        input.dataset.key,
        input.value,
      ]),
    );
  const value = main.querySelector("#response")?.value || "";
  if (spec.kind === "numeric") return value.trim() === "" ? "" : Number(value);
  if (spec.kind === "ordering")
    return value
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
  return value;
}
async function commit() {
  if (state.submitted) return;
  const item = state.item,
    answer = responseFor(item.interaction);
  if (
    answer === null ||
    answer === "" ||
    (Array.isArray(answer) && !answer.length)
  ) {
    setStatus(t("chooseAnswer"));
    return;
  }
  try {
    const data = await request(
      "POST",
      `/exercises/${item.exercise_id}/submit`,
      { response: answer },
    );
    state.submitted = true;
    main.querySelector("#commit").disabled = true;
    if (
      ["correct", "incorrect", "partial"].includes(data.attempt.grade.outcome)
    )
      state.dueItems = state.dueItems.filter(
        (i) => i.exercise_id !== item.exercise_id,
      );
    const previous = item.last_outcome;
    item.last_outcome = data.attempt.grade.outcome;
    const collection = state.collections.find((entry) => entry.id === item.collection_id);
    if (collection) {
      if (!previous) collection.answered = (collection.answered || 0) + 1;
      if (data.attempt.grade.outcome === "correct" && previous !== "correct")
        collection.correct = (collection.correct || 0) + 1;
      if (previous === "correct" && data.attempt.grade.outcome !== "correct")
        collection.correct = Math.max(0, (collection.correct || 0) - 1);
    }
    const grade = data.attempt.grade;
    const explain = text(data.explanation);
    const sample = data.answer.sample_answer
      ? `<p>${t("sampleAnswer")}: ${esc(data.answer.sample_answer)}</p>`
      : "";
    main.querySelector("#feedback").innerHTML =
      `<div class="feedback ${esc(grade.outcome)}"><strong>${esc(grade.outcome[0].toUpperCase() + grade.outcome.slice(1))}${grade.score !== null ? " · " + Math.round(grade.score * 100) + "%" : ""}</strong>${esc(grade.feedback)}${explain ? `<p>${esc(explain)}</p>` : ""}${sample}</div>${grade.outcome === "ungraded" ? `<p class="small">${t("howWell")}</p><div class="toolbar"><button class="secondary" data-rating="1">${t("again")}</button><button class="secondary" data-rating="2">${t("hard")}</button><button class="secondary" data-rating="3">${t("good")}</button><button class="secondary" data-rating="4">${t("easy")}</button></div>` : ""}`;
    if (grade.details?.visible_cases) {
      renderTestConsole(grade);
    }
    main.querySelectorAll("[data-rating]").forEach(
      (button) =>
        (button.onclick = async () => {
          try {
            const result = await request(
              "POST",
              `/attempts/${data.attempt.id}/assess`,
              { rating: Number(button.dataset.rating) },
            );
            main
              .querySelectorAll("[data-rating]")
              .forEach((b) => (b.disabled = true));
            state.dueItems = state.dueItems.filter(
              (i) => i.exercise_id !== item.exercise_id,
            );
            setStatus(t("reviewScheduled"));
          } catch (err) {
            error(err);
          }
        }),
    );
    if (item.interaction.kind === "choice")
      main.querySelectorAll("[data-answer]").forEach((b) => {
        if (data.answer.correct?.includes(b.dataset.answer))
          b.classList.add("correct");
        else if (b.classList.contains("selected")) b.classList.add("wrong");
      });
    setStatus(t("attemptSaved"));
  } catch (err) {
    error(err);
  }
}
function next() {
  const count = activeItems().length;
  if (count) {
    state.index = (state.index + 1) % count;
    practice();
  }
}
function previous() {
  const count = activeItems().length;
  if (count) {
    state.index = (state.index - 1 + count) % count;
    practice();
  }
}
function collectionYear(name) {
  const match = String(name || "").match(/\b(?:19|20)\d{2}\b/);
  return match ? match[0] : "";
}
function bookletTitle(name, year) {
  const marker = `${year} · `;
  const at = String(name).indexOf(marker);
  return at >= 0 ? name.slice(at + marker.length) : name;
}
function compareLabels(left, right) {
  const parts = (label) => String(label || "").split(".").map((part) => {
    const number = Number(part);
    return Number.isFinite(number) && String(number) === part ? number : part;
  });
  const a = parts(left);
  const b = parts(right);
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    const x = a[index];
    const y = b[index];
    if (x === y) continue;
    if (x === undefined) return -1;
    if (y === undefined) return 1;
    if (typeof x === "number" && typeof y === "number") return x - y;
    return String(x).localeCompare(String(y));
  }
  return 0;
}
function statementLine(item) {
  const lines = reflowLines(text(item.prompt));
  const line = [...lines].reverse().find((part) => !isScoreNote(part) && !isCommandLine(part)) || lines[0] || item.title || "";
  return line.length > 140 ? `${line.slice(0, 137)}…` : line;
}
function library() {
  if (!state.collections.length) {
    flatLibrary();
    return;
  }
  const years = [...new Set(state.collections.map((item) => collectionYear(item.name)).filter(Boolean))]
    .sort((a, b) => Number(b) - Number(a));
  if (!state.libraryYear || !years.includes(state.libraryYear)) state.libraryYear = years[0] || "";
  const filters = state.projectInfo.project?.library_filters || [];
  const authoring = state.projectInfo.project?.show_project === false ? "" : `<div class="toolbar"><button id="create" class="link">${t("createExercise")}</button><button id="add" class="link">${t("importSourceBtn")}</button></div>`;
  main.innerHTML = `<h1>${t("library")}</h1>${authoring}<div class="chip-row" id="years" role="group" aria-label="${t("years")}"></div><div class="chip-row" id="filters" role="group"></div><div class="rows" id="rows"></div>`;
  if (main.querySelector("#add")) main.querySelector("#add").onclick = () => nav("import");
  if (main.querySelector("#create")) main.querySelector("#create").onclick = createView;
  const yearRow = main.querySelector("#years");
  yearRow.innerHTML = years.map((year) => `<button class="chip ${year === state.libraryYear ? "active" : ""}" data-year="${esc(year)}">${esc(year)}</button>`).join("");
  yearRow.querySelectorAll("[data-year]").forEach((button) => {
    button.onclick = () => {
      state.libraryYear = button.dataset.year;
      state.catalogId = "";
      library();
    };
  });
  const filterRow = main.querySelector("#filters");
  if (filters.length) {
    const active = new Set(state.libraryFilters);
    filterRow.innerHTML = `<button class="chip ${active.size ? "" : "active"}" data-filter="">${t("allFilters")}</button>${filters.map((filter) => `<button class="chip ${active.has(filter) ? "active" : ""}" data-filter="${esc(filter)}">${esc(filter)}</button>`).join("")}`;
    filterRow.querySelectorAll("[data-filter]").forEach((button) => {
      button.onclick = () => {
        const name = button.dataset.filter;
        if (!name) state.libraryFilters = [];
        else if (state.libraryFilters.includes(name)) state.libraryFilters = state.libraryFilters.filter((item) => item !== name);
        else state.libraryFilters = [...state.libraryFilters, name];
        state.catalogId = "";
        library();
      };
    });
  }
  const visible = state.collections.filter((item) => {
    if (collectionYear(item.name) !== state.libraryYear) return false;
    return state.libraryFilters.every((filter) => item.name.toLocaleLowerCase().includes(filter.toLocaleLowerCase()));
  }).sort((a, b) => bookletTitle(a.name, state.libraryYear).localeCompare(bookletTitle(b.name, state.libraryYear)));
  const rows = main.querySelector("#rows");
  if (state.catalogId && !visible.some((item) => item.id === state.catalogId)) state.catalogId = "";
  if (!state.catalogId) {
    rows.innerHTML = visible.length
      ? visible.map((item) => `<button class="row" data-collection="${esc(item.id)}"><span class="row-title">${esc(bookletTitle(item.name, state.libraryYear))}</span><span class="row-meta">${progressLine(item)}</span></button>`).join("")
      : `<p class="empty">${t("noBooklets")}</p>`;
    rows.querySelectorAll("[data-collection]").forEach((button) => {
      button.onclick = async () => {
        try {
          await openBooklet(button.dataset.collection);
          state.catalogId = state.bookletId;
          library();
        } catch (err) {
          error(err);
        }
      };
    });
    return;
  }
  rows.innerHTML = `<button class="link" id="back-exams">${esc(state.bookletTitle || t("backToExams"))}</button>${state.items.map((item) => `<button class="row" data-id="${esc(item.exercise_id)}"><span class="row-title"><span class="row-label">${esc(item.label || "")}</span>${esc(statementLine(item))}</span></button>`).join("") || `<p class="empty">${t("noExercisesFound")}</p>`}`;
  main.querySelector("#back-exams").onclick = () => {
    state.catalogId = "";
    library();
  };
  rows.querySelectorAll("[data-id]").forEach((button) => {
    button.onclick = () => {
      state.index = state.items.findIndex((item) => item.exercise_id === button.dataset.id);
      state.mode = "all";
      nav("practice");
    };
  });
}
function flatLibrary() {
  const authoring = state.projectInfo.project?.show_project === false ? "" : `<button id="create" class="secondary">${t("createExercise")}</button><button id="add" class="secondary">${t("importSourceBtn")}</button>`;
  main.innerHTML = `<h1>${t("library")}</h1><div class="toolbar"><input id="search" class="input" type="search" placeholder="${t("searchExercises")}" aria-label="${t("searchExercises")}">${authoring}</div><div class="rows" id="rows"></div>`;
  if (main.querySelector("#add")) main.querySelector("#add").onclick = () => nav("import");
  if (main.querySelector("#create")) main.querySelector("#create").onclick = createView;
  const rows = main.querySelector("#rows");
  function draw(items, searching = false) {
    rows.innerHTML = items.length
      ? items.map((i) => `<button class="row" data-id="${esc(i.exercise_id)}"><span class="row-title">${esc(i.title || text(i.prompt).slice(0, 120))}</span><span class="row-meta">${esc(i.label || "")}</span></button>`).join("")
      : `<p class="empty">${t("noExercisesFound")}</p>`;
    if (!searching && state.hasMore)
      rows.insertAdjacentHTML("beforeend", `<button id="load-more" class="link">${t("loadMore")}</button>`);
    rows.querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => {
      const found = items.find((i) => i.exercise_id === b.dataset.id);
      state.index = state.items.findIndex((i) => i.exercise_id === b.dataset.id);
      if (state.index < 0) {
        state.items.push(found);
        state.index = state.items.length - 1;
      }
      state.bookletTitle = "";
      state.mode = "all";
      nav("practice");
    }));
    const more = rows.querySelector("#load-more");
    if (more) more.onclick = async () => {
      more.disabled = true;
      try {
        const next = await api("/exercises?status=approved&limit=100&offset=" + state.items.length);
        state.hasMore = next.length === 100;
        state.items.push(...next);
        draw(state.items);
      } catch (err) { error(err); }
    };
  }
  draw(state.items);
  let timer;
  main.querySelector("#search").oninput = (e) => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = e.target.value.trim();
      draw(q ? await api("/search?q=" + encodeURIComponent(q)) : state.items, Boolean(q));
    }, 180);
  };
}
function createView() {
  main.innerHTML =
    `<h1>${t("createExercise")}</h1><label>${t("subject")}<input id="author-subject" class="input" value="${esc(state.projectInfo.project?.subject || "General")}"></label><label>${t("prompt")}<textarea id="author-prompt"></textarea></label><label>${t("interaction")}<select id="author-kind"><option value="choice">${t("choice")}</option><option value="text">${t("shortText")}</option><option value="rubric">${t("openResponse")}</option><option value="code">Python</option><option value="sql">SQL</option></select></label><label>${t("optionsLine")}<textarea id="author-options"></textarea></label><label>${t("answerOrQuery")}<input id="author-answer" class="input"></label><div class="actions"><button id="author-save" class="primary">${t("sendReview")}</button><button id="author-back" class="link">${t("library")}</button></div>`;
  main.querySelector("#author-back").onclick = () => nav("library");
  main.querySelector("#author-save").onclick = async () => {
    try {
      const subject = main.querySelector("#author-subject").value || "General",
        prompt = main.querySelector("#author-prompt").value,
        kind = main.querySelector("#author-kind").value,
        answer = main.querySelector("#author-answer").value,
        options = main
          .querySelector("#author-options")
          .value.split("\n")
          .map((x) => x.trim())
          .filter(Boolean);
      if (!prompt.trim()) throw Error(t("writePrompt"));
      let interaction;
      if (kind === "choice") {
        if (options.length < 2) throw Error(t("twoOptions"));
        interaction = {
          kind: "choice",
          options: options.map((value, i) => ({
            id: String.fromCharCode(65 + i),
            blocks: [{ text: value }],
          })),
          correct: answer.trim() ? [answer.trim().toUpperCase()] : [],
        };
      } else if (kind === "text")
        interaction = { kind: "text", accepted: answer ? [answer] : [] };
      else if (kind === "code")
        interaction = { kind: "code", language: "python", cases: [] };
      else if (kind === "sql")
        interaction = { kind: "sql", setup_sql: "", reference_query: answer };
      else interaction = { kind: "rubric", sample_answer: answer || null };
      await request("POST", "/exercises", {
        subject,
        title: prompt.slice(0, 100),
        prompt: [{ text: prompt }],
        interaction,
      });
      setStatus(t("exerciseCreated"));
      await refresh();
      nav("review");
    } catch (err) {
      error(err);
    }
  };
}
function review() {
  const item = state.review[state.reviewIndex];
  const filter = `<label for="review-collection">${t("collection")}</label><select id="review-collection" aria-label="${t("collection")}"><option value="">${t("allCollections")}</option>${state.collections.map((collection) => `<option value="${esc(collection.id)}" ${state.reviewCollection === collection.id ? "selected" : ""}>${esc(collection.name)}</option>`).join("")}</select>`;
  if (!item) {
    main.innerHTML = `<h1>${state.reviewCollection ? t("noProposals") : t("reviewClear")}</h1>${filter}`;
    main.querySelector("#review-collection").onchange = async (event) => {
      state.reviewCollection = event.target.value;
      state.reviewPage = 0;
      state.reviewIndex = 0;
      await refresh();
    };
    return;
  }
  const spec = item.interaction;
  const options =
    spec.kind === "choice"
      ? spec.options.map((o) => `${o.id}. ${text(o.blocks)}`).join("\n")
      : "";
  const answer =
    spec.kind === "choice"
      ? (spec.correct || []).join(", ")
      : spec.kind === "text"
        ? (spec.accepted || []).join(" | ")
        : spec.kind === "boolean"
          ? spec.correct == null ? "" : item.metadata?.boolean_labels
            ? (spec.correct ? "C" : "E") : String(spec.correct)
          : "";
  const queueRows = state.review.map((draft) => `<label class="queue-row"><input type="checkbox" value="${esc(draft.id)}"><span>${esc(draft.title || text(draft.prompt).slice(0, 90))}</span></label>`).join("");
  main.innerHTML = `<div class="split"><span class="eyebrow">${t("navReview")} · ${state.reviewPage * 100 + state.reviewIndex + 1}</span><div><button id="queue-toggle" class="quiet">${t("queue")}</button> <button id="review-next" class="quiet">${t("next")} →</button></div></div><h1>${esc(item.title || t("reviewExercise"))}</h1>${filter}<div id="review-queue" ${state.reviewQueueOpen ? "" : "hidden"}>${queueRows}<button id="discard-selected" class="secondary">${t("discardSelected")}</button></div><div class="meta"><span>${esc(item.subject)}</span><span>${esc(spec.kind)}</span><span>${esc(item.answer_origin)}</span></div><label>${t("prompt")}<textarea id="edit-prompt">${esc(text(item.prompt))}</textarea></label>${options ? `<label>${t("options")}<textarea id="edit-options">${esc(options)}</textarea></label>` : ""}${["choice", "text", "boolean"].includes(spec.kind) ? `<label>${t("answerKey")}<input id="edit-answer" class="input" value="${esc(answer)}"></label>` : `<label>${t("interaction")}<textarea id="edit-json" class="code">${esc(JSON.stringify(spec, null, 2))}</textarea></label>`}<label>${t("subject")}<input id="edit-subject" class="input" value="${esc(item.subject)}"></label><div class="source">${sourceLink(item.sources[0])}<br>${esc(item.sources[0]?.quote || t("noCitation"))}</div><div class="actions"><button id="save-review" class="secondary">${t("saveChanges")}</button><button id="approve" class="primary">${t("approvePractice")}</button></div><p class="small">${esc(item.review_notes.join(" "))}</p>`;
  main.classList.add("review-active");
  const reference = item.sources[0];
  const preview = document.createElement("aside");
  preview.id = "source-preview";
  preview.setAttribute("aria-label", t("sourcePage"));
  const pageImage = reference?.source_id && reference.page && !reference.source_id.startsWith("legacy:")
    ? `<img class="source-image" src="/api/sources/${encodeURIComponent(reference.source_id)}/render/${reference.page}" alt="${t("sourcePage")}">`
    : "";
  preview.innerHTML = `<p class="eyebrow">${t("source")}${reference?.page ? " · " + t("page") + " " + esc(reference.page) : ""}</p>${sourceLink(reference)}${pageImage}<div class="source-body">${esc(reference?.quote || t("noCitation"))}</div>`;
  main.append(preview);
  preview.querySelector(".source-image")?.addEventListener("error", (event) => event.currentTarget.remove());
  if (item.passage_id) {
    preview.insertAdjacentHTML("afterbegin", `<section id="shared-review"><div class="split"><span class="eyebrow">${t("sharedText")}</span><button id="edit-shared" class="quiet" aria-label="${t("editShared")}">✎</button></div><div id="shared-text" class="source-body"></div><div id="shared-editor" hidden><label>${t("title")}<input id="shared-title" class="input"></label><label>${t("text")}<textarea id="shared-content"></textarea></label><button id="save-shared" class="quiet">${t("saveText")}</button></div><button id="approve-shared" class="quiet" hidden>${t("approveText")}</button></section>`);
    api(`/passages/${encodeURIComponent(item.passage_id)}`).then((passage) => {
      if (!preview.isConnected) return;
      let current = passage;
      const textField = preview.querySelector("#shared-content");
      const titleField = preview.querySelector("#shared-title");
      const approveButton = preview.querySelector("#approve-shared");
      const fill = () => {
        preview.querySelector("#shared-text").innerHTML = content(current.blocks);
        textField.value = text(current.blocks);
        titleField.value = current.title;
        approveButton.hidden = current.status === "approved";
      };
      fill();
      preview.querySelector("#edit-shared").onclick = () => {
        const editor = preview.querySelector("#shared-editor");
        editor.hidden = !editor.hidden;
        if (!editor.hidden) textField.focus();
      };
      preview.querySelector("#save-shared").onclick = async () => {
        try {
          current = await request("PATCH", `/review/passages/${item.passage_id}`, {
            title: titleField.value, text: textField.value,
          });
          fill();
          preview.querySelector("#shared-editor").hidden = true;
          setStatus(t("sharedSaved"));
        } catch (err) { error(err); }
      };
      approveButton.onclick = async () => {
        try {
          await request("POST", `/review/passages/${current.id}/approve`, {});
          setStatus(t("sharedApproved"));
          await refresh();
        } catch (err) { error(err); }
      };
    }).catch(error);
  }
  if (reference?.source_id && reference.page && !reference.source_id.startsWith("legacy:")) {
    api(`/sources/${encodeURIComponent(reference.source_id)}/pages/${reference.page}`)
      .then((data) => {
        if (preview.isConnected) preview.querySelector(".source-body").innerHTML = content(data.page.blocks);
      }).catch(() => {});
  }
  main.querySelector("#review-collection").onchange = async (event) => {
    state.reviewCollection = event.target.value;
    state.reviewPage = 0;
    state.reviewIndex = 0;
    await refresh();
  };
  const figures = item.prompt.filter((block) => block.kind === "image");
  if (figures.length)
    main
      .querySelector("#edit-prompt")
      .insertAdjacentHTML("afterend", content(figures));
  main.querySelector("#review-next").onclick = nextReview;
  main.querySelector("#queue-toggle").onclick = () => {
    state.reviewQueueOpen = !state.reviewQueueOpen;
    main.querySelector("#review-queue").hidden = !state.reviewQueueOpen;
  };
  main.querySelector("#discard-selected").onclick = async () => {
    const ids = [...main.querySelectorAll("#review-queue input:checked")].map((input) => input.value);
    if (!ids.length || !window.confirm(`${t("discardSelected")} (${ids.length})?`)) return;
    try {
      await request("POST", "/review/archive", { revision_ids: ids });
      state.reviewIndex = 0;
      await refresh();
    } catch (err) { error(err); }
  };
  main.querySelector("#save-review").onclick = async () => {
    try {
      const changes = {
        subject: main.querySelector("#edit-subject").value,
        prompt: [
          { ...item.prompt[0], text: main.querySelector("#edit-prompt").value },
          ...item.prompt.slice(1),
        ],
      };
      if (spec.kind === "choice") {
        const lines = main
          .querySelector("#edit-options")
          .value.split("\n")
          .filter(Boolean);
        const options = lines.map((line, i) => ({
          id: String.fromCharCode(65 + i),
          blocks: [
            { kind: "text", text: line.replace(/^[A-H]\s*[).:-]\s*/, "") },
          ],
        }));
        changes.interaction = {
          ...spec,
          options,
          correct: main
            .querySelector("#edit-answer")
            .value.split(",")
            .map((x) => x.trim())
            .filter(Boolean),
        };
      } else if (spec.kind === "text")
        changes.interaction = {
          ...spec,
          accepted: main
            .querySelector("#edit-answer")
            .value.split("|")
            .map((x) => x.trim())
            .filter(Boolean),
        };
      else if (spec.kind === "boolean") {
        const value = main.querySelector("#edit-answer").value.trim().toLowerCase();
        if (!["", "c", "e", "true", "false"].includes(value)) throw new Error(t("useCE"));
        changes.interaction = { ...spec, correct: value ? ["c", "true"].includes(value) : null };
      }
      else
        changes.interaction = JSON.parse(
          main.querySelector("#edit-json").value,
        );
      await request("PATCH", `/review/${item.exercise_id}`, { changes });
      setStatus(t("newRevision"));
      await refresh();
    } catch (err) {
      error(err);
    }
  };
  let dirty = false;
  main.querySelectorAll("input,textarea").forEach((field) =>
    field.addEventListener("input", () => {
      dirty = true;
      main.querySelector("#approve").disabled = true;
      setStatus(t("saveBeforeApproval"));
    }),
  );
  main.querySelector("#approve").onclick = async () => {
    if (dirty) return;
    try {
      await request("POST", `/review/${item.id}/approve`, {});
      setStatus(t("approvedPractice"));
      state.reviewIndex = 0;
      state.reviewPage = 0;
      await refresh();
    } catch (err) {
      error(err);
    }
  };
}
async function nextReview() {
  if (state.reviewIndex + 1 < state.review.length) {
    state.reviewIndex += 1;
    review();
    return;
  }
  state.reviewPage += 1;
  state.reviewIndex = 0;
  await refresh();
  if (!state.review.length) {
    state.reviewPage = 0;
    await refresh();
  }
}
function importView() {
  const available = Object.values(state.providers).some(Boolean);
  const preference = state.projectInfo.project?.ai_provider || "auto";
  const provider = preference === "auto" || preference === "none"
    ? Object.keys(state.providers).find((name) => state.providers[name]) || "gemini" : preference;
  const providerOptions = Object.entries(state.providers).map(([name, ready]) =>
    `<option value="${esc(name)}" ${ready ? "" : "disabled"}>${esc(name === "gemini" ? "Gemini" : name)}</option>`).join("");
  const aiBlock = preference === "none" ? "" : `<label id="ai-field"><input id="use-ai" type="checkbox" ${available && preference !== "none" ? "checked" : ""} ${available ? "" : "disabled"}> ${t("generateAI")}</label><div id="provider-field"><label for="provider">${t("provider")}</label><select id="provider">${providerOptions}</select></div>`;
  main.innerHTML = `<h1>${t("importTitle")}</h1><form class="import-form" id="import-form"><label>${t("type")}<select id="import-mode"><option value="originals">${t("originalExam")}</option><option value="study">${t("studySource")}</option></select></label><div class="import-files"><label class="file-control">${t("sourceFile")}<input id="source-file" class="file-input" type="file" accept="${esc(state.projectOptions.formats.join(","))}"><span class="file-name">${t("chooseFileNamed")}</span></label><label class="file-control" id="answer-field">${t("answerKeyFile")}<input id="answer-file" class="file-input" type="file" accept="${esc(state.projectOptions.formats.join(","))}"><span class="file-name">${t("chooseFileNamed")}</span></label></div>${aiBlock}<div class="actions"><button id="upload" class="primary" type="button">${t("importForReview")}</button></div></form><div id="import-result" aria-live="polite"></div>`;
  main.querySelector("#import-form").onsubmit = (event) => event.preventDefault();
  main.querySelectorAll(".file-input").forEach((input) => {
    input.onchange = () => {
      const name = input.files[0]?.name || t("chooseFileNamed");
      input.parentElement.querySelector(".file-name").textContent = name;
    };
  });
  if (main.querySelector("#provider")) main.querySelector("#provider").value = provider;
  const toggleProvider = () => {
    const originals = main.querySelector("#import-mode").value === "originals";
    main.querySelector("#answer-field").hidden = !originals;
    const ai = main.querySelector("#ai-field");
    const providerField = main.querySelector("#provider-field");
    if (ai) ai.hidden = originals;
    if (providerField) providerField.hidden = originals || !main.querySelector("#use-ai")?.checked;
  };
  main.querySelector("#use-ai") && (main.querySelector("#use-ai").onchange = toggleProvider);
  main.querySelector("#import-mode").onchange = toggleProvider;
  toggleProvider();
  main.querySelector("#upload").onclick = async () => {
    const file = main.querySelector("#source-file").files[0];
    if (!file) {
      setStatus(t("chooseFile"));
      return;
    }
    const button = main.querySelector("#upload");
    button.disabled = true;
    setStatus(t("importing"));
    try {
      const form = new FormData();
      form.append("file", file);
      const mode = main.querySelector("#import-mode").value;
      const answer = main.querySelector("#answer-file").files[0];
      if (mode === "originals" && answer) form.append("answer_file", answer);
      const ai = mode === "study" && Boolean(main.querySelector("#use-ai")?.checked);
      if (ai && !available)
        throw Error(
          "Configure Gemini or agy before enabling cloud generation.",
        );
      const provider = main.querySelector("#provider")?.value || "gemini";
      const res = await fetch(
        `/api/import?mode=${mode}&generate_ai=${ai}&provider=${encodeURIComponent(provider)}`,
        { method: "POST", body: form },
      );
      let job = await res.json();
      if (!res.ok) throw Error(job.detail || t("importFailed"));
      const showJob = () => {
        const result = main.querySelector("#import-result");
        if (!result) return;
        result.innerHTML = `<p>${esc(job.stage.replaceAll("_", " "))} · ${Math.round(job.progress * 100)}%</p>${["queued", "extracting", "generating"].includes(job.stage) ? `<button class="link" id="cancel-job">${t("cancel")}</button>` : ""}`;
        const cancel = result.querySelector("#cancel-job");
        if (cancel) cancel.onclick = async () => {
          job = await request("POST", `/jobs/${job.id}/cancel`, {});
          showJob();
        };
      };
      while (["queued", "extracting", "generating"].includes(job.stage)) {
        showJob();
        await new Promise((resolve) => setTimeout(resolve, 500));
        job = await api(`/jobs/${job.id}`);
      }
      if (job.stage === "failed") throw Error(job.error || t("importFailed"));
      if (job.stage === "cancelled") {
        setStatus(t("importCancelled"));
        return;
      }
      await refresh();
      const result = main.querySelector("#import-result");
      if (result) result.innerHTML = job.proposals_count
        ? `<p>${job.proposals_count} ${t("sentToReview")}</p><button class="link" id="open-review">${t("openReview")} →</button>`
        : `<p>${t("sourceSaved")}</p>`;
      result?.querySelector("#open-review")?.addEventListener("click", () => nav("review"));
      setStatus(t("importComplete"));
    } catch (err) {
      error(err);
    } finally {
      button.disabled = false;
    }
  };
}
document
  .querySelectorAll(".nav")
  .forEach((button) => (button.onclick = () => nav(button.dataset.view)));
function progressLine(item) {
  return `${item.answered || 0}/${item.total || 0} · ${item.correct || 0} ${t("correctCount")}`;
}
async function openBooklet(id) {
  const collection = state.collections.find((item) => item.id === id);
  const year = collectionYear(collection?.name || "");
  state.bookletId = id;
  state.bookletTitle = collection ? bookletTitle(collection.name, year) : "";
  if (year) state.libraryYear = year;
  localStorage.setItem("vengine-booklet", id);
  const items = await api(`/exercises?status=approved&collection_id=${encodeURIComponent(id)}&limit=500`);
  state.items = items.sort((a, b) => compareLabels(a.label, b.label));
  state.index = 0;
  state.mode = "all";
  updateProva();
}
function menuChoice(group, value, label, pressed) {
  return `<button class="menu-choice" role="menuitemradio" data-group="${group}" data-value="${esc(value)}" aria-checked="${pressed ? "true" : "false"}">${esc(label)}</button>`;
}
function menuSection(label, choices) {
  return `<div class="menu-section"><p class="menu-label">${esc(label)}</p><div class="menu-group" role="group" aria-label="${esc(label)}">${choices}</div></div>`;
}
function fillAppearance() {
  const current = appearanceChoice();
  const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
  const fonts = READING_FONTS.map((name) => menuChoice("font", name, name || t("readingDefault"), (current.font || "") === name)).join("");
  const sizes = [["xs", "12"], ["sm", "14"], ["md", "15"], ["lg", "18"]].map(([value, label]) => menuChoice("size", value, label, (current.text_size || "md") === value)).join("");
  const widths = [["narrow", t("narrow")], ["standard", t("standard")]].map(([value, label]) => menuChoice("width", value, label, (current.reading_width || "standard") === value)).join("");
  const languages = [["en", "English"], ["pt-BR", "Português"]].map(([value, label]) => menuChoice("locale", value, label, locale() === value)).join("");
  const themes = [["dark", t("dark")], ["light", t("light")]].map(([value, label]) => menuChoice("theme", value, label, theme === value)).join("");
  const here = state.view === "practice" && state.mode === "due" ? "due" : state.view;
  const study = studyShell()
    ? menuSection(t("goTo"), [["practice", t("navPractice")], ["library", t("navLibrary")], ["review", t("navReview")], ["import", t("navImport")], ["due", t("due")]].map(([value, label]) => `<button class="menu-choice" role="menuitem" data-go="${value}" ${here === value ? 'aria-current="true"' : ""}>${esc(label)}</button>`).join(""))
    : "";
  const panel = document.querySelector("#appearance");
  panel.innerHTML = `${menuSection(t("font"), fonts)}${menuSection(t("size"), sizes)}${menuSection(t("width"), widths)}${menuSection(t("language"), languages)}${menuSection(t("theme"), themes)}${study}`;
  panel.querySelectorAll("[data-group]").forEach((button) => {
    button.onclick = () => applyMenuChoice(button.dataset.group, button.dataset.value).catch(error);
  });
  panel.querySelectorAll("[data-go]").forEach((button) => {
    button.onclick = () => {
      closeAppearance();
      if (button.dataset.go === "due") {
        state.mode = "due";
        state.index = 0;
        nav("practice");
        return;
      }
      nav(button.dataset.go);
    };
  });
}
async function applyMenuChoice(group, value) {
  if (group === "font") await saveAppearance({ font: value });
  else if (group === "size") await saveAppearance({ text_size: value });
  else if (group === "width") await saveAppearance({ reading_width: value });
  else if (group === "theme") {
    document.documentElement.dataset.theme = value === "light" ? "light" : "dark";
    localStorage.setItem("theme", document.documentElement.dataset.theme);
  } else if (group === "locale") {
    const project = state.projectInfo.project;
    if (!state.projectInfo.editable || !project) return;
    state.projectInfo = await request("PUT", "/project", { ...project, locale: value });
    applyChrome();
    render();
  }
  if (!document.querySelector("#appearance").hidden) fillAppearance();
}
function closeAppearance() {
  document.querySelector("#appearance").hidden = true;
  document.querySelector("#home").setAttribute("aria-expanded", "false");
}
function openAppearance() {
  closePicker();
  fillAppearance();
  const panel = document.querySelector("#appearance");
  panel.hidden = false;
  document.querySelector("#home").setAttribute("aria-expanded", "true");
  panel.querySelector("button")?.focus();
}
function closePicker() {
  document.querySelector("#picker").hidden = true;
  document.querySelector("#prova").setAttribute("aria-expanded", "false");
}
function openPicker() {
  closeAppearance();
  const picker = document.querySelector("#picker");
  picker.hidden = false;
  document.querySelector("#prova").setAttribute("aria-expanded", "true");
  renderPicker();
  picker.querySelector("button")?.focus();
}
function renderPicker() {
  const years = [...new Set(state.collections.map((item) => collectionYear(item.name)).filter(Boolean))]
    .sort((a, b) => Number(b) - Number(a));
  if (!state.libraryYear || !years.includes(state.libraryYear)) state.libraryYear = years[0] || "";
  const filters = state.projectInfo.project?.library_filters || [];
  const active = new Set(state.libraryFilters);
  const visible = state.collections.filter((item) => {
    if (collectionYear(item.name) !== state.libraryYear) return false;
    return state.libraryFilters.every((filter) => item.name.toLocaleLowerCase().includes(filter.toLocaleLowerCase()));
  }).sort((a, b) => bookletTitle(a.name, state.libraryYear).localeCompare(bookletTitle(b.name, state.libraryYear)));
  const picker = document.querySelector("#picker");
  picker.setAttribute("aria-label", t("provas"));
  picker.innerHTML = `<div class="chip-row" id="picker-years" role="group" aria-label="${t("years")}">${years.map((year) => `<button class="chip ${year === state.libraryYear ? "active" : ""}" data-year="${esc(year)}">${esc(year)}</button>`).join("")}</div><div class="chip-row" id="picker-filters" role="group">${filters.length ? `<button class="chip ${active.size ? "" : "active"}" data-filter="">${t("allFilters")}</button>${filters.map((filter) => `<button class="chip ${active.has(filter) ? "active" : ""}" data-filter="${esc(filter)}">${esc(filter)}</button>`).join("")}` : ""}</div><div class="rows">${visible.length ? visible.map((item) => `<button class="row" data-collection="${esc(item.id)}"><span class="row-title">${esc(bookletTitle(item.name, state.libraryYear))}</span><span class="row-meta">${progressLine(item)}</span></button>`).join("") : `<p class="empty">${t("noBooklets")}</p>`}</div>`;
  picker.querySelectorAll("[data-year]").forEach((button) => {
    button.onclick = () => {
      state.libraryYear = button.dataset.year;
      renderPicker();
    };
  });
  picker.querySelectorAll("[data-filter]").forEach((button) => {
    button.onclick = () => {
      const name = button.dataset.filter;
      if (!name) state.libraryFilters = [];
      else if (state.libraryFilters.includes(name)) state.libraryFilters = state.libraryFilters.filter((item) => item !== name);
      else state.libraryFilters = [...state.libraryFilters, name];
      renderPicker();
    };
  });
  picker.querySelectorAll("[data-collection]").forEach((button) => {
    button.onclick = async () => {
      try {
        await openBooklet(button.dataset.collection);
        closePicker();
        nav("practice");
      } catch (err) {
        error(err);
      }
    };
  });
}
function moveMenu(root, key) {
  const buttons = [...root.querySelectorAll("button")];
  if (!buttons.length) return;
  const current = buttons.indexOf(document.activeElement);
  const delta = key === "ArrowUp" || key === "ArrowLeft" ? -1 : 1;
  const next = current < 0 ? 0 : (current + delta + buttons.length) % buttons.length;
  buttons[next].focus();
}
document.querySelector("#home").onclick = (event) => {
  event.stopPropagation();
  if (document.querySelector("#appearance").hidden) openAppearance();
  else closeAppearance();
};
document.querySelector("#appearance").onclick = (event) => event.stopPropagation();
document.querySelector("#prova").onclick = (event) => {
  event.stopPropagation();
  if (document.querySelector("#picker").hidden) openPicker();
  else closePicker();
};
document.querySelector("#picker").onclick = (event) => event.stopPropagation();
document.addEventListener("click", (event) => {
  const image = event.target.closest?.(".source-image")
    || event.target.closest?.(".figure")?.querySelector(".source-image");
  if (image && !image.closest("#zoom")) {
    openZoom(image);
    return;
  }
  if (event.target.closest?.("#zoom")) return;
  closeAppearance();
  closePicker();
});
function openZoom(image) {
  const dialog = document.querySelector("#zoom");
  const target = document.querySelector("#zoom-image");
  target.src = image.currentSrc || image.src;
  target.alt = image.alt || t("zoomImage");
  setZoom(1);
  if (!dialog.open) dialog.showModal();
  document.querySelector("#zoom-title").textContent = t("zoomImage");
}
function setZoom(scale) {
  const next = Math.min(4, Math.max(1, Math.round(scale * 4) / 4));
  const dialog = document.querySelector("#zoom");
  dialog.dataset.scale = String(next);
  const target = document.querySelector("#zoom-image");
  target.style.width = `${next * 100}%`;
  target.style.transform = "none";
}
document.querySelector("#zoom-in").onclick = () => setZoom(Number(document.querySelector("#zoom").dataset.scale || "1") + 0.25);
document.querySelector("#zoom-out").onclick = () => setZoom(Number(document.querySelector("#zoom").dataset.scale || "1") - 0.25);
document.querySelector("#zoom-close").onclick = () => document.querySelector("#zoom").close();
document.querySelector("#zoom-stage").addEventListener("wheel", (event) => {
  if (!document.querySelector("#zoom").open) return;
  event.preventDefault();
  const scale = Number(document.querySelector("#zoom").dataset.scale || "1");
  setZoom(scale + (event.deltaY < 0 ? 0.25 : -0.25));
}, { passive: false });
document.documentElement.dataset.theme = localStorage.getItem("theme") || "dark";
document.addEventListener("keydown", (event) => {
  const panel = document.querySelector("#appearance");
  const picker = document.querySelector("#picker");
  const menu = !panel.hidden ? panel : !picker.hidden ? picker : null;
  if (menu) {
    if (event.key === "Escape") {
      if (menu === panel) closeAppearance();
      else closePicker();
      (menu === panel ? document.querySelector("#home") : document.querySelector("#prova")).focus();
      event.preventDefault();
    } else if (["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft"].includes(event.key)) {
      moveMenu(menu, event.key);
      event.preventDefault();
    }
    return;
  }
  if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
  if (state.view !== "practice") {
    if (event.key.toLowerCase() === "j" && state.view === "review" && state.review.length) nextReview();
    return;
  }
  if (event.key.toLowerCase() === "j" || event.key === "ArrowRight") {
    next();
    event.preventDefault();
  }
  if (event.key.toLowerCase() === "k" || event.key === "ArrowLeft") {
    previous();
    event.preventDefault();
  }
  if (event.key === "Enter" && !["BUTTON", "A"].includes(document.activeElement?.tagName)) commit();
});
refresh();
