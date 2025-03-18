import openai
from typing import Dict, List, Any
import json

class LLMService:
    def __init__(self, api_key: str):
        """Initialize the LLM service with OpenAI API key"""
        openai.api_key = api_key
        self.model = "gpt-4-turbo-preview"  # Using the latest GPT-4 model

    def process_cloud_query(self, user_query: str, available_platforms: List[str], current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a natural language query about cloud resources"""
        try:
            # Construct the prompt
            prompt = self._construct_cloud_query_prompt(user_query, available_platforms, current_context)
            
            # Get completion from OpenAI
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a cloud infrastructure assistant that helps interpret natural language queries into structured commands for cloud resource management. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic outputs
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = response.choices[0].message.content
            try:
                # Try to parse as JSON
                parsed_result = json.loads(result)
            except json.JSONDecodeError:
                # If not valid JSON, provide a structured response
                parsed_result = {
                    "platforms": [],
                    "resources": [],
                    "action": "",
                    "parameters": {}
                }
            
            return parsed_result

        except Exception as e:
            raise Exception(f"Error getting LLM completion: {str(e)}")

    def _construct_cloud_query_prompt(self, query: str, available_platforms: List[str], context: Dict[str, Any] = None) -> str:
        """Construct a prompt for the LLM to process cloud queries"""
        prompt = f"""
You are a cloud infrastructure assistant that helps interpret natural language queries into structured commands for cloud resource management.

Parse the following natural language query about cloud resources into a structured JSON format.

Available cloud platforms: {', '.join(available_platforms)}
Query: {query}
Current context: {json.dumps(context) if context else 'No additional context'}

Provide ONLY a JSON response with this exact structure, no other text:
{{
    "platforms": ["List of cloud platforms, e.g., AWS, Azure"],
    "resources": ["List of resource types, e.g., EC2, S3, costs"],
    "action": "Action to perform (e.g., list, describe, start)",
    "parameters": {{
        "region": "AWS region if specified",
        "filters": [],
        "other_params": "any other parameters from the query"
    }}
}}

Example 1 - For query "show all my AWS resources":
{{
    "platforms": ["AWS"],
    "resources": ["EC2", "S3", "costs"],
    "action": "list",
    "parameters": {{}}
}}

Example 2 - For query "list EC2 instances and S3 buckets in eu-west-2":
{{
    "platforms": ["AWS"],
    "resources": ["EC2", "S3"],
    "action": "list",
    "parameters": {{"region": "eu-west-2"}}
}}

Example 3 - For query "show my AWS costs and running instances":
{{
    "platforms": ["AWS"],
    "resources": ["costs", "EC2"],
    "action": "list",
    "parameters": {{"filters": [{{"Name": "instance-state-name", "Values": ["running"]}}]}}
}}

Example 4 - For query "show all my Azure VMs and storage accounts":
{{
    "platforms": ["Azure"],
    "resources": ["VM", "Storage"],
    "action": "list",
    "parameters": {{}}
}}

Example 5 - For query "get Azure costs for last week":
{{
    "platforms": ["Azure"],
    "resources": ["costs"],
    "action": "list",
    "parameters": {{"timeframe": "LastWeek"}}
}}

Provide ONLY the JSON response for the given query, no other text:"""
        return prompt

    def analyze_error(self, operation: str, error_message: str, platform: str, resource: str) -> Dict[str, Any]:
        """Analyze cloud operation errors and provide recommendations"""
        try:
            prompt = f"""
Analyze the following cloud operation error and provide recommendations:
Platform: {platform}
Resource: {resource}
Operation: {operation}
Error Message: {error_message}

Provide a response in JSON format with:
1. Root cause analysis
2. Potential solutions
3. Best practices to prevent similar issues
"""
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a cloud infrastructure expert that helps analyze and solve cloud operation errors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f"Error analyzing error: {str(e)}")

    def optimize_costs(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource usage and provide cost optimization recommendations"""
        try:
            prompt = f"""
Analyze the following cloud resource data and provide cost optimization recommendations:
{json.dumps(resource_data, indent=2)}

Provide recommendations in JSON format with:
1. Identified cost optimization opportunities
2. Specific actions to take
3. Estimated cost savings
"""
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a cloud cost optimization expert that helps identify cost-saving opportunities."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f"Error generating cost optimization recommendations: {str(e)}")
