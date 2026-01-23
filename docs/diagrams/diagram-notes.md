# Architecture Overview Notes

- **External clients → Front Door (FD):** Client apps enter through FD for unified access, authentication (JWT/API key), and routing. FD performs validation, rate limiting, request/response transforms, and telemetry logging before dispatching.
- **LLM & RAG paths via FD:** Requests can be routed to LLM providers (Cohere, OpenAI-compatible, LangGraph) or into DSP Core Services for retrieval-augmented answers.
- **DSP Core Services:**
  - **RAG Interface:** Handles file upload, token generation, LLM prompts, queries, and orchestrates RAG workflows (including LangGraph and LLM APIs).
  - **Control Tower (RME):** Hosts manifest store, configuration, and CPM policy enforcement; supplies versioned configs/policies to other services.
  - **RAG/Provider layer:** Processing + storage for embeddings/vector stores; notebook-based testing support.
- **Security & Identity:**
  - **Vault/Cert Manager:** Issues JWTs and manages keys/certs for secure access.
  - **LDAP:** Provides user/group identity; identity flows through FD and downstream services.
- **Data stores:**
  - **SDP / LangSmith:** Telemetry/observability data from FD and services.
  - **Vector stores:** Used by RAG for search/retrieval.
- **LLM providers:** Cohere, OpenAI-compatible endpoints (e.g., NVIDIA/Triton), LangGraph apps—reachable directly or via FD.
- **Telemetry & governance:** FD and RAG emit logs/metrics; Control Tower enforces policies/configs; Vault/LDAP secure access and identity propagation.
