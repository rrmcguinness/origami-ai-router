# Gemini 3.5 Flash Assessment Report

## Overview

This report evaluates the zero-shot routing accuracy of Google's Gemini 3.5 Flash model within the stateless Origami AI Router ecosystem under async load testing (100 scenarios across 11 agents).

---

## Load Test Metrics

- **Total Requests**: 100
- **Successful Classifications**: 100
- **Failed Classifications**: 0
- **Load Generation Duration**: 61.67 seconds
- **Throughput (RPS)**: 1.62 RPS
- **Overall Accuracy**: **100%**

---

## Key Performance Insights

1. **Zero-Shot Context Accuracy**: Gemini parsed granular context across all 11 agents without requiring few-shot examples or prompt hacks.
2. **Stateful Fallback Compliance**: Consistently recognized out-of-bounds cart/list modification commands, delegating them cleanly to `fallback`.
3. **Network & Quota Stability**: Navigated concurrency boundaries efficiently using `asyncio.Semaphore` rate-limiting.

---

## Deployment Recommendation

Gemini 3.5 Flash serves as the **Primary Cloud Backend** across production deployments. Provisioned Throughput (PT) is recommended for high-volume enterprise production tiers (>120 RPS).
