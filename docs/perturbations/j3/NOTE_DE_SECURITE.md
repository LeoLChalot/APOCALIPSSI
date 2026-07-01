
# Note de Sécurité J3 : Protection contre les Injections de Prompt

**Date :** 2026-07-01  
**Projet :** EduTutor IA  
**Statut :** Implémenté et Validé  

## 1. Diagnostic
L'analyse de l'architecture initiale a révélé que les entrées de l'utilisateur (textes collés ou extraits de PDF) étaient concaténées de manière naïve à la suite du prompt système. N'ayant pas de frontière hermétique, le LLM interprétait le texte de l'utilisateur sur le même niveau de priorité que les directives des développeurs. 

Lorsqu'un utilisateur insérait des phrases de type évasion (`</course>`, `[ADMIN OVERRIDE]`), le LLM considérait que le contexte d'exercice était clos et exécutait les nouvelles instructions pirates, conduisant à des détournements de comportement ou des corruptions de format (hallucinations, non-respect du format JSON).

## 2. Stratégie défensive mise en place
Une stratégie de défense en profondeur a été déployée à 3 niveaux :
1. **Couche d'assainissement (Fail-Fast) :** Utilisation d'un `PromptSanitizer` interceptant en amont via expressions régulières les patterns d'attaques connus (fermetures de balises, mots-clés d'override) et neutralisant les chevrons HTML (`<` -> `&lt;`).
2. **Isolation Structurelle (Sandboxing de l'input) :** Encapsulation stricte du texte utilisateur au sein de balises de délimitation claires (`======= DEBUT ... =======`) combinée à une directive système défensive explicite ordonnant au LLM de traiter tout contenu situé entre ces balises comme de simples données passives.
3. **Validation Post-LLM (Garde-fou) :** Durcissement de la fonction `parse_and_validate_quiz` pour interdire les doublons dans les choix de réponses et lever une exception bloquante si la structure de l'objet JSON (10 questions, 4 options uniques) est altérée par une injection qui aurait contourné les filtres amont.

## 3. Limites résiduelles
Bien que robuste, cette protection présente des angles morts :
- **Injections sémantiques subtiles (Indirect Prompt Injection) :** Si un texte de cours décrit de manière purement théorique une attaque ou simule un dialogue d'injection historique, le sanitizer ou le LLM peut générer un faux positif et bloquer un cours légitime de cybersécurité.
- **Évolution des techniques d'obfuscation :** Les chiffrements complexes ou des métaphores poussées non répertoriées dans nos regex dépendent exclusivement de la capacité d'attention du LLM à respecter son Prompt Système.