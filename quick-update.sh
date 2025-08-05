#!/bin/bash

# Quick Update Script for Bedrock Chat
# Minimal version for fast deployment updates

set -e

echo "🚀 Quick Update: Bedrock Chat with Nova Canvas, Nova Reel & Document Tools"
echo "=========================================================================="

# Check if we're in the right directory
if [[ ! -f "bin.sh" ]] || [[ ! -d "cdk" ]]; then
    echo "❌ Error: Run this script from the Bedrock Chat root directory"
    exit 1
fi

echo "📦 Updating CDK dependencies..."
cd cdk && npm ci && cd ..

echo "🚀 Deploying updates via CodeBuild..."

# Get CodeBuild project name
PROJECT_NAME=$(aws cloudformation describe-stacks --stack-name CodeBuildForDeploy --query 'Stacks[0].Outputs[?OutputKey==`ProjectName`].OutputValue' --output text 2>/dev/null)

if [[ -n "$PROJECT_NAME" ]]; then
    echo "📦 Starting CodeBuild deployment..."
    BUILD_ID=$(aws codebuild start-build --project-name "$PROJECT_NAME" --query 'build.id' --output text)
    
    if [[ -n "$BUILD_ID" ]]; then
        echo "⏳ Waiting for deployment to complete..."
        while true; do
            BUILD_STATUS=$(aws codebuild batch-get-builds --ids "$BUILD_ID" --query 'builds[0].buildStatus' --output text)
            if [[ "$BUILD_STATUS" == "SUCCEEDED" ]]; then
                echo "✅ Deployment completed successfully!"
                break
            elif [[ "$BUILD_STATUS" == "FAILED" || "$BUILD_STATUS" == "STOPPED" ]]; then
                echo "❌ Deployment failed. Check CloudWatch logs for details."
                exit 1
            fi
            sleep 10
        done
    else
        echo "❌ Failed to start CodeBuild project"
        exit 1
    fi
else
    echo "❌ CodeBuild project not found. Run ./bin.sh first."
    exit 1
fi

echo ""
echo "✅ Update Complete!"
echo ""
echo "🆕 New Features Added:"
echo "   📸 Nova Canvas - Image generation (/media-generation)"
echo "   🎬 Nova Reel - Video generation (/media-generation)" 
echo "   📄 Document tools - PowerPoint, Word, Excel (enable in bot config)"
echo ""
echo "🔗 Access your updated Bedrock Chat application now!"

# Try to get the frontend URL
FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name BedrockChatStack --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' --output text 2>/dev/null || echo "")
if [[ -n "$FRONTEND_URL" ]]; then
    echo "🌐 Frontend URL: $FRONTEND_URL"
fi