import { Routes, Route } from "react-router-dom";
import TopBar from "./components/TopBar";
import AskPage from "./pages/AskPage";
import WorkspacePage from "./pages/WorkspacePage";
import LibraryPage from "./pages/LibraryPage";
import InsightsPage from "./pages/InsightsPage";

export default function App() {
  return (
    <div className="min-h-screen bg-bond text-ink">
      <TopBar />
      <Routes>
        <Route path="/" element={<AskPage />} />
        <Route path="/search" element={<WorkspacePage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/insights" element={<InsightsPage />} />
      </Routes>
    </div>
  );
}
