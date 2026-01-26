#!/bin/bash
set -e

# Configuration - UPDATE THESE VALUES
AWS_REGION="eu-west-1"
CLUSTER_NAME="cronpulse-cluster"
SERVICE_NAME="cronpulse-service"
TASK_NAME="cronpulse-task"
ECR_REPO="cronpulse"
IMAGE_TAG="latest"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
ACTION="${1:-deploy}"

if [[ "$ACTION" != "deploy" && "$ACTION" != "teardown" ]]; then
    echo "Usage: $0 [deploy|teardown]"
    echo "  deploy   - Build and deploy to AWS Fargate (default)"
    echo "  teardown - Remove all AWS resources"
    exit 1
fi

# Check if AWS credentials are configured (via Granted assume or otherwise)
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo -e "${YELLOW}Please run: assume <profile-name>${NC}"
    echo -e "Then run this script again."
    exit 1
fi

# Auto-detect AWS Account ID from current credentials
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CURRENT_PROFILE=${AWS_PROFILE:-"default"}

echo -e "${GREEN}Using AWS Profile: ${CURRENT_PROFILE}${NC}"
echo -e "${GREEN}AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}AWS Region: ${AWS_REGION}${NC}"
echo ""

# Teardown function
teardown() {
    echo -e "${RED}Starting teardown of AWS resources...${NC}"
    echo ""
    
    # Step 1: Delete ECS Service
    echo -e "${YELLOW}Step 1: Deleting ECS service...${NC}"
    if aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} &>/dev/null; then
        echo "Scaling service to 0..."
        aws ecs update-service --cluster ${CLUSTER_NAME} --service ${SERVICE_NAME} --desired-count 0 --region ${AWS_REGION} &>/dev/null || true
        echo "Deleting service..."
        aws ecs delete-service --cluster ${CLUSTER_NAME} --service ${SERVICE_NAME} --force --region ${AWS_REGION} || echo "Service not found or already deleted"
        echo "Waiting for service deletion..."
        sleep 10
    else
        echo "Service not found, skipping..."
    fi
    
    # Step 2: Deregister all task definitions
    echo -e "${YELLOW}Step 2: Deregistering task definitions...${NC}"
    TASK_DEFS=$(aws ecs list-task-definitions --family-prefix ${TASK_NAME} --region ${AWS_REGION} --query 'taskDefinitionArns[]' --output text)
    if [ ! -z "$TASK_DEFS" ]; then
        for TASK_DEF in $TASK_DEFS; do
            echo "Deregistering $TASK_DEF..."
            aws ecs deregister-task-definition --task-definition $TASK_DEF --region ${AWS_REGION} &>/dev/null || true
        done
    else
        echo "No task definitions found, skipping..."
    fi
    
    # Step 3: Delete ECS Cluster
    echo -e "${YELLOW}Step 3: Deleting ECS cluster...${NC}"
    if aws ecs describe-clusters --clusters ${CLUSTER_NAME} --region ${AWS_REGION} --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
        aws ecs delete-cluster --cluster ${CLUSTER_NAME} --region ${AWS_REGION} || echo "Cluster deletion failed or already deleted"
    else
        echo "Cluster not found, skipping..."
    fi
    
    # Step 4: Delete CloudWatch Log Group
    echo -e "${YELLOW}Step 4: Deleting CloudWatch log group...${NC}"
    if aws logs describe-log-groups --log-group-name-prefix "/ecs/${ECR_REPO}" --region ${AWS_REGION} --query 'logGroups[0]' --output text &>/dev/null; then
        aws logs delete-log-group --log-group-name "/ecs/${ECR_REPO}" --region ${AWS_REGION} || echo "Log group deletion failed or already deleted"
    else
        echo "Log group not found, skipping..."
    fi
    
    # Step 5: Delete Security Group
    echo -e "${YELLOW}Step 5: Looking for security groups...${NC}"
    SG_IDS=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=cronpulse-sg" --query 'SecurityGroups[*].GroupId' --output text --region ${AWS_REGION})
    if [ ! -z "$SG_IDS" ]; then
        for SG_ID in $SG_IDS; do
            echo "Deleting security group $SG_ID..."
            aws ec2 delete-security-group --group-id $SG_ID --region ${AWS_REGION} 2>/dev/null || echo "Could not delete $SG_ID (may be in use or already deleted)"
        done
    else
        echo "No security groups found, skipping..."
    fi
    
    # Step 6: Delete ECR Repository
    echo -e "${YELLOW}Step 6: Deleting ECR repository...${NC}"
    read -p "Delete ECR repository and all images? This cannot be undone. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${AWS_REGION} &>/dev/null; then
            aws ecr delete-repository --repository-name ${ECR_REPO} --force --region ${AWS_REGION} || echo "ECR deletion failed or already deleted"
        else
            echo "ECR repository not found, skipping..."
        fi
    else
        echo "Skipping ECR repository deletion"
    fi
    
    echo ""
    echo -e "${GREEN}Teardown complete!${NC}"
    echo -e "${YELLOW}Note: Some resources may take a few minutes to fully delete.${NC}"
    exit 0
}

# Execute teardown if requested
if [[ "$ACTION" == "teardown" ]]; then
    teardown
fi

# Deployment starts here
echo -e "${BLUE}Starting deployment to AWS Fargate...${NC}"
echo ""

# Step 1: Create ECR repository if it doesn't exist
echo -e "${GREEN}Step 1: Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${AWS_REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${ECR_REPO} --region ${AWS_REGION}

# Step 2: Login to ECR
echo -e "${GREEN}Step 2: Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 3: Build Docker image
echo -e "${GREEN}Step 3: Building Docker image...${NC}"
docker build -t ${ECR_REPO}:${IMAGE_TAG} .

# Step 4: Tag image
echo -e "${GREEN}Step 4: Tagging image...${NC}"
docker tag ${ECR_REPO}:${IMAGE_TAG} ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}

# Step 5: Push image to ECR
echo -e "${GREEN}Step 5: Pushing image to ECR...${NC}"
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}

# Step 6: Create ECS cluster if it doesn't exist
echo -e "${GREEN}Step 6: Creating ECS cluster...${NC}"
aws ecs describe-clusters --clusters ${CLUSTER_NAME} --region ${AWS_REGION} 2>/dev/null || \
    aws ecs create-cluster --cluster-name ${CLUSTER_NAME} --region ${AWS_REGION}

echo -e "${BLUE}Deployment preparation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update aws-task-definition.json with your account ID and region"
echo "2. Create EFS file system for SQLite persistence (or use temporary storage for testing)"
echo "3. Register task definition: aws ecs register-task-definition --cli-input-json file://aws-task-definition.json"
echo "4. Create or update the service with the new task definition"
echo ""
echo "For quick testing without EFS, remove the volumes and mountPoints sections from the task definition."
