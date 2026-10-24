import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getCurrentUser,
  changePassword,
  deleteAccount,
  logoutUser,
  updateProfile,
  uploadAvatar,
  BASE_URL,
} from "../api/client";

export default function AccountPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Previously this page relied on `currentUser`/`onLogout` props that
  // AppRouter never actually passed in (it rendered <AccountPage /> bare),
  // so `isOAuth` below always evaluated true and the password form never
  // showed for real password accounts. Fetching directly fixes that and
  // also makes this page work standalone under Layout.
  const [currentUser, setCurrentUser] = useState(null);
  const [userLoading, setUserLoading] = useState(true);
  const [userError, setUserError] = useState(null);
  const [displayName, setDisplayName] = useState("");

  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        setCurrentUser(user);
        setDisplayName(user.display_name || "");
      })
      .catch((error) => setUserError(error.message))
      .finally(() => setUserLoading(false));
  }, []);

  // ── Profile: display name + avatar ──────────────────────────────────────
  const [nameLoading, setNameLoading]   = useState(false);
  const [nameMsg, setNameMsg]           = useState(null);
  const [avatarLoading, setAvatarLoading] = useState(false);
  const [avatarMsg, setAvatarMsg]         = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);

  async function handleSaveName(e) {
    e.preventDefault();
    setNameLoading(true);
    setNameMsg(null);
    try {
      const updated = await updateProfile({ displayName });
      setCurrentUser(updated);
      setNameMsg({ type: "ok", text: "Display name updated." });
    } catch (err) {
      setNameMsg({ type: "err", text: err.message });
    } finally {
      setNameLoading(false);
    }
  }

  function handleAvatarPick(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarPreview(URL.createObjectURL(file));
    handleAvatarUpload(file);
  }

  async function handleAvatarUpload(file) {
    setAvatarLoading(true);
    setAvatarMsg(null);
    try {
      const updated = await uploadAvatar(file);
      setCurrentUser(updated);
      setAvatarMsg({ type: "ok", text: "Photo updated." });
    } catch (err) {
      setAvatarMsg({ type: "err", text: err.message });
    } finally {
      setAvatarLoading(false);
    }
  }

  // ── Change password ─────────────────────────────────────────────────────
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw]         = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMsg, setPwMsg]         = useState(null);

  async function handleChangePassword(e) {
    e.preventDefault();
    setPwLoading(true);
    setPwMsg(null);
    try {
      await changePassword(currentPw, newPw);
      setPwMsg({ type: "ok", text: "Password updated." });
      setCurrentPw(""); setNewPw("");
    } catch (err) {
      setPwMsg({ type: "err", text: err.message });
    } finally {
      setPwLoading(false);
    }
  }

  // ── Delete account ──────────────────────────────────────────────────────
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  async function handleDeleteAccount() {
    setDeleteLoading(true);
    try {
      await deleteAccount();
      await logoutUser().catch(() => {});
      navigate("/", { replace: true });
    } catch (err) {
      setDeleteLoading(false);
      alert(err.message);
    }
  }

  if (userLoading) {
    return (
      <div className="flex-1 p-8">
        <p className="text-slate-500 text-sm animate-pulse">Loading account...</p>
      </div>
    );
  }

  if (userError) {
    return (
      <div className="flex-1 p-8">
        <p className="text-red-400 text-sm">{userError}</p>
      </div>
    );
  }

  const isOAuth = !currentUser?.has_password;
  const avatarSrc = avatarPreview || (currentUser?.avatar_url ? `${BASE_URL}${currentUser.avatar_url}` : null);

  return (
    <div className="flex-1 p-8">
      <div className="max-w-lg mx-auto flex flex-col gap-8">

        <h1 className="text-xl font-semibold">Account</h1>

        {/* Avatar + email */}
        <div className="flex items-center gap-5 px-4 py-4 rounded-lg bg-indigo-900 border border-indigo-700">
          <div className="relative shrink-0">
            {avatarSrc ? (
              <img
                src={avatarSrc}
                alt=""
                className="w-16 h-16 rounded-full object-cover border border-indigo-600"
              />
            ) : (
              <div className="w-16 h-16 rounded-full bg-indigo-700 border border-indigo-600
                              flex items-center justify-center text-xl text-slate-300 uppercase">
                {(currentUser?.display_name || currentUser?.email || "?")[0]}
              </div>
            )}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={avatarLoading}
              title="Change photo"
              className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-indigo-600
                         hover:bg-slate-500 border border-violet-950 flex items-center justify-center
                         text-[11px] text-white active:scale-90 transition-all duration-150
                         disabled:opacity-50"
            >
              {avatarLoading ? "…" : "✎"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleAvatarPick}
              className="hidden"
            />
          </div>
          <div className="min-w-0">
            <p className="text-slate-100 text-sm font-medium truncate">
              {currentUser?.display_name || "No display name set"}
            </p>
            <p className="text-slate-400 text-sm truncate">{currentUser?.email}</p>
            {isOAuth && <p className="text-slate-500 text-xs mt-0.5">Signed in with Google</p>}
          </div>
        </div>
        {avatarMsg && (
          <p className={`-mt-4 text-sm ${avatarMsg.type === "ok" ? "text-green-400" : "text-red-400"}`}>
            {avatarMsg.text}
          </p>
        )}

        {/* Display name */}
        <form onSubmit={handleSaveName} className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-widest">
            Display name
          </h2>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="How mentors should address you"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={40}
              className="flex-1 px-4 py-2 rounded bg-violet-950 border border-indigo-600 text-slate-100
                         placeholder-slate-500 focus:outline-none focus:border-slate-400"
            />
            <button
              type="submit"
              disabled={nameLoading}
              className="px-5 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-slate-100
                         font-semibold text-sm transition-all duration-150 active:scale-95
                         disabled:opacity-40"
            >
              {nameLoading ? "Saving..." : "Save"}
            </button>
          </div>
          {nameMsg && (
            <p className={`text-sm ${nameMsg.type === "ok" ? "text-green-400" : "text-red-400"}`}>
              {nameMsg.text}
            </p>
          )}
        </form>

        {/* Change password — only for email/password accounts */}
        {!isOAuth && (
          <form onSubmit={handleChangePassword} className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-widest">
              Change password
            </h2>
            <input
              type="password"
              placeholder="Current password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              required
              className="px-4 py-2 rounded bg-violet-950 border border-indigo-600 text-slate-100
                         placeholder-slate-500 focus:outline-none focus:border-slate-400"
            />
            <input
              type="password"
              placeholder="New password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
              className="px-4 py-2 rounded bg-violet-950 border border-indigo-600 text-slate-100
                         placeholder-slate-500 focus:outline-none focus:border-slate-400"
            />
            {pwMsg && (
              <p className={`text-sm ${pwMsg.type === "ok" ? "text-green-400" : "text-red-400"}`}>
                {pwMsg.text}
              </p>
            )}
            <button
              type="submit"
              disabled={pwLoading}
              className="px-5 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-slate-100
                         font-semibold text-sm transition-all duration-150 active:scale-95
                         disabled:opacity-40 self-start"
            >
              {pwLoading ? "Updating..." : "Update password"}
            </button>
          </form>
        )}

        {/* Delete account */}
        <div className="flex flex-col gap-3 border-t border-indigo-900 pt-6">
          <h2 className="text-sm font-semibold text-red-400 uppercase tracking-widest">
            Danger zone
          </h2>
          {!deleteConfirm ? (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="px-5 py-2 rounded border border-red-800 text-red-400 hover:bg-red-900/30
                         text-sm font-semibold transition-all duration-150 active:scale-95 self-start"
            >
              Delete account
            </button>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-red-300">
                This will permanently delete your account and all session history. Are you sure?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleteLoading}
                  className="px-5 py-2 rounded bg-red-800 hover:bg-red-700 text-white
                             text-sm font-semibold transition-all duration-150 active:scale-95
                             disabled:opacity-40"
                >
                  {deleteLoading ? "Deleting..." : "Yes, delete everything"}
                </button>
                <button
                  onClick={() => setDeleteConfirm(false)}
                  className="px-5 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-slate-100
                             text-sm transition-all duration-150 active:scale-95"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
