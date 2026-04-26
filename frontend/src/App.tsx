import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { GenerationTaskProvider } from "./context/GenerationTaskContext";
import { ConfigPage } from "./pages/ConfigPage";
import { DefectListPage } from "./pages/DefectListPage";
import { GeneratorPage } from "./pages/GeneratorPage";
import { KnowledgeDetailPage } from "./pages/KnowledgeDetailPage";
import { KnowledgeListPage } from "./pages/KnowledgeListPage";
import { QuickGeneratePage } from "./pages/QuickGeneratePage";
import { ReviewListPage } from "./pages/ReviewListPage";
import { SubmissionDetailPage } from "./pages/SubmissionDetailPage";
import { SubmissionPage } from "./pages/SubmissionPage";
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
            <Route path="settings" element={<ConfigPage />} />
          </Route>
        </Routes>
      </GenerationTaskProvider>
    </BrowserRouter>
  );
}

export default App;
