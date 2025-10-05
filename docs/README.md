# DSP Front Door (FD2) Documentation

Complete documentation for the DSP AI Front Door with APISIX integration and Langfuse observability.

## 📚 Documentation Index

### Quick Start
- **[Langfuse Quick Start](LANGFUSE_QUICK_START.md)** - Get started with Langfuse observability in 5 minutes

### Core Documentation
- **[Front Door Overview](FRONT_DOOR.md)** - Architecture and features of the DSP Front Door
- **[APISIX Integration](README_APISIX.md)** - APISIX gateway integration guide
- **[APISIX Module](APISIX_MODULE.md)** - Modular APISIX client documentation

### Langfuse & Observability
- **[Langfuse Integration Guide](APISIX_LANGFUSE_INTEGRATION.md)** - Complete guide to LLM tracing with Langfuse
- **[Refactoring Summary](REFACTORING_SUMMARY.md)** - Details of the APISIX client refactoring

### Security & Authentication
- **[JWT Integration](JWT_INTEGRATION.md)** - JWT authentication setup and configuration
- **[JWT Token Endpoint](JWT_TOKEN_ENDPOINT.md)** - Token generation and validation
- **[Security Design](SECURITY_DESIGN.md)** - Security architecture and best practices

### Operations & Deployment
- **[Scalability & Resilience](SCALABILITY_RESILIENCE.md)** - High availability and scaling strategies
- **[APISIX Project Organization](APISIX_PROJECT_ORGANIZATION.md)** - Project structure and organization
- **[APISIX Commands Reference](check_apisix_commands.md)** - Useful APISIX CLI commands

## 🚀 Getting Started

### 1. Basic Setup

```bash
# Clone and setup
git clone <repo>
cd dsp-fd2

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 2. Add Langfuse Observability

```bash
# Get Langfuse keys from https://cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."

# Run setup script
python setup_langfuse.py
```

### 3. Start Services

```bash
# Start APISIX and dependencies
docker-compose -f docker-compose-apisix.yml up -d

# Start Front Door
python run.py
```

## 📖 Documentation by Topic

### For Developers

1. **Getting Started**
   - [Front Door Overview](FRONT_DOOR.md)
   - [APISIX Integration](README_APISIX.md)
   - [Langfuse Quick Start](LANGFUSE_QUICK_START.md)

2. **Implementation**
   - [APISIX Module](APISIX_MODULE.md)
   - [JWT Integration](JWT_INTEGRATION.md)
   - [Refactoring Summary](REFACTORING_SUMMARY.md)

3. **Advanced Topics**
   - [Langfuse Integration Guide](APISIX_LANGFUSE_INTEGRATION.md)
   - [Security Design](SECURITY_DESIGN.md)
   - [Scalability & Resilience](SCALABILITY_RESILIENCE.md)

### For Operators

1. **Deployment**
   - [APISIX Integration](README_APISIX.md)
   - [APISIX Project Organization](APISIX_PROJECT_ORGANIZATION.md)
   - [Scalability & Resilience](SCALABILITY_RESILIENCE.md)

2. **Security**
   - [Security Design](SECURITY_DESIGN.md)
   - [JWT Integration](JWT_INTEGRATION.md)
   - [JWT Token Endpoint](JWT_TOKEN_ENDPOINT.md)

3. **Operations**
   - [APISIX Commands Reference](check_apisix_commands.md)
   - [Langfuse Integration Guide](APISIX_LANGFUSE_INTEGRATION.md)

### For Architects

1. **Architecture**
   - [Front Door Overview](FRONT_DOOR.md)
   - [Security Design](SECURITY_DESIGN.md)
   - [Scalability & Resilience](SCALABILITY_RESILIENCE.md)

2. **Integration**
   - [APISIX Integration](README_APISIX.md)
   - [JWT Integration](JWT_INTEGRATION.md)
   - [Langfuse Integration Guide](APISIX_LANGFUSE_INTEGRATION.md)

3. **Organization**
   - [APISIX Project Organization](APISIX_PROJECT_ORGANIZATION.md)
   - [Refactoring Summary](REFACTORING_SUMMARY.md)

## 🔧 Key Features

### APISIX Gateway
- ✅ Automatic route configuration from Control Tower manifests
- ✅ JWT authentication and authorization
- ✅ Rate limiting and throttling
- ✅ Load balancing across LLM services
- ✅ Request/response transformation
- ✅ CORS and security policies

### Langfuse Observability
- ✅ LLM request/response tracing
- ✅ Performance monitoring and analytics
- ✅ Cost tracking and optimization
- ✅ Debugging and error analysis
- ✅ Custom metadata and tagging
- ✅ Sampling and batching controls

### Security
- ✅ JWT token validation
- ✅ API key management
- ✅ Rate limiting per user/IP
- ✅ CORS configuration
- ✅ Request validation
- ✅ Audit logging

### Scalability
- ✅ Horizontal scaling
- ✅ Load balancing
- ✅ Health checks
- ✅ Circuit breakers
- ✅ Retry policies
- ✅ Connection pooling

## 📊 Architecture Overview

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│   DSP Front Door (FD2)          │
│   - FastAPI Application         │
│   - Module System               │
│   - Request Routing             │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│   APISIX Gateway                │
│   - JWT Authentication          │
│   - Rate Limiting               │
│   - Langfuse Tracing           │
│   - Load Balancing              │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│   LLM Services                  │
│   - OpenAI, Groq, etc.         │
│   - Custom Models               │
└─────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│   Observability                 │
│   - Langfuse (Traces)          │
│   - Prometheus (Metrics)        │
│   - Grafana (Dashboards)        │
└─────────────────────────────────┘
```

## 🔗 Related Projects

- **Control Tower**: Centralized configuration management
- **JWT Service**: Token generation and validation
- **APISIX**: API Gateway for routing and policies

## 📝 Contributing

When adding new documentation:

1. Place markdown files in the `docs/` directory
2. Update this README.md index
3. Use clear section headers and code examples
4. Include troubleshooting sections
5. Add links to related documentation

## 🆘 Support

- **Issues**: Check troubleshooting sections in relevant docs
- **Questions**: Review the documentation index above
- **Bugs**: Check APISIX logs and Langfuse dashboard

## 📄 License

[Your License Here]
