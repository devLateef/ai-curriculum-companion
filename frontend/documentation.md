# Lumina Frontend Architecture Report

## Overview
Lumina is an AI-powered curriculum companion designed to analyze textbooks, identify outdated content, and provide modern, age-appropriate updates. The frontend is a Single Page Application (SPA) that allows users to upload PDF textbooks, navigate through them, and scan specific pages for AI-driven analysis.

## Technology Stack
- **Framework**: React 19 with TypeScript for strong typing and modern component architecture.
- **Build Tool**: Vite, providing fast Hot Module Replacement (HMR) and optimized production builds.
- **Styling**: Tailwind CSS (v4) combined with inline styles for dynamic, state-driven styling.
- **Icons**: `lucide-react` for clean, consistent SVG iconography.
- **PDF Rendering**: `react-pdf` (backed by `pdfjs-dist` v6) for rendering PDF pages and extracting text content. 

## Application Architecture
The frontend is structured into a minimal, focused component tree, primarily residing in the `src` directory.

### 1. Entry Point (`main.tsx` & `App.tsx`)
- **`main.tsx`**: Bootstraps the application, rendering the root `<App />` component within React's `StrictMode`.
- **`App.tsx`**: Acts as the primary state controller. It maintains a `loaded` state (`LoadedFile | null`) that dictates which view is currently presented to the user.
  - If no file is loaded, it renders the `UploadView`.
  - Once a file is loaded, it transitions to the `ReaderView`, passing along the `File` object and its generated `URL`.

### 2. Upload View (`views/UploadView.tsx`)
The `UploadView` handles the initial user interaction of uploading a textbook.
- **Drag & Drop Interface**: Provides a smooth, animated drag-and-drop zone.
- **Validation**: Ensures the uploaded file is strictly an `application/pdf`.
- **Backend Integration**: Posts the file to a backend service (`http://127.0.0.1:5000/process`) via `FormData`. 
- **Transition**: Upon successful upload, it generates a local object URL (`URL.createObjectURL(file)`) and triggers the `onFileLoaded` callback to switch the view.

### 3. Reader View (`views/ReaderView.tsx`)
The `ReaderView` is the core application interface, divided into a Header, a Navigation Sidebar, a PDF Viewer, and an Analysis Panel.

#### Header
- Displays the current file name and size.
- Contains controls for pagination (Next/Previous page) and Zoom (Scale in/out).
- Provides a "New Upload" button to reset the state.

#### Page Navigation (Left Sidebar)
- Renders miniature thumbnails of the PDF pages using `react-pdf`'s `<Page>` component with text and annotation layers disabled for performance.
- Allows users to quickly jump to any page in the document.

#### PDF Viewer (Main Content)
- Renders the active page of the PDF.
- **Grammarly-style Highlighting**: Implements a custom `textRenderer` that intersects the extracted PDF text with the AI's findings. If a match is found, it wraps the text in a `<mark>` tag with custom CSS classes to highlight outdated or critical content directly on the PDF.

#### Analysis Panel (Right Sidebar)
- **Scan Controls**: Users can click the scan button to analyze the current page.
- **Text Extraction**: Uses `pdfjs` API (`getTextContent()`) to extract raw text from the current page locally before analysis.
- **AI Analysis (Mocked)**: Currently, the scanning process simulates backend processing delays and returns a set of `MOCK_FINDINGS` (Critical, Outdated, Aligned). 
- **Findings Display**: Renders an accordion-style list of findings. Clicking a finding expands it to show the original textbook excerpt side-by-side with the AI's updated understanding.

## Data Flow & State Management
- Local state is heavily utilized within components using React's `useState` and `useCallback` hooks.
- **Cross-Component Communication**: Handled via simple prop passing (e.g., `onFileLoaded`, `onReset`). There is no complex global state manager (like Redux or Zustand), which keeps the architecture lightweight.

## Important Notes for Future Development
- **Hardcoded API Endpoint**: The `UploadView.tsx` currently contains a hardcoded backend URL (`http://127.0.0.1:5000/process`). This should be migrated to an environment variable (e.g., `import.meta.env.VITE_API_URL`) for production deployments.
- **AI Analysis Integration**: The `ReaderView.tsx` currently relies on `MOCK_FINDINGS`. The `startScan` function needs to be updated to send the extracted `extractedText` to the backend AI service and process the real response.
