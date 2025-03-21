SYSTEM_PROMPT = """
You are CloudWise, an AI assistant specialized in cloud resource management. Your role is to help users manage their cloud resources across AWS and Azure platforms.

When responding to queries:
1. Always use lowercase for resource names (e.g., 'ec2', 's3', 'vpc')
2. For EC2 queries, include standard AWS filter parameters like:
   - instance-state-name
   - instance-type
   - vpc-id
   - tag:Name
3. For S3 queries, consider:
   - bucket name patterns
   - region filters
   - tag filters
4. For cost queries, always specify time ranges
"""

CLOUD_QUERY_TEMPLATE = """
User Request: {user_query}

Available Cloud Platforms: {available_platforms}
Current Context: {current_context}

Please analyze the request and provide a structured response with the following sections:

Platforms:
- AWS
- Azure (if applicable)

Resources:
- For EC2 instances, always use 'ec2' as the resource type
- For S3 buckets, use 's3'
- For cost analysis, use 'costs'
- One resource per line, all lowercase

Action:
- For EC2: use 'describe' for listing instances
- For S3: use 'describe' for listing buckets
- For metrics: use 'get_metrics'
- For costs: use 'get_costs'
- For analysis: use 'analyze'

Parameters:
- Specify as key: value pairs
- For EC2 filters, only include if specified in query:
  instance-state-name: ["running", "stopped", "pending", "terminated"]
  instance-type: ["t2.micro", "t2.small", etc]
  vpc-id: ["vpc-123456"]
  tag:Name: ["name1", "name2"]
- For S3 filters:
  name: ["pattern"]
  region: ["region-name"]
- For metrics:
  instance-id: "i-1234567890abcdef0"
  metric_name: "CPUUtilization" or "NetworkIn" or "NetworkOut" or "DiskReadOps" or "DiskWriteOps"
- For costs:
  start_date: "YYYY-MM-DD"
  end_date: "YYYY-MM-DD"
"""

ERROR_ANALYSIS_TEMPLATE = """
Error Context:
- Operation: {operation}
- Error Message: {error_message}
- Platform: {platform}
- Resource: {resource}

Please analyze this error and provide:
1. A clear explanation of what went wrong
2. Potential causes
3. Recommended solutions
4. Prevention steps for the future
"""

COST_OPTIMIZATION_TEMPLATE = """
Resource Context:
{resource_details}

Current Costs:
{cost_data}

Analyze the current resource usage and costs to provide:
1. Cost optimization opportunities
2. Specific recommendations for resource adjustments
3. Potential cost savings estimates
4. Implementation steps for the recommendations
"""
