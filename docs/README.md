# Documentation Index

Welcome to the Luminate Cookbook documentation. This directory contains all technical documentation, user guides, and deployment instructions.

## Quick Start

- **New to the project?** Start with the [main README](../README.md)
- **Deploying?** See [Deployment Guide](DEPLOYMENT.md) or [Google Cloud Run Setup](GOOGLE_CLOUD_RUN.md)
- **Having issues?** Check [Troubleshooting](TROUBLESHOOTING.md)

## Documentation Structure

### User Guides

**[Banner Processor User Guide](BANNER_PROCESSOR_USER_GUIDE.md)**
- How to use the Banner Processor tool
- Two-workflow options: Preview & Adjust vs Auto-Process
- Tips for best results with different photo types
- Settings explained (padding, quality, retina)
- Common scenarios and examples

### Technical Documentation

**[Architecture](ARCHITECTURE.md)**
- Overall system design and philosophy
- Tech stack rationale
- 2FA flow explanation (the critical innovation)
- Browser automation strategy
- Performance considerations

**[Banner Processor Technical](BANNER_PROCESSOR_TECHNICAL.md)**
- MediaPipe person detection implementation
- Smart crop algorithm details
- API endpoints and data models
- Testing results and deployment notes
- Troubleshooting specific to banner processor

**[Deployment Guide](DEPLOYMENT.md)**
- Local development setup
- Docker deployment
- Google Cloud Run deployment
- Environment variables and configuration

**[Google Cloud Run Setup](GOOGLE_CLOUD_RUN.md)**
- Cloud Run specific instructions
- IAM permissions required
- Cloud Build integration
- Monitoring and logging

**[Troubleshooting](TROUBLESHOOTING.md)**
- Common issues and solutions
- Browser session problems
- Upload failures
- Performance issues
- Cloud Run specific troubleshooting

## Sample Files

The `samples/` directory contains:
- Example PDFs showing banner options
- Sample HTML files for testing

## Documentation Conventions

### For Users
User-facing documentation focuses on:
- What the tool does (features)
- How to use it (step-by-step)
- Tips and best practices
- Common scenarios

### For Developers
Technical documentation focuses on:
- Why design decisions were made
- How systems work internally
- API contracts and data models
- Testing and deployment procedures

## Need Help?

1. **Check the docs** - Most questions are answered here
2. **Review troubleshooting** - Common issues have known solutions
3. **Check server logs** - Cloud Run provides excellent logging
4. **Review the code** - Code is well-commented with rationale

## Contributing to Documentation

When adding features:
1. Update relevant user guides
2. Add technical documentation for complex features
3. Update API endpoint documentation in README
4. Add troubleshooting entries for known issues
5. Update CHANGELOG.md

Keep documentation:
- **Concise** - Users don't read walls of text
- **Practical** - Include examples and code snippets
- **Current** - Remove outdated information
- **Organized** - Related information should be together
