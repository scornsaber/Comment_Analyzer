# Comment Analyzer – UML Diagrams (DB-less)

Below are activity, sequence, state, component, and deployment diagrams for the DB-less version of the Comment Analyzer.

---

## Activity Diagram 1 – Fetch YouTube Comments
```mermaid
flowchart TD
    A[Start] --> B[User enters YouTube URL or ID]
    B --> C{Extract video ID}
    C -->|valid| D[Build API request URL]
    C -->|invalid| E[Show validation error]\nReturn
    D --> F{API key present?}
    F -->|No| E2[Prompt for API key / creds]\nReturn
    F -->|Yes| G[Call YouTube commentThreads API]
    G --> H{HTTP 200?}
    H -->|No| I[Parse error payload -> Show readable error]\nReturn
    H -->|Yes| J[Append items to results]
    J --> K{nextPageToken?}
    K -->|Yes| G
    K -->|No| L[Normalize to DataFrame]
    L --> M[Return comments to UI]
    M --> N[End]
```



flowchart TD
    A[Start] --> B[Receive comments DataFrame]
    B --> C[Clean text (trim, lower, strip URLs/emojis)]
    C --> D[Compute metrics: count, avg length]
    D --> E[Optional: toxicity/sentiment model]
    E --> F[Aggregate by author/time/thread]
    F --> G[Select sample comments]
    G --> H[Prepare summary dict for UI]
    H --> I[Optionally export CSV/JSON]
    I --> J[Render dashboard panels]
    J --> K[End]




flowchart TD
    A[Launch app.py (Streamlit)] --> B[Render input form]
    B --> C{User clicks "Fetch"}
    C -->|No| B
    C -->|Yes| D[Call fetch_youtube.extract_video_id]
    D --> E[fetch_youtube.request() pages -> DataFrame]
    E --> F[Call analyze.summarize(df)]
    F --> G[Update UI: counts, averages, samples]
    G --> H{User clicks Export?}
    H -->|Yes| I[Write CSV/JSON to /tmp or session]
    H -->|No| J[Stay in-memory]
    I --> K[Provide download buttons]
    J --> K
    K --> L[Done]




sequenceDiagram
    actor User
    participant UI as Streamlit UI (app.py)
    participant FY as fetch_youtube.py
    participant GAPI as YouTube Data API

    User->>UI: Paste URL/ID + click Fetch
    UI->>FY: extract_video_id(url)
    FY-->>UI: video_id
    UI->>FY: request(video_id, pageToken?)
    loop Paginate until no nextPageToken
        FY->>GAPI: GET commentThreads (videoId, key, pageToken)
        GAPI-->>FY: JSON {items, nextPageToken?}
        FY-->>UI: items (append)
    end
    UI->>UI: to_dataframe(items)
    UI-->>User: Show total comments & basic stats
  



sequenceDiagram
    actor User
    participant UI as Streamlit UI (app.py)
    participant AZ as analyze.py
    participant PD as pandas

    User->>UI: Click Analyze
    UI->>AZ: summarize(df)
    AZ->>PD: compute metrics, groupbys
    PD-->>AZ: aggregates
    AZ-->>UI: summary (counts, avg length, samples)
    UI-->>User: Dashboard panels & (optional) downloads




stateDiagram-v2
    [*] --> Idle
    Idle --> Validating : Fetch clicked
    Validating --> Error : Bad URL/ID or missing key
    Validating --> Fetching : OK
    Fetching --> Error : HTTP/Quota/Network failure
    Fetching --> Analyzing : All pages received
    Analyzing --> Error : Data/processing failure
    Analyzing --> Displaying : Summary computed
    Displaying --> Exporting : User clicks export
    Exporting --> Displaying : Files ready
    Displaying --> Idle : User resets/new query
    Error --> Idle : User retries



flowchart LR
    subgraph UI[Streamlit UI (app.py)]
        UI1[Forms & Buttons]
        UI2[Pages/Panels]
        UI3[Session State]
    end

    FY[fetch_youtube.py\n- extract_video_id\n- request(url)]
    AZ[analyze.py\n- summarize(df)\n- aggregates]
    EX[Exporter\n- to_csv/json]
    CFG[Config/.streamlit]
    FS[(Local FS / Temp Files)]
    GAPI[[YouTube Data API]]

    UI1 --> FY
    FY --> GAPI
    FY --> UI2
    UI2 --> AZ
    AZ --> UI2
    EX --> FS
    UI3 --> EX
    CFG --> UI



flowchart TB
    subgraph Client
        BR[Web Browser]
    end

    subgraph Host[Dev/Prod Host]
        CNT[(Docker Container: Streamlit)]
        SRV[app.py + fetch_youtube.py + analyze.py]
        TMP[(Ephemeral Storage /tmp)]
    end

    BR <--HTTP(S)--> CNT
    CNT --> SRV
    SRV --> TMP
    SRV -->|HTTPS| GAPI[[Google YouTube Data API]]
