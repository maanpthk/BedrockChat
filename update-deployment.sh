#!/bin/bash

# Bedrock Chat Update Deployment Script
# This script updates an existing Bedrock Chat deployment with new features:
# - Amazon Nova Canvas (image generation)
# - Amazon Nova Reel (video generation) 
# - Document generation tools (PowerPoint, Word, Excel)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check AWS CLI and credentials
check_aws_setup() {
    print_status "Checking AWS setup..."
    
    if ! command_exists aws; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS setup verified"
}

# Function to check if we're in the right directory
check_project_directory() {
    print_status "Checking project directory..."
    
    if [[ ! -f "bin.sh" ]] || [[ ! -d "backend" ]] || [[ ! -d "frontend" ]] || [[ ! -d "cdk" ]]; then
        print_error "This script must be run from the root of the Bedrock Chat project directory."
        print_error "Please navigate to the directory where you originally ran ./bin.sh"
        exit 1
    fi
    
    print_success "Project directory verified"
}

# Function to backup current deployment
backup_deployment() {
    print_status "Creating backup of current deployment configuration..."
    
    BACKUP_DIR="deployment-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup CDK configuration
    if [[ -f "cdk/cdk.json" ]]; then
        cp "cdk/cdk.json" "$BACKUP_DIR/"
    fi
    
    if [[ -f "cdk/parameter.ts" ]]; then
        cp "cdk/parameter.ts" "$BACKUP_DIR/"
    fi
    
    # Backup backend configuration
    if [[ -f "backend/pyproject.toml" ]]; then
        cp "backend/pyproject.toml" "$BACKUP_DIR/"
    fi
    
    print_success "Backup created in $BACKUP_DIR"
}

# Function to check Bedrock model access
check_bedrock_models() {
    print_status "Checking Bedrock model access..."
    
    local region=$(aws configure get region)
    if [[ -z "$region" ]]; then
        region="us-east-1"
    fi
    
    print_status "Checking model access in region: $region"
    
    # Check if Nova Canvas is available
    if aws bedrock list-foundation-models --region "$region" --query 'modelSummaries[?contains(modelId, `amazon.nova-canvas`)]' --output text >/dev/null 2>&1; then
        print_success "Amazon Nova Canvas model access verified"
    else
        print_warning "Amazon Nova Canvas model may not be available in $region"
        print_warning "Please ensure you have requested access to Nova Canvas in the Bedrock console"
    fi
    
    # Check if Nova Reel is available
    if aws bedrock list-foundation-models --region "$region" --query 'modelSummaries[?contains(modelId, `amazon.nova-reel`)]' --output text >/dev/null 2>&1; then
        print_success "Amazon Nova Reel model access verified"
    else
        print_warning "Amazon Nova Reel model may not be available in $region"
        print_warning "Please ensure you have requested access to Nova Reel in the Bedrock console"
    fi
}

# Function to update backend dependencies
update_backend_dependencies() {
    print_status "Updating backend dependencies..."
    
    cd backend
    
    # Check if poetry is available
    if command_exists poetry; then
        print_status "Using Poetry to update dependencies..."
        poetry install
        print_success "Backend dependencies updated with Poetry"
    else
        print_warning "Poetry not found. Dependencies will be installed during CDK deployment."
    fi
    
    cd ..
}

# Function to update CDK dependencies
update_cdk_dependencies() {
    print_status "Updating CDK dependencies..."
    
    cd cdk
    
    if [[ -f "package.json" ]]; then
        if command_exists npm; then
            npm ci
            print_success "CDK dependencies updated"
        else
            print_error "npm is not installed. Please install Node.js and npm first."
            exit 1
        fi
    else
        print_error "package.json not found in cdk directory"
        exit 1
    fi
    
    cd ..
}

# Function to deploy the updated application
deploy_application() {
    print_status "Deploying updated Bedrock Chat application using CodeBuild..."
    
    # Use the same CodeBuild approach as the original bin.sh
    local stack_name="CodeBuildForDeploy"
    
    print_status "Checking if CodeBuild stack exists..."
    if aws cloudformation describe-stacks --stack-name "$stack_name" >/dev/null 2>&1; then
        print_status "CodeBuild stack exists. Getting project name..."
        
        local project_name=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --query 'Stacks[0].Outputs[?OutputKey==`ProjectName`].OutputValue' \
            --output text)
        
        if [[ -n "$project_name" ]]; then
            print_status "Starting CodeBuild project: $project_name"
            print_warning "This will take 10-15 minutes. Please be patient..."
            
            local build_id=$(aws codebuild start-build \
                --project-name "$project_name" \
                --query 'build.id' \
                --output text)
            
            if [[ -n "$build_id" ]]; then
                print_status "Build started with ID: $build_id"
                print_status "Waiting for build to complete..."
                
                # Wait for build to complete
                while true; do
                    local build_status=$(aws codebuild batch-get-builds \
                        --ids "$build_id" \
                        --query 'builds[0].buildStatus' \
                        --output text)
                    
                    if [[ "$build_status" == "SUCCEEDED" ]]; then
                        print_success "CodeBuild deployment completed successfully!"
                        break
                    elif [[ "$build_status" == "FAILED" || "$build_status" == "STOPPED" ]]; then
                        print_error "CodeBuild deployment failed with status: $build_status"
                        
                        # Get build logs for debugging
                        local build_detail=$(aws codebuild batch-get-builds \
                            --ids "$build_id" \
                            --query 'builds[0].logs.{groupName: groupName, streamName: streamName}' \
                            --output json)
                        
                        local log_group=$(echo "$build_detail" | jq -r '.groupName')
                        local log_stream=$(echo "$build_detail" | jq -r '.streamName')
                        
                        print_error "Check logs at: https://console.aws.amazon.com/cloudwatch/home#logEventViewer:group=$log_group;stream=$log_stream"
                        exit 1
                    fi
                    
                    sleep 10
                done
            else
                print_error "Failed to start CodeBuild project"
                exit 1
            fi
        else
            print_error "Could not get CodeBuild project name"
            exit 1
        fi
    else
        print_error "CodeBuild stack not found. Please run ./bin.sh first to create the initial deployment."
        exit 1
    fi
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Get the CloudFormation stack outputs
    local stack_name="BedrockChatStack"
    local region=$(aws configure get region)
    if [[ -z "$region" ]]; then
        region="us-east-1"
    fi
    
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$region" >/dev/null 2>&1; then
        print_success "Deployment stack verified"
        
        # Get the frontend URL
        local frontend_url=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --region "$region" \
            --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' \
            --output text 2>/dev/null)
        
        if [[ -n "$frontend_url" ]]; then
            print_success "Frontend URL: $frontend_url"
        fi
    else
        print_warning "Could not verify deployment stack"
    fi
}

# Function to display new features
display_new_features() {
    print_success "🎉 Deployment Update Complete!"
    echo ""
    echo "New features added to your Bedrock Chat deployment:"
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

# Function to display usage instructions
display_usage_instructions() {
    echo ""
    echo "📋 Quick Start Guide:"
    echo ""
    echo "Media Generation:"
    echo "   • Navigate to the Media Generation page in the sidebar"
    echo "   • Switch between Text, Image, and Video modes"
    echo "   • Enter prompts like: 'Create a sunset landscape image'"
    echo ""
    echo "Document Generation:"
    echo "   • Go to Bot Console → Create/Edit Bot"
    echo "   • Enable Agent tools: PowerPoint, Word, Excel generators"
    echo "   • Chat with prompts like: 'Create a presentation about AI'"
    echo ""
    echo "Model Access:"
    echo "   • Ensure Nova Canvas and Nova Reel are enabled in AWS Bedrock console"
    echo "   • Visit: https://console.aws.amazon.com/bedrock/home#/modelaccess"
    echo ""
}

# Main execution
main() {
    echo "🚀 Bedrock Chat Update Deployment Script"
    echo "========================================"
    echo ""
    echo "This script will update your existing Bedrock Chat deployment with:"
    echo "• Amazon Nova Canvas (Image Generation)"
    echo "• Amazon Nova Reel (Video Generation)"
    echo "• Document Generation Tools (PowerPoint, Word, Excel)"
    echo ""
    
    # Confirmation prompt
    read -p "Do you want to proceed with the update? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Update cancelled by user"
        exit 0
    fi
    
    # Run all checks and updates
    check_aws_setup
    check_project_directory
    backup_deployment
    check_bedrock_models
    update_backend_dependencies
    update_cdk_dependencies
    deploy_application
    verify_deployment
    
    # Display success message and new features
    display_new_features
    display_usage_instructions
    
    print_success "Update deployment completed successfully! 🎉"
}

# Handle script interruption
trap 'print_error "Script interrupted by user"; exit 1' INT

# Run main function
main "$@"