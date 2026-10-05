import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useTheme } from "@/app/ThemeProvider";
import {
  AccountingIcon,
  AuditIcon,
  CloseIcon,
  DashboardIcon,
  LogoutIcon,
  MenuIcon,
  MoonIcon,
  NasIcon,
  PostAuthIcon,
  ProfilesIcon,
  SessionsIcon,
  SettingsIcon,
  SunIcon,
  UserIcon,
  UsersIcon,
} from "@/components/ui/icons";
import { useAuth } from "@/features/auth/AuthProvider";

const navItems = [
  { to: "/", labelKey: "nav.dashboard", icon: DashboardIcon },
  { to: "/users", labelKey: "nav.users", icon: UserIcon },
  { to: "/groups", labelKey: "nav.groups", icon: UsersIcon },
  { to: "/profiles", labelKey: "nav.profiles", icon: ProfilesIcon },
  { to: "/nas", labelKey: "nav.nas", icon: NasIcon },
  { to: "/sessions", labelKey: "nav.sessions", icon: SessionsIcon },
  { to: "/accounting", labelKey: "nav.accounting", icon: AccountingIcon },
  { to: "/postauth", labelKey: "nav.postauth", icon: PostAuthIcon },
  { to: "/audit", labelKey: "nav.audit", icon: AuditIcon },
  { to: "/settings", labelKey: "nav.settings", icon: SettingsIcon },
];

export function AppLayout() {
  const { t } = useTranslation();
  const { admin, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const nav = (
    <nav className="flex flex-col gap-0.5 px-3">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-foreground/70 hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <Icon className="shrink-0" />
            <span className="truncate">{t(item.labelKey)}</span>
          </NavLink>
        );
      })}
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 flex-col border-r border-border bg-card py-4 lg:flex">
        <div className="mb-4 px-4 text-base font-semibold">{t("app.title")}</div>
        {nav}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            aria-label="Close menu"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-60 flex-col bg-card py-4 shadow-xl">
            <div className="mb-4 flex items-center justify-between px-4">
              <span className="text-base font-semibold">{t("app.title")}</span>
              <button
                type="button"
                aria-label="Close menu"
                onClick={() => setMobileOpen(false)}
                className="rounded-md p-1 text-foreground/60 hover:bg-muted hover:text-foreground"
              >
                <CloseIcon width={16} height={16} />
              </button>
            </div>
            {nav}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border bg-card px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label="Open menu"
              onClick={() => setMobileOpen(true)}
              className="rounded-md p-1.5 text-foreground/70 hover:bg-muted lg:hidden"
            >
              <MenuIcon />
            </button>
            <span className="text-sm font-medium lg:hidden">{t("app.title")}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? t("theme.light") : t("theme.dark")}
              title={theme === "dark" ? t("theme.light") : t("theme.dark")}
              className="rounded-md p-1.5 text-foreground/70 transition-colors hover:bg-muted hover:text-foreground"
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>
            {admin && (
              <>
                <span className="hidden sm:inline">
                  {admin.username} · {t(`auth.roles.${admin.role}`)}
                </span>
                <button
                  type="button"
                  onClick={() => void logout()}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:bg-muted"
                >
                  <LogoutIcon width={16} height={16} />
                  {t("auth.logout")}
                </button>
              </>
            )}
          </div>
        </header>
        <main className="min-w-0 flex-1 bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
