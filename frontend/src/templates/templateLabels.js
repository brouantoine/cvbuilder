export const TEMPLATE_STYLE_LABELS = {
  classic: "Classique",
  modern: "Moderne",
  creative: "Standard",
  minimal: "Minimaliste",
  colorful: "Coloré",
};

export const TEMPLATE_STYLE_ALIASES = {
  classic: ["classique", "classic"],
  modern: ["moderne", "modern"],
  creative: ["standard", "standar", "creative", "creatif"],
  minimal: ["minimaliste", "minimal", "epure", "épuré"],
  colorful: ["colore", "coloré", "colorful", "couleur"],
};

export function templateStyleLabel(template) {
  return TEMPLATE_STYLE_LABELS[template?.category] || template?.category_display || "Standard";
}

export function normalizeSearchText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function templateSearchText(template) {
  const aliases = TEMPLATE_STYLE_ALIASES[template?.category] || [];
  return normalizeSearchText([
    template?.name,
    template?.description,
    template?.category,
    template?.category_display,
    templateStyleLabel(template),
    ...aliases,
  ].filter(Boolean).join(" "));
}
