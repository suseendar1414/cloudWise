# CloudWise: Natural Language Cloud Management Interface

CloudWise is an intelligent cloud management platform that allows users to interact with their cloud resources using natural language. It currently supports AWS and Azure cloud platforms, making cloud management more intuitive and accessible.

## Features

### Multi-Cloud Support
- **AWS Services**:
  - EC2 instance management
  - S3 bucket operations
  - Cost analysis and optimization
  - Resource metrics monitoring

- **Azure Services**:
  - Virtual Machine management
  - Storage account operations
  - Cost analysis and optimization
  - Resource metrics monitoring

### Natural Language Processing
- Powered by GPT-4 for understanding user queries
- Context-aware responses
- Intelligent error handling

### Cost Management
- Detailed cost breakdowns by service
- Cost optimization recommendations
- Historical cost analysis
- Multi-currency support

### Resource Monitoring
- Real-time metrics visualization
- Resource health monitoring
- Performance analytics

## Architecture

### Backend (FastAPI)
- `app/`
  - `cloud_providers/` - AWS and Azure client implementations
  - `llm/` - GPT-4 integration and prompt management
  - `api/` - REST API endpoints

### Frontend (Streamlit)
- Interactive dashboard
- Real-time data visualization
- Responsive design

## Setup

### Prerequisites
- Python 3.8+
- AWS credentials (for AWS features)
- Azure credentials (for Azure features)
- OpenAI API key (for GPT-4)

### Environment Variables
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region

# Azure Credentials
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_SUBSCRIPTION_ID=your_subscription_id

# OpenAI
OPENAI_API_KEY=your_openai_key
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/suseendar1414/cloudWise.git
cd cloudWise
```

2. Set up backend:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Set up frontend:
```bash
cd ../frontend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Running the Application

1. Start the backend server:
```bash
cd backend
source venv/bin/activate
python main.py
```

2. Start the frontend (in a new terminal):
```bash
cd frontend
source venv/bin/activate
streamlit run app.py
```

3. Access the application at http://localhost:8501

## Usage Examples

### AWS Operations
- "Show me all running EC2 instances"
- "List S3 buckets with encryption status"
- "Get AWS costs for last 30 days"

### Azure Operations
- "Show me all Azure VMs"
- "List Azure storage accounts"
- "Get Azure costs for last month"

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for GPT-4
- AWS SDK for Python (Boto3)
- Azure SDK for Python
- Streamlit for the frontend framework
