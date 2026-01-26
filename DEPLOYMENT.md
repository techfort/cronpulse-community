# AWS Fargate Deployment Guide

## Quick Start for Testing (No Persistence)

For a quick test deployment without data persistence:

### 1. Prerequisites
```bash
# Install AWS CLI
# Configure AWS credentials
aws configure
```

### 2. Get Your AWS Account ID
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION="us-east-1"  # Change if needed
echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
```

### 3. Deploy Using the Script
```bash
chmod +x deploy-aws.sh
# Edit deploy-aws.sh and update AWS_ACCOUNT_ID and AWS_REGION
./deploy-aws.sh
```

### 4. Create Simple Task Definition (No Persistence)

Create `task-definition-simple.json`:
```json
{
  "family": "cronpulse-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "cronpulse",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cronpulse:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "SECRET_KEY", "value": "test-secret-key-12345"},
        {"name": "JWT_SECRET", "value": "test-jwt-secret-12345"},
        {"name": "ADMIN_EMAIL", "value": "admin@test.com"},
        {"name": "ADMIN_PASSWORD", "value": "TestPassword123"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cronpulse",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole"
}
```

### 5. Update and Register Task Definition
```bash
# Replace YOUR_ACCOUNT_ID in the JSON file
sed -i "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g" task-definition-simple.json

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition-simple.json --region $AWS_REGION
```

### 6. Create the Service

First, get your default VPC and subnets:
```bash
# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)

# Get subnets
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region $AWS_REGION)
SUBNET_1=$(echo $SUBNET_IDS | cut -d' ' -f1)
SUBNET_2=$(echo $SUBNET_IDS | cut -d' ' -f2)

# Create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name cronpulse-sg \
    --description "Security group for CronPulse" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text)

# Allow inbound traffic on port 8000
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

echo "VPC: $VPC_ID"
echo "Subnets: $SUBNET_1, $SUBNET_2"
echo "Security Group: $SG_ID"
```

Create the service:
```bash
aws ecs create-service \
    --cluster cronpulse-cluster \
    --service-name cronpulse-service \
    --task-definition cronpulse-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION
```

### 7. Get the Public IP
```bash
# Wait a minute for the task to start, then:
TASK_ARN=$(aws ecs list-tasks --cluster cronpulse-cluster --service-name cronpulse-service --region $AWS_REGION --query 'taskArns[0]' --output text)

ENI_ID=$(aws ecs describe-tasks --cluster cronpulse-cluster --tasks $TASK_ARN --region $AWS_REGION --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region $AWS_REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

echo "Access your app at: http://$PUBLIC_IP:8000"
```

### 8. Check Logs
```bash
aws logs tail /ecs/cronpulse --follow --region $AWS_REGION
```

## Using AWS Console (Easier for First Time)

1. **Push your image to ECR:**
   - Run `./deploy-aws.sh`

2. **Create Task Definition:**
   - Go to ECS Console → Task Definitions → Create new
   - Select Fargate
   - Set CPU: 0.25 vCPU, Memory: 0.5 GB
   - Add container with your ECR image
   - Add environment variables
   - Port mapping: 8000

3. **Create Service:**
   - Go to your cluster → Create Service
   - Select Fargate, your task definition
   - Enable public IP
   - Create security group allowing port 8000

4. **Access:**
   - Go to Tasks tab, click on your task
   - Find the Public IP in the network section
   - Visit http://PUBLIC_IP:8000

## Production Deployment with Persistence

For production, you'll want:
1. **EFS for SQLite database persistence**
2. **Application Load Balancer**
3. **Route 53 for custom domain**
4. **Secrets Manager for environment variables**

See `aws-task-definition.json` for the configuration with EFS.

## Clean Up
```bash
# Delete service
aws ecs delete-service --cluster cronpulse-cluster --service cronpulse-service --force --region $AWS_REGION

# Delete cluster
aws ecs delete-cluster --cluster cronpulse-cluster --region $AWS_REGION

# Delete security group
aws ec2 delete-security-group --group-id $SG_ID --region $AWS_REGION

# Delete ECR repository
aws ecr delete-repository --repository-name cronpulse --force --region $AWS_REGION
```
