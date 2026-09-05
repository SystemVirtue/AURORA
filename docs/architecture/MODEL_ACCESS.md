# AURORA Model Access Architecture

## Purpose

AURORA treats model selection and model provenance as first-class cognitive state. A user must be able to explicitly choose which models participate in a reasoning run, including QUORUM, without requiring a paid LLM-provider subscription.

## Zero-cost operating paths

### 1. OpenRouter — Free Models

The canonical server-side pathway is OpenRouter with a user-provided `OPENROUTER_API_KEY` configured in AURORA's server environment.

AURORA's model picker does **not** default to the complete OpenRouter catalogue. It queries the live `/api/v1/models` catalogue and initially exposes only models whose current prompt and completion pricing are both zero.

This roster is deliberately dynamic: free models can be added, removed, deprecated, or have availability/pricing changed.

The OpenRouter key is never placed in browser JavaScript, local storage, or the AURORA database.

### 2. Puter.js — keyless browser execution

Puter.js is a separate execution pathway. The browser loads Puter.js and calls `puter.ai.chat()` directly using the explicitly selected model. AURORA does not receive or store a provider API key.

The initial Puter model picker is restricted to models reporting zero input and output cost through `puter.ai.listModels()`. Users authenticate with their Puter account when required by Puter.js. Puter uses its user-pays architecture; therefore AURORA describes this pathway as **keyless / user-account based**, not as a promise of unlimited free inference.

AURORA receives the completed contribution and persists it as authoritative cognitive history.

## Execution boundary

```text
                         AURORA Reasoning Gateway
                                  |
                 +----------------+----------------+
                 |                                 |
          SERVER EXECUTION                   BROWSER EXECUTION
                 |                                 |
           OpenRouter API                       Puter.js
                 |                                 |
          selected free model              user's Puter session
                 |                                 |
                 +----------------+----------------+
                                  |
                         AURORA cognitive record
                                  |
              reasoning run / contribution / evidence / event
```

The distinction is intentional. AURORA owns cognition, retrieval, provenance and persistence; providers own model execution.

## Puter persistence flow

```text
Question
   |
   v
AURORA authenticated retrieval
   |
   v
Evidence context -> Puter.js -> selected model(s)
                              |
                              v
                     optional QUORUM synthesis
                              |
                              v
                 POST /v1/ask/puter
                              |
                              v
                AURORA reasoning_run
                model_contributions
                assistant event
                provenance/evidence links
```

This prevents Puter from becoming a second cognitive database. It is an execution provider only.

## Explicit model selection

The web workspace exposes:

- provider pathway;
- live OpenRouter free catalogue;
- live Puter model catalogue filtered to zero-cost entries by default;
- explicit model selection;
- up to three Puter contributors for QUORUM/deep mode;
- an explicit Puter synthesis model.

Every persisted model contribution records its provider and model identity.

## Current limitations

- OpenRouter model execution remains server-side and therefore requires `OPENROUTER_API_KEY`.
- Puter browser execution currently uses lexical AURORA retrieval rather than server-side semantic retrieval when no embedding provider is configured.
- Puter model discovery is client-side because Puter.js is a browser execution API.
- Puter authentication and usage are governed by Puter's current service policies and user account state.
- The current Puter bridge trusts the browser for the returned text; AURORA validates workspace membership and persists the result but cannot independently verify that the browser actually called the declared model.
- The OpenRouter catalogue is filtered by current zero input/output pricing, but production hardening should additionally validate the selected model immediately before execution if a strict no-cost guarantee is required.

## Design principle

> **The user chooses the intelligence. AURORA records the intelligence. The provider is replaceable.**
