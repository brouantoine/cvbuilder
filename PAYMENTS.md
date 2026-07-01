# Paiement Paystack — flow solide (13 scénarios de surveillance)

Le flux repose sur **3 sources de vérité** qui convergent, pour qu'aucun paiement
ne soit perdu ni compté deux fois :

1. **Webhook** Paystack (`charge.success`) — serveur→serveur, arrive même si le
   téléphone du client s'éteint ou s'il ferme l'onglet.
2. **Verify** au retour (`callback_url` → `/api/cvs/payments/verify/`).
3. **Réconciliation** des paiements en attente (`reconcile_pending_payments`),
   déclenchée à chaque chargement du dashboard (`/api/cvs/plans/`).

Fichiers : `backend/cvs/services/payments.py`, `access.py`, `views.py`.

## Garanties clés

- **Signature vérifiée** (HMAC-SHA512) sur chaque webhook — un faux webhook est rejeté.
- **Montant + devise + user + plan** revalidés côté serveur (`_validate_payment_confirmation`)
  — impossible de payer 100 F et débloquer un plan à 1000 F.
- **Idempotence** : `mark_success` est `@transaction.atomic` + `select_for_update`,
  et `grant_access` fait `update_or_create(payment=…)` → **un seul droit par paiement**,
  même si webhook ET verify ET réconciliation arrivent ensemble.
- **Le serveur ne fait jamais confiance au client** : le retour navigateur ne
  débloque rien tant que Paystack n'a pas confirmé `status == "success"`.

## Les 13 scénarios couverts

| # | Situation | Comportement |
|---|-----------|--------------|
| 1 | Paiement réussi normal | Webhook + verify → 1 droit octroyé |
| 2 | Paiement échoué | `status=failed`, aucun droit |
| 3 | Paiement abandonné (client ferme la page Paystack) | reste `pending`, aucun droit ; nettoyé à la réconciliation |
| 4 | **Téléphone éteint / connexion coupée après paiement** | le **webhook** octroie le droit sans le client |
| 5 | Webhook ET verify arrivent en même temps | `select_for_update` + idempotence → 1 seul droit |
| 6 | Webhook en double (Paystack réémet) | idempotent → aucun droit en double |
| 7 | Verify appelé avant l'arrivée du webhook | verify interroge Paystack et octroie immédiatement |
| 8 | Ni webhook ni verify (client revient plus tard) | **réconciliation** au dashboard re-vérifie et octroie |
| 9 | Faux webhook / signature invalide | rejeté (`Signature Paystack invalide`) |
| 10 | Montant payé ≠ montant attendu | rejeté (`Montant Paystack invalide`) |
| 11 | Devise incorrecte | rejeté (`Devise Paystack invalide`) |
| 12 | Référence d'un autre utilisateur (vol de ref) | rejeté (`Transaction introuvable` / user mismatch) |
| 13 | Référence inexistante / rejouée | `Transaction introuvable` ; une ref est unique et à usage unique |
| +  | Paystack momentanément injoignable | l'appel échoue proprement, le paiement reste `pending` et sera réconcilié |

## Ce qui débloque quoi

- **Essai gratuit** (7 j, inscription) → CV illimités, aucun crédit consommé.
- **Abonnement hebdo** (1000 F, 7 j) → **5 crédits** ; générer un CV pas encore
  débloqué en consomme 1. Un CV débloqué reste téléchargeable à vie (`CV.is_unlocked`).
- La consommation d'un crédit est atomique (`unlock_cv`, `select_for_update`) :
  impossible de débloquer 6 CV avec 5 crédits, même en cliquant vite plusieurs fois.
