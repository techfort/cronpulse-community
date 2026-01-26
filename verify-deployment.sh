#!/bin/bash

# Configuration
AWS_REGION="eu-west-1"
CLUSTER_NAME="cronpulse-cluster"
SERVICE_NAME="cronpulse-service"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Verifying CronPulse Deployment...${NC}\n"

# Check cluster
echo -e "${YELLOW}1. Checking ECS Cluster...${NC}"
CLUSTER_STATUS=$(aws ecs describe-clusters --cluster ${CLUSTER_NAME} --region ${AWS_REGION} --query 'clusters[0].status' --output text 2>/dev/null)
if [ "$CLUSTER_STATUS" == "ACTIVE" ]; then
    echo -e "${GREEN}✓ Cluster is ACTIVE${NC}"
    RUNNING_TASKS=$(aws ecs describe-clusters --cluster ${CLUSTER_NAME} --region ${AWS_REGION} --query 'clusters[0].runningTasksCount' --output text)
    echo -e "  Running tasks: $RUNNING_TASKS"
else
    echo -e "${RED}✗ Cluster not found or not active${NC}"
    exit 1
fi

# Check service
echo -e "\n${YELLOW}2. Checking ECS Service...${NC}"
SERVICE_STATUS=$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} --query 'services[0].status' --output text 2>/dev/null)
if [ "$SERVICE_STATUS" == "ACTIVE" ]; then
    echo -e "${GREEN}✓ Service is ACTIVE${NC}"
    DESIRED=$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} --query 'services[0].desiredCount' --output text)
    RUNNING=$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} --query 'services[0].runningCount' --output text)
    echo -e "  Desired tasks: $DESIRED"
    echo -e "  Running tasks: $RUNNING"
else
    echo -e "${RED}✗ Service not found or not active${NC}"
    exit 1
fi

# Get task details
echo -e "\n${YELLOW}3. Getting Task Information...${NC}"
TASK_ARN=$(aws ecs list-tasks --cluster ${CLUSTER_NAME} --service-name ${SERVICE_NAME} --region ${AWS_REGION} --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" == "None" ] || [ -z "$TASK_ARN" ]; then
    echo -e "${RED}✗ No running tasks found${NC}"
    echo -e "${YELLOW}Check service events for issues:${NC}"
    aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} --query 'services[0].events[0:3].[createdAt,message]' --output table
    exit 1
fi

TASK_STATUS=$(aws ecs describe-tasks --cluster ${CLUSTER_NAME} --tasks $TASK_ARN --region ${AWS_REGION} --query 'tasks[0].lastStatus' --output text)
echo -e "${GREEN}✓ Task Status: $TASK_STATUS${NC}"

# Get public IP
echo -e "\n${YELLOW}4. Retrieving Public IP...${NC}"
ENI_ID=$(aws ecs describe-tasks --cluster ${CLUSTER_NAME} --tasks $TASK_ARN --region ${AWS_REGION} --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

if [ -z "$ENI_ID" ]; then
    echo -e "${RED}✗ Could not find network interface${NC}"
    exit 1
fi

PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region ${AWS_REGION} --query 'NetworkInterfaces[0].Association.PublicIp' --output text 2>/dev/null)

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" == "None" ]; then
    echo -e "${RED}✗ No public IP assigned${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Public IP: $PUBLIC_IP${NC}"

# Test endpoint
echo -e "\n${YELLOW}5. Testing HTTP Endpoint...${NC}"
echo -e "Testing: http://$PUBLIC_IP:8000"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://$PUBLIC_IP:8000 2>/dev/null)

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "307" ]; then
    echo -e "${GREEN}✓ Application is responding (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response (HTTP $HTTP_CODE)${NC}"
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Verification Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "Access your application at:"
echo -e "${GREEN}http://$PUBLIC_IP:8000${NC}"
echo -e ""
echo -e "View logs:"
echo -e "aws logs tail /ecs/cronpulse --follow --region ${AWS_REGION}"
echo -e ""
echo -e "Login with:"
echo -e "Email: admin@test.com"
echo -e "Password: TestPassword123"
echo -e "(or the credentials you set in the task definition)"
