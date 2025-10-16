# Comment Analyzer – UML Diagrams (DB-less)

Below are activity, sequence, state, component, and deployment diagrams for the DB-less version of the Comment Analyzer.

---

## Activity Diagram 1 – Fetch YouTube Comments
```mermaid
flowchart TD
    A[Start] --> B[User enters YouTube URL or ID]
    B --> C{Extract video ID}
    C -->|valid| D[Build API request URL]
    C -->|invalid| E[Show validation error]
    E --> R1[Return]
    D --> F{API key present?}
    F -->|No| E2[Prompt for API key or credentials]
    E2 --> R2[Return]
    F -->|Yes| G[Call YouTube commentThreads API]
    G --> H{HTTP 200?}
    H -->|No| I[Parse API error and show message]
    I --> R3[Return]
    H -->|Yes| J[Append items to results]
    J --> K{nextPageToken?}
    K -->|Yes| G
    K -->|No| L[Normalize results to DataFrame]
    L --> M[Return comments to UI]
    M --> N[End]
```


```mermaid
flowchart TD
    A[Start] --> B[Receive comments DataFrame]
    B --> C[Clean text – trim, lowercase, remove URLs and emojis]
    C --> D[Compute metrics – count and avg length]
    D --> E[Optional step – toxicity or sentiment]
    E --> F[Aggregate by author, time, thread]
    F --> G[Select sample comments]
    G --> H[Prepare summary data for UI]
    H --> I[Optional export – CSV or JSON]
    I --> J[Render dashboard panels]
    J --> K[End]
```


```mermaid
A[Launch app.py (Streamlit)] --> B[Render input form]
    B --> C{User clicks "Fetch"?}
    C -->|No| B
    C -->|Yes| D[extract_video_id called]
    D --> E[Fetch pages and build DataFrame]
    E --> F[Summarize data]
    F --> G[Update UI – counts, averages, samples]
    G --> H{User clicks Export?}
    H -->|Yes| I[Write CSV or JSON to temp storage]
    H -->|No| J[Keep in memory]
    I --> K[Provide download buttons]
    J --> K
    K --> L[Done]
```


```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI (app.py)
    participant FY as fetch_youtube.py
    participant GAPI as YouTube Data API

    User->>UI: Paste URL/ID and click Fetch
    UI->>FY: extract_video_id(url)
    FY-->>UI: video_id
    UI->>FY: request(video_id, pageToken?)
    loop Paginate until no nextPageToken
        FY->>GAPI: GET commentThreads(videoId, key, pageToken)
        GAPI-->>FY: JSON items and nextPageToken?
        FY-->>UI: items (append)
    end
    UI->>UI: to_dataframe(items)
    UI-->>User: Show totals and basic stats
```


```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI (app.py)
    participant AZ as analyze.py
    participant PD as pandas

    User->>UI: Click Analyze
    UI->>AZ: summarize(df)
    AZ->>PD: compute metrics and groupbys
    PD-->>AZ: aggregates
    AZ-->>UI: summary (counts, avg length, samples)
    UI-->>User: Dashboard panels and optional downloads
```


```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Validating : Fetch clicked
    Validating --> Error : Bad URL/ID or missing key
    Validating --> Fetching : OK
    Fetching --> Error : HTTP, quota, or network failure
    Fetching --> Analyzing : All pages received
    Analyzing --> Error : Processing failure
    Analyzing --> Displaying : Summary computed
    Displaying --> Exporting : User clicks Export
    Exporting --> Displaying : Files ready
    Displaying --> Idle : User resets or new query
    Error --> Idle : User retries
```

```mermaid
flowchart LR
    subgraph UI[Streamlit UI (app.py)]
        UI1[Forms and buttons]
        UI2[Pages and panels]
        UI3[Session state]
    end

    FY[fetch_youtube.py<br/>extract_video_id<br/>request]
    AZ[analyze.py<br/>summarize<br/>aggregates]
    EX[Exporter<br/>to_csv, to_json]
    CFG[Config /.streamlit]
    FS[(Local temp storage)]
    GAPI[[YouTube Data API]]

    UI1 --> FY
    FY --> GAPI
    FY --> UI2
    UI2 --> AZ
    AZ --> UI2
    EX --> FS
    UI3 --> EX
    CFG --> UI
```

```mermaid
flowchart TB
    subgraph Client
        BR[Web browser]
    end

    subgraph Host[Dev or Prod Host]
        CNT[(Docker container – Streamlit)]
        SRV[app.py + fetch_youtube.py + analyze.py]
        TMP[(Ephemeral storage /tmp)]
    end

    BR <-- HTTP(S) --> CNT
    CNT --> SRV
    SRV --> TMP
    SRV -->|HTTPS| GAPI[[YouTube Data API]]
```