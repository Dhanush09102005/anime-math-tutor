import { useEffect, useState } from "react";
import { fetchSessionHistory } from "../api/client";
import SessionHistory from "../components/SessionHistory";

// Standalone /history page — lives under Layout like Dashboard/Syllabus/Account.
// Previously this was handled as a phase inside App.jsx, meaning /history
// never had a proper URL, TopNav, or page transition. Moving it here makes
// the routing consistent and removes the fragile phase-via-URL pattern.
export default function HistoryPage() {
  const [sessions, setSessions]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);

  useEffect(() => {
    fetchSessionHistory()
      .then(setSessions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <SessionHistory
        sessions={sessions}
        loading={loading}
        error={error}
        onBack={null}   // no back button — TopNav handles navigation
      />
    </div>
  );
}
