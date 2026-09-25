Every trigger goes through the same seven stages. Each stage writes an entry to the execution log, so the first stage without a success entry tells you where a notification stopped.

```mermaid
flowchart LR
  A[Request received] --> B[Validate payload] --> C[Load subscriber] --> D[Resolve workflow] --> E[Render templates] --> F[Send to provider] --> G[Record delivery]
```

Bad input stops at validation. A missing subscriber stops at load. An opt-out stops at workflow resolution. A template bug stops at render.
