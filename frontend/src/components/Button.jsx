export function Button({ children, variant = "primary", type = "button", disabled, onClick, className = "" }) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`btn btn-${variant} ${className}`}
    >
      {children}
    </button>
  );
}
