import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { GenerationTaskProvider } from "./context/GenerationTaskContext";
import { GeneratorPage } from "./pages/GeneratorPage";
import { KnowledgeListPage } from "./pages/KnowledgeListPage";
import { KnowledgeDetailPage } from "./pages/KnowledgeDetailPage";

function App() {
  return (
    <BrowserRouter>
      <GenerationTaskProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<GeneratorPage />} />
            <Route path="knowledge" element={<KnowledgeListPage />} />
            <Route path="knowledge/:id" element={<KnowledgeDetailPage />} />
          </Route>
        </Routes>
      </GenerationTaskProvider>
    </BrowserRouter>
  );
}

export default App;
