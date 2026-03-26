
# 🧠 Memory Search Engine (Semantic Document Retrieval)

## 📌 Overview

The **Memory Search Engine** is an AI-powered system that enables users to search documents and notes based on **semantic meaning** rather than exact keyword matching.

It uses **vector embeddings and similarity search** to retrieve the most relevant information, making it significantly more powerful than traditional search systems.

---

## 🚀 Features

* 🔍 **Semantic Search** – Understands intent, not just keywords
* 📄 **Document Ingestion Pipeline** – Automatically processes and indexes files
* 🧠 **Embedding-Based Retrieval** – Converts text into vector representations
* ⚡ **Fast Query System** – Efficient similarity-based search
* 📊 **Debug & Inspection Tools** – Analyze scores and database behavior
* 🧪 **Testing Support** – Includes test scripts for validation
* ⚙️ **Configurable System** – Centralized configuration for flexibility

---

## 🛠️ Tech Stack

* **Backend:** Python
* **NLP Model:** Sentence Transformers (HuggingFace)
* **Vector Database:** ChromaDB / FAISS
* **Other Tools:** NumPy, OS, Custom utilities

---

## 📂 Project Structure

```bash
memory-search-engine/
│
├── app.py              # Main application (entry point)
├── config.py           # Configuration settings
├── ingest.py           # Document ingestion & indexing pipeline
├── query.py            # Semantic search logic
├── watcher.py          # Monitors changes in data directory
│
├── debug_scores.py     # Debug similarity scores
├── inspect_db.py       # Inspect vector database contents
│
├── test_query.py       # Test query functionality
├── test_diagnostic.py  # Diagnostic tests
│
├── requirements        # Project dependencies
├── .gitignore         # Ignored files
│
├── data/              # Stored documents
├── venv/              # Virtual environment (ignored)
├── __pycache__/       # Python cache (ignored)
```

---

## ⚙️ How It Works

### 1️⃣ Document Ingestion

* Files are loaded from the `data/` directory
* Text is cleaned and split into chunks
* Each chunk is converted into embeddings

### 2️⃣ Vector Storage

* Embeddings are stored in a vector database
* Enables fast similarity-based retrieval

### 3️⃣ Query Processing

* User query → converted to embedding
* Compared with stored vectors
* Returns most relevant results

---

## ▶️ How to Run

### 1. Clone Repository

```bash
git clone https://github.com/your-username/memory-search-engine.git
cd memory-search-engine
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements
```

### 4. Run Application

```bash
python app.py
```

---

## 🧪 Testing & Debugging

### Run Query Test

```bash
python test_query.py
```

### Run Diagnostic Test

```bash
python test_diagnostic.py
```

### Debug Similarity Scores

```bash
python debug_scores.py
```

### Inspect Database

```bash
python inspect_db.py
```

---

## 📊 Example

**Query:**

```
What is artificial intelligence?
```

**Result:**

* Retrieves semantically related documents
* Even if exact words are not present

---

## 💡 Use Cases

* 📚 Personal knowledge base
* 🎓 Student notes search
* 🧾 Document retrieval systems
* 🤖 AI assistants
* 🏢 Enterprise search systems

---

## 🔥 Future Improvements

* 🤖 Add LLM-based Q&A (RAG system)
* 🌐 Web-based UI interface
* 📂 Support for more file types (PDF, DOCX)
* ☁️ Cloud deployment
* 🔐 User authentication

---

## ⚠️ Notes

* `venv/` and `__pycache__/` are excluded using `.gitignore`
* Ensure data files are placed inside the `data/` directory

---

## 🧑‍💻 Author

**Ayush Kumar**
B.Tech Student | Data Science Enthusiast

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
