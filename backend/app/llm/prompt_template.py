SYSTEM_PROMPT = """
You are CloudWise, an AI assistant specialized in cloud resource management. Your role is to help users manage their cloud resources across AWS and Azure platforms.
Analyze the user's request and determine the appropriate cloud management actions to take.
"""

CLOUD_QUERY_TEMPLATE = """
User Request: {user_query}

Available Cloud Platforms: {available_platforms}
Current Context: {current_context}

Please analyze the request and provide:
1. The specific cloud platform(s) involved
2. The resources or services being targeted
3. The action to be performed
4. Any relevant parameters or filters
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
