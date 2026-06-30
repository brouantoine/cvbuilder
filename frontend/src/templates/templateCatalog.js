export const TEMPLATE_STYLES = {
  "modele-simple": {
    variant: "simple",
    category: "classic",
    accent: "#1f2937",
    label: "Essentiel",
  },
  "modele-classique": {
    variant: "classic",
    category: "classic",
    accent: "#1d4ed8",
    label: "Classique",
  },
  "modele-moderne": {
    variant: "modern",
    category: "modern",
    accent: "#0f766e",
    label: "Moderne",
  },
  "modele-compact": {
    variant: "compact",
    category: "minimal",
    accent: "#7c2d12",
    label: "Compact",
  },
  "modele-executif": {
    variant: "executive",
    category: "minimal",
    accent: "#111827",
    label: "Executif",
  },
  "modele-creatif": {
    variant: "creative",
    category: "creative",
    accent: "#9f1239",
    label: "Creatif",
  },
};

const CATEGORY_STYLES = {
  classic: TEMPLATE_STYLES["modele-classique"],
  modern: TEMPLATE_STYLES["modele-moderne"],
  creative: TEMPLATE_STYLES["modele-creatif"],
  minimal: TEMPLATE_STYLES["modele-executif"],
  colorful: {
    variant: "creative",
    category: "colorful",
    accent: "#be123c",
    label: "Coloré",
  },
};

export function templateStyle(template) {
  return TEMPLATE_STYLES[template?.slug] || CATEGORY_STYLES[template?.category] || TEMPLATE_STYLES["modele-simple"];
}
