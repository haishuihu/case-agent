import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { GenerationTaskProvider } from "./context/GenerationTaskContext";
import { AutoTestDashboard, CaseListPage, ExecutionDetailPage, ExecutionListPage, PlanListPage, RecommendPage, SuiteListPage } from "./pages/AutoTest";
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
import { TranslationPage } from "./pages/TranslationPage";

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
            <Route path="translate" element={<TranslationPage />} />
            <Route path="submissions" element={<SubmissionPage />} />
            <Route path="submissions/:id" element={<SubmissionDetailPage />} />
            <Route path="reviews" element={<ReviewListPage />} />
            <Route path="defects" element={<DefectListPage />} />
            <Route path="settings" element={<ConfigPage />} />
            {/* Auto Test Routes */}
            <Route path="auto-test" element={<AutoTestDashboard />} />
            <Route path="auto-test/suites" element={<SuiteListPage />} />
            <Route path="auto-test/cases" element={<CaseListPage />} />
            <Route path="auto-test/plans" element={<PlanListPage />} />
            <Route path="auto-test/recommend" element={<RecommendPage />} />
            <Route path="auto-test/executions" element={<ExecutionListPage />} />
            <Route path="auto-test/executions/:id" element={<ExecutionDetailPage />} />
          </Route>
        </Routes>
      </GenerationTaskProvider>
    </BrowserRouter>
  );
}

export default App;
