#!/bin/bash

# Deploy Local Changes Script
# This script uploads your local changes to S3 and deploys them using CodeBuild

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if we're in the right directory
check_project_directory() {
    print_status "Checking project directory..."
    
    if [[ ! -f "bin.sh" ]] || [[ ! -d "backend" ]] || [[ ! -d "frontend" ]] || [[ ! -d "cdk" ]]; then
        print_error "This script must be run from the root of the Bedrock Chat project directory."
        exit 1
    fi
    
    print_success "Project directory verified"
}

# Function to create S3 bucket for source code
create_source_bucket() {
    print_status "Creating S3 bucket for source code..."
    
    local region=$(aws configure get region)
    if [[ -z "$region" ]]; then
        region="us-east-1"
    fi
    
    local bucket_name="bedrock-chat-source-$(date +%s)-$(openssl rand -hex 4)"
    
    if [[ "$region" == "us-east-1" ]]; then
        aws s3 mb "s3://$bucket_name"
    else
        aws s3 mb "s3://$bucket_name" --region "$region"
    fi
    
    echo "$bucket_name"
}

# Function to upload local source code
upload_source_code() {
    local bucket_name=$1
    print_status "Uploading local source code to S3..."
    
    # Create a temporary directory for the source
    local temp_dir=$(mktemp -d)
    local source_zip="$temp_dir/bedrock-chat-source.zip"
    
    # Create zip file excluding unnecessary files
    zip -r "$source_zip" . \
        -x "*.git*" \
        -x "node_modules/*" \
        -x "cdk/node_modules/*" \
        -x "cdk/cdk.out/*" \
        -x "backend/.venv/*" \
        -x "backend/__pycache__/*" \
        -x "*.pyc" \
        -x "deployment-backup-*/*" \
        -x ".DS_Store" \
        >/dev/null 2>&1
    
    # Upload to S3
    aws s3 cp "$source_zip" "s3://$bucket_name/source.zip"
    
    # Clean up
    rm -rf "$temp_dir"
    
    print_success "Source code uploaded to s3://$bucket_name/source.zip"
}

# Function to update CodeBuild project to use S3 source
update_codebuild_project() {
    local bucket_name=$1
    print_status "Updating CodeBuild project to use local source..."
    
    local stack_name="CodeBuildForDeploy"
    local project_name=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs[?OutputKey==`ProjectName`].OutputValue' \
        --output text)
    
    if [[ -z "$project_name" ]]; then
        print_error "Could not find CodeBuild project name"
        exit 1
    fi
    
    # Update the project to use S3 source
    aws codebuild update-project \
        --name "$project_name" \
        --source '{
            "type": "S3",
            "location": "'$bucket_name'/source.zip",
            "buildspec": {
                "version": 0.2,
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "nodejs": "18"
                        },
                        "on-failure": "ABORT"
                    },
                    "build": {
                        "commands": [
                            "echo '\''Build phase...'\''",
                            "pwd",
                            "ls -la",
                            "cd cdk",
                            "cat cdk.json",
                            "npm ci",
                            "npx cdk bootstrap",
                            "npx cdk deploy --require-approval never --all"
                        ]
                    }
                }
            }
        }' >/dev/null
    
    print_success "CodeBuild project updated to use local source"
    echo "$project_name"
}

# Function to start CodeBuild deployment
start_deployment() {
    local project_name=$1
    print_status "Starting CodeBuild deployment with local changes..."
    
    local build_id=$(aws codebuild start-build \
        --project-name "$project_name" \
        --query 'build.id' \
        --output text)
    
    if [[ -z "$build_id" ]]; then
        print_error "Failed to start CodeBuild project"
        exit 1
    fi
    
    print_status "Build started with ID: $build_id"
    print_warning "Deployment will take 10-15 minutes. Please be patient..."
    
    # Wait for build to complete
    while true; do
        local build_status=$(aws codebuild batch-get-builds \
            --ids "$build_id" \
            --query 'builds[0].buildStatus' \
            --output text)
        
        case "$build_status" in
            "SUCCEEDED")
                print_success "Deployment completed successfully!"
                
                # Get build logs to extract frontend URL
                local build_detail=$(aws codebuild batch-get-builds \
                    --ids "$build_id" \
                    --query 'builds[0].logs.{groupName: groupName, streamName: streamName}' \
                    --output json)
                
                local log_group=$(echo "$build_detail" | jq -r '.groupName')
                local log_stream=$(echo "$build_detail" | jq -r '.streamName')
                
                if [[ "$log_group" != "null" && "$log_stream" != "null" ]]; then
                    local logs=$(aws logs get-log-events \
                        --log-group-name "$log_group" \
                        --log-stream-name "$log_stream" \
                        --query 'events[].message' \
                        --output text 2>/dev/null || echo "")
                    
                    local frontend_url=$(echo "$logs" | grep -o 'FrontendURL = [^ ]*' | cut -d' ' -f3 | tr -d '\n,' | head -1)
                    
                    if [[ -n "$frontend_url" ]]; then
                        print_success "Frontend URL: $frontend_url"
                    fi
                fi
                break
                ;;
            "FAILED"|"STOPPED")
                print_error "Deployment failed with status: $build_status"
                
                # Get build logs for debugging
                local build_detail=$(aws codebuild batch-get-builds \
                    --ids "$build_id" \
                    --query 'builds[0].logs.{groupName: groupName, streamName: streamName}' \
                    --output json)
                
                local log_group=$(echo "$build_detail" | jq -r '.groupName')
                local log_stream=$(echo "$build_detail" | jq -r '.streamName')
                
                print_error "Check logs at: https://console.aws.amazon.com/cloudwatch/home#logEventViewer:group=$log_group;stream=$log_stream"
                exit 1
                ;;
            *)
                printf "."
                sleep 10
                ;;
        esac
    done
}

# Function to cleanup S3 bucket
cleanup_source_bucket() {
    local bucket_name=$1
    print_status "Cleaning up temporary S3 bucket..."
    
    aws s3 rm "s3://$bucket_name/source.zip" >/dev/null 2>&1 || true
    aws s3 rb "s3://$bucket_name" >/dev/null 2>&1 || true
    
    print_success "Cleanup completed"
}

# Function to restore original CodeBuild configuration
restore_codebuild_project() {
    local project_name=$1
    print_status "Restoring original CodeBuild configuration..."
    
    # Restore to GitHub source
    aws codebuild update-project \
        --name "$project_name" \
        --source '{
            "type": "NO_SOURCE",
            "buildspec": "{\n  \"version\": 0.2,\n  \"phases\": {\n    \"install\": {\n      \"runtime-versions\": {\n        \"nodejs\": \"18\"\n      },\n      \"on-failure\": \"ABORT\"\n    },\n    \"build\": {\n      \"commands\": [\n        \"echo '\''Build phase...'\''",\n        \"git clone --branch $VERSION $REPO_URL bedrock-chat\",\n        \"cd bedrock-chat\",\n        \"if [ \\\"$ALLOW_SELF_REGISTER\\\" = \\\"false\\\" ]; then sed -i '\''s/\\\"selfSignUpEnabled\\\": true/\\\"selfSignUpEnabled\\\": false/'\'' cdk/cdk.json; fi\",\n        \"if [ \\\"$ENABLE_LAMBDA_SNAPSTART\\\" = \\\"false\\\" ]; then sed -i '\''s/\\\"enableLambdaSnapStart\\\": true/\\\"enableLambdaSnapStart\\\": false/'\'' cdk/cdk.json; fi\",\n        \"if [ ! -z \\\"$IPV4_RANGES\\\" ]; then jq --arg ipv4 \\\"$IPV4_RANGES\\\" '\''.context.allowedIpV4AddressRanges = ($ipv4 | split(\\\",\\\"))'\'' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; fi\",\n        \"if [ \\\"$DISABLE_IPV6\\\" = \\\"true\\\" ]; then jq '\''.context.allowedIpV6AddressRanges = []'\'' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; elif [ ! -z \\\"$IPV6_RANGES\\\" ]; then jq --arg ipv6 \\\"$IPV6_RANGES\\\" '\''.context.allowedIpV6AddressRanges = ($ipv6 | split(\\\",\\\"))'\'' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; fi\",\n        \"if [ ! -z \\\"$ALLOWED_SIGN_UP_EMAIL_DOMAINS\\\" ]; then jq --arg domains \\\"$ALLOWED_SIGN_UP_EMAIL_DOMAINS\\\" '\''.context.allowedSignUpEmailDomains = ($domains | split(\\\",\\\"))'\'' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json; fi\",\n        \"sed -i \\\"s/\\\\\\\"bedrockRegion\\\\\\\": \\\\\\\"[^\\\\\\\"]*\\\\\\\"/\\\\\\\"bedrockRegion\\\\\\\": \\\\\\\"${BEDROCK_REGION}\\\\\\\"/\\\" cdk/cdk.json\",\n        \"echo \\\"$CDK_JSON_OVERRIDE\\\" | jq '\''.'\'' && jq --argjson override \\\"$CDK_JSON_OVERRIDE\\\" '\''. * $override'\'' cdk/cdk.json > temp.json && mv temp.json cdk/cdk.json\",\n        \"cd cdk\",\n        \"cat cdk.json\",\n        \"npm ci\",\n        \"npx cdk bootstrap\",\n        \"npx cdk deploy --require-approval never --all\"\n      ]\n    }\n  }\n}"
        }' >/dev/null
    
    print_success "Original CodeBuild configuration restored"
}

# Function to display new features
display_new_features() {
    print_success "🎉 Local Changes Deployed Successfully!"
    echo ""
    echo "Your Bedrock Chat now includes these new features:"
    echo ""
    echo "📸 Amazon Nova Canvas - Image Generation"
    echo "   • Generate high-quality images from text prompts"
    echo "   • Accessible via /media-generation page"
    echo "   • Configurable image dimensions, styles, and seeds"
    echo ""
    echo "🎬 Amazon Nova Reel - Video Generation"
    echo "   • Create short videos from text descriptions"
    echo "   • Up to 6 seconds duration"
    echo "   • Customizable frame rates and settings"
    echo ""
    echo "📄 Document Generation Tools"
    echo "   • PowerPoint Generator - Create professional presentations"
    echo "   • Word Document Generator - Generate formatted documents"
    echo "   • Excel Spreadsheet Generator - Build data tables and reports"
    echo "   • Enable in Bot Console → Agent Tools"
    echo ""
    echo "🔧 How to use:"
    echo "   1. Access your Bedrock Chat application"
    echo "   2. For media generation: Visit /media-generation page"
    echo "   3. For document tools: Enable in bot agent configuration"
    echo "   4. Start creating with natural language prompts!"
    echo ""
}

# Main execution
main() {
    echo "🚀 Deploy Local Changes to Bedrock Chat"
    echo "======================================="
    echo ""
    echo "This script will deploy your local changes including:"
    echo "• Amazon Nova Canvas (Image Generation)"
    echo "• Amazon Nova Reel (Video Generation)"
    echo "• Document Generation Tools (PowerPoint, Word, Excel)"
    echo ""
    
    # Confirmation prompt
    read -p "Deploy your local changes? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled by user"
        exit 0
    fi
    
    # Check prerequisites
    check_project_directory
    
    # Check if CodeBuild stack exists
    if ! aws cloudformation describe-stacks --stack-name CodeBuildForDeploy >/dev/null 2>&1; then
        print_error "CodeBuild stack not found. Please run ./bin.sh first to create the initial deployment."
        exit 1
    fi
    
    # Create S3 bucket and upload source
    local bucket_name=$(create_source_bucket)
    upload_source_code "$bucket_name"
    
    # Update CodeBuild and deploy
    local project_name=$(update_codebuild_project "$bucket_name")
    
    # Trap to ensure cleanup happens
    trap "cleanup_source_bucket $bucket_name; restore_codebuild_project $project_name" EXIT
    
    # Start deployment
    start_deployment "$project_name"
    
    # Display success message
    display_new_features
    
    print_success "Local changes deployed successfully! 🎉"
}

# Handle script interruption
trap 'print_error "Script interrupted by user"; exit 1' INT

# Run main function
main "$@"