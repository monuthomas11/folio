"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  IconBell,
  IconBookmark,
  IconBriefcase,
  IconClose,
  IconGrid,
  IconLogout,
  IconMenu,
  IconSparkles,
} from "@/components/icons";
import styles from "./app-shell.module.css";

interface NavItem {
  href: string;
  label: string;
  icon: (props: { width?: number; height?: number }) => ReactNode;
  badge?: number;
}

interface AppShellProps {
  children: ReactNode;
  activeAlertCount?: number;
}

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: IconGrid },
  { href: "/portfolio", label: "Portfolio", icon: IconBriefcase },
  { href: "/watchlist", label: "Watchlist", icon: IconBookmark },
  { href: "/alerts", label: "Alerts", icon: IconBell },
  { href: "/ai", label: "AI Advisor", icon: IconSparkles },
] satisfies NavItem[];

function isIndianMarketOpen() {
  const now = new Date();
  const istOffset = 330 * 60 * 1000;
  const istTime = now.getTime() + istOffset;
  const ist = new Date(istTime);
  const day = ist.getUTCDay();
  const hours = ist.getUTCHours();
  const minutes = ist.getUTCMinutes();
  const totalMinutes = hours * 60 + minutes;
  if (day === 0 || day === 6) return false;
  return totalMinutes >= 555 && totalMinutes <= 930;
}

export function AppShell({ children, activeAlertCount = 0 }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, status, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [marketOpen, setMarketOpen] = useState(false);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (status === "guest") {
      router.replace("/login");
    }
  }, [status, router]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (drawerOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [drawerOpen]);

  useEffect(() => {
    const tick = () => setMarketOpen(isIndianMarketOpen());
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, []);

  if (status === "loading" || status === "guest") {
    return (
      <div className={styles.loader} role="status" aria-label="Loading">
        <span className={styles.loaderMark} aria-hidden>
          <IconGrid width={18} height={18} />
        </span>
      </div>
    );
  }

  const initials = user
    ? user.name
        .split(/\s+/)
        .map((part) => part[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "AK";

  const navItems = NAV_ITEMS.map((item) => {
    const active =
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
    const badge = item.href === "/alerts" ? activeAlertCount : undefined;
    const Icon = item.icon;
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
        aria-current={active ? "page" : undefined}
      >
        <Icon width={17} height={17} />
        <span>{item.label}</span>
        {badge !== undefined && badge > 0 && (
          <span className={styles.navBadge}>{badge}</span>
        )}
      </Link>
    );
  });

  const sidebarContent = (
    <>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden>
          <IconGrid width={16} height={16} />
        </span>
        <span className={styles.brandName}>Folio</span>
      </div>

      <nav className={styles.nav} aria-label="Primary">
        {navItems}
      </nav>

      <div className={styles.user}>
        <span className={styles.avatar} aria-hidden>
          {initials}
        </span>
        <div className={styles.userMeta}>
          <span className={styles.userName}>{user?.name ?? "Account"}</span>
          <span className={styles.userEmail}>{user?.email ?? ""}</span>
        </div>
        <button
          type="button"
          className={styles.logout}
          aria-label="Sign out"
          title="Sign out"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
        >
          <IconLogout width={16} height={16} />
        </button>
      </div>
    </>
  );

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>{sidebarContent}</aside>

      {mounted && drawerOpen && (
        <div
          className={styles.drawerBackdrop}
          onClick={() => setDrawerOpen(false)}
        >
          <aside
            className={styles.drawer}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
          >
            <button
              type="button"
              className={styles.drawerClose}
              onClick={() => setDrawerOpen(false)}
              aria-label="Close navigation"
            >
              <IconClose width={18} height={18} />
            </button>
            {sidebarContent}
          </aside>
        </div>
      )}

      <div className={styles.main}>
        <header className={styles.topbar}>
          <button
            type="button"
            className={styles.menuButton}
            onClick={() => setDrawerOpen(true)}
            aria-label="Open navigation"
          >
            <IconMenu width={18} height={18} />
          </button>
          <div className={styles.topbarSpacer} />
          <span className={`${styles.marketStatus} ${marketOpen ? styles.marketStatusOpen : ""}`}>
            <span
              className={`${styles.marketDot} ${marketOpen ? styles.marketDotOpen : ""}`}
              aria-hidden
            />
            {marketOpen ? "Market open" : "Market closed"}
          </span>
        </header>
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
