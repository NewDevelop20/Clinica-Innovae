#!/usr/bin/env bash
# Ejecutar en Cloud Shell, desde una cuenta y proyecto del titular. No contiene claves.
set -euo pipefail
: "${INNOVAE_PROJECT_ID:?Indica el ID del proyecto de Google Cloud con facturación activa}"
: "${INNOVAE_GOOGLE_ACCOUNT:?Indica el Gmail autorizado en gcloud}"
: "${INNOVAE_SERVICE_ACCOUNT:?Indica la cuenta de servicio dedicada al chatbot}"
: "${INNOVAE_APPS_SCRIPT_URL:?Indica la URL pública /exec de Apps Script}"
INNOVAE_SECRET_NAME="${INNOVAE_SECRET_NAME:-anthropic-key}"
INNOVAE_REGION="${INNOVAE_REGION:-europe-southwest1}"
INNOVAE_MODEL="${INNOVAE_MODEL:-claude-haiku-5-5}"
command -v gcloud >/dev/null || { echo 'Ejecuta este archivo desde Google Cloud Shell o instala gcloud.' >&2; exit 1; }
[[ "$INNOVAE_GOOGLE_ACCOUNT" != *.gserviceaccount.com ]] || { echo 'Usa tu cuenta de Google autorizada, no credenciales de otro servicio.' >&2; exit 1; }
[[ "$INNOVAE_SERVICE_ACCOUNT" == *@"$INNOVAE_PROJECT_ID".iam.gserviceaccount.com ]] || { echo 'La cuenta de servicio debe pertenecer al proyecto indicado.' >&2; exit 1; }
[[ "$INNOVAE_APPS_SCRIPT_URL" == https://script.google.com/macros/s/*/exec ]] || { echo 'URL de Apps Script no válida.' >&2; exit 1; }
INNOVAE_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GCLOUD=(gcloud --account="$INNOVAE_GOOGLE_ACCOUNT" --project="$INNOVAE_PROJECT_ID")
# Estos recursos deben haberse creado desde la cuenta del titular. Solo consultar metadatos.
"${GCLOUD[@]}" projects describe "$INNOVAE_PROJECT_ID" >/dev/null
"${GCLOUD[@]}" iam service-accounts describe "$INNOVAE_SERVICE_ACCOUNT" >/dev/null
"${GCLOUD[@]}" secrets versions describe latest --secret="$INNOVAE_SECRET_NAME" >/dev/null
"${GCLOUD[@]}" services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
"${GCLOUD[@]}" secrets add-iam-policy-binding "$INNOVAE_SECRET_NAME" \
  --member="serviceAccount:$INNOVAE_SERVICE_ACCOUNT" --role=roles/secretmanager.secretAccessor >/dev/null
"${GCLOUD[@]}" run deploy chatbot-innovae --source "$INNOVAE_SCRIPT_DIR" \
  --region "$INNOVAE_REGION" --allow-unauthenticated \
  --service-account "$INNOVAE_SERVICE_ACCOUNT" \
  --min-instances 0 --max-instances 1 --concurrency 8 --cpu 1 --memory 512Mi --timeout 300 \
  --set-env-vars "MODO_SIMULADO=0,ANTHROPIC_MODEL=$INNOVAE_MODEL,APPS_SCRIPT_URL=$INNOVAE_APPS_SCRIPT_URL,ORIGENES_PERMITIDOS=https://newdevelop20.github.io" \
  --set-secrets "ANTHROPIC_API_KEY=$INNOVAE_SECRET_NAME:latest"
INNOVAE_RUN_URL="$("${GCLOUD[@]}" run services describe chatbot-innovae --region "$INNOVAE_REGION" --format='value(status.url)')"
# Permitir la demo del propio servicio, además de la web pública. El separador |
# mantiene la coma de la lista CORS dentro de una única variable de entorno.
"${GCLOUD[@]}" run services update chatbot-innovae --region "$INNOVAE_REGION" \
  --update-env-vars "^|^ORIGENES_PERMITIDOS=https://newdevelop20.github.io,${INNOVAE_RUN_URL%/}"
printf '%s\n' "$INNOVAE_RUN_URL"
echo 'No se ha cambiado la configuración pública del widget ni se ha activado WhatsApp.'
echo 'Comprueba /health y una conversación real antes de configurar assets/chatbot-config.js.'
