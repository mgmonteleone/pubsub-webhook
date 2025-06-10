gcloud beta functions deploy monday-webhook \
     --source . \
     --runtime python311 \
     --entry-point pubsub_webhook \
     --service-account webhook@mythic-tenure-197922.iam.gserviceaccount.com \
     --trigger-http \
     --allow-unauthenticated