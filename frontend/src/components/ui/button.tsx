import {
  cloneElement,
  forwardRef,
  isValidElement,
  type ButtonHTMLAttributes,
  type ReactElement,
  type ReactNode,
} from "react";
import styles from "./button.module.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
  loading?: boolean;
  asChild?: boolean;
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      asChild = false,
      className,
      children,
      ...props
    },
    ref,
  ) {
    const classes = [
      styles.btn,
      styles[variant],
      styles[size],
      loading ? styles.loading : "",
      className ?? "",
    ]
      .filter(Boolean)
      .join(" ");

    if (asChild && isValidElement(children)) {
      const child = children as ReactElement<{ className?: string; disabled?: boolean }>;
      return cloneElement(child, {
        className: [child.props.className, classes].filter(Boolean).join(" "),
        ...(disabled || loading ? { "aria-disabled": true } : {}),
        ...props,
      });
    }

    return (
      <button
        ref={ref}
        className={classes}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading && <span className={styles.spinner} aria-hidden />}
        {children}
      </button>
    );
  },
);