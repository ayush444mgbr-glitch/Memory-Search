# ─────────────────────────────────────────────────────────
# app.py
# The browser interface for your memory engine.
#
# Usage:
#   streamlit run app.py
#
# Then open http://localhost:8501 in your browser.
# ─────────────────────────────────────────────────────────

import streamlit as st
from pathlib import Path

from config import APP_TITLE, APP_ICON, WATCH_FOLDER
from ingest import ingest_folder, ingest_file, ingest_quick_note, get_stats
from query import ask, search, get_collection


# ── Page Config ───────────────────────────────────────────

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ── Custom CSS ────────────────────────────────────────────

st.markdown("""
<style>
    /* Main answer box */
    .answer-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #f8fafc;
        border-left: 5px solid #3b82f6;
        padding: 1.5rem 2rem;
        border-radius: 8px;
        margin: 1.5rem 0;
        font-size: 1.1rem;
        line-height: 1.8;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* Relevance score badge */
    .relevance-high   { color: #4ade80; font-weight: bold; background: rgba(74, 222, 128, 0.1); padding: 2px 8px; border-radius: 4px; }
    .relevance-medium { color: #fbbf24; font-weight: bold; background: rgba(251, 191, 36, 0.1); padding: 2px 8px; border-radius: 4px; }
    .relevance-low    { color: #f87171; font-weight: bold; background: rgba(248, 113, 113, 0.1); padding: 2px 8px; border-radius: 4px; }

    /* Source tag */
    .source-tag {
        display: inline-block;
        background: #f1f5f9;
        color: #334155;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 4px;
        border: 1px solid #e2e8f0;
    }

    /* Stats card */
    .stat-container {
        background: #ffffff;
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .stat-number {
        font-size: 1.75rem;
        font-weight: 800;
        color: #2563eb;
        line-height: 1;
        margin-bottom: 0.25rem;
    }

    .stat-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────

def relevance_color(score: float) -> str:
    if score >= 0.7:
        return "relevance-high"
    elif score >= 0.5:
        return "relevance-medium"
    else:
        return "relevance-low"


def relevance_bar(score: float) -> str:
    """Visual bar representing relevance score."""
    filled = int(score * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar} {score:.2f}"


@st.cache_data(ttl=30)
def get_db_stats():
    """Cache stats so they don't reload on every interaction."""
    return get_stats()


# ── Sidebar ───────────────────────────────────────────────

with st.sidebar:
    st.title(f"{APP_ICON} Memory Engine")
    st.caption("Everything you know, searchable by meaning.")

    st.divider()

    # ── Database Stats ─────────────────────────────────────
    st.subheader("📊 Memory Stats")

    stats = get_db_stats()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f'<div class="stat-container">'
            f'<div class="stat-number">{stats["total_chunks"]}</div>'
            f'<div class="stat-label">Memory chunks</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'<div class="stat-container">'
            f'<div class="stat-number">{stats["total_sources"]}</div>'
            f'<div class="stat-label">Source files</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Quick Note ─────────────────────────────────────────
    st.subheader("✍️ Quick Note")
    st.caption("Type a thought and hit Remember. It's instantly searchable.")

    quick_note = st.text_area(
        "Note",
        placeholder="Had a great idea about...\nMet someone interesting named...\nRemember to look into...",
        height=100,
        label_visibility="collapsed"
    )
    note_tag = st.text_input("Tag (optional)", placeholder="work, personal, idea...")

    if st.button("💾 Remember This", use_container_width=True):
        if quick_note.strip():
            with st.spinner("Storing..."):
                count = ingest_quick_note(quick_note, tag=note_tag)
            if count > 0:
                st.success("✓ Remembered!")
                st.cache_data.clear()
            else:
                st.info("Already in memory.")
        else:
            st.warning("Write something first.")

    st.divider()

    # ── Ingest Folder ──────────────────────────────────────
    st.subheader("📁 Ingest Files")

    folder_input = st.text_input(
        "Folder path",
        value=WATCH_FOLDER,
        help="Path to your notes folder. Will ingest all .md, .txt, .pdf, .png, .jpg files."
    )

    if st.button("⬆️ Ingest Folder", use_container_width=True):
        if folder_input.strip():
            with st.spinner(f"Ingesting {folder_input}..."):
                count = ingest_folder(folder_input)
            st.success(f"✓ Done! Added {count} new chunks.")
            st.cache_data.clear()
        else:
            st.warning("Enter a folder path.")

    # Upload a single file
    st.caption("Or upload a single file:")
    uploaded = st.file_uploader(
        "Upload file",
        type=["txt", "md", "pdf", "png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

    if uploaded is not None:
        # Save to temp location, ingest, done
        tmp_path = Path(f"./data/uploads/{uploaded.name}")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(uploaded.read())

        if st.button("⬆️ Ingest This File", use_container_width=True):
            with st.spinner(f"Ingesting {uploaded.name}..."):
                count = ingest_file(str(tmp_path))
            if count > 0:
                st.success(f"✓ Ingested {count} chunks from {uploaded.name}")
                st.cache_data.clear()
            else:
                st.info("Already in memory.")

    st.divider()

    # ── Source Browser ─────────────────────────────────────
    if stats["sources"]:
        with st.expander(f"📚 All Sources ({stats['total_sources']})"):
            for source in stats["sources"]:
                st.caption(f"• {source}")


# ── Main Area ─────────────────────────────────────────────

st.title(APP_TITLE)
st.caption("Ask anything. Your memory answers.")

# ── Search Bar ─────────────────────────────────────────────

question = st.text_input(
    "Ask your memory:",
    placeholder="Who did I meet at the conference?   |   What did I write about focus last year?   |   What books mentioned stoicism?",
    key="main_question"
)

col_ask, col_raw, col_clear = st.columns([2, 2, 1])

with col_ask:
    ask_button = st.button("🔍 Ask Memory", type="primary", use_container_width=True)

with col_raw:
    raw_button = st.button("📄 Show Raw Chunks", use_container_width=True)

with col_clear:
    if st.button("✕ Clear", use_container_width=True):
        st.session_state["main_question"] = ""
        st.rerun()

st.divider()


# ── Check if DB is empty ───────────────────────────────────

collection = get_collection()
if collection is None or collection.count() == 0:
    st.info(
        "**No memories yet.** \n\n"
        "To get started:\n"
        "1. Put some notes in `./data/notes/` (or any folder)\n"
        "2. Click **Ingest Folder** in the sidebar\n"
        "3. Or type a quick note above and hit **Remember This**\n\n"
        "Then come back here and ask a question."
    )
    st.stop()


# ── Answer ─────────────────────────────────────────────────

if ask_button and question.strip():
    with st.status("🧠 Searching memory and thinking...", expanded=True) as status:
        # Step 1: Search (Embed + Retrieve)
        stream_gen, chunks = ask(question, stream=True)
        
        # Step 2: Stream the answer
        st.subheader("💬 Answer")
        
        def stream_with_status():
            for i, chunk in enumerate(stream_gen):
                if i == 0:
                    status.update(label="Generating answer...", state="running")
                yield chunk["message"]["content"]

        full_answer = st.write_stream(stream_with_status())
        status.update(label="Done!", state="complete", expanded=False)

    # Apply the styling to the completed answer if it exists
    if full_answer:
        st.markdown(
            f'<div class="answer-box">{full_answer}</div>',
            unsafe_allow_html=True
        )

    # Step 5: Collect unique source files (locally here since ask returned a stream)
    sources = []
    seen = set()
    for chunk in chunks:
        s = chunk["source"]
        if s not in seen:
            seen.add(s)
            sources.append({
                "name": s,
                "path": chunk["file_path"],
                "type": chunk["file_type"]
            })

    # Sources used
    if sources:
        st.markdown("**Sources used:**")
        source_html = ""
        for s in sources:
            source_html += f'<span class="source-tag">📄 {s["name"]}</span> '
        st.markdown(source_html, unsafe_allow_html=True)

    # Open source file button (if it's a local file)
    for s in sources:
        if s["path"] and Path(s["path"]).exists():
            st.caption(f"📂 Full path: `{s['path']}`")

    st.divider()

    # Memory fragments used
    st.subheader("🧩 Memory Fragments Used")
    st.caption("These are the exact chunks retrieved from your notes that were fed to the AI.")

    for i, chunk in enumerate(chunks, 1):
        score = chunk["relevance"]
        color_class = relevance_color(score)

        with st.expander(
            f"Fragment {i} — {chunk['source']} — relevance: {score:.2f}",
            expanded=(i == 1)  # expand first one by default
        ):
            st.markdown(
                f'<span class="{color_class}">Relevance: {relevance_bar(score)}</span>',
                unsafe_allow_html=True
            )
            st.markdown(f"**Source:** `{chunk['source']}`")
            if chunk["total_chunks"] > 1:
                st.caption(f"Chunk {chunk['chunk_index']+1} of {chunk['total_chunks']}")
            st.markdown("---")
            st.write(chunk["text"])

            # Open original file
            if chunk["file_path"] and Path(chunk["file_path"]).exists():
                st.caption(f"📂 `{chunk['file_path']}`")


# ── Raw Chunk View (debug mode) ────────────────────────────

elif raw_button and question.strip():
    with st.spinner("Searching..."):
        chunks = search(question)

    st.subheader(f"📄 Raw Search Results for: \"{question}\"")
    st.caption(f"{len(chunks)} chunks found above minimum similarity threshold")

    if not chunks:
        st.warning("No relevant chunks found. Try a different question or ingest more notes.")
    else:
        for i, chunk in enumerate(chunks, 1):
            score = chunk["relevance"]
            with st.expander(f"#{i} — {chunk['source']} — {score:.3f}", expanded=True):
                st.progress(score, text=f"Relevance: {score:.3f}")
                st.write(chunk["text"])
                if chunk["file_path"]:
                    st.caption(f"📂 `{chunk['file_path']}`")


# ── Empty State ────────────────────────────────────────────

elif not question.strip():
    st.markdown("### 💡 Example questions to try:")

    examples = [
        "Who have I met that works in tech?",
        "What did I write about when I was feeling overwhelmed?",
        "What ideas did I capture about my project?",
        "What books or articles mentioned productivity?",
        "What was I working on in the last few months?",
        "Who should I follow up with?",
    ]

    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(f"🔍 {example}", use_container_width=True, key=f"example_{i}"):
                st.session_state["main_question"] = example
                st.rerun()
