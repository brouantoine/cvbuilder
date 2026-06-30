import samplePhoto from "../assets/cv-photos/normalized/cv-photo-01.png";

export const SECTION_DEFINITIONS = [
  { id: "profile", label: "Profil", shortLabel: "Profil" },
  { id: "experiences", label: "Expériences professionnelles", shortLabel: "Expériences" },
  { id: "education", label: "Formation", shortLabel: "Formation" },
  { id: "skills", label: "Compétences", shortLabel: "Compétences" },
  { id: "languages", label: "Langues", shortLabel: "Langues" },
  { id: "hobbies", label: "Loisirs", shortLabel: "Loisirs" },
];

export const DEFAULT_SECTION_ORDER = SECTION_DEFINITIONS.map((section) => section.id);

export const DEFAULT_ENABLED_SECTIONS = SECTION_DEFINITIONS.reduce((sections, section) => {
  sections[section.id] = true;
  return sections;
}, {});

export const defaultExperience = () => ({
  job_title: "",
  company: "",
  location: "",
  period: "",
  type: "",
  missions: [""],
});

export const defaultEducation = () => ({
  degree: "",
  institution: "",
  location: "",
  period: "",
});

export const defaultLanguage = () => ({ language: "", level: "" });
export const defaultExtraSection = () => ({ title: "", items: [""] });

export function createDefaultCVData() {
  return {
    first_name: "",
    last_name: "",
    job_title: "",
    photo_url: "",
    phone: "",
    email: "",
    address: "",
    linkedin: "",
    github: "",
    portfolio: "",
    driving_license: "",
    profile: "",
    experiences: [defaultExperience()],
    education: [defaultEducation()],
    skills: [""],
    languages: [defaultLanguage()],
    hobbies: [""],
    extra_sections: [],
    enabled_sections: { ...DEFAULT_ENABLED_SECTIONS },
    section_order: [...DEFAULT_SECTION_ORDER],
  };
}

export const sampleCVData = {
  first_name: "Awa",
  last_name: "Kone",
  job_title: "Cheffe de projet digital",
  photo_url: samplePhoto,
  phone: "+225 07 00 00 00 00",
  email: "awa.kone@email.com",
  address: "Abidjan, Côte d'Ivoire",
  linkedin: "linkedin.com/in/awakone",
  github: "github.com/awakone",
  portfolio: "awakone.dev",
  driving_license: "Permis B",
  profile:
    "Profil orienté résultats, avec une solide expérience dans la coordination de projets digitaux, la relation client et l'amélioration continue des opérations.",
  experiences: [
    {
      job_title: "Cheffe de projet digital",
      company: "Studio Nova",
      location: "Abidjan",
      period: "2023 - Aujourd'hui",
      type: "CDI",
      missions: [
        "Pilotage de projets web et coordination d'équipes créatives.",
        "Suivi des indicateurs de performance et amélioration des parcours utilisateurs.",
      ],
    },
    {
      job_title: "Assistante marketing",
      company: "Market CI",
      location: "Abidjan",
      period: "2021 - 2023",
      type: "CDD",
      missions: ["Gestion de campagnes social media.", "Préparation de reportings mensuels."],
    },
  ],
  education: [
    {
      degree: "Cycle ingénieur",
      institution: "Université Félix Houphouët-Boigny",
      location: "Abidjan",
      period: "2019 - 2021",
    },
  ],
  skills: ["Gestion de projet", "Communication", "Analyse de données", "React", "Notion"],
  languages: [
    { language: "Français", level: "Courant" },
    { language: "Anglais", level: "Intermédiaire" },
  ],
  hobbies: ["Lecture", "Design", "Bénévolat"],
  extra_sections: [
    {
      title: "Certifications",
      items: ["Gestion de projet agile", "Communication professionnelle"],
    },
  ],
  enabled_sections: { ...DEFAULT_ENABLED_SECTIONS },
  section_order: [...DEFAULT_SECTION_ORDER],
};

export function normalizeCVData(data = {}) {
  const defaults = createDefaultCVData();
  const normalized = { ...defaults, ...data };

  for (const key of ["experiences", "education", "skills", "languages", "hobbies", "extra_sections"]) {
    if (!Array.isArray(normalized[key])) normalized[key] = defaults[key];
  }

  normalized.enabled_sections = {
    ...DEFAULT_ENABLED_SECTIONS,
    ...(data.enabled_sections || {}),
  };

  const knownSections = new Set(DEFAULT_SECTION_ORDER);
  const savedOrder = Array.isArray(data.section_order) ? data.section_order.filter((id) => knownSections.has(id)) : [];
  normalized.section_order = [
    ...savedOrder,
    ...DEFAULT_SECTION_ORDER.filter((id) => !savedOrder.includes(id)),
  ];

  return normalized;
}

export function sectionLabel(sectionId) {
  return SECTION_DEFINITIONS.find((section) => section.id === sectionId)?.label || sectionId;
}
