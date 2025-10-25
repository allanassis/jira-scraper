# Web Scraping Tutor Assignment

## Overview

You are tasked with developing a data scraping and transformation pipeline that extracts public issue data from Apache’s Jira instance and converts it into a format suitable for training Large Language Models (LLMs).
The goal of this assignment is to evaluate your ability to design an efficient, fault-tolerant, and scalable scraping system, handle real-world data inconsistencies, and transform unstructured data into a structured, high-quality dataset.

## Objective

### Build a system that:

- Scrapes issue data from Apache’s public Jira projects (choose any 3 projects).
- Handles network and data edge cases gracefully.
- Transforms the scraped data into a clean JSONL corpus suitable for LLM training.

### Requirements

1. Data Scraping

Implement a scraper that can:

- Fetch issues, comments, and metadata (status, priority, assignee, labels, timestamps, etc.) from Apache Jira.
- Handle pagination and rate limits.
- Resume from the last successful state if interrupted.

Include mechanisms to handle:

- Request failures, retries, and timeouts.
- HTTP 429 and 5xx responses.
- Empty or malformed data.

2. Data Transformation

- Convert the raw Jira data into a structured JSONL format.
- Each JSON object should contain:
- Issue metadata (title, status, project, reporter, etc.)
- Description and comments (as plain text)
- Derived tasks (e.g., summarization, classification, QnA)

3. Optimization and Reliability
   Implement strategies to improve efficiency.
   Demonstrate your approach to make the system fault-tolerant and recoverable.

4. Documentation
   Provide a comprehensive README that includes:

- Setup instructions and environment configuration.
- Architecture overview and design reasoning.
- Detailed explanation of edge cases handled.
- Optimization decisions and potential future improvements.

**Use only publicly available data from Apache Jira.**
**Respect the website’s rate limits.**
**We encourage you to be explorative and innovative on how you scrape data. There may be solutions outside HTML scraping as well for this.**
