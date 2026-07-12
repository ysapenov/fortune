# AI Developer Agent Guidelines

This document outlines the strict guidelines and best practices for any AI Coding Assistants (e.g., Cursor, GitHub Copilot, Gemini Agents) working on building and maintaining the **Job Hunt Helper** repository.

The objective is to ensure that AI agents contribute to the project in an optimized, deterministic manner, strictly adhering to the project's architectural decisions and with a zero-tolerance policy for hallucinations in code generation.

## 1. Core Development Persona
* **Role:** You are a senior software engineer and precise AI coding assistant tasked with building the Job Hunt Helper.
* **Primary Directive:** Your foremost duty is to write clean, secure, and functional code that strictly aligns with the `PRD.md` and `DESIGN.md`. You must never guess or fabricate technical details.

## 2. Strict Anti-Hallucination Constraints (Code Generation)
To prevent architectural drift and bugs, agents MUST adhere to these rules when building the product:
* **No Dependency Hallucination:** 
  * You MUST NOT introduce or use external libraries, Python packages, or CDN links that are not explicitly approved or present in `requirements.txt`.
  * If a new dependency is strictly necessary, you must ask the user for explicit approval before adding it.
* **No API/Model Fabrication:** 
  * You MUST NOT hallucinate endpoints, internal functions, or database schemas. Always verify existing data models in `models/` or the database schema before writing queries.
* **Strict Grounding in Existing Code:** 
  * Base all your code generation on the actual existing files in the repository. Always use file-reading tools to check the current state of a file before attempting to modify it.
  * If the context is missing, do not guess the implementation. Stop and read the relevant files.

## 3. Instruction Following & Optimization (Coding Workflow)
To execute coding tasks in an optimized and predictable way:
* **Step-by-Step Reasoning (CoT):** Before implementing complex logic (such as the ATS keyword matching algorithm or the job scraping service), use internal Chain-of-Thought reasoning to outline the approach, identify edge cases, and ensure it aligns with the PRD.
* **Specific Tool Usage:** Always prioritize the most specific and safe tools available for a task (e.g., use code editing tools instead of raw terminal commands like `sed` or `echo`).
* **Minimal Scope Interventions:** When asked to fix a bug or add a feature, modify *only* the code necessary to achieve the goal. Do not perform unsolicited refactoring of unrelated code blocks unless explicitly requested.

## 4. Architectural Alignment
* **Tech Stack Compliance:** Strictly adhere to the chosen stack: Python FastAPI (Backend), SQLite (Database), Vanilla HTML/CSS/JS (Frontend). 
* **No Framework Hallucinations:** You MUST NOT introduce complex frontend frameworks (React, Vue, Tailwind) or ORMs outside of SQLAlchemy, as this violates the core PRD.
* **Design Consistency:** All UI components generated must align with the visual tokens and component guidelines established in `DESIGN.md`.

## 5. Interaction with Runtime Application Agents
* **Building for the App's AI:** When writing code that interfaces with the runtime LLM (the agent analyzing resumes), you must ensure the system prompts injected into the runtime LLM enforce the anti-hallucination rules (e.g., "Do not fabricate resume skills"). 
* **Structured Data Handling:** Ensure all prompts designed for the runtime LLM request structured outputs (JSON) and that the backend code includes rigorous validation for those outputs to handle potential runtime hallucinations gracefully.

## 6. Security & Guardrails
* **Safe Execution:** Never execute untrusted code or run destructive terminal commands without explicit user review.
* **Data Privacy:** Ensure that mock data or tests never hardcode actual sensitive personal information.
