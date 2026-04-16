#!/bin/bash
# PainPan deployment script
# Usage: ./deploy.sh [backend|frontend|all]
# Default: all

set -e

PROJECT="agenticaicolumbia"
REGION="us-central1"
REPO="painpan"
BACKEND_URL="https://painpan-backend-953400329307.us-central1.run.app"
FRONTEND_URL="https://painpan-frontend-953400329307.us-central1.run.app"

# Generate a version tag from git short hash + timestamp
VERSION="v-$(git rev-parse --short HEAD)-$(date +%Y%m%d%H%M)"

TARGET="${1:-all}"

deploy_backend() {
    echo "=== Building backend image ($VERSION) ==="
    gcloud builds submit --config=cloudbuild-backend.yaml \
        --substitutions=SHORT_SHA=$VERSION .

    echo "=== Deploying backend to Cloud Run ==="
    gcloud run deploy painpan-backend \
        --image=us-central1-docker.pkg.dev/$PROJECT/$REPO/backend:$VERSION \
        --platform=managed --region=$REGION \
        --service-account=painpan-sa@$PROJECT.iam.gserviceaccount.com \
        --env-vars-file=deploy-env.yaml \
        --timeout=3600

    echo "=== Backend deployed ==="
    gcloud run services describe painpan-backend --region=$REGION --format='value(status.url)'
}

deploy_frontend() {
    echo "=== Building frontend image ($VERSION) ==="
    gcloud builds submit --config=cloudbuild-frontend.yaml \
        --substitutions=SHORT_SHA=$VERSION .

    echo "=== Deploying frontend to Cloud Run ==="
    gcloud run deploy painpan-frontend \
        --image=us-central1-docker.pkg.dev/$PROJECT/$REPO/frontend:$VERSION \
        --platform=managed --region=$REGION \
        --set-env-vars=NEXT_PUBLIC_API_URL=$BACKEND_URL

    echo "=== Frontend deployed ==="
    gcloud run services describe painpan-frontend --region=$REGION --format='value(status.url)'
}

case "$TARGET" in
    backend)
        deploy_backend
        ;;
    frontend)
        deploy_frontend
        ;;
    all)
        deploy_backend
        echo ""
        deploy_frontend
        ;;
    *)
        echo "Usage: $0 [backend|frontend|all]"
        exit 1
        ;;
esac

echo ""
echo "=== Done ==="
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo "Docs:     $BACKEND_URL/docs"
