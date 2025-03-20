import os
from dotenv import load_dotenv
from app.cloud_providers.azure_client import AzureClient
import json

def main():
    # Load environment variables
    load_dotenv()
    
    # Debug: Print environment variables (masked)
    print("Environment variables:")
    for var in ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_SUBSCRIPTION_ID']:
        value = os.getenv(var)
        if value:
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
            print(f"{var}: {masked}")
        else:
            print(f"{var}: Not found")
    
    try:
        # Initialize Azure client
        client = AzureClient()
        
        # Get cost analysis for last month
        print("\nGetting cost analysis for last month...")
        monthly_costs = client.get_cost_analysis(timeframe='LastMonth')
        print("\nMonthly Cost Analysis:")
        print(f"Total Cost: {monthly_costs['total_cost']} {monthly_costs['currency']}")
        print("\nCosts by Service:")
        for service, cost in monthly_costs['costs_by_service'].items():
            print(f"- {service}: {cost:.2f} {monthly_costs['currency']}")
        
        print("\nCosts by Location:")
        for location, cost in monthly_costs['costs_by_location'].items():
            print(f"- {location}: {cost:.2f} {monthly_costs['currency']}")
        
        # Get cost analysis for last week
        print("\nGetting cost analysis for last week...")
        weekly_costs = client.get_cost_analysis(timeframe='LastWeek')
        print("\nWeekly Cost Analysis:")
        print(f"Total Cost: {weekly_costs['total_cost']} {weekly_costs['currency']}")
        print("\nCosts by Service:")
        for service, cost in weekly_costs['costs_by_service'].items():
            print(f"- {service}: {cost:.2f} {weekly_costs['currency']}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
