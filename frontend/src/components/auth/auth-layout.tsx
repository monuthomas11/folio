import type { ReactNode } from "react";
import Link from "next/link";
import { IconGrid, IconShield } from "@/components/icons";
import styles from "./auth-layout.module.css";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <Link href="/" className={styles.brand} aria-label="Folio home">
          <span className={styles.brandMark} aria-hidden>
            <IconGrid width={18} height={18} />
          </span>
          <span className={styles.brandName}>Folio</span>
        </Link>

        <header className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>{subtitle}</p>
        </header>

        {children}

        <footer className={styles.footer}>{footer}</footer>
      </section>

      <p className={styles.trust}>
        <IconShield width={14} height={14} />
        Your data stays yours — positions, levels, and alerts are private to your
        account.
      </p>
    </main>
  );
}
