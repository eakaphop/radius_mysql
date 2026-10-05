/**
 * Minimal Tailwind primitives standing in for shadcn/ui components.
 *
 * shadcn is a generator, not a runtime dependency, and this repo was written
 * on a machine without Node, so its CLI could not be run. Once `npx shadcn
 * init` is available, these can be replaced file-by-file by the generated
 * components in src/components/ui/.
 */

import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";
import { forwardRef } from "react";

import { CloseIcon } from "@/components/ui/icons";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-foreground shadow-sm hover:opacity-90",
  secondary: "border border-border bg-card shadow-sm hover:bg-muted",
  danger: "border border-destructive/30 text-destructive shadow-sm hover:bg-destructive/10",
  ghost: "text-foreground/70 hover:bg-muted hover:text-foreground",
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 ${buttonVariants[variant]} ${className}`}
      {...props}
    />
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...props }, ref) {
    return (
      <input
        ref={ref}
        className={`w-full rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground ${className}`}
        {...props}
      />
    );
  }
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = "", ...props }, ref) {
    return (
      <select
        ref={ref}
        className={`rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm transition-colors ${className}`}
        {...props}
      />
    );
  }
);

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

const badgeTones: Record<string, string> = {
  green: "bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-400",
  red: "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-400",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-400",
  blue: "bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-400",
  gray: "bg-gray-100 text-gray-700 dark:bg-gray-500/15 dark:text-gray-300",
};

export function Badge({ tone = "gray", children }: { tone?: string; children: ReactNode }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${badgeTones[tone] ?? badgeTones.gray}`}
    >
      {children}
    </span>
  );
}

const alertTones: Record<string, string> = {
  amber:
    "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300",
  green:
    "border-green-300 bg-green-50 text-green-900 dark:border-green-500/30 dark:bg-green-500/10 dark:text-green-300",
  red: "border-red-300 bg-red-50 text-red-900 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300",
  blue: "border-blue-300 bg-blue-50 text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300",
};

export function Alert({
  tone = "amber",
  children,
  onDismiss,
}: {
  tone?: string;
  children: ReactNode;
  onDismiss?: () => void;
}) {
  return (
    <div
      role="status"
      className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 text-sm ${alertTones[tone] ?? alertTones.amber}`}
    >
      <div>{children}</div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="opacity-60 hover:opacity-100"
        >
          <CloseIcon width={14} height={14} />
        </button>
      )}
    </div>
  );
}

export function Card({
  title,
  actions,
  children,
  className = "",
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-border bg-card p-4 shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title && <h2 className="text-sm font-medium text-foreground/70">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1 border-b border-border">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === active}
          onClick={() => onChange(tab.id)}
          className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
            tab.id === active
              ? "border-primary font-medium text-foreground"
              : "border-transparent text-foreground/60 hover:text-foreground"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function Dialog({
  open,
  title,
  onClose,
  size = "md",
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  size?: "md" | "lg";
  children: ReactNode;
}) {
  if (!open) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-6 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        className={`w-full ${size === "lg" ? "max-w-5xl" : "max-w-2xl"} rounded-xl border border-border bg-card p-6 shadow-xl`}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1 text-foreground/60 transition-colors hover:bg-muted hover:text-foreground"
          >
            <CloseIcon width={16} height={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
