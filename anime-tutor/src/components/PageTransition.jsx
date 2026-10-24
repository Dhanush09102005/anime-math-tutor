// Lightweight page/phase transition.
//
// HOW IT WORKS:
// React remounts a component when its `key` prop changes. This component
// is itself the thing being keyed — the parent renders:
//   <PageTransition transitionKey={phase} ...>
// which causes PageTransition to unmount+remount whenever `transitionKey`
// changes, replaying the `page-enter` CSS animation defined in index.css.
//
// A plain `<div key={...}>` does NOT cause remount — only components do.
// That was the original bug: the key was on the inner div, not on this
// component itself. The fix is to key PageTransition at the call site,
// which App.jsx and Layout.jsx now do.

export default function PageTransition({ className = "", children }) {
  return (
    <div className={`page-enter ${className}`}>
      {children}
    </div>
  );
}
