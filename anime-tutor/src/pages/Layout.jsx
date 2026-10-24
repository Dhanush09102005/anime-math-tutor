import { useLocation } from "react-router-dom";
import TopNav from "../components/TopNav";
import PageTransition from "../components/PageTransition";

// Shared shell for every standalone routed page (Dashboard, Syllabus,
// Account, History detail). Persistent TopNav + CSS fade/slide transition
// on route change. NOT used for the character-select/mode/topic/qna/chat
// flow inside App.jsx, which embeds TopNav directly so it can share App's
// own currentUser/logout state and correctly hide during active sessions.
export default function Layout({ children }) {
  const location = useLocation();
  return (
    <div className="min-h-screen bg-indigo-950 text-slate-100 flex flex-col">
      <TopNav />
      {/* key on the component itself triggers remount → replays page-enter animation */}
      <PageTransition key={location.pathname} className="flex-1 flex flex-col">
        {children}
      </PageTransition>
    </div>
  );
}
