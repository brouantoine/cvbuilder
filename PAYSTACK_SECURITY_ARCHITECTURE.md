# Architecture securite Paystack

Ce document definit les scenarios a couvrir pour que le paiement reste fiable meme quand l'utilisateur perd le reseau, ferme son navigateur, eteint son telephone ou revient plus tard.

Principes non negociables:

- La cle secrete Paystack reste uniquement cote serveur Django.
- Le frontend ne recoit que `authorization_url`, `access_code`, `reference` et la cle publique.
- Le droit d'acces n'est jamais donne par le simple retour navigateur.
- La livraison de valeur passe par une verification serveur Paystack ou un webhook signe.
- Toute operation doit etre idempotente: relancer, recevoir deux webhooks ou verifier deux fois ne doit jamais donner deux droits incoherents.
- Le serveur valide toujours le montant, la devise, le plan, l'utilisateur et le CV avant de debloquer l'acces.

Sources Paystack a respecter:

- Initialiser la transaction depuis le backend et ne jamais exposer la cle secrete dans le frontend: https://paystack.com/docs/payments/accept-payments/
- Verifier le statut et le montant avant livraison: https://paystack.com/docs/payments/verify-payments/
- Verifier les webhooks par signature HMAC SHA512 et repondre rapidement `200 OK`: https://paystack.com/docs/payments/webhooks/

## Scenarios de securite et resilience

| # | Scenario | Risque | Comportement attendu |
|---|---|---|---|
| 1 | Absence de reseau avant initialisation | L'utilisateur clique sur payer, mais Django ne joint pas Paystack. | Creer ou conserver une transaction locale `pending` avec reference unique, afficher "paiement non initialise", permettre un retry sur la meme intention sans accorder d'acces. |
| 2 | Coupure internet apres initialisation | Paystack a retourne une URL, mais le navigateur ne s'ouvre pas ou la page ne charge pas. | Stocker `reference`, `authorization_url`, `access_code`; le dashboard affiche "paiement en attente" et permet de reprendre ou verifier. |
| 3 | Fermeture navigateur pendant le checkout | L'utilisateur quitte avant validation. | Aucun acces n'est donne. La transaction reste `pending`; verification manuelle possible via le bouton "Verifier le paiement". |
| 4 | Extinction ou redemarrage du telephone | Le contexte frontend est perdu. | Au retour, le serveur retrouve les transactions `pending` de l'utilisateur et propose reprise ou verification. |
| 5 | Reinitialisation telephone / changement d'appareil | L'utilisateur perd l'etat local. | Apres connexion, le backend liste les paiements en attente lies au compte; aucune dependance critique au localStorage. |
| 6 | Retour Paystack sans webhook recu | Callback charge, mais webhook retarde ou perdu. | Le frontend envoie la `reference` au backend; Django appelle `/transaction/verify/{reference}` avant tout acces. |
| 7 | Webhook recu sans retour utilisateur | L'utilisateur ferme tout apres paiement. | Le webhook signe marque la transaction `success` et cree l'acces; le prochain chargement du dashboard voit le droit actif. |
| 8 | Webhook duplique | Paystack renvoie plusieurs fois le meme evenement. | Traitement idempotent: si la transaction est deja `success`, ne pas recreer de droits differents; `AccessGrant` reste unique par paiement. |
| 9 | Double clic ou double onglet paiement | Plusieurs initialisations concurrentes pour le meme CV. | Generer une reference unique par intention; verrouiller ou reutiliser une transaction `pending` recente pour le meme `user + cv + plan` si elle n'a pas expire. |
| 10 | Callback falsifie par URL | Un attaquant ouvre `/dashboard?reference=...`. | La reference seule ne vaut rien; Django verifie proprietaire, statut Paystack, montant, devise et metadata avant livraison. |
| 11 | Montant manipule | Le client tente de payer 50 F pour un plan a 200 F. | Ignorer les montants venant du frontend. Comparer `data.amount`, `currency`, `plan_type` et `amount_xof` avec la transaction locale. Si mismatch: bloquer et journaliser. |
| 12 | Reference inconnue | Verification d'une reference inexistante localement. | Repondre "transaction introuvable"; ne jamais creer d'acces a partir d'une reference non initiee par notre serveur. |
| 13 | Transaction payee par un autre utilisateur | Reference valide mais liee a un autre compte. | Verification refusee si `payment.user_id != request.user.id`; webhook peut traiter car il ne depend pas de session, mais seulement sur transaction locale. |
| 14 | Statuts non finaux Paystack | Paystack renvoie `pending`, `ongoing`, `processing` ou `queued`. | Garder `pending`, ne pas donner acces; afficher attente et prevoir une reconciliation periodique. |
| 15 | Echec, abandon, reversement ou chargeback | Paiement echoue, abandonne, rembourse ou inverse. | Marquer `failed`, `abandoned` ou statut equivalent; bloquer l'acces futur si le paiement est reverse; journaliser le motif Paystack. |
| 16 | Secret webhook invalide | Requete webhook publique envoyee par un tiers. | Valider `x-paystack-signature` avec HMAC SHA512 sur le corps brut; refuser sans effet si invalide. |
| 17 | Indisponibilite temporaire Paystack verify | Paiement peut etre reussi, mais l'API verify timeout. | Ne pas accorder d'acces tant que non confirme; conserver un statut `verification_pending` logique, retry avec backoff et message utilisateur clair. |
| 18 | Environnement test/live melange | Cle test avec callback live ou inversement. | Verifier prefixes des cles au demarrage, separer URLs callback test/live, refuser `PAYMENTS_ENFORCED=true` si configuration incoherente. |
| 19 | Expiration de droit pendant usage | L'utilisateur paye 2 h, puis continue apres expiration. | Chaque action IA/generation verifie l'acces cote serveur au moment de l'action, pas seulement a l'ouverture de page. |
| 20 | Rejeu de webhook ancien | Un ancien `charge.success` est renvoye. | Comparer reference, statut local, montant, devise et date; ne jamais etendre un droit deja cree sauf regle business explicite. |

## Modele serveur recommande

Etats minimaux:

- `pending`: transaction creee localement, pas encore confirmee.
- `initialized`: Paystack a retourne `authorization_url` et `access_code`.
- `verification_pending`: Paystack non joignable ou statut non final.
- `success`: paiement confirme et montant valide.
- `failed`: paiement refuse.
- `abandoned`: checkout abandonne.
- `reversed`: paiement rembourse, inverse ou conteste.

Regles d'acces:

- Plan `single_cv`: acces limite au CV et a la duree configuree.
- Plan `weekly`: acces global limite a 7 jours.
- Plan `extra_ai`: credit IA consomme de maniere atomique.

## Checklist technique

- Ajouter une validation stricte `amount/currency/metadata` dans `verify_payment` et `handle_webhook`.
- Ajouter une tache de reconciliation qui verifie les transactions `pending` agees de quelques minutes.
- Journaliser les erreurs Paystack sans stocker de cle secrete.
- Afficher les paiements en attente dans le dashboard.
- Permettre "reprendre le paiement" et "verifier le paiement" depuis l'interface.
- Garder un audit trail: reference, user, cv, plan, montant attendu, montant recu, statut Paystack, payload brut.
- Tester les cas reseau avec mocks: timeout, 403, 429, webhook duplique, callback falsifie, montant mismatch.
