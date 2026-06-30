# Modeles CV a presenter aux clients

1. Depose tes fichiers Word `.docx` dans ce dossier.
2. Connecte-toi avec un compte admin/staff.
3. Va dans la page "Choisir un modele".
4. Clique sur "Synchroniser les modeles".

Le systeme lit automatiquement les noms des fichiers et complete `templates.json`.

Exemple: si tu ajoutes ces fichiers:

```text
modele_commercial.docx
modele_comptable.docx
modele_etudiant.docx
```

Apres synchronisation, `templates.json` contiendra une entree pour chaque fichier.

Tu peux ensuite modifier seulement les champs visibles:

```json
{
  "filename": "modele_commercial.docx",
  "name": "Commercial propre",
  "category": "modern",
  "description": "CV clair pour vente, accueil et relation client.",
  "is_premium": false,
  "is_active": true,
  "order": 1
}
```

Ne change pas `filename` sauf si tu renommes aussi le fichier `.docx`.

Categories possibles: `classic`, `modern`, `creative`, `minimal`, `colorful`.

Important: pour remplir parfaitement un fichier Word, il doit contenir des placeholders comme `{{ first_name }}`, `{{ last_name }}`, `{{ profile }}`, `{{ experiences_text }}`. Si le fichier n'a pas de placeholders, le systeme garde un rendu propre genere par code.
