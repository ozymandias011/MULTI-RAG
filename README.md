# MULRAG - Multi-Agent RAG System

A sophisticated Multi-Agent Retrieval-Augmented Generation (RAG) system for intelligent document analysis and question answering.

## 🚀 Features

### Core Functionality
- **Multi-Agent Architecture**: 4 specialized agents working in concert
  - Question Understanding Agent: Analyzes and rephrases questions
  - History Analysis Agent: Analyzes chat history for context
  - Context Retrieval Agent: Retrieves relevant document chunks
  - Answer Generation Agent: Generates comprehensive responses

- **Document Processing**
  - PDF text extraction from local files and URLs
  - Smart text chunking with paragraph awareness
  - Advanced embedding generation with Azure OpenAI
  - FAISS vector indexing for efficient retrieval

- **Authentication & Security**
  - JWT-based authentication system
  - Secure password hashing with bcrypt
  - User registration and login management
  - Session-based chat management

### Technical Features
- **FastAPI Backend**: High-performance async web framework
- **MongoDB Integration**: Scalable document storage
- **Azure OpenAI Integration**: Advanced AI capabilities
- **Semantic Search**: Hybrid keyword and semantic search
- **Real-time Chat**: Session-based conversation management
- **File Upload**: Secure PDF upload and processing

## 📁 Project Structure

```
MULRAG/
├── main.py                     # Main application entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create from .env.example)
├── README.md                   # This file
├── src/                        # Source code modules
│   ├── config/                 # Configuration management
│   │   └── __init__.py        # Settings and environment variables
│   ├── models/                 # Data models and schemas
│   │   └── __init__.py        # Pydantic models and database schemas
│   ├── database/               # Database operations
│   │   └── __init__.py        # MongoDB repositories and operations
│   ├── auth/                   # Authentication system
│   │   └── __init__.py        # JWT auth, password management, middleware
│   ├── agents/                 # Multi-agent RAG system
│   │   └── __init__.py        # RAG agents and orchestration
│   ├── document_processing/    # Document processing pipeline
│   │   └── __init__.py        # PDF extraction, chunking, embeddings
│   ├── api/                    # API routes
│   │   └── __init__.py        # FastAPI endpoints and routing
│   └── utils/                  # Utility functions
│       └── __init__.py        # Helpers, logging, validation
├── app/                        # Frontend assets
│   ├── static/                 # Static files (CSS, JS, images)
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── templates/              # HTML templates
│   └── uploads/                # Uploaded file storage
└── tests/                      # Test files (optional)
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- MongoDB database
- Azure OpenAI account with API access

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd MULRAG
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file based on the example:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Azure OpenAI Configuration
OPENAI_API_KEY=your_azure_openai_api_key
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_DEPLOYMENT=gpt-4o-mini
OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
OPENAI_API_VERSION=2024-12-01-preview

# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
DB_NAME=hackrx_logs

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRATION_HOURS=168

# Application Settings
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

5. **Create necessary directories**
```bash
mkdir -p app/uploads app/static/css app/static/js app/static/images app/templates
```

6. **Run the application**
```bash
python main.py
```

The application will be available at `http://localhost:8000`

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Main Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info
- `GET /api/v1/auth/health` - Health check

#### Session Management
- `POST /api/v1/sessions/create` - Create chat session
- `GET /api/v1/sessions/list` - List user sessions
- `GET /api/v1/sessions/{session_id}/messages` - Get session messages
- `DELETE /api/v1/sessions/{session_id}` - Delete session

#### Document & Chat
- `POST /api/v1/upload-pdf` - Upload PDF document
- `POST /api/v1/chat` - Chat with RAG system

#### Legacy (Compatibility)
- `POST /api/v1/hackrx/run` - Original endpoint

## 🤖 Multi-Agent System

The system uses a sophisticated multi-agent architecture:

### Agent 1: Question Understanding
- Analyzes user questions
- Rephrases for better semantic search
- Identifies user intent
- **Output**: Understood question + intent type

### Agent 2: History Analysis
- Analyzes chat conversation history
- Identifies relevant context from previous messages
- Determines if current question references history
- **Output**: Relevant historical context

### Agent 3: Context Retrieval
- Processes documents (PDF extraction, chunking, embedding)
- Performs semantic search with question expansion
- Reranks results by keyword overlap
- **Output**: Top relevant document chunks

### Agent 4: Answer Generation
- Synthesizes information from all sources
- Generates comprehensive, well-formatted answers
- Uses markdown formatting for readability
- **Output**: Final answer with metadata

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Azure OpenAI API key | Required |
| `OPENAI_API_BASE` | Azure OpenAI endpoint | Required |
| `OPENAI_DEPLOYMENT` | Chat model deployment | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model | `text-embedding-3-large` |
| `MONGO_URI` | MongoDB connection string | Required |
| `JWT_SECRET` | JWT signing secret | Required |
| `DEBUG` | Debug mode | `false` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |

### RAG Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CHUNK_SIZE` | Maximum chunk size | `800` |
| `MIN_CHUNK_WORDS` | Minimum words per chunk | `5` |
| `RETRIEVAL_TOP_K` | Number of chunks to retrieve | `21` |
| `EMBEDDING_BATCH_SIZE` | Embedding batch size | `20` |

## 🧪 Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
flake8 src/
mypy src/
```

### Project Structure Guidelines

1. **Modular Design**: Each module has a single responsibility
2. **Dependency Injection**: Use FastAPI's dependency system
3. **Async/Await**: All I/O operations are asynchronous
4. **Error Handling**: Centralized error handling with proper logging
5. **Configuration**: Environment-based configuration management
6. **Documentation**: Comprehensive docstrings and type hints

## 🚀 Deployment

### Docker Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t mulrag .
docker run -p 8000:8000 --env-file .env mulrag
```

### Production Considerations
- Use a proper WSGI server (Gunicorn, Uvicorn workers)
- Set up reverse proxy (Nginx)
- Configure proper CORS origins
- Use environment-specific configuration
- Set up monitoring and logging
- Implement rate limiting
- Use HTTPS

## 🔒 Security

- JWT tokens with expiration
- Password hashing with bcrypt
- File upload validation
- Input sanitization
- CORS protection
- Rate limiting capabilities

## 📊 Monitoring

The application includes comprehensive logging:
- Request/response logging
- Agent performance metrics
- Error tracking
- System resource monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Check environment configuration
4. Verify database connectivity
5. Ensure Azure OpenAI credentials are valid

## 🔄 Version History

- **v1.0.0** - Initial release with multi-agent RAG system
  - Complete API implementation
  - Authentication and session management
  - Document processing pipeline
  - Multi-agent orchestration
