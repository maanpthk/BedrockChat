# Bedrock Chat Deployment Update Guide

This guide explains how to update your existing Bedrock Chat deployment with the new features:
- **Amazon Nova Canvas** (Image Generation)
- **Amazon Nova Reel** (Video Generation)  
- **Document Generation Tools** (PowerPoint, Word, Excel)

## 🚀 Quick Start

### Option 1: Full Update Script (Recommended)
```bash
./update-deployment.sh
```

### Option 2: Quick Update (Minimal)
```bash
./quick-update.sh
```

## 📋 Prerequisites

Before running the update scripts, ensure you have:

1. **AWS CLI configured** with appropriate permissions
2. **Node.js and npm** installed (for CDK)
3. **Existing Bedrock Chat deployment** (previously deployed with `./bin.sh`)
4. **Bedrock model access** for Nova Canvas and Nova Reel

### Check Bedrock Model Access

1. Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/home#/modelaccess)
2. Ensure you have access to:
   - **Amazon Nova Canvas** (`amazon.nova-canvas-v1:0`)
   - **Amazon Nova Reel** (`amazon.nova-reel-v1:0`)
3. If not available, click "Manage model access" and request access

## 🔧 Detailed Update Process

### Step 1: Navigate to Project Directory
```bash
cd /path/to/your/bedrock-chat
```

### Step 2: Run Update Script
```bash
# Full update with checks and backup
./update-deployment.sh

# OR quick update
./quick-update.sh
```

### Step 3: Wait for Deployment
The update process typically takes **10-15 minutes**. The script will:
- Update backend dependencies
- Deploy new features via CDK
- Verify the deployment

## 🆕 What's New After Update

### 1. Media Generation Page
- **Access**: Navigate to `/media-generation` in your Bedrock Chat app
- **Features**: 
  - Switch between Text, Image, and Video generation modes
  - Generate images with Nova Canvas
  - Create videos with Nova Reel
  - Download and share generated media

### 2. Document Generation Tools
- **Access**: Enable in Bot Console → Agent Tools
- **Available Tools**:
  - **PowerPoint Generator**: Create professional presentations
  - **Word Document Generator**: Generate formatted documents
  - **Excel Spreadsheet Generator**: Build data tables and reports

### 3. Enhanced Chat Interface
- **Media Display**: Generated images and videos appear in chat messages
- **Download Support**: Direct download of generated files
- **Model Selection**: Automatic switching between generation modes

## 🎯 How to Use New Features

### Media Generation
1. Open your Bedrock Chat application
2. Click on "Media Generation" in the sidebar
3. Select generation mode (Text/Image/Video)
4. Enter your prompt and configure settings
5. Click generate and download your media

### Document Generation
1. Go to **Bot Console** → **Create/Edit Bot**
2. Scroll to **Agent** section
3. Enable desired document generation tools:
   - ✅ PowerPoint Generator
   - ✅ Word Document Generator
   - ✅ Excel Spreadsheet Generator
4. Save bot configuration
5. Chat with prompts like:
   - *"Create a presentation about AI with 5 slides"*
   - *"Generate a project report document"*
   - *"Make a sales tracking spreadsheet"*

## 🔍 Verification Steps

After deployment, verify the update worked:

1. **Check Frontend**: Access your Bedrock Chat URL
2. **Media Generation**: Look for "Media Generation" in the sidebar
3. **Bot Configuration**: Verify new tools appear in agent configuration
4. **Model Selection**: Confirm Nova Canvas and Nova Reel are available

## 🛠️ Troubleshooting

### Common Issues

#### 1. "Model not available" errors
**Solution**: Ensure Nova Canvas and Nova Reel access in Bedrock console
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `nova`)]'
```

#### 2. CDK deployment fails
**Solution**: Check AWS permissions and try bootstrap
```bash
cd cdk
npx cdk bootstrap
npx cdk deploy --all
```

#### 3. Dependencies not installing
**Solution**: Clear cache and reinstall
```bash
cd cdk
rm -rf node_modules package-lock.json
npm install
```

#### 4. "Stack does not exist" error
**Solution**: Verify you're in the correct AWS region and account
```bash
aws sts get-caller-identity
aws configure get region
```

### Manual Deployment Steps

If the scripts fail, you can deploy manually:

```bash
# 1. Update CDK dependencies
cd cdk
npm ci

# 2. Deploy application
npx cdk deploy --require-approval never --all

# 3. Verify deployment
aws cloudformation describe-stacks --stack-name BedrockChatStack
```

## 📊 Deployment Verification

### Check Stack Status
```bash
aws cloudformation describe-stacks --stack-name BedrockChatStack --query 'Stacks[0].StackStatus'
```

### Get Frontend URL
```bash
aws cloudformation describe-stacks --stack-name BedrockChatStack --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' --output text
```

### Test New Features
1. **Media Generation**: Visit `/media-generation` page
2. **Document Tools**: Create a bot with agent tools enabled
3. **Model Access**: Try generating an image or video

## 🔄 Rollback Process

If you need to rollback the deployment:

1. **Use backup**: Restore from the backup created by `update-deployment.sh`
2. **Previous version**: Deploy previous CDK configuration
3. **Stack rollback**: Use CloudFormation console to rollback

```bash
# Restore from backup (if available)
cp deployment-backup-*/cdk.json cdk/
cd cdk && npx cdk deploy --all
```

## 📞 Support

If you encounter issues:

1. **Check logs**: Review CloudFormation events in AWS console
2. **Verify permissions**: Ensure your AWS user has necessary permissions
3. **Model access**: Confirm Bedrock model access is properly configured
4. **Dependencies**: Verify all prerequisites are installed

## 🎉 Success Indicators

Your update is successful when you see:

- ✅ "Media Generation" appears in the sidebar
- ✅ Nova Canvas and Nova Reel models are selectable
- ✅ Document generation tools appear in bot agent configuration
- ✅ Generated media displays properly in chat
- ✅ Document downloads work correctly

---

**Congratulations!** Your Bedrock Chat deployment now includes powerful media and document generation capabilities powered by Amazon Nova models! 🚀