export function StepIndicator({ steps, currentStep }) {
  return (
    <nav className="step-indicator" aria-label="Étapes du formulaire">
      {steps.map((label, i) => (
        <div
          key={i}
          className={`step ${i + 1 <= currentStep ? "active" : ""} ${i + 1 === currentStep ? "current" : ""}`}
        >
          <span className="step-num">{i + 1}</span>
          <span className="step-label">{label}</span>
        </div>
      ))}
    </nav>
  );
}
