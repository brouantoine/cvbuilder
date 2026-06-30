# Modèles Word pour la génération de CV

Place ici tes fichiers `.docx` (ex: `modele_classique.docx`).

Dans l’admin Django (Templates / CV templates), renseigne pour chaque modèle le champ **Docx filename** avec le nom du fichier (ex: `modele_classique.docx`).

## Placeholders à utiliser dans le Word

Tu peux écrire dans ton .docx les marqueurs suivants ; ils seront remplacés par les données du CV.

### Identité et contact
- `{{first_name}}` — Prénom  
- `{{last_name}}` — Nom  
- `{{job_title}}` — Intitulé du poste  
- `{{photo_url}}` — URL de la photo (affichée en texte ; pour insérer l’image il faudra du code en plus)  
- `{{phone}}` — Téléphone  
- `{{email}}` — Email  
- `{{address}}` — Adresse ou ville  
- `{{linkedin}}` — Profil LinkedIn  
- `{{driving_license}}` — Permis  

### Texte
- `{{profile}}` — Paragraphe « À propos de moi »  

### Blocs (déjà formatés en texte avec puces)
- `{{experiences}}` — Liste des expériences (poste, entreprise, lieu, période, missions)  
- `{{education}}` — Liste des formations  
- `{{skills}}` — Liste des compétences  
- `{{languages}}` — Langues et niveaux  
- `{{hobbies}}` — Loisirs / centres d’intérêt  

Exemple dans Word :  
`{{first_name}} {{last_name}}`  
`{{job_title}}`  
`{{profile}}`  
`{{experiences}}`  
`{{education}}`  
`{{skills}}`  
`{{languages}}`  
`{{hobbies}}`
