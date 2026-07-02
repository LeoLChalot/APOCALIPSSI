# Analyse de risques — EduTutor IA · Perturbation J4

## Matrice probabilité × impact

> **Notation :** Probabilité (P) et Impact (I) sur une échelle de 1 à 3.
>
> **Score = P × I** — Priorité : 🔴 Critique (≥ 6) · 🟠 Élevé (4-5) · 🟡 Modéré (2-3) · 🟢 Faible (1)

Voici la liste des 8 riques avec le score le plus haut :

| #   | Axe            | Risque                                                                                             | P (1-3) | I (1-3) | Score | Priorité    |
| --- | -------------- | -------------------------------------------------------------------------------------------------- | ------- | ------- | ----- | ----------- |
| R1  | ⚡ Scalabilité | Surcharge serveur lors des pics de connexion (ex. veille de bac) → indisponibilité totale          | 3       | 3       | **9** | 🔴 Critique |
| R2  | ⚡ Scalabilité | LLM Local submergé : panne ou rate-limit → service IA coupé                                        | 2       | 3       | **6** | 🔴 Critique |
| R3  | ♿ RGAA        | Non-conformité RGAA au moment du contrôle État → rejet du contrat plateforme nationale             | 2       | 3       | **6** | 🔴 Critique |
| R4  | ♿ RGAA        | Génération de quiz par le LLM sans structure sémantique → inutilisable par lecteur d'écran         | 3       | 2       | **6** | 🔴 Critique |
| R5  | 🌍 i18n        | Textes codés en dur dans les composants → internationalisation impossible sans refactoring massif  | 3       | 2       | **6** | 🔴 Critique |
| R6  | 🌍 i18n        | LLM répondant toujours en français quelle que soit la langue de l'élève                            | 3       | 2       | **6** | 🔴 Critique |
| R7  | ⚡ Scalabilité | Base de données non optimisée (absence d'index, N+1 queries) → dégradation progressive sous charge | 2       | 2       | **4** | 🟠 Élevé    |
| R8  | ♿ RGAA        | Palette de couleurs insuffisante en contraste (ratio < 4.5:1) → non-conformité WCAG AA             | 2       | 2       | **4** | 🟠 Élevé    |

---

## Actions préventives

| #   | Risque                 | Action préventive                                                                                                       | Estimation | MoSCoW     | Tag       |
| --- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | --------- |
| R1  | Surcharge serveur      | Mettre en place autoscaling (ex. k8s) + CDN pour les assets statiques + test de charge (k6 ou Locust)                   | 13 pts     | **Must**   | `[scale]` |
| R2  | Fournisseur LLM unique | Implémenter un pattern de fallback vers un LLM secondaire avec circuit breaker                                          | 8 pts      | **Must**   | `[scale]` |
| R3  | Non-conformité RGAA    | Audit RGAA complet (outil Axe ou Lighthouse) + plan de remédiation priorisé avant livraison État                        | 8 pts      | **Must**   | `[a11y]`  |
| R4  | Quiz non structuré     | Forcer une sortie JSON structurée du LLM (rôles ARIA injectés côté prompt) + tests avec lecteur d'écran NVDA            | 5 pts      | **Must**   | `[a11y]`  |
| R5  | Textes codés en dur    | Externaliser tous les textes UI en fichiers de langue (`fr.json`, `en.json`, `es.json`) via i18next                     | 8 pts      | **Must**   | `[i18n]`  |
| R6  | LLM en français forcé  | Ajouter un paramètre `lang` au system prompt : `"Réponds exclusivement en {langue}."` + sélecteur de langue utilisateur | 5 pts      | **Must**   | `[i18n]`  |
| R7  | BDD non optimisée      | Audit des requêtes (Django Debug Toolbar / EF Core logs) + ajout d'index sur les colonnes filtrées fréquemment          | 5 pts      | **Should** | `[scale]` |
| R8  | Contraste insuffisant  | Audit couleurs avec Colour Contrast Analyser + mise à jour du design token `--color-primary` si ratio < 4.5:1           | 3 pts      | **Should** | `[a11y]`  |

---

## Synthèse visuelle

```
         Impact
    3 |  R3  R2  R1
      |  R4  R5  R6
    2 |       R7  R8
      |
    1 |
      +--+---+---+--→ Probabilité
         1   2   3
```

**5 risques critiques (🔴)** à traiter en priorité absolue dans le next sprint backlog · **2 risques élevés (🟠)** à planifier au Sprint suivant. Seul l'audit RGAA sera fait lorsque le developpement sur l'accessibilité sera fini et prêt à être livré.
