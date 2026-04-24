import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { GenerationTaskProvider } from "./context/GenerationTaskContext";
import { GeneratorPage } from "./pages/GeneratorPage";
import { KnowledgeListPage } from "./pages/KnowledgeListPage";
import { KnowledgeDetailPage } from "./pages/KnowledgeDetailPage";
import { QuickGeneratePage } from "./pages/QuickGeneratePage";
import { SubmissionPage } from "./pages/SubmissionPage";
import { SubmissionDetailPage } from "./pages/SubmissionDetailPage";
import { ReviewListPage } from "./pages/ReviewListPage";
import { DefectListPage } from "./pages/DefectListPage";
import { ToolsPage } from "./pages/ToolsPage";

function App() {
  return (
    <BrowserRouter>
      <GenerationTaskProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<GeneratorPage />} />
            <Route path="quick" element={<QuickGeneratePage />} />
            <Route path="knowledge" element={<KnowledgeListPage />} />
            <Route path="knowledge/:id" element={<KnowledgeDetailPage />} />
            <Route path="tools" element={<ToolsPage />} />
            <Route path="submissions" element={<SubmissionPage />} />
            <Route path="submissions/:id" element={<SubmissionDetailPage />} />
            <Route path="reviews" element={<ReviewListPage />} />
            <Route path="defects" element={<DefectListPage />} />
          </Route>
        </Routes>
      </GenerationTaskProvider>
    </BrowserRouter>
  );
}

export default App;
