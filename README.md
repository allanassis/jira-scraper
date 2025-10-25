# Jira Scraper for LLM Training Data

A robust, fault-tolerant web scraper that extracts issue data from Apache's public Jira instance and transforms it into high-quality training data for Large Language Models.

## Features

- **Fault-Tolerant Scraping**: Automatic retries, rate limiting, and graceful error handling
- **Resumable Operations**: State persistence allows resuming interrupted scraping sessions
- **Concurrent Processing**: Configurable concurrency with proper rate limiting
- **Data Transformation**: Converts raw Jira data into structured JSONL format for LLM training
- **Comprehensive Testing**: Full test suite with async support
- **Rich CLI Interface**: User-friendly command-line interface with progress indicators

## Architecture

### Core Components

1. **JiraScraper** (`scraper.py`): Main scraping engine with fault tolerance
2. **DataTransformer** (`transformer.py`): Converts raw data to LLM training format
3. **Models** (`models.py`): Pydantic models for type safety and validation
4. **CLI** (`cli.py`): Command-line interface with rich output

### Design Principles

- **Fault Tolerance**: Exponential backoff retries, rate limit handling, malformed data recovery
- **Performance**: Async/await concurrency, connection pooling, efficient pagination
- **Extensibility**: Modular design, configurable parameters, pluggable transformations
- **Observability**: Comprehensive logging, progress tracking, detailed statistics

## Installation

### Prerequisites

- Python 3.9+
- pip or poetry

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd scraping-tutor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Install development dependencies (optional)
pip install -e ".[dev]"
```

## Usage

### Basic Usage

```bash
# Scrape default projects (KAFKA, SPARK, HADOOP)
jira-scraper

# Scrape specific projects
jira-scraper -p KAFKA -p SPARK -p FLINK

# Custom output directory
jira-scraper -o /path/to/output

# Resume interrupted session
jira-scraper --resume
```

### Advanced Configuration

```bash
# High-performance scraping
jira-scraper -c 10 -r 0.5  # 10 concurrent requests, 0.5s rate limit

# Conservative scraping (respectful of server resources)
jira-scraper -c 2 -r 2.0   # 2 concurrent requests, 2s rate limit
```

### Output Files

- `training_data.jsonl`: LLM training data in JSONL format
- `raw_issues.json`: Raw Jira data for debugging/analysis
- `stats.json`: Scraping statistics and metadata
- `scraper_state.json`: State file for resumption

## Data Format

### Training Data Structure

Each line in `training_data.jsonl` contains:

```json
{
  "issue_key": "KAFKA-12345",
  "project": "KAFKA",
  "metadata": {
    "summary": "Issue title",
    "status": "Resolved",
    "priority": "Major",
    "assignee": "John Doe",
    "reporter": "Jane Smith",
    "created": "2023-01-01T00:00:00Z",
    "labels": ["bug", "performance"],
    "components": ["core", "streams"]
  },
  "text_content": "Description: ...\n\nComment by user: ...",
  "tasks": {
    "summarization": {
      "input": "full issue text",
      "target": "issue summary"
    },
    "classification": {
      "input": "full issue text", 
      "target": {"status": "Resolved", "priority": "Major"}
    },
    "qa": {
      "context": "full issue text",
      "questions": ["What is the status?", "Who reported this?"]
    }
  }
}
```

## Edge Cases Handled

### Network Issues
- **HTTP 429 (Rate Limited)**: Exponential backoff with jitter
- **5xx Server Errors**: Automatic retries with increasing delays
- **Timeouts**: Configurable timeout with retry logic
- **Connection Failures**: Graceful degradation and resumption

### Data Issues
- **Malformed JSON**: Skip corrupted records, continue processing
- **Missing Fields**: Default values and optional field handling
- **Empty Content**: Filter out issues without meaningful content
- **Encoding Issues**: Proper UTF-8 handling for international content

### Operational Issues
- **Interruption Recovery**: State persistence for resumable operations
- **Memory Management**: Streaming processing for large datasets
- **Disk Space**: Incremental file writing with error handling

## Performance Optimizations

### Concurrency
- Async/await for I/O-bound operations
- Semaphore-based concurrency limiting
- Connection pooling with httpx

### Rate Limiting
- Configurable delays between requests
- Adaptive rate limiting based on server responses
- Respectful default settings (1 req/sec)

### Memory Efficiency
- Streaming JSONL output (no full dataset in memory)
- Generator-based issue processing
- Efficient data structures with Pydantic

### Resumption
- Persistent state tracking
- Skip already processed issues
- Incremental progress saving

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jira_scraper

# Run specific test file
pytest tests/test_scraper.py

# Run with verbose output
pytest -v
```

### Test Coverage

- **Unit Tests**: All core components with mocking
- **Integration Tests**: End-to-end scraping workflows
- **Error Handling**: Network failures, malformed data
- **State Management**: Persistence and resumption logic

## Configuration

### Environment Variables

```bash
export JIRA_RATE_LIMIT=1.0      # Rate limit in seconds
export JIRA_MAX_CONCURRENT=5    # Max concurrent requests
export JIRA_TIMEOUT=30          # Request timeout in seconds
```

### Project Selection

Default projects are chosen for diversity:
- **KAFKA**: High-volume messaging system
- **SPARK**: Big data processing engine  
- **HADOOP**: Distributed computing framework

These provide varied issue types, discussion patterns, and technical domains.

## Future Improvements

### Scalability
- Distributed scraping across multiple workers
- Database backend for large-scale state management
- Cloud storage integration for output data

### Data Quality
- Advanced text preprocessing and cleaning
- Duplicate detection and deduplication
- Content quality scoring and filtering

### Monitoring
- Prometheus metrics integration
- Real-time progress dashboards
- Alert system for scraping failures

### API Enhancements
- GraphQL support for more efficient queries
- Webhook integration for real-time updates
- Custom field extraction and transformation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Troubleshooting

### Common Issues

**Rate Limiting**: Increase `--rate-limit` value or decrease `--max-concurrent`

**Memory Issues**: Process projects individually or reduce concurrency

**Network Timeouts**: Check internet connection and increase timeout values

**Permission Errors**: Ensure write access to output directory

### Debug Mode

```bash
# Enable verbose logging
export PYTHONPATH=.
python -m jira_scraper.cli --help
```

### Support

For issues and questions, please check the existing issues or create a new one with:
- Python version
- Command used
- Error message
- Expected vs actual behavior
