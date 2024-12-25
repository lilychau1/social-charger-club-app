sam deploy --guided --profile ev-dev --parameter-overrides Environment=dev --stack-name=social-charger-club-dev
sam deploy --guided --profile ev-prod --parameter-overrides Environment=prod --stack-name=social-charger-club-prod

sam deploy --profile ev-dev --parameter-overrides Environment=dev --stack-name=social-charger-club-dev --resolve-s3 --capabilities CAPABILITY_IAM


sam pipeline bootstrap --profile ev-dev --stage dev
sam pipeline bootstrap --profile ev-prod --stage prod

sam pipeline init

