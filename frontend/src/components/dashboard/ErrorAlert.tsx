interface ErrorAlertProps {
  title?: string;
  message: string;
  onDismiss?: () => void;
}

export function ErrorAlert({ title = "Something went wrong", message, onDismiss }: ErrorAlertProps) {
  return (
    <div
      className="rounded-lg border border-risk-high/40 bg-risk-high/10 px-4 py-3 text-sm text-risk-high"
      role="alert"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-risk-high/90">{message}</p>
        </div>
        {onDismiss ? (
          <button
            type="button"
            onClick={onDismiss}
            className="shrink-0 rounded-md px-2 py-1 text-xs font-medium hover:bg-risk-high/10"
          >
            Dismiss
          </button>
        ) : null}
      </div>
    </div>
  );
}
