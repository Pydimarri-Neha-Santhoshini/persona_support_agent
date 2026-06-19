# Adaptive Customer Support Agent

I built this customer support assistant to handle user queries by matching their communication style (Technical Expert, Frustrated User, or Business Executive). It searches a local document database to find answers. If it doesn't find the answer, detects a sensitive keyword (like a legal threat or billing issue), or if the user stays frustrated for too long, it pauses and creates a structured JSON handoff ticket for a human agent.

---

## Tech Stack & Versions

Here are the main tools and libraries I used to build this:
* **Python 3.11+** - Core programming language.
* **Streamlit (v1.30.0+)** - For the chat user interface.
* **Google GenAI SDK (v0.1.1+)** - For classification, tone adjustment, and ticket generation.
* **ChromaDB (v0.4.22+)** - To save and search document vectors locally.
* **LangChain Text Splitters (v0.0.1+)** - For chunking text files into manageable pieces.
* **PyPDF (v3.17.0+)** - To read data from PDF documents.
* **python-dotenv (v1.0.0+)** - To load API keys from the `.env` file.

---

## Architecture Diagram

Here is how a message moves through the system from start to finish:
```text
[User Query]
     │
     ▼
[Persona Detection]
     │
     ▼
[Retrieval]
     │
     ▼
[Response Generation]
     │
     ▼
[Escalation Check]
     │
     ▼
[Human Handoff]
```


1. **User Query**: The customer types a message.
2. **Persona Detection**: The system classifies the user's tone/persona.
3. **Retrieval**: The chatbot searches local documents using ChromaDB.
4. **Response Generation**: The bot forms an answer using the retrieved info in the user's specific tone.
5. **Escalation Check**: The system checks if any rules (like low confidence or sensitive keywords) require a human helper.
6. **Human Handoff**: If triggered, it stops the chatbot and creates a structured JSON ticket.

---

## Persona Detection Strategy

* **Classification Method**: I used `gemini-3.5-flash` with the Gemini API's Structured Outputs feature. By passing a JSON schema, it always returns a clean JSON block with the persona name, a confidence rating (0 to 1), and the reasoning behind its choice.
* **Prompt Design**: The prompt instructs the model to look at the phrasing, punctuation, and terminology in the user's message to decide which class it fits into.
* **Rules Used**:
  * **Technical Expert**: Uses code snippets, technical jargon, mentions specific error codes, configurations, or APIs.
  * **Frustrated User**: Uses angry words, all-caps, exclamation marks, or demands immediate help.
  * **Business Executive**: Keeps statements brief, professional, and focuses on timelines, outcomes, and high-level summaries.

---

## RAG Pipeline Design

* **Chunking Strategy**: I used LangChain's `RecursiveCharacterTextSplitter` to split TXT, MD, and PDF documents into small chunks of **500 characters** with a **50-character overlap** to preserve context at the borders.
* **Embedding Model**: I chose Google's `gemini-embedding-001` model to turn these text chunks into 768-dimensional mathematical vectors.
* **Vector Database Choice**: I went with **ChromaDB** because it's lightweight, runs completely locally in the workspace (`chroma_db/` folder), and doesn't require any cloud accounts or keys.
* **Retrieval Strategy**: When a user asks a question, the query is converted into a vector and matched against the database. The system retrieves the top **3** most relevant chunks based on cosine similarity.

---

## Escalation Logic

* **Escalation Triggers**:
  1. **Sensitive Topics**: Immediate handoff if the query contains keywords like `refund`, `billing`, `sue`, `lawsuit`, `hack`, `breach`, or `stolen password`. I used regex word boundaries (`\b`) to make sure letters inside normal words (like "sue" inside "issue") don't cause false handoffs.
  2. **Low Confidence**: If the best matching document's similarity score is below `0.45`, it means the answer isn't in our docs, so the bot escalates.
  3. **Frustration Limit**: If the user is classified as "Frustrated User" for `2` turns in a row, the bot hands them off to a human.
  4. **Grounding Check**: If the model finds document segments but determines they don't answer the user's specific question, it triggers a handoff.
* **Confidence Thresholds**:
  * I set the minimum acceptable match score to **0.45** (computed as `1.0 - cosine_distance`).

---

## Setup Instructions

1. **Clone/Open the Project Folder** in your terminal.
2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate the Environment**:
   * Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
   * macOS/Linux: `source venv/bin/activate`
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Set up Environment Variables** (see details below).
6. **Launch the Streamlit App**:
   ```bash
   streamlit run app.py
   ```
   This will open the user interface at `http://localhost:8501`.

---

## Environment Variables

Create a file named `.env` in the root folder of the project and add your API key:

```env
GEMINI_API_KEY="your-google-gemini-api-key"
```

---

## Example Queries to Test

You can try these queries in the Streamlit app to see different outcomes:

1. **Technical Expert**:
   > *"What are the header parameter requirements for your bearer token auth implementation?"*
   > *(Result: Tone classified as Technical. Replies with code parameters and format details.)*
2. **Frustrated User**:
   > *"Where is the guide to clear cookies? It's been an hour and nothing is loading on your interface!"*
   > *(Result: Tone classified as Frustrated. Replies with a polite apology and simple steps.)*
3. **Business Executive**:
   > *"Our operational uptime is decreasing. We need a timeline of when billing disputes are resolved."*
   > *(Result: Tone classified as Business Executive. Replies with a brief, high-level outline.)*
4. **Immediate Billing Escalation**:
   > *"My billing statement has unexpected duplicate charges. I demand an immediate refund!"*
   > *(Result: Triggers billing/refund keywords, pauses the chatbot, and shows a structured handoff ticket.)*
5. **Out-of-Domain Escalation**:
   > *"Can you give me a recipe for chocolate chip cookies?"*
   > *(Result: Document similarity score drops below 0.45, prompting the system to hand off to a human.)*

---

## Known Limitations & Future Improvements

**Session Memory**: Conversations and escalation flags are saved in Streamlit's temporary memory. If you refresh the web tab, the chat is cleared. I could save chat histories in a database like SQLite or Redis.
**Database File Locks**: ChromaDB runs as a local file SQLite instance. If indexing scripts and the web app try to write or read at the exact same millisecond, file locking issues can happen. Moving to a hosted database (like Pinecone) would solve this.
**Full Index Rebuilds**: The ingestion script deletes and rebuilds the database from scratch each time. Using file hashing to track changed documents would allow faster incremental indexing.
