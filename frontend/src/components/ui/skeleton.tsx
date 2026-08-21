import type { CSSProperties, ReactNode } from "react";
import styles from "./skeleton.module.css";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  radius?: string;
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
}

export function Skeleton({
  width = "100%",
  height = "1rem",
  radius = "var(--radius-sm)",
  className,
  style,
  children,
}: SkeletonProps) {
  return (
    <span
      className={`${styles.skeleton} ${className ?? ""}`}
      aria-hidden
      style={{ width, height, borderRadius: radius, ...style }}
    >
      {children}
    </span>
  );
}