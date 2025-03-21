import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="CloudWise",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .success {
        background-color: #d4edda;
        color: #155724;
    }
    .error {
        background-color: #f8d7da;
        color: #721c24;
    }
    .warning {
        background-color: #fff3cd;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("☁️ CloudWise")
    st.markdown("---")
    
    # Example queries
    st.subheader("📝 Example Queries")
    
    # Cloud provider selection
    cloud_provider = st.selectbox(
        "Select Cloud Provider",
        ["AWS", "Azure"],
        help="Choose which cloud provider to query"
    )
    
    if cloud_provider == "AWS":
        examples = [
            "Show me all running EC2 instances",
            "List S3 buckets with encryption status",
            "Get AWS costs for last 30 days",
            "Show CPU metrics for instance i-1234567890"
        ]
    else:  # Azure
        examples = [
            "Show me all Azure VMs",
            "List Azure storage accounts",
            "Get Azure costs for last month",
            "Show metrics for VM myvm-001"
        ]
    
    for example in examples:
        if st.button(example):
            st.session_state.user_query = example
    
    st.markdown("---")
    
    # Settings
    st.subheader("⚙️ Settings")
    api_url = st.text_input(
        "API URL",
        value="http://localhost:8001",
        help="The URL of your CloudWise API"
    )

# Initialize session state
if 'user_query' not in st.session_state:
    st.session_state.user_query = ""

# Main content
st.title("Natural Language Cloud Management")

# Query input
col1, col2 = st.columns([6, 1])
with col1:
    user_query = st.text_input(
        "Enter your cloud query",
        value=st.session_state.user_query,
        placeholder="e.g., Show me all running EC2 instances",
        help="Ask about EC2 instances, S3 buckets, costs, or metrics"
    )
with col2:
    send_button = st.button("🚀 Send", use_container_width=True)

if send_button and user_query:
    # Show spinner while processing
    with st.spinner("Processing your query..."):
        try:
            # Make request
            response = requests.post(
                f"{api_url}/query",
                json={"query": user_query},
                timeout=30
            )
            
            # Parse response
            result = response.json()
            
            # Display results based on query type and cloud provider
            query_lower = user_query.lower()
            
            # Azure VM handling
            if "azure" in query_lower and ("vm" in query_lower or "virtual machine" in query_lower):
                st.subheader("🖥️ Azure Virtual Machines")
                if result.get("data"):
                    vms = []
                    for region, region_vms in result["data"].items():
                        for vm in region_vms:
                            vm["Region"] = region
                            vms.append(vm)
                    
                    if vms:
                        df = pd.DataFrame(vms)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No Azure VMs found matching your criteria")
                else:
                    st.warning(result.get("message", "No Azure VMs found"))
            
            # Azure Storage handling
            elif "azure" in query_lower and "storage" in query_lower:
                st.subheader("📦 Azure Storage Accounts")
                if result.get("data"):
                    storage_accounts = []
                    for region, accounts in result["data"].items():
                        for account in accounts:
                            account["Region"] = region
                            storage_accounts.append(account)
                    
                    if storage_accounts:
                        df = pd.DataFrame(storage_accounts)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No storage accounts found")
                else:
                    st.warning(result.get("message", "No storage accounts found"))
            
            # Azure Cost Analysis
            elif "azure" in query_lower and "cost" in query_lower:
                st.subheader("💰 Azure Cost Analysis")
                if result.get("data"):
                    cost_data = result["data"]
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Cost", f"${cost_data.get('totalCost', 0):.2f}")
                    with col2:
                        st.metric("Currency", cost_data.get('currency', 'USD'))
                    with col3:
                        st.metric("Time Range", cost_data.get('timeframe', 'Last Month'))
                    
                    # Costs by service
                    if 'costsByService' in cost_data:
                        st.subheader("Costs by Service")
                        service_costs = pd.DataFrame(
                            cost_data['costsByService'].items(),
                            columns=['Service', 'Cost']
                        )
                        st.bar_chart(service_costs.set_index('Service'))
                    
                    # Costs by location
                    if 'costsByLocation' in cost_data:
                        st.subheader("Costs by Location")
                        location_costs = pd.DataFrame(
                            cost_data['costsByLocation'].items(),
                            columns=['Location', 'Cost']
                        )
                        st.bar_chart(location_costs.set_index('Location'))
                    
                    # Optimization recommendations
                    if 'optimizationRecommendations' in cost_data:
                        with st.expander("💡 Cost Optimization Recommendations"):
                            for rec in cost_data['optimizationRecommendations']:
                                st.markdown(f"**{rec.get('type', 'Recommendation')}**")
                                st.markdown(f"- {rec.get('description', '')}")
                                if 'estimatedSavings' in rec:
                                    st.markdown(f"- Estimated Savings: ${rec['estimatedSavings']:.2f}")
                else:
                    st.warning("No Azure cost data available")
            
            # Azure Metrics
            elif "azure" in query_lower and "metric" in query_lower:
                st.subheader("📊 Azure Metrics")
                if result.get("data") and result["data"].get("metrics"):
                    metrics_data = result["data"]["metrics"]
                    if metrics_data:
                        df = pd.DataFrame(metrics_data)
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        st.line_chart(df.set_index('timestamp')['value'])
                        
                        # Show metrics details
                        with st.expander("ℹ️ Metrics Details"):
                            st.markdown(f"**Resource**: {result['data']['resource_id']}")
                            st.markdown(f"**Metric**: {result['data']['metric_name']}")
                            st.markdown(f"**Unit**: {metrics_data[0].get('unit', 'N/A')}")
                    else:
                        st.info("No metrics data available for the specified resource")
                else:
                    st.warning(result.get("message", "No metrics data found"))
            
            # AWS EC2 handling
            elif "ec2" in query_lower:
                st.subheader("🖥️ EC2 Instances")
                if result.get("data"):
                    # Convert to DataFrame
                    instances = []
                    for region, region_instances in result["data"].items():
                        for instance in region_instances:
                            instance["Region"] = region
                            instances.append(instance)
                    
                    if instances:
                        df = pd.DataFrame(instances)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No instances found matching your criteria")
                else:
                    st.warning(result.get("message", "No instances found"))
            
            elif "s3" in user_query.lower():
                st.subheader("📦 S3 Buckets")
                if result.get("data", {}).get("data"):
                    buckets = []
                    for region, region_buckets in result["data"]["data"].items():
                        for bucket in region_buckets:
                            bucket["Region"] = region
                            buckets.append(bucket)
                    
                    if buckets:
                        df = pd.DataFrame(buckets)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No buckets found")
                        
                    # Show warnings if any
                    if "warnings" in result["data"]:
                        with st.expander("⚠️ Warnings"):
                            st.warning(result["data"]["warnings"]["message"])
                            st.json(result["data"]["warnings"]["errors"])
                else:
                    st.warning(result.get("data", {}).get("message", "No buckets found"))
            
            elif "cost" in user_query.lower():
                st.subheader("💰 Cost Analysis")
                if result.get("data"):
                    cost_data = result["data"]
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Cost", f"${cost_data['totalCost']:.2f}")
                    with col2:
                        st.metric("Currency", cost_data['currency'])
                    with col3:
                        st.metric("Time Range", cost_data['timeframe'])
                    
                    # Costs by service
                    st.subheader("Costs by Service")
                    service_costs = pd.DataFrame(
                        cost_data['costsByService'].items(),
                        columns=['Service', 'Cost']
                    )
                    st.bar_chart(service_costs.set_index('Service'))
                    
                    # Optimization recommendations
                    if 'optimization_recommendations' in cost_data:
                        with st.expander("💡 Optimization Recommendations"):
                            recs = cost_data['optimization_recommendations']
                            if 'opportunities' in recs:
                                st.markdown("### Opportunities")
                                for opp in recs['opportunities']:
                                    st.markdown(f"- {opp}")
                            
                            if 'recommendations' in recs:
                                st.markdown("### Recommendations")
                                for rec in recs['recommendations']:
                                    st.markdown(f"- {rec}")
                else:
                    st.warning("No cost data available")
            
            elif "metric" in user_query.lower():
                st.subheader("📊 Metrics")
                if result.get("data"):
                    # Convert metrics to DataFrame
                    metrics_data = result["data"]
                    if isinstance(metrics_data, dict) and metrics_data:
                        df = pd.DataFrame(metrics_data)
                        st.line_chart(df.set_index('Timestamp')['Value'])
                    else:
                        st.info("No metrics data available for the specified time range")
                else:
                    st.warning(result.get("message", "No metrics data found"))
                    if "details" in result:
                        with st.expander("ℹ️ Details"):
                            st.json(result["details"])
            
            # Show raw response in expander
            with st.expander("🔍 Raw Response"):
                st.json(result)
                
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to the API: {str(e)}")
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse API response: {str(e)}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")

elif send_button:
    st.warning("Please enter a query")
