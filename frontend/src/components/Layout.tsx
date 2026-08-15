import { NavLink, Outlet } from "react-router-dom";
import { motion } from "framer-motion";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
    isActive ? "bg-ink-800 text-ink-50" : "text-ink-200 hover:text-ink-50"
  }`;

export function Layout() {
  return (
    <div className="min-h-screen bg-ink-950">
      <header className="sticky top-0 z-20 border-b border-ink-800/60 bg-ink-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <NavLink to="/" className="font-display text-lg font-bold tracking-tight text-ink-50">
            Vrutti<span className="text-coral-500">.</span>
          </NavLink>
          <nav className="flex items-center gap-1">
            <NavLink to="/jobs" className={navLinkClass}>
              Jobs
            </NavLink>
            <NavLink to="/profile" className={navLinkClass}>
              Profile
            </NavLink>
          </nav>
        </div>
      </header>
      <motion.main
        key={typeof window !== "undefined" ? window.location.pathname : "main"}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <Outlet />
      </motion.main>
    </div>
  );
}
