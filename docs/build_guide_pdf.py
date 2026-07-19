"""
Generates 'Agentic_Compliance_Auditor_Guide.pdf' — a learning-oriented
walkthrough of the project, from fundamentals to deep architecture.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable, KeepTogether
)

# ----------------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------------
INK      = colors.HexColor("#1a1a2e")
ACCENT   = colors.HexColor("#412991")   # OpenAI purple-ish
ACCENT2  = colors.HexColor("#0f766e")   # teal
LIGHT    = colors.HexColor("#f4f4f8")
CODE_BG  = colors.HexColor("#1e1e2e")
CODE_FG  = colors.HexColor("#e6e6e6")
GREY     = colors.HexColor("#555566")
RULE     = colors.HexColor("#d8d8e0")

# ----------------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------------
styles = getSampleStyleSheet()

def S(name, **kw):
    styles.add(ParagraphStyle(name, **kw))

S("CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=36,
  textColor=INK, alignment=TA_CENTER, spaceAfter=10)
S("CoverSub", fontName="Helvetica", fontSize=13, leading=19,
  textColor=GREY, alignment=TA_CENTER, spaceAfter=6)
S("CoverTag", fontName="Helvetica-Oblique", fontSize=11, leading=16,
  textColor=ACCENT, alignment=TA_CENTER)

S("H1", fontName="Helvetica-Bold", fontSize=19, leading=23,
  textColor=ACCENT, spaceBefore=6, spaceAfter=10)
S("H2", fontName="Helvetica-Bold", fontSize=14, leading=18,
  textColor=INK, spaceBefore=14, spaceAfter=6)
S("H3", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
  textColor=ACCENT2, spaceBefore=10, spaceAfter=4)

S("Body", fontName="Helvetica", fontSize=10.2, leading=15.5,
  textColor=INK, alignment=TA_JUSTIFY, spaceAfter=8)
S("BodyL", fontName="Helvetica", fontSize=10.2, leading=15.5,
  textColor=INK, alignment=TA_LEFT, spaceAfter=8)
S("XBullet", fontName="Helvetica", fontSize=10.2, leading=15,
  textColor=INK, spaceAfter=3)
S("Note", fontName="Helvetica-Oblique", fontSize=9.3, leading=13.5,
  textColor=GREY, spaceAfter=8)
S("Caption", fontName="Helvetica-Oblique", fontSize=8.8, leading=12,
  textColor=GREY, alignment=TA_CENTER, spaceAfter=10)
S("XCode", fontName="Courier", fontSize=8.6, leading=12.2,
  textColor=CODE_FG, leftIndent=2, rightIndent=2)
S("TOCItem", fontName="Helvetica", fontSize=11, leading=20, textColor=INK)
S("TOCNum", fontName="Helvetica-Bold", fontSize=11, leading=20, textColor=ACCENT)
S("KV", fontName="Helvetica", fontSize=9.3, leading=13, textColor=INK)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def code_block(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = text.split("\n")
    para = "<br/>".join(line.replace(" ", "&nbsp;") for line in lines)
    p = Paragraph(para, styles["XCode"])
    t = Table([[p]], colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t

def bullets(items, style="XBullet"):
    return ListFlowable(
        [ListItem(Paragraph(t, styles[style]), leftIndent=12, value="•")
         for t in items],
        bulletType="bullet", start="•", leftIndent=10, bulletColor=ACCENT,
    )

def callout(title, body, color=ACCENT2):
    inner = []
    inner.append(Paragraph(f"<b>{title}</b>", ParagraphStyle(
        "cot", fontName="Helvetica-Bold", fontSize=10, textColor=color,
        leading=14, spaceAfter=3)))
    inner.append(Paragraph(body, ParagraphStyle(
        "cob", fontName="Helvetica", fontSize=9.6, textColor=INK,
        leading=14, alignment=TA_JUSTIFY)))
    t = Table([[inner]], colWidths=[170*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t

def kv_table(rows, col0=45*mm, col1=125*mm):
    data = [[Paragraph(f"<b>{k}</b>", styles["KV"]), Paragraph(v, styles["KV"])]
            for k, v in rows]
    t = Table(data, colWidths=[col0, col1])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]),
    ]))
    return t

def data_table(header, rows, widths):
    data = [[Paragraph(f"<b>{h}</b>", ParagraphStyle(
        "th", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white,
        leading=12)) for h in header]]
    for r in rows:
        data.append([Paragraph(c, ParagraphStyle(
            "td", fontName="Helvetica", fontSize=8.8, textColor=INK,
            leading=12)) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
    ]))
    return t

def h1(num, title):
    return [
        Spacer(1, 2),
        Paragraph(f'<font color="#b9b3d6">{num:02d}</font>&nbsp;&nbsp;{title}', styles["H1"]),
        HRFlowable(width="100%", thickness=1.2, color=RULE, spaceAfter=10),
    ]

# ----------------------------------------------------------------------------
# Page furniture (header / footer)
# ----------------------------------------------------------------------------
def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # footer rule
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, 14*mm, w - 20*mm, 14*mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(20*mm, 9*mm, "Agentic Compliance Auditor — Project Guide")
    canvas.drawRightString(w - 20*mm, 9*mm, f"Page {doc.page}")
    canvas.restoreState()

def on_cover(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 18*mm, w, 18*mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT2)
    canvas.rect(0, 0, w, 8*mm, fill=1, stroke=0)
    canvas.restoreState()

# ----------------------------------------------------------------------------
# Build story
# ----------------------------------------------------------------------------
story = []

# ===== COVER =====
story.append(Spacer(1, 55*mm))
story.append(Paragraph("Agentic Compliance Auditor", styles["CoverTitle"]))
story.append(Paragraph("A Build-Up Guide: From First Principles to Deep Architecture",
                       styles["CoverSub"]))
story.append(Spacer(1, 6))
story.append(Paragraph("An AI assistant that audits documents against GDPR, HIPAA, and SOC2 "
                       "using autonomous agents that plan, retrieve, reason, and self-check "
                       "before returning a cited answer.", styles["CoverTag"]))
story.append(Spacer(1, 30*mm))
meta = Table([
    [Paragraph("<b>Author</b>", styles["KV"]), Paragraph("Balaji V", styles["KV"])],
    [Paragraph("<b>Stack</b>", styles["KV"]),
     Paragraph("LangGraph · OpenAI gpt-4o-mini · ChromaDB · FastAPI · Streamlit · Redis · Neo4j", styles["KV"])],
    [Paragraph("<b>Purpose</b>", styles["KV"]),
     Paragraph("Understand the system end-to-end — what was built and why", styles["KV"])],
], colWidths=[35*mm, 130*mm])
meta.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
]))
story.append(meta)
story.append(PageBreak())

# ===== TABLE OF CONTENTS =====
story += h1(0, "What's Inside")
toc = [
    ("01", "The Problem & The Idea", "Why generic LLMs fail at compliance, and the core insight"),
    ("02", "Concepts You Need First", "RAG, embeddings, vector search, and what 'agentic' means"),
    ("03", "The Big Picture", "How a question flows through the whole system"),
    ("04", "Step 1 — Ingestion", "Turning regulatory PDFs into searchable chunks"),
    ("05", "Step 2 — Retrieval", "Hybrid semantic + keyword search with citations"),
    ("06", "Step 3 — The Agent", "LangGraph state machine: retrieve, generate, reflect"),
    ("07", "Step 4 — Memory & Graph", "Redis sessions and the Neo4j knowledge graph"),
    ("08", "Step 5 — Serving It", "FastAPI endpoints and the Streamlit UI"),
    ("09", "Evaluation", "Measuring quality with RAGAS"),
    ("10", "Design Decisions & Lessons", "The 'why' behind the choices, and what was hard"),
    ("11", "Glossary", "Every key term in one place"),
]
for num, title, desc in toc:
    row = Table([[
        Paragraph(num, styles["TOCNum"]),
        Paragraph(f"<b>{title}</b><br/><font size=8 color='#777'>{desc}</font>", styles["TOCItem"]),
    ]], colWidths=[14*mm, 156*mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(row)
story.append(PageBreak())

# ===== 01 PROBLEM =====
story += h1(1, "The Problem & The Idea")
story.append(Paragraph(
    "Compliance teams spend hours cross-referencing regulatory documents to answer "
    "questions like <i>“Do our data-retention policies meet GDPR Article 17?”</i> or "
    "<i>“What exactly does HIPAA require for PHI access logs?”</i>. The work is slow, but "
    "the deeper problem is trust: a generic large language model will happily invent a "
    "plausible-sounding regulatory detail and cite nothing. In compliance, every claim "
    "must be traceable to a source — an unsourced answer is worse than no answer.",
    styles["Body"]))
story.append(Paragraph("The core insight", styles["H2"]))
story.append(Paragraph(
    "Don't ask the model to <i>know</i> the regulations. Ask it to <i>reason over</i> the "
    "specific regulatory text you hand it, force it to cite, and then make it check its own "
    "work before answering. That single shift — from a model that recalls to a system that "
    "retrieves, grounds, and self-verifies — is the whole project.", styles["Body"]))
story.append(callout(
    "What the system does, in one breath",
    "You ask a compliance question. The system (1) searches your regulatory documents "
    "using both semantic and keyword retrieval, (2) drafts an answer grounded only in what "
    "it found, (3) critiques its own draft — if citations are missing or the answer is "
    "vague, it tries again — and (4) returns the final answer with specific article and "
    "section references. Everything except the LLM call runs on your machine."))
story.append(Spacer(1, 4))
story.append(Paragraph("A key privacy property", styles["H3"]))
story.append(Paragraph(
    "Documents, embeddings, and session state never leave your machine. Only the composed "
    "prompt (your question plus the retrieved chunks) is sent to OpenAI for the generation "
    "step. The vector database, the embedding model, and conversation history are all local.",
    styles["Body"]))
story.append(PageBreak())

# ===== 02 CONCEPTS =====
story += h1(2, "Concepts You Need First")
story.append(Paragraph(
    "Before tracing the code, here are the four ideas the whole system rests on. If these "
    "click, everything else is just plumbing.", styles["Body"]))

story.append(Paragraph("1. Embeddings — turning meaning into numbers", styles["H3"]))
story.append(Paragraph(
    "An embedding model reads a piece of text and outputs a fixed-length list of numbers "
    "(a vector) that captures its meaning. Texts with similar meaning land close together "
    "in this number-space, even if they share no words. This project uses "
    "<b>all-MiniLM-L6-v2</b>, which produces 384-dimensional vectors and runs locally as a "
    "library call — there is no embedding server to deploy.", styles["Body"]))

story.append(Paragraph("2. Vector search — finding by meaning", styles["H3"]))
story.append(Paragraph(
    "Once every chunk of your documents is an embedding, answering “what's relevant to this "
    "question?” becomes “which stored vectors are closest to the question's vector?”. "
    "<b>ChromaDB</b> stores the vectors and answers that nearest-neighbour query using "
    "cosine similarity. This is <i>semantic</i> search — it finds conceptually related text "
    "even when the wording differs.", styles["Body"]))

story.append(Paragraph("3. RAG — Retrieval-Augmented Generation", styles["H3"]))
story.append(Paragraph(
    "RAG is the pattern of retrieving relevant text first, then asking the LLM to answer "
    "<i>using that text</i>. The retrieved chunks become the model's evidence, which is what "
    "makes citations possible and hallucinations rare. A plain RAG pipeline is two steps: "
    "retrieve, then generate.", styles["Body"]))

story.append(Paragraph("4. “Agentic” — the step beyond plain RAG", styles["H3"]))
story.append(Paragraph(
    "An <i>agent</i> doesn't just run a fixed pipeline; it can decide what to do next. Here, "
    "after generating a draft the system runs a <b>reflection</b> step that judges whether "
    "the answer is well-grounded and properly cited. If not, it loops back and retrieves "
    "again. That decision-and-loop — “is this good enough, or should I try harder?” — is "
    "what earns the word <i>agentic</i>. A plain pipeline can't do it; it stops after the "
    "first draft.", styles["Body"]))
story.append(callout(
    "The one-sentence mental model",
    "Plain RAG = retrieve → generate.  This project = retrieve → generate → reflect → "
    "(maybe loop back). The reflection loop is the difference between a search box and an "
    "agent.", color=ACCENT))
story.append(PageBreak())

# ===== 03 BIG PICTURE =====
story += h1(3, "The Big Picture")
story.append(Paragraph(
    "Here is the full journey of a single question, from the HTTP request to the cited "
    "answer. Read it top to bottom — each later section zooms into one of these stages.",
    styles["Body"]))
story.append(Spacer(1, 2))
flow = """User question
   |  HTTP POST /query  { query, session_id }
   v
FastAPI endpoint
   v
ComplianceAgent  --- LangGraph StateGraph ------------------+
                                                            |
  Step 1. RETRIEVE                                          |
     HybridRetriever                                        |
       - Semantic search  -> ChromaDB (384-dim vectors)     |
       - Keyword boost     -> term matching over chunk text  |
       => top-k chunks + similarity scores + citations      |
                                                            |
  Step 2. GENERATE                                          |
     system prompt + question + retrieved chunks            |
       -> OpenAI gpt-4o-mini  => draft answer               |
                                                            |
  Step 3. REFLECT (conditional)                             |
     draft answer -> reflection LLM call                    |
       grounded + cited?  yes -> finalize                   |
                          no  -> loop back to RETRIEVE ------+
                                  (max N iterations)
   v
Final answer + citations
   |
   +--> Redis  (session history; in-memory fallback)
   +--> Neo4j  (regulation -> article -> requirement; optional)
   v
HTTP response  { answer, sources[], citations[], iterations }"""
story.append(code_block(flow))
story.append(Paragraph("Three things the diagram makes explicit", styles["H2"]))
story.append(bullets([
    "<b>The agent is sequential, not parallel.</b> Retrieve finishes before generate starts; "
    "generate finishes before reflect starts. The arrows are data flow, not concurrent threads.",
    "<b>Embeddings are a library call, not a service.</b> sentence-transformers runs in-process "
    "inside the retriever — nothing extra to host.",
    "<b>Reflection is the only optional, looping part.</b> Everything else runs exactly once "
    "per iteration; reflection is what can send the state back to the start.",
]))
story.append(PageBreak())

# ===== 04 INGESTION =====
story += h1(4, "Step 1 — Ingestion: Documents into Chunks")
story.append(Paragraph(
    "Before any question can be answered, the regulatory documents must be loaded, split "
    "into chunks, embedded, and stored. This is a one-time offline step you run with "
    "<font face='Courier'>python setup.py</font>. Code lives in "
    "<font face='Courier'>src/ingestion/</font>.", styles["Body"]))

story.append(Paragraph("Loading — document_loader.py", styles["H3"]))
story.append(Paragraph(
    "<b>DocumentLoader</b> reads PDF (via PyMuPDF), TXT, and DOCX files into plain text plus "
    "metadata. It infers the regulation type straight from the filename — a file with "
    "“gdpr” in its name is tagged <font face='Courier'>document_type: GDPR</font>. That tag "
    "later powers filtered search (“only look in HIPAA”).", styles["Body"]))

story.append(Paragraph("Chunking — chunker.py", styles["H3"]))
story.append(Paragraph(
    "Documents are too long to embed whole, so they are split into chunks. Naive fixed-size "
    "splitting cuts sentences in half and destroys meaning. Instead, <b>SemanticChunker</b> "
    "splits on natural boundaries — section breaks, then paragraphs, then sentences — in "
    "priority order, with a small overlap between chunks so context isn't lost at the seams. "
    "<b>RegulationChunker</b> extends it: it detects article/section headers (e.g. "
    "“Article 17”, “Section 164.502”, “CC6.1”) and attaches the legal references it finds "
    "to each chunk's metadata.", styles["Body"]))
story.append(callout(
    "Lesson the author learned the hard way",
    "“Chunking strategy matters more than the model.” Retrieval quality was the bottleneck, "
    "not generation. Switching from fixed-size to boundary-aware chunking improved how often "
    "the right text was found. No amount of agent sophistication fixes bad retrieval."))

story.append(Paragraph("Embedding & storing — vector_store.py", styles["H3"]))
story.append(Paragraph(
    "Each chunk is encoded into a 384-dim vector by all-MiniLM-L6-v2 and written to a "
    "<b>ChromaDB</b> collection configured for cosine similarity. Metadata (filename, "
    "document_type, section, legal references) is stored alongside each vector so results "
    "can be filtered and cited. ChromaDB persists to "
    "<font face='Courier'>./data/chroma_db</font> on disk, so ingestion only happens once.",
    styles["Body"]))
story.append(Spacer(1, 2))
story.append(kv_table([
    ("Input formats", "PDF, TXT, DOCX"),
    ("Splitting", "Boundary-aware (section → paragraph → sentence) with overlap"),
    ("Embedding model", "all-MiniLM-L6-v2 (384 dimensions, runs locally)"),
    ("Storage", "ChromaDB persistent collection, cosine similarity"),
    ("Metadata kept", "filename, document_type, section, legal_references, char offsets"),
]))
story.append(PageBreak())

# ===== 05 RETRIEVAL =====
story += h1(5, "Step 2 — Retrieval: Hybrid Search with Citations")
story.append(Paragraph(
    "When a question arrives, the retriever's job is to surface the handful of chunks most "
    "likely to contain the answer. Code lives in "
    "<font face='Courier'>src/retrieval/retriever.py</font>.", styles["Body"]))

story.append(Paragraph("Why hybrid, not pure semantic", styles["H3"]))
story.append(Paragraph(
    "Semantic search alone struggles with exact references. Ask for “Article 17 of GDPR” and "
    "pure vector similarity tends to surface broadly related material about data rights — not "
    "the specific article. Keyword matching catches the literal “Article 17” that semantics "
    "miss. <b>HybridRetriever</b> runs semantic search first, then nudges the ranking up for "
    "chunks that also contain the query's keywords. Semantic relevance leads; keyword matches "
    "act as a tie-breaker so exact references float to the top.", styles["Body"]))

story.append(Paragraph("The retrieval strategies", styles["H3"]))
story.append(bullets([
    "<b>semantic</b> — pure nearest-vector search in ChromaDB.",
    "<b>hybrid</b> (default) — semantic results, then a light keyword boost for chunks that "
    "contain the query's meaningful terms (stop-words removed).",
    "<b>keyword</b> — a BM25-style scorer that counts term frequencies and blends them with "
    "the semantic score (roughly 60% semantic, 40% keyword).",
]))

story.append(Paragraph("Adding citations — CitationRetriever", styles["H3"]))
story.append(Paragraph(
    "<b>CitationRetriever</b> wraps the hybrid retriever and, for every result, builds a "
    "human-readable citation from its metadata — e.g. "
    "<font face='Courier'>[1] GDPR - Article 17... (Source: GDPR_Sample.txt)</font>. It also "
    "keeps the raw cosine similarity for ranking while presenting a rescaled, more intuitive "
    "0–1 relevance score in the UI. These citation strings are what later appear under each "
    "answer, so every claim links back to a specific source.", styles["Body"]))
story.append(callout(
    "Why this matters for the whole project",
    "Citations aren't decoration — they are the product. The entire reason the system exists "
    "is that compliance answers must be traceable. Retrieval is where that traceability is "
    "manufactured: every chunk carries its origin, and that origin rides all the way to the "
    "final answer.", color=ACCENT))
story.append(PageBreak())

# ===== 06 AGENT =====
story += h1(6, "Step 3 — The Agent: A LangGraph State Machine")
story.append(Paragraph(
    "This is the heart of the project. The agent is built as a <b>LangGraph StateGraph</b> — "
    "an explicit state machine with nodes (steps) and edges (transitions). Code lives in "
    "<font face='Courier'>src/agents/compliance_agent.py</font>.", styles["Body"]))

story.append(Paragraph("The shared state", styles["H3"]))
story.append(Paragraph(
    "Every node reads and writes one shared <b>ComplianceState</b> object that travels "
    "through the graph. It carries the query, the retrieved docs, the draft answer, the "
    "reflection text, and the iteration counter — so each step builds on the last.",
    styles["Body"]))

story.append(Paragraph("The nodes", styles["H3"]))
story.append(bullets([
    "<b>retrieve</b> — calls the hybrid retriever, stores the top-k chunks in state.",
    "<b>generate</b> — builds a system prompt that demands citations and forbids speculation, "
    "appends the question and the retrieved context, and calls gpt-4o-mini. The LLM can also "
    "request <b>tools</b> here.",
    "<b>reflect</b> — a second LLM call that reviews the draft: are claims cited? Any "
    "speculation? Contradictions? Anything missing? It returns a short critique.",
    "<b>tools</b> — a ToolNode exposing helper tools (search a specific article, cross-"
    "reference regulations, extract requirements, etc.).",
]))

story.append(Paragraph("The edges — how it decides", styles["H3"]))
story.append(Paragraph(
    "The flow isn't fixed; conditional edges route based on state. After <b>generate</b>, the "
    "agent checks: did the LLM ask to call a tool? → go to <b>tools</b>, then back to "
    "generate. Otherwise → go to <b>reflect</b>. After <b>reflect</b>, it checks whether the "
    "critique flagged problems (words like “missing”, “incomplete”, “unsupported”). If so and "
    "the iteration budget isn't spent, it loops back to <b>retrieve</b> to try again; "
    "otherwise it ends.", styles["Body"]))
story.append(Spacer(1, 2))
graph = """          +-----------+
 entry --> | retrieve  |
          +-----------+
                |
                v
          +-----------+      tool call?      +-------+
          | generate  | -----------------> | tools |
          +-----------+ <----------------- +-------+
                |
                | no tool call
                v
          +-----------+   needs work? & budget left
          |  reflect  | ----------------------------> back to retrieve
          +-----------+
                |
                | good enough OR max iterations
                v
              END  ->  final answer + citations"""
story.append(code_block(graph))
story.append(callout(
    "Why LangGraph instead of a plain LangChain agent",
    "The older agent APIs don't give fine-grained control over the execution loop. LangGraph "
    "lets you define explicit state transitions and conditional edges — exactly what the "
    "self-reflection loop needs. Without it, the agent either always reflects or never does. "
    "With it, reflection fires only when the answer fails a quality check."))
story.append(Paragraph("Two agents, one system", styles["H3"]))
story.append(Paragraph(
    "There's also a <b>SimpleComplianceAgent</b>: a one-shot retrieve-then-answer path with "
    "no graph and no reflection, selectable via "
    "<font face='Courier'>use_simple_agent: true</font>. It's the baseline — useful for fast "
    "answers and for showing, by contrast, what the reflection loop adds.", styles["Body"]))
story.append(PageBreak())

# ===== 07 MEMORY & GRAPH =====
story += h1(7, "Step 4 — Memory & the Knowledge Graph")
story.append(Paragraph(
    "Two optional subsystems give the agent context beyond a single question. Both are "
    "designed to degrade gracefully — if the service isn't running, the system keeps working.",
    styles["Body"]))

story.append(Paragraph("Redis — conversation memory", styles["H3"]))
story.append(Paragraph(
    "<b>RedisMemory</b> (in <font face='Courier'>src/memory/redis_memory.py</font>) stores "
    "each session's messages under a key like "
    "<font face='Courier'>session:&lt;id&gt;:messages</font>, with a one-hour TTL. Fast "
    "key-value lookup means conversation history is cheap to read back. Crucially, if Redis "
    "isn't reachable it silently falls back to <b>ConversationBufferMemory</b>, a plain "
    "in-process dictionary — single-session use works with zero infrastructure.", styles["Body"]))

story.append(Paragraph("Neo4j — the compliance knowledge graph", styles["H3"]))
story.append(Paragraph(
    "Compliance data is naturally a graph: Regulations <i>contain</i> Articles, Articles "
    "<i>specify</i> Requirements, Articles <i>cross-reference</i> each other across "
    "regulations. <b>ComplianceKnowledgeGraph</b> (in "
    "<font face='Courier'>neo4j_graph.py</font>) models exactly that with node types "
    "(Regulation, Article, Requirement, Entity) and typed relationships (CONTAINS, "
    "SPECIFIES, REFERENCES).", styles["Body"]))
story.append(Paragraph(
    "Why a graph and not a relational table? A question like “what do <i>both</i> GDPR and "
    "HIPAA say about breach notification?” is a multi-level join in SQL but a simple two-hop "
    "traversal in Neo4j. Like Redis, it has a dictionary-based fallback if the database is "
    "offline, so graph features simply switch off rather than crash the app.", styles["Body"]))
story.append(callout(
    "A design principle the author would keep",
    "“Redis and Neo4j add real operational complexity.” Early versions crashed if either "
    "service was down. Adding graceful degradation — in-memory fallback for Redis, disabling "
    "graph features when Neo4j is absent — is what made the system usable without the full "
    "stack. The takeaway: design optional services as optional from day one."))
story.append(PageBreak())

# ===== 08 SERVING =====
story += h1(8, "Step 5 — Serving It: API & UI")
story.append(Paragraph(
    "The agent is wrapped in a REST API and a web UI so it's usable by both machines and "
    "people.", styles["Body"]))

story.append(Paragraph("FastAPI — src/api/main.py", styles["H3"]))
story.append(Paragraph(
    "On startup the API builds the vector store, retriever, tools, agent, and memory once and "
    "keeps them in memory. It exposes a small, focused set of endpoints:", styles["Body"]))
story.append(Spacer(1, 2))
story.append(data_table(
    ["Method & Path", "What it does"],
    [
        ["POST /query", "Ask a compliance question; returns answer, sources, citations, iterations"],
        ["GET /search", "Raw chunk search with optional document_type filter"],
        ["GET /conversation/{id}", "Fetch a session's message history"],
        ["DELETE /conversation/{id}", "Clear a session"],
        ["GET /stats", "Collection stats (chunk count, embedding dim, active sessions)"],
        ["GET /regulations", "List supported regulations"],
        ["GET /health", "Component-by-component health check"],
        ["POST /ingest", "Ingest a new document in the background"],
    ],
    [55*mm, 115*mm]))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "The <font face='Courier'>/query</font> handler ties everything together: it records the "
    "user message in memory, picks the full agent or the simple agent, runs it, stores the "
    "assistant reply, and returns a structured response.", styles["Body"]))

story.append(Paragraph("Streamlit — ui/streamlit_app.py", styles["H3"]))
story.append(Paragraph(
    "The UI is the friendly front door: a text box for the question, a Submit button, and a "
    "results panel that shows the answer with its source document and article reference "
    "underneath. A sidebar surfaces settings and system stats, and a history view shows past "
    "turns. It talks to the FastAPI server over HTTP — the same endpoints any other client "
    "would use.", styles["Body"]))
story.append(callout(
    "How the pieces run together",
    "1) python setup.py loads documents into ChromaDB.  2) python src/api/main.py starts the "
    "API on :8000.  3) streamlit run ui/streamlit_app.py opens the UI on :8501. Redis and "
    "Neo4j are optional; without them the system uses its fallbacks.", color=ACCENT))
story.append(PageBreak())

# ===== 09 EVALUATION =====
story += h1(9, "Evaluation: Measuring Quality with RAGAS")
story.append(Paragraph(
    "A compliance tool you can't measure is a compliance tool you can't trust. The project "
    "includes a <b>RAGAS</b>-based evaluation pipeline (in "
    "<font face='Courier'>src/evaluation/ragas_eval.py</font>) that runs a fixed set of test "
    "questions with known-good answers and scores the system on four axes.", styles["Body"]))
story.append(Spacer(1, 2))
story.append(data_table(
    ["Metric", "The question it answers"],
    [
        ["Faithfulness", "Are answers grounded in the retrieved docs, not hallucinated?"],
        ["Answer Relevancy", "Does the answer actually address the question asked?"],
        ["Context Recall", "Are the right chunks being retrieved in the first place?"],
        ["Citation Accuracy", "Are the article/section references correct?"],
    ],
    [45*mm, 125*mm]))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "The test set covers real questions across all three regulations — the right to erasure "
    "under GDPR, Protected Health Information under HIPAA, the five Trust Services Criteria in "
    "SOC2 — each paired with a ground-truth answer. Running "
    "<font face='Courier'>python ragas_eval.py</font> produces the scores. Faithfulness "
    "doubles as the signal the reflection loop uses: when retrieved chunks score poorly "
    "against the draft, the agent retries.", styles["Body"]))
story.append(PageBreak())

# ===== 10 DESIGN DECISIONS =====
story += h1(10, "Design Decisions & Lessons")
story.append(Paragraph(
    "The interesting part of any build is the <i>why</i>. These are the choices that shaped "
    "the system and the things that turned out to be hard.", styles["Body"]))

story.append(Paragraph("Decisions", styles["H2"]))
story.append(Paragraph("Why LangGraph over plain LangChain agents", styles["H3"]))
story.append(Paragraph(
    "Fine-grained control over the execution loop. Explicit state transitions and conditional "
    "edges are what make a <i>conditional</i> reflection step possible.", styles["Body"]))
story.append(Paragraph("Why hybrid retrieval", styles["H3"]))
story.append(Paragraph(
    "Pure semantic search missed exact article references. Blending in keyword matching and "
    "reranking the combined results noticeably improved precision on targeted queries.",
    styles["Body"]))
story.append(Paragraph("Why Neo4j for the knowledge graph", styles["H3"]))
story.append(Paragraph(
    "Cross-regulation relationships are graph traversals, not table joins. Two-hop queries "
    "stay simple where SQL would need multi-level joins.", styles["Body"]))
story.append(Paragraph("Why Redis for session memory", styles["H3"]))
story.append(Paragraph(
    "Fast key-value history per session, with graceful in-memory fallback so the system runs "
    "without it.", styles["Body"]))

story.append(Paragraph("What was hard", styles["H2"]))
story.append(bullets([
    "<b>Making the reflection loop terminate reliably.</b> Defining “good enough” was the "
    "crux. Too strict and it loops forever; too loose and it never catches a bad answer. "
    "RAGAS faithfulness against a threshold became the exit signal — and tuning that "
    "threshold took many runs.",
    "<b>Tuning hybrid retrieval.</b> Merging two ranked lists without reranking just gives "
    "you two noisy lists stapled together. A weighted combination that favours semantic "
    "similarity but boosts exact article-number matches worked best.",
    "<b>Operational complexity of Redis and Neo4j.</b> Retrofitting graceful degradation "
    "taught the lesson to design optional services as optional from the start.",
    "<b>Chunking beats model tuning.</b> Time spent on the LLM was wasted while retrieval was "
    "the bottleneck; boundary-aware chunking moved the needle far more.",
]))

story.append(Paragraph("What's next", styles["H2"]))
story.append(bullets([
    "Streaming responses, so long agent chains feel responsive instead of blocking.",
    "A Docker Compose setup to bring up API + Redis + Neo4j + ChromaDB in one command.",
    "Drag-and-drop document upload in the UI for non-technical users.",
    "API authentication — fine locally, a blocker for any real deployment.",
]))
story.append(PageBreak())

# ===== 11 GLOSSARY =====
story += h1(11, "Glossary")
gloss = [
    ("Agentic", "A system that decides its own next step (e.g. whether to reflect and retry) rather than running a fixed pipeline."),
    ("Embedding", "A fixed-length numeric vector that captures the meaning of a piece of text. Here, 384 dimensions."),
    ("Vector store", "A database (ChromaDB) that stores embeddings and answers nearest-neighbour queries by similarity."),
    ("Cosine similarity", "A measure of how close two vectors point in the same direction; used to rank relevance."),
    ("RAG", "Retrieval-Augmented Generation — retrieve relevant text, then have the LLM answer using it."),
    ("Hybrid retrieval", "Combining semantic (vector) search with keyword matching, then reranking the merged results."),
    ("BM25", "A classic keyword-relevance scoring formula based on term frequency."),
    ("Chunk", "A bounded piece of a document, split on natural boundaries, that gets embedded and stored."),
    ("LangGraph", "A framework for building agents as explicit state machines with nodes and conditional edges."),
    ("StateGraph / node / edge", "The graph (StateGraph), its steps (nodes), and the transitions between them (edges)."),
    ("Reflection", "A second LLM pass that critiques the draft answer and can trigger a retry."),
    ("Citation", "A source reference (regulation, article/section, filename) attached to each retrieved chunk and answer."),
    ("Knowledge graph", "A graph of entities and typed relationships (Neo4j) modelling how regulations relate."),
    ("Graceful degradation", "Continuing to work with reduced features when an optional service (Redis/Neo4j) is unavailable."),
    ("RAGAS", "An evaluation framework scoring RAG systems on faithfulness, relevancy, recall, and precision."),
    ("gpt-4o-mini", "The OpenAI model used for generation and reflection — fast, cheap, strong reasoning."),
]
for term, desc in gloss:
    row = Table([[
        Paragraph(f"<b>{term}</b>", ParagraphStyle("gt", fontName="Helvetica-Bold",
                  fontSize=9.5, textColor=ACCENT2, leading=13)),
        Paragraph(desc, ParagraphStyle("gd", fontName="Helvetica", fontSize=9.5,
                  textColor=INK, leading=13)),
    ]], colWidths=[42*mm, 128*mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(row)
story.append(Spacer(1, 14))
story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=10))
story.append(Paragraph(
    "You now have the full arc: the problem, the concepts, the pipeline stage by stage, and "
    "the reasoning behind every major choice. The single thread tying it together — "
    "<i>retrieve, ground, cite, and self-check</i> — is what turns a chatbot into a "
    "compliance auditor you can actually trust.", styles["Note"]))

# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
doc = SimpleDocTemplate(
    "Agentic_Compliance_Auditor_Guide.pdf",
    pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=22*mm, bottomMargin=20*mm,
    title="Agentic Compliance Auditor — Project Guide",
    author="Balaji V",
)

def first_page(canvas, doc):
    on_cover(canvas, doc)

doc.build(story, onFirstPage=first_page, onLaterPages=on_page)
print("PDF written: Agentic_Compliance_Auditor_Guide.pdf")
