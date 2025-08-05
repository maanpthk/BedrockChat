#!/bin/bash

# Simple Local Deployment Script
# This script temporarily modifies your local cdk.json and deploys using the existing CodeBuild setup

set -e

echo "🚀 Simple Local Deployment for Bedrock Chat"
echo "============================================"
echo ""
echo "This will deploy your local changes by temporarily uploading them to S3"
echo "and using the existing CodeBuild infrastructure."
echo ""

# Check if we're in the right directory
if [[ ! -f "bin.sh" ]] || [[ ! -d "cdk" ]]; then
    echo "❌ Error: Run this script from the Bedrock Chat root directory"
    exit 1
fi

# Check if CodeBuild stack exists
if ! aws cloudformation describe-stacks --stack-name CodeBuildForDeploy >/dev/null 2>&1; then
    echo "❌ Error: CodeBuild stack not found. Run ./bin.sh first."
    exit 1
fi

echo "📦 Creating deployment package..."

# Create a unique S3 bucket name
BUCKET_NAME="bedrock-chat-deploy-$(date +%s)"
REGION=$(aws configure get region || echo "us-east-1")

# Create S3 bucket
echo "🪣 Creating temporary S3 bucket: $BUCKET_NAME"
if [[ "$REGION" == "us-east-1" ]]; then
    aws s3 mb "s3://$BUCKET_NAME"
else
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"
fi

# Create deployment package
echo "📦 Packaging local changes..."
zip -r /tmp/bedrock-chat-local.zip . \
    -x "*.git*" "node_modules/*" "cdk/node_modules/*" "cdk/cdk.out/*" \
    -x "backend/.venv/*" "backend/__pycache__/*" "*.pyc" \
    -x "deployment-backup-*/*" ".DS_Store" >/dev/null 2>&1

# Upload to S3
echo "⬆️  Uploading to S3..."
aws s3 cp /tmp/bedrock-chat-local.zip "s3://$BUCKET_NAME/source.zip"

# Get CodeBuild project name
PROJECT_NAME=$(aws cloudformation describe-stacks \
    --stack-name CodeBuildForDeploy \
    --query 'Stacks[0].Outputs[?OutputKey==`ProjectName`].OutputValue' \
    --output text)

echo "🔧 Updating CodeBuild project to use local source..."

# Create buildspec for local deployment
cat > /tmp/buildspec.yml << 'EOF'
version: 0.2
phases:
  install:
    runtime-versions:
      nodejs: 18
    on-failure: ABORT
  build:
    commands:
      - echo 'Deploying local changes...'
      - pwd
      - ls -la
      - cd cdk
      - echo 'Installing dependencies...'
      - npm ci
      - echo 'Bootstrapping CDK...'
      - npx cdk bootstrap
      - echo 'Deploying application...'
      - npx cdk deploy --require-approval never --all
EOF

# Update CodeBuild project to use S3 source
aws codebuild update-project \
    --name "$PROJECT_NAME" \
    --source type=S3,location="$BUCKET_NAME/source.zip",buildspec=/tmp/buildspec.yml

echo "🚀 Starting deployment..."
BUILD_ID=$(aws codebuild start-build --project-name "$PROJECT_NAME" --query 'build.id' --output text)

if [[ -n "$BUILD_ID" ]]; then
    echo "⏳ Build started: $BUILD_ID"
    echo "⏳ Waiting for deployment to complete (this takes 10-15 minutes)..."
    
    while true; do
        BUILD_STATUS=$(aws codebuild batch-get-builds --ids "$BUILD_ID" --query 'builds[0].buildStatus' --output text)
        
        case "$BUILD_STATUS" in
            "SUCCEEDED")
                echo ""
                echo "✅ Deployment completed successfully!"
                
                # Try to get the frontend URL from logs
                BUILD_LOGS=$(aws codebuild batch-get-builds --ids "$BUILD_ID" --query 'builds[0].logs.{groupName: groupName, streamName: streamName}' --output json)
                LOG_GROUP=$(echo "$BUILD_LOGS" | jq -r '.groupName')
                LOG_STREAM=$(echo "$BUILD_LOGS" | jq -r '.streamName')
                
                if [[ "$LOG_GROUP" != "null" && "$LOG_STREAM" != "null" ]]; then
                    FRONTEND_URL=$(aws logs get-log-events --log-group-name "$LOG_GROUP" --log-stream-name "$LOG_STREAM" --query 'events[].message' --output text 2>/dev/null | grep -o 'FrontendURL = [^ ]*' | cut -d' ' -f3 | tr -d '\n,' | head -1)
                    
                    if [[ -n "$FRONTEND_URL" ]]; then
                        echo "🌐 Frontend URL: $FRONTEND_URL"
                    fi
                fi
                break
                ;;
            "FAILED"|"STOPPED")
                echo ""
                echo "❌ Deployment failed with status: $BUILD_STATUS"
                echo "📋 Check logs at: https://console.aws.amazon.com/cloudwatch/home#logEventViewer:group=$LOG_GROUP;stream=$LOG_STREAM"
                break
                ;;
            *)
                printf "."
                sleep 15
                ;;
        esac
    done
else
    echo "❌ Failed to start build"
    exit 1
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
aws s3 rm "s3://$BUCKET_NAME/source.zip" >/dev/null 2>&1 || true
aws s3 rb "s3://$BUCKET_NAME" >/dev/null 2>&1 || true
rm -f /tmp/bedrock-chat-local.zip /tmp/buildspec.yml

# Restore original CodeBuild configuration
echo "🔄 Restoring original CodeBuild configuration..."
aws codebuild update-project \
    --name "$PROJECT_NAME" \
    --source '{
        "type": "NO_SOURCE",
        "buildspec": "{\n  \"version\": 0.2,\n  \"phases\": {\n    \"install\": {\n      \"runtime-versions\": {\n        \"nodejs\": \"18\"\n      },\n      \"on-failure\": \"ABORT\"\n    },\n    \"build\": {\n      \"commands\": [\n        \"echo '\'Build phase...\'\",\n        \"git clone --branch $VERSION $REPO_URL bedrock-chat\",\n        \"cd bedrock-chat\",\n        \"if [ \\\"$ALLOW_SELF_REGISTER\\\" = \\\"false\\\" ]; then sed -i '\'s/\\\"selfSignUpEnabled\\\": true/\\\"selfSignUpEnabled\\\": false/\' cdk/cdk.json; fi\",\n        \"if [ \\\"$ENABLE_LAMBDA_SNAPSTART\\\" = \\\"false\\\" ]; then sed -i '\'s/\\\"enableLambdaSnapStart\\\": true/\\\"enableLambdaSnapStart\\\": false/\' cdk/cdk.json; fi\",\n        \"if [ ! -z \\\"$IPV4_RANGES\\\" ]; then jq --arg ipv4 \\\"$IPV4_RANGES\\\" \'.context.allowedIpV4AddressRanges = ($ipv4 | split(\\\",\\\"))\' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; fi\",\n        \"if [ \\\"$DISABLE_IPV6\\\" = \\\"true\\\" ]; then jq \'.context.allowedIpV6AddressRanges = []\' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; elif [ ! -z \\\"$IPV6_RANGES\\\" ]; then jq --arg ipv6 \\\"$IPV6_RANGES\\\" \'.context.allowedIpV6AddressRanges = ($ipv6 | split(\\\",\\\"))\' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; fi\",\n        \"if [ ! -z \\\"$ALLOWED_SIGN_UP_EMAIL_DOMAINS\\\" ]; then jq --arg domains \\\"$ALLOWED_SIGN_UP_EMAIL_DOMAINS\\\" \'.context.allowedSignUpEmailDomains = ($domains | split(\\\",\\\"))\' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; fi\",\n        \"sed -i \\\"s/\\\\\\\"bedrockRegion\\\\\\\": \\\\\\\"[^\\\\\\\"]*\\\\\\\"/\\\\\\\"bedrockRegion\\\\\\\": \\\\\\\"${BEDROCK_REGION}\\\\\\\"/\\\" cdk/cdk.json\",\n        \"echo \\\"$CDK_JSON_OVERRIDE\\\" | jq \'.\' && jq --argjson override \\\"$CDK_JSON_OVERRIDE\\\" \'. * $override\' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json\",\n        \"cd cdk\",\n        \"cat cdk.json\",\n        \"npm ci\",\n        \"npx cdk bootstrap\",\n        \"npx cdk deploy --require-approval never --all\"\n      ]\n    }\n  }\n}"
    }' >/dev/null

echo ""
echo "🎉 Local changes deployed successfully!"
echo ""
echo "🆕 New Features Added:"
echo "   📸 Nova Canvas - Image generation (/media-generation)"
echo "   🎬 Nova Reel - Video generation (/media-generation)" 
echo "   📄 Document tools - PowerPoint, Word, Excel (enable in bot config)"
echo ""
echo "✅ Your Bedrock Chat now includes all the new features!"