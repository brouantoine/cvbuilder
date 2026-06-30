export function Input({
  label,
  type = "text",
  name,
  value,
  onChange,
  placeholder,
  error,
  required,
  autoComplete,
}) {
  return (
    <div className="form-group">
      {label && (
        <label htmlFor={name}>
          {label}
          {required && " *"}
        </label>
      )}
      <input
        id={name}
        name={name}
        type={type}
        value={value ?? ""}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className={error ? "input-error" : ""}
      />
      {error && <span className="form-error">{error}</span>}
    </div>
  );
}
