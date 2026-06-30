#!/bin/bash
# ==============================================================================
# APOCAL'IPSSI 2026 - Générateur de Tableau ADR Automatisé
# Rôle : Benchmark technique complet + Notation Humaine + Export Markdown
# ==============================================================================

COURSE_REF="backend/quizzes/fixtures/cours_reference.pdf"
OLLAMA_CONTAINER="apocalipssi-2026-ollama"               
OLLAMA_PORT="11434"                                      
MODELS=("llama3.1:8b" "llama3.2:3b" "phi3:mini")         

OUTPUT_DIR="docs/adr"
MD_FILE="$OUTPUT_DIR/TABLEAU_ADR_0002.md"

mkdir -p "$OUTPUT_DIR"
cd "$(dirname "$0")/.." || exit

# Initialisation du tableau Markdown
echo "### Tableau Récapitulatif du Benchmark IA (Automatisé)" > "$MD_FILE"
echo "| Modèle testé | Latence (p50) | Latence (p95) | Note Équipe | Poids Disque | RAM max estimée |" >> "$MD_FILE"
echo "| :--- | :---: | :---: | :---: | :---: | :---: |" >> "$MD_FILE"

echo "📝 Extraction du PDF en cours..."
TEXTE_BRUT=$(pdftotext "$COURSE_REF" - | tr -d '"' | tr -d '\\' | tr '\n' ' ' | tr '\r' ' ')
PROMPT_TEXT="${TEXTE_BRUT:0:4000}"

echo "========================================================"
echo "🤖 DÉBUT DE LA CAMPAGNE D'ÉVALUATION DES MODÈLES"
echo "========================================================"

for MODEL in "${MODELS[@]}"; do
    echo -e "\n👉 Modèle en cours d'analyse : \033[1;36m$MODEL\033[0m"
    docker exec -i "$OLLAMA_CONTAINER" ollama pull "$MODEL" > /dev/null 2>&1
    
    # 1. Récolte Automatique : Taille sur le disque
    DISK_SIZE=$(docker exec -i "$OLLAMA_CONTAINER" ollama list | grep -w "$MODEL" | awk '{print $3$4}')
    
    DUREES=()
    QCM_EXEMPLE=""
    RAM_MAX="N/A"

    for run in {1..5}; do
        echo -n "   - Run #$run / 5... "
        
        START=$(date +%s)
        
        # Envoi de la requête avec jq
        PAYLOAD=$(jq -n --arg m "$MODEL" --arg p "Génère un QCM de 10 questions à partir de ce texte : $PROMPT_TEXT" '{model: $m, prompt: $p, stream: false}')
        
        # ⚠️ On lance la génération en tâche de fond (& à la fin)
        # On sauvegarde temporairement la réponse dans un fichier pour y accéder après le wait
        curl -s -X POST "http://localhost:$OLLAMA_PORT/api/generate" -H "Content-Type: application/json" -d "$PAYLOAD" > response_$run.tmp &
        GEN_PID=$!
        
        # Interrogation API pour voir la RAM consommée
        sleep 2
        
        # On attend que le modèle soit chargé en mémoire
        if [ "$run" -eq 1 ]; then
             RAM_BYTES=""
             for attempt in {1..10}; do
                 sleep 1
                 # On prend la taille totale en mémoire (.size) du premier modèle actif
                 RAM_BYTES=$(curl -s "http://localhost:$OLLAMA_PORT/api/ps" | jq -r '.models[0].size // empty')
                 
                 # Si la valeur n'est pas vide et ne vaut pas null, le modèle est chargé !
                 if [ -n "$RAM_BYTES" ] && [ "$RAM_BYTES" != "null" ]; then
                     break
                 fi
             done

             if [ -n "$RAM_BYTES" ] && [ "$RAM_BYTES" != "null" ]; then
                # Conversion propre via bc
                RAM_MAX=$(echo "scale=1; $RAM_BYTES / (1024^3)" | bc)
                RAM_MAX="${RAM_MAX} GB"
             else
                RAM_MAX="N/A"
             fi
        fi

        # On attend obligatoirement que la génération se termine avant de passer à la suite
        wait $GEN_PID
        END=$(date +%s)
        
        # Récupération de la réponse depuis le fichier temporaire
        RESPONSE=$(cat response_$run.tmp)
        rm response_$run.tmp
        
        DUREE=$((END - START))
        DUREES+=($DUREE)
        
        if [ "$run" -eq 1 ]; then
             echo "${DUREE}s (VRAM: $RAM_MAX)"
        else
             echo "${DUREE}s"
        fi
        
        # On sauvegarde le texte généré du premier run pour la notation humaine
        if [ "$run" -eq 1 ]; then
            QCM_EXEMPLE=$(echo "$RESPONSE" | jq -r '.response')
        fi
    done

    # 2. Récolte Automatique : Calcul Mathématique (Médiane et p95)
    # Tri du tableau des durées
    IFS=$'\n' SORTED=($(sort -n <<<"${DUREES[*]}"))
    unset IFS
    P50=${SORTED[2]} # La médiane est le 3ème élément
    P95=${SORTED[4]} # Le p95 sur 5 éléments correspond au temps le plus long

    # 3. Récolte Humaine : Notation subjective
    echo "--------------------------------------------------------"
    echo -e "\033[1;33mVoici l'évaluation générée par $MODEL (Aperçu) :\033[0m"
    echo "..."
    echo "${QCM_EXEMPLE:0:800}" # Affiche les 800 premiers caractères
    echo "..."
    echo "--------------------------------------------------------"
    
    # Pause le script et attend que votre équipe saisisse une note
    read -p "🤔 Quelle note sur 5 donnez-vous à la qualité de ce quiz ? (ex: 3.5) : " NOTE
    
    # 4. Écriture finale dans le tableau Markdown
    echo "| **$MODEL** | ${P50}s | ${P95}s | **$NOTE / 5** | $DISK_SIZE | ~ $RAM_MAX |" >> "$MD_FILE"

done

echo ""
echo "========================================================"
echo "🎉 BENCHMARK TERMINÉ ! VOICI VOTRE LIVRABLE POUR L'ADR :"
echo "========================================================"
cat "$MD_FILE"