import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { getCurrentUser, logoutUser, BASE_URL } from "../api/client";

const NAV_ITEMS = [
  { to: "/", label: "Mentor", end: true },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/syllabus", label: "Syllabus" },
  { to: "/history", label: "History" },
  { to: "/account", label: "Account" },
];

// Self-sufficient: works both embedded inside App.jsx (pass currentUser/onLogout
// so App's existing state-reset logic runs) and standalone on routed pages like
// Dashboard/Syllabus/Account (no props needed — fetches its own user, logs out
// and navigates home directly, which remounts App fresh and re-triggers its
// auth check).
export default function TopNav({ currentUser, onLogout }) {
  const navigate = useNavigate();
  const [selfUser, setSelfUser] = useState(null);
  const user = currentUser ?? selfUser;

  useEffect(() => {
    // currentUser is explicitly passed as null from App while it's still
    // checking auth — treat both null and undefined as "not yet known."
    // Only self-fetch when no user was passed at all (standalone Layout pages).
    if (currentUser == null) {
      getCurrentUser().then(setSelfUser).catch(() => {});
    }
  }, [currentUser]);

  async function handleLogout() {
    if (onLogout) return onLogout();
    try {
      await logoutUser();
    } catch {
      // fall through regardless
    }
    navigate("/", { replace: true });
  }

  const avatarSrc = user?.avatar_url ? `${BASE_URL}${user.avatar_url}` : null;

  return (
    <nav className="sticky top-0 z-30 w-full bg-violet-950 border-b border-indigo-900 shadow-sm shadow-black/20">
      <div className="max-w-5xl mx-auto flex items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-1 flex-wrap">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 active:scale-95 ${
                  isActive
                    ? "bg-indigo-700 text-white"
                    : "text-slate-400 hover:text-slate-100 hover:bg-indigo-900"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-2 pl-2 pr-4 py-1.5 rounded-lg text-sm font-medium
                     text-slate-400 border border-indigo-700 hover:text-red-300 hover:border-red-800
                     hover:bg-red-950/30 active:scale-95 transition-all duration-150 whitespace-nowrap"
        >
          {avatarSrc ? (
            <img
              src={avatarSrc}
              alt=""
              className="w-6 h-6 rounded-full object-cover border border-indigo-600"
            />
          ) : (
            <span className="w-6 h-6 rounded-full bg-indigo-700 flex items-center justify-center text-[10px] text-slate-300 uppercase">
              {(user?.display_name || user?.email || "?")[0]}
            </span>
          )}
          <span className="hidden sm:inline">
            {user?.display_name || user?.email || ""}
          </span>
          <span>· Log out</span>
        </button>
      </div>
    </nav>
  );
}
