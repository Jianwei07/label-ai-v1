# AI Regulatory Label Checker

**Project Summary:** This is a full-stack application designed to automate the verification of product labels against user-defined regulatory requirements. Users upload a label image and a set of instructions (e.g., as a JSON/YAML file). The backend uses **OCR** and **computer vision** to scan the label, compare it against the rules, and send back results for the frontend to visually highlight correct (green) and incorrect (red) elements.

**Tech Stack:**

- **Frontend:** Next.js, TailwindCSS
- **Backend:** FastAPI (Python), Docker
- **Core AI/CV:** Tesseract (OCR), OpenCV (Visual Checks)

---

## Current Status (as of June 10, 2025)

The project is in the **early development phase**.

- **Backend:**
  - The folder structure is fully scaffolded.
  - Dependency management is set up with **Poetry**. Dependencies have been installed successfully.
  - The FastAPI server can be started, and the API endpoints (`/labels/check`, `/rules`) are defined.
  - The core logic inside the services (`ocr_service`, `rule_engine_service`, `visual_analysis_service`) is primarily **boilerplate/placeholder code** and requires implementation.
- **Frontend:**
  - The Next.js project is set up but not yet connected to the backend API.
- **Immediate Goal:** Implement the minimal viable end-to-end flow: upload an image and a simple rule from the frontend, have the backend process one simple rule type (e.g., exact text match), and return a basic JSON response.

---

## Local Development Setup

Follow these steps to run the full application on your local machine. Run the backend and frontend in separate terminal windows.

### 1. Running the Backend (FastAPI)

The backend server must be running for the frontend to make API calls.

1.  **Navigate to the backend directory:**

    ```bash
    cd path/to/your/project/label-ai/backend
    ```

2.  **Install Dependencies (if you haven't recently):**
    This command reads the `pyproject.toml` and `poetry.lock` files to install all necessary Python packages into the project's virtual environment.

    ```bash
    poetry install
    ```

3.  **Run the Server:**
    This starts the FastAPI application using the Uvicorn server. The `--reload` flag enables auto-reloading when you save code changes.

    ```bash
    poetry run uvicorn main:app --reload --port 8000
    ```

4.  **Verify Backend:**
    - The server should now be running on `http://localhost:8000`.
    - You can access the interactive API documentation (Swagger UI) at **[http://localhost:8000/docs](http://localhost:8000/docs)** to test the endpoints manually.

### 2. Running the Frontend (Next.js)

1.  **Navigate to the frontend directory:**

    ```bash
    cd path/to/your/project/label-ai/frontend
    ```

2.  **Install Dependencies:**
    This command reads the `package.json` file and installs the required Node.js modules.

    ```bash
    npm install
    ```

3.  **Run the Development Server:**

    ```bash
    npm run dev
    ```

4.  **Verify Frontend:**
    - The Next.js application should now be accessible at **[http://localhost:3000](http://localhost:3000)** in your browser.

---

This should be everything you need to pick up where you left off. The next immediate step is to start implementing the logic within the backend's service files.
