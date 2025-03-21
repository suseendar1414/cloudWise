from typing import Dict, List, Any
from openai import OpenAI
from .prompt_template import (
    SYSTEM_PROMPT,
    CLOUD_QUERY_TEMPLATE,
    ERROR_ANALYSIS_TEMPLATE,
    COST_OPTIMIZATION_TEMPLATE
)

class LLMService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def _get_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Get completion from OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f'Error getting LLM completion: {str(e)}')

    def process_cloud_query(self, 
                          user_query: str, 
                          available_platforms: List[str],
                          current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a natural language cloud management query"""
        try:
            # Format the query template
            formatted_query = CLOUD_QUERY_TEMPLATE.format(
                user_query=user_query,
                available_platforms=', '.join(available_platforms),
                current_context=str(current_context or {})
            )

            # Prepare messages for the API
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": formatted_query}
            ]

            # Get completion
            response = self._get_completion(messages, temperature=0.7)

            # Parse the response into structured format
            lines = response.split('\n')
            result = {
                'platforms': [],
                'resources': [],
                'action': '',
                'parameters': {}
            }

            current_section = ''
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check for section headers
                lower_line = line.lower()
                if lower_line.startswith('platforms:'):
                    current_section = 'platforms'
                    continue
                elif lower_line.startswith('resources:'):
                    current_section = 'resources'
                    continue
                elif lower_line.startswith('action:'):
                    current_section = 'action'
                    continue
                elif lower_line.startswith('parameters:'):
                    current_section = 'parameters'
                    continue

                # Process content based on current section
                if line.startswith('-'):
                    line = line[1:].strip()
                    if current_section == 'platforms':
                        if line:
                            result['platforms'].append(line)
                    elif current_section == 'resources':
                        if line:
                            result['resources'].append(line.lower())
                    elif current_section == 'action':
                        if line:
                            result['action'] = line
                    elif current_section == 'parameters':
                        if ':' in line:
                            key, value = [x.strip() for x in line.split(':', 1)]
                            # Handle list values in square brackets
                            if value.startswith('[') and value.endswith(']'):
                                values = [x.strip().strip('"') for x in value[1:-1].split(',')]
                                result['parameters'][key] = values
                            else:
                                result['parameters'][key] = value

            return result

        except Exception as e:
            raise Exception(f'Error processing cloud query: {str(e)}')

    def analyze_error(self, 
                     operation: str, 
                     error_message: str, 
                     platform: str, 
                     resource: str) -> Dict[str, Any]:
        """Analyze a cloud operation error and provide recommendations"""
        try:
            formatted_query = ERROR_ANALYSIS_TEMPLATE.format(
                operation=operation,
                error_message=error_message,
                platform=platform,
                resource=resource
            )

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": formatted_query}
            ]

            response = self._get_completion(messages, temperature=0.7)
            
            # Parse the response into sections
            sections = {
                'explanation': [],
                'causes': [],
                'solutions': [],
                'prevention': []
            }
            
            current_section = None
            for line in response.split('\n'):
                line = line.strip()
                if 'explanation' in line.lower():
                    current_section = 'explanation'
                elif 'causes' in line.lower():
                    current_section = 'causes'
                elif 'solution' in line.lower():
                    current_section = 'solutions'
                elif 'prevention' in line.lower():
                    current_section = 'prevention'
                elif line and current_section:
                    sections[current_section].append(line)

            return sections

        except Exception as e:
            raise Exception(f'Error analyzing cloud error: {str(e)}')

    def get_cost_optimization(self, 
                            resource_details: Dict[str, Any], 
                            cost_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource usage and provide cost optimization recommendations"""
        try:
            formatted_query = COST_OPTIMIZATION_TEMPLATE.format(
                resource_details=str(resource_details),
                cost_data=str(cost_data)
            )

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": formatted_query}
            ]

            response = self._get_completion(messages, temperature=0.7)
            
            # Parse the response into sections
            sections = {
                'opportunities': [],
                'recommendations': [],
                'savings_estimates': [],
                'implementation_steps': []
            }
            
            current_section = None
            for line in response.split('\n'):
                line = line.strip()
                if 'opportunities' in line.lower():
                    current_section = 'opportunities'
                elif 'recommendation' in line.lower():
                    current_section = 'recommendations'
                elif 'saving' in line.lower():
                    current_section = 'savings_estimates'
                elif 'implementation' in line.lower():
                    current_section = 'implementation_steps'
                elif line and current_section:
                    sections[current_section].append(line)

            return sections

        except Exception as e:
            raise Exception(f'Error getting cost optimization recommendations: {str(e)}')
