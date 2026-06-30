import { normalizeCVData, sampleCVData, sectionLabel } from "../templates/cvData";
import { templateStyle } from "../templates/templateCatalog";
import "../styles/CVPreview.css";

function cleanList(items) {
  return (items || []).filter((item) => {
    if (typeof item === "string") return item.trim();
    if (!item || typeof item !== "object") return false;
    return Object.values(item).some((value) => {
      if (Array.isArray(value)) return value.some((entry) => String(entry || "").trim());
      return String(value || "").trim();
    });
  });
}

function ContactLine({ data }) {
  const items = [
    ["Téléphone", data.phone],
    ["Email", data.email],
    ["Ville", data.address],
    ["LinkedIn", data.linkedin],
    ["GitHub", data.github],
    ["Portfolio", data.portfolio],
    ["Permis", data.driving_license],
  ].filter(([, value]) => String(value || "").trim());
  if (!items.length) return null;
  return (
    <div className="cvp-contact">
      {items.map(([label, value]) => (
        <span className="cvp-contact-item" key={label}>
          <strong>{label}</strong>
          <span>{value}</span>
        </span>
      ))}
    </div>
  );
}

function Section({ id, children }) {
  if (!children) return null;
  return (
    <section className={`cvp-section cvp-section-${id}`}>
      <h3>{sectionLabel(id)}</h3>
      {children}
    </section>
  );
}

function CustomSection({ section, index }) {
  const items = cleanList(section.items);
  const title = String(section.title || "").trim();
  if (!title || !items.length) return null;
  return (
    <section className={`cvp-section cvp-section-extra-${index}`}>
      <h3>{title}</h3>
      <ul className="cvp-flat-list">
        {items.slice(0, 5).map((item, itemIndex) => (
          <li key={itemIndex}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function renderProfile(data) {
  if (!data.profile?.trim()) return null;
  return <p>{data.profile}</p>;
}

function renderExperiences(data) {
  const experiences = cleanList(data.experiences);
  if (!experiences.length) return null;
  return (
    <div className="cvp-stack">
      {experiences.slice(0, 3).map((exp, index) => (
        <article key={index} className="cvp-entry">
          <div className="cvp-entry-head">
            <strong>{exp.job_title || "Intitulé du poste"}</strong>
            <span>{exp.period}</span>
          </div>
          <p className="cvp-entry-meta">{[exp.company, exp.location, exp.type].filter(Boolean).join(" · ")}</p>
          {cleanList(exp.missions).length > 0 && (
            <ul>
              {cleanList(exp.missions).slice(0, 2).map((mission, missionIndex) => (
                <li key={missionIndex}>{mission}</li>
              ))}
            </ul>
          )}
        </article>
      ))}
    </div>
  );
}

function renderEducation(data) {
  const education = cleanList(data.education);
  if (!education.length) return null;
  return (
    <div className="cvp-stack">
      {education.slice(0, 2).map((edu, index) => (
        <article key={index} className="cvp-entry">
          <div className="cvp-entry-head">
            <strong>{edu.degree || "Diplôme"}</strong>
            <span>{edu.period}</span>
          </div>
          <p className="cvp-entry-meta">{[edu.institution, edu.location].filter(Boolean).join(" · ")}</p>
        </article>
      ))}
    </div>
  );
}

function renderSkills(data) {
  const skills = cleanList(data.skills);
  if (!skills.length) return null;
  return (
    <div className="cvp-tags">
      {skills.slice(0, 8).map((skill, index) => (
        <span key={index}>{skill}</span>
      ))}
    </div>
  );
}

function renderLanguages(data) {
  const languages = cleanList(data.languages);
  if (!languages.length) return null;
  return (
    <ul className="cvp-flat-list">
      {languages.slice(0, 4).map((language, index) => (
        <li key={index}>
          {typeof language === "string" ? language : [language.language, language.level].filter(Boolean).join(" - ")}
        </li>
      ))}
    </ul>
  );
}

function renderHobbies(data) {
  const hobbies = cleanList(data.hobbies);
  if (!hobbies.length) return null;
  return <p>{hobbies.slice(0, 6).join(", ")}</p>;
}

const RENDERERS = {
  profile: renderProfile,
  experiences: renderExperiences,
  education: renderEducation,
  skills: renderSkills,
  languages: renderLanguages,
  hobbies: renderHobbies,
};

function sectionContent(sectionId, data) {
  return RENDERERS[sectionId]?.(data) || null;
}

export function CVPreview({ template, data = sampleCVData, compact = false }) {
  const normalized = normalizeCVData(data);
  const style = templateStyle(template);
  const photoUrl = normalized.photo_url || normalized.photo;
  const orderedSections = normalized.section_order.filter((id) => normalized.enabled_sections[id]);
  const sidebarSections = ["skills", "languages", "hobbies"].filter((id) => orderedSections.includes(id));
  const mainSections =
    style.variant === "modern" || style.variant === "creative"
      ? orderedSections.filter((id) => !sidebarSections.includes(id))
      : orderedSections;

  const renderSection = (sectionId) => (
    <Section key={sectionId} id={sectionId}>
      {sectionContent(sectionId, normalized)}
    </Section>
  );
  const customSections = cleanList(normalized.extra_sections);

  return (
    <div
      className={`cv-preview cv-preview-${style.variant} ${compact ? "cv-preview-compact-card" : ""}`}
      style={{ "--cv-accent": style.accent }}
    >
      <div className="cvp-paper">
        <header className={`cvp-header ${photoUrl ? "cvp-header-with-photo" : ""}`}>
          {photoUrl && (
            <img
              className="cvp-photo"
              src={photoUrl}
              alt=""
              aria-hidden="true"
            />
          )}
          <div className="cvp-header-text">
            <p className="cvp-kicker">{template?.name || style.label}</p>
            <h2>
              {[normalized.first_name, normalized.last_name].filter(Boolean).join(" ") || "Mon CV"}
            </h2>
            {normalized.job_title && <p className="cvp-role">{normalized.job_title}</p>}
            <ContactLine data={normalized} />
          </div>
        </header>

        {style.variant === "modern" || style.variant === "creative" ? (
          <div className="cvp-two-column">
            <main>{mainSections.map(renderSection)}</main>
            <aside>
              {sidebarSections.map(renderSection)}
              {customSections.map((section, index) => (
                <CustomSection key={index} section={section} index={index} />
              ))}
            </aside>
          </div>
        ) : (
          <main>
            {mainSections.map(renderSection)}
            {customSections.map((section, index) => (
              <CustomSection key={index} section={section} index={index} />
            ))}
          </main>
        )}
      </div>
    </div>
  );
}
