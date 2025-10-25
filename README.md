# Jira Scraper for LLM Training Data

A robust, fault-tolerant web scraper that extracts issue data from Apache's public Jira instance and transforms it into high-quality training data for Large Language Models.

## Requirements

- **Python 3.9+**
- Internet connection for API access

## Setup Instructions

### Installation

```bash
# Clone the repository
$ git clone <repository-url> scraping-tutor
$ cd scraping-tutor

# Create virtual environment and install dependencies
$ make install

# Switch to the created env on your terminal
$ source jira_scraper_env/bin/activate
```

## Usage

### Basic Commands

```bash
# Scrape default projects (KAFKA, SPARK, HADOOP)
jira-scraper

# Scrape specific projects
jira-scraper -p KAFKA -p SPARK

# Custom output directory
jira-scraper -o /path/to/output

# Limit issues for testing
jira-scraper --limit 10

# Resume interrupted session
jira-scraper --resume
```

### CLI Options

```
Options:
  -p, --projects TEXT        Jira projects to scrape (default: KAFKA, SPARK, HADOOP)
  -o, --output-dir PATH      Output directory for scraped data (default: output)
  -c, --max-concurrent INT   Maximum concurrent requests (default: 5)
  -r, --rate-limit FLOAT     Rate limit delay in seconds (default: 1.0)
  -l, --limit INT           Limit number of issues per project (for testing)
  --resume                  Resume from previous scraping session
  --help                    Show this message and exit
```

### Performance Tuning

```bash
# High-performance scraping
jira-scraper -c 10 -r 0.5  # 10 concurrent requests, 0.5s rate limit

# Conservative scraping (respectful of server resources)
jira-scraper -c 2 -r 2.0   # 2 concurrent requests, 2s rate limit

# Quick test with limited data
jira-scraper -p KAFKA --limit 5 -r 2.0
```

## Architecture Overview

### Design Philosophy

The scraper follows a **modular, async-first architecture** designed for:

- **Fault tolerance**: Graceful handling of network failures and malformed data
- **Performance**: Concurrent processing with respectful rate limiting
- **Maintainability**: Clear separation of concerns and unified data models
- **Extensibility**: Pluggable components for future enhancements

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │───▶│   JiraScraper    │───▶│ DataTransformer │
│   (cli.py)      │    │   (scraper.py)   │    │ (transformer.py)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ JiraHttpClient   │───▶│ Pydantic Models │
                       │ (http_client.py) │    │ (models.py)     │
                       └──────────────────┘    └─────────────────┘
```

#### 1. **JiraScraper** (`scraper.py`)

- **Purpose**: Orchestrates the scraping workflow
- **Responsibilities**: Project iteration, state management, concurrent processing
- **Key Features**: Resumable operations, progress tracking, error aggregation

#### 2. **JiraHttpClient** (`http_client.py`)

- **Purpose**: Handles all HTTP communication with Jira API
- **Responsibilities**: Rate limiting, retries, pagination, connection pooling
- **Key Features**: Exponential backoff, automatic pagination

#### 3. **Pydantic Models** (`models.py`)

- **Purpose**: Unified data validation and serialization
- **Responsibilities**: API response parsing, data validation
- **Key Features**: Graceful None handling, validation decorators

#### 4. **DataTransformer** (`transformer.py`)

- **Purpose**: Converts raw Jira data to LLM training format
- **Responsibilities**: JSONL generation, statistics calculation, file management
- **Key Features**: Streaming output, memory efficiency, structured training tasks

#### 5. **CLI Interface** (`cli.py`)

- **Purpose**: User-friendly command-line interface
- **Responsibilities**: Argument parsing, progress display, error reporting
- **Key Features**: Rich terminal output, configuration validation, help system

### Design Reasoning

#### **Async/Await Architecture**

- **Why**: I/O-bound operations benefit significantly from concurrency
- **Implementation**: All HTTP requests and file operations use async/await
- **Benefit**: Non blocking requests

#### **Decoupled HTTP Client**

- **Why**: Separates network concerns from business logic
- **Implementation**: Dedicated JiraHttpClient with built-in resilience
- **Benefit**: Easier testing, reusable across components, centralized retry logic

#### **State Persistence**

- **Why**: Long-running scrapes need resumption capability
- **Implementation**: JSON state file tracking processed issues
- **Benefit**: Fault tolerance, cost efficiency, user experience

## Edge Cases Handled

### Network Resilience

#### **HTTP 429 (Rate Limited)**

```python
# Exponential backoff with jitter
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60) + wait_random(0, 1)
)
```

- **Detection**: HTTP 429 status code or rate limit headers
- **Response**: Exponential backoff with randomized jitter
- **Fallback**: Automatic rate limit adjustment

#### **5xx Server Errors**

- **Detection**: HTTP 500-599 status codes
- **Response**: Retry with increasing delays (1s, 2s, 4s, 8s, 16s)
- **Fallback**: Skip problematic issues after max retries

#### **Connection Failures**

- **Detection**: Network timeouts, DNS failures, connection refused
- **Fallback**: Graceful degradation with state preservation

### Data Quality Issues

#### **Malformed JSON Responses**

```python
try:
    issue = JiraIssue.from_api_response(data)
except ValidationError as e:
    logger.warning(f"Skipping malformed issue {issue_key}: {e}")
    continue
```

- **Detection**: JSON parsing errors, schema validation failures, extensible
- **Response**: Log warning, skip corrupted record, continue processing
- **Preservation**: Raw data saved for manual inspection

#### **Missing Required Fields**

```python
@field_validator("key")
@classmethod
def validate_key(cls, v):
    if not v:
        raise ValueError("Key is required")
    return v
```

- **Detection**: Pydantic validation with custom validators
- **Response**: Provide sensible defaults or raise validation errors
- **Handling**: Graceful None handling in from_api_response methods

### Operational Resilience

#### **Interruption Recovery**

```python
def save_state(self) -> None:
    """Save scraper state to disk."""
    state = {"processed_issues": list(self.processed_issues)}
    with open(self.state_file, "w") as f:
        json.dump(state, f)
```

- **Trigger**: SIGINT, SIGTERM, unexpected crashes
- **Mechanism**: Persistent state file with processed issue tracking
- **Recovery**: Automatic resumption with `--resume` flag

#### **Memory Management**

- **Issue**: Large datasets exceeding available memory
- **Solution**: Streaming JSONL output, generator-based processing
- **Monitoring**: Progress tracking without full dataset in memory

#### **Disk Space Exhaustion**

- **Detection**: OSError on file write operations
- **Response**: Graceful error handling with user notification
- **Prevention**: Incremental file writing, size estimation

## Optimization Decisions

### Performance Optimizations

#### **Concurrent Processing**

```python
semaphore = asyncio.Semaphore(self.max_concurrent)
tasks = [fetch_issue(key) for key in issue_keys]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

- **Decision**: Semaphore-controlled concurrency vs thread pools
- **Reasoning**: Better resource control, async-native, lower overhead
- **Impact**: 5-10x performance improvement with configurable limits

#### **Connection Pooling**

```python
self.client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    timeout=httpx.Timeout(30.0)
)
```

- **Decision**: httpx connection pooling vs requests
- **Reasoning**: Async support, HTTP/2, better connection reuse
- **Impact**: Reduced connection overhead, improved throughput

#### **Streaming Output**

```python
async with aiofiles.open(self.training_file, "w") as f:
    for record in training_records:
        await f.write(f"{record.model_dump_json()}\n")
```

- **Decision**: Streaming JSONL vs in-memory collection
- **Reasoning**: Constant memory usage, early output availability
- **Impact**: Handles datasets larger than available memory

### Memory Optimizations

#### **Generator-Based Processing**

```python
async def get_project_issues(self, project: str) -> AsyncGenerator[str, None]:
    async for issue in self.client.search_issues(project, fields="key"):
        yield issue["key"]
```

- **Decision**: Generators vs list collection
- **Reasoning**: Lazy evaluation, constant memory usage
- **Impact**: Memory usage independent of dataset size

#### **Efficient Data Structures**

- **Decision**: Pydantic models vs dictionaries
- **Reasoning**: Type safety, validation, serialization efficiency
- **Trade-off**: Slight memory overhead for significant safety gains

### Reliability Optimizations

#### **Exponential Backoff with Jitter**

```python
wait=wait_exponential(multiplier=1, min=4, max=60) + wait_random(0, 1)
```

- **Decision**: Exponential backoff vs fixed delays
- **Reasoning**: Reduces server load, handles temporary failures
- **Enhancement**: Jitter prevents thundering herd problems

#### **Circuit Breaker Pattern**

- **Decision**: Fail-fast vs continuous retries
- **Reasoning**: Prevents cascade failures, faster error detection
- **Implementation**: Built into httpx client with timeout handling

## Testing Strategy

### Test Coverage

```bash
# Run all tests
pytest

# Run with coverage
make test-cov

# Run E2E test (uses real API)
make e2e-test

# Run integration tests with mocks
makte unit-test
```

#### **Unit Tests** (85% coverage)

- All core components with comprehensive mocking
- Edge case validation and error handling
- Pydantic model validation scenarios

#### **E2E Tests**

- Real API calls with limited scope (--limit parameter)
- Complete workflow validation
- Output file verification

## Output Files

- `training_data.jsonl`: LLM training data in JSONL format
- `raw_issues.json`: Raw Jira data for debugging/analysis
- `stats.json`: Scraping statistics and metadata
- `scraper_state.json`: State file for resumption

## Data Format

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
      "target": { "status": "Resolved", "priority": "Major" }
    },
    "qa": {
      "context": "full issue text",
      "questions": ["What is the status?", "Who reported this?"]
    }
  }
}
```

## Future Improvements

### Improve Jira Integration

- Migrate from V2 API to V3, I only realized that the V2 was deprecated when the project timeline was close to the end.

The [Jira API V2](https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-search/#api-rest-api-2-search-get) is deprecated and we should move to [Jira API V3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/#api-rest-api-3-search-jql-get)

- Add autentication to the API call

#### API V2 is deprecated

### Scalability Enhancements

#### **Distributed Scraping**

- **Current**: Single-process scraping
- **Future**: Multi-worker distributed architecture
- **Benefits**: Horizontal scaling, fault isolation
- **Implementation**: Message queue coordination, shared state store

#### **Database Backend**

```python
# Future: Replace JSON state with database
class DatabaseStateManager:
    async def mark_processed(self, issue_key: str) -> None:
        await self.db.execute("INSERT INTO processed_issues (key) VALUES (?)", issue_key)
```

- **Current**: JSON file state management
- **Future**: PostgreSQL/SQLite for large-scale state
- **Benefits**: ACID properties, concurrent access, query capabilities

#### **Cloud Storage Integration**

- **Current**: Local file output
- **Future**: S3/GCS direct upload with streaming
- **Benefits**: Unlimited storage, built-in redundancy, cost efficiency

### Data Quality Improvements

#### **Advanced Text Processing**

```python
# Future: Enhanced text cleaning pipeline
class TextProcessor:
    def clean_content(self, text: str) -> str:
        # normalize whitespace, handle encoding
        # Extract code blocks, filter spam content
        # Standardize formatting for better LLM training
```

- **Current**: Basic text extraction
- **Future**: NLP-based content cleaning and enhancement
- **Benefits**: Higher quality training data, better model performance

#### **Duplicate Detection**

- **Current**: No deduplication
- **Future**: Content-based similarity detection
- **Implementation**: MinHash, LSH, or embedding-based clustering
- **Benefits**: Reduced dataset size, improved training efficiency

#### **Content Quality Scoring**

```python
class QualityScorer:
    def score_issue(self, issue: JiraIssue) -> float:
        # Length, complexity, engagement metrics
        # Technical depth, resolution quality
        # Community interaction patterns
```

- **Current**: All issues included
- **Future**: ML-based quality assessment
- **Benefits**: Focus on high-value training examples

### Monitoring and Observability

#### **Prometheus Metrics**

```python
# Future: Comprehensive metrics collection
SCRAPING_DURATION = Histogram('jira_scraping_duration_seconds')
ISSUES_PROCESSED = Counter('jira_issues_processed_total')
ERROR_RATE = Gauge('jira_error_rate')
```

- **Current**: Basic console logging
- **Future**: Full observability stack
- **Benefits**: Performance monitoring, alerting, capacity planning

#### **Real-time Dashboards**

- **Current**: Post-completion statistics
- **Future**: Live progress visualization
- **Implementation**: Grafana dashboards, WebSocket updates
- **Benefits**: Operational visibility, proactive issue detection

### API Enhancements

#### **Custom Field Extraction**

```python
# Future: Configurable field mapping
class FieldExtractor:
    def __init__(self, field_config: Dict[str, str]):
        self.field_mapping = field_config

    def extract_custom_fields(self, issue_data: Dict) -> Dict:
        # Dynamic field extraction based on configuration
```

- **Current**: Fixed field set
- **Future**: User-configurable field extraction
- **Benefits**: Adaptability to different Jira instances, custom workflows

## Troubleshooting

### Common Issues

**Rate Limiting**: Increase `--rate-limit` value or decrease `--max-concurrent`

**Memory Issues**: Process projects individually or reduce concurrency

**Network Timeouts**: Check internet connection and increase timeout values

**Permission Errors**: Ensure write access to output directory

### Debug Mode

```bash
# Enable verbose logging
python -m jira_scraper.cli --help
```

## License

MIT License - see LICENSE file for details.
