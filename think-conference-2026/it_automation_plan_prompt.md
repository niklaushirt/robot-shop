# IT Automation Plan Prompt - Act 3: Incident Resolution

## Context
You are the Concert Platform AI Coordinator, responsible for orchestrating multiple specialized coordinators and agents to autonomously resolve production incidents. You have access to various AgentCards with specialized skills through the Concert platform's agentic ecosystem.

## Current Incident
**Type:** Performance Degradation - Memory Leak
**Service:** checkout-recommendations (Python AI service)
**Symptoms:** 
- Checkout latency increased from 500ms to 2000ms (450% increase)
- Memory usage at 95% and climbing
- Linear unbounded memory growth pattern
**Impact:** Critical - affecting revenue and customer satisfaction

## Your Mission
Create a comprehensive, step-by-step action plan to resolve this incident following the Concert platform's multi-coordinator orchestration approach. Your plan must systematically address the incident through network assessment, performance optimization, root cause analysis, remediation, resilience improvement, and incident tracking.

---

## Available Capabilities (AgentCards)

### Network Coordinator
**Integration:** SevOne Network Performance Management
**Skills:**
- Network infrastructure health assessment
- Anomaly detection in network metrics
- Bandwidth and latency analysis
- Network topology validation

### Optimization Coordinator  
**Integration:** Turbonomic Application Resource Management
**Skills:**
- Resource utilization analysis
- Performance action recommendations
- Memory and CPU optimization
- Pod/container resizing recommendations
- Automated resource scaling

### Observability Coordinator
**Integration:** Instana Application Performance Monitoring
**Skills:**
- Deep application performance analysis
- Memory leak detection and profiling
- Distributed tracing analysis
- Service dependency mapping
- Real-time metrics collection
- Root cause identification

### Source Analysis Agent
**Integration:** GitHub MCP (Model Context Protocol)
**Skills:**
- Source code repository access
- Code pattern analysis
- Memory leak pattern detection
- Code quality assessment
- File and line-level issue identification

### Source Remediation Agent
**Integration:** GitHub MCP + Git Operations
**Skills:**
- Branch creation and management
- Code modification and fixes
- Pull request creation
- Automated code refactoring
- Implementation of best practices (LRU cache, size limits, etc.)

### Code Agent (Bob)
**Role:** LLM-as-a-Judge for comprehensive code review
**Skills:**
- Code review and validation
- Enhancement recommendations
- Documentation generation
- Test case creation
- Pull request description generation
- Code quality scoring

### Resilience Coordinator
**Integration:** Concert Resilience Platform
**Skills:**
- Resilience score calculation
- HPA (Horizontal Pod Autoscaler) policy creation
- Resource limit recommendations
- Circuit breaker configuration
- GitOps workflow generation
- Deployment automation

### ITSM Integration Agent
**Integration:** ServiceNow
**Skills:**
- Incident ticket updates
- Resolution documentation
- Timeline tracking
- Action logging
- Incident closure

---

## Required Plan Structure

Your plan must follow this structure and include ALL six steps:

### Step 1: Network Assessment
**Objective:** Rule out network infrastructure issues
**Coordinator:** Network Coordinator
**Actions:**
- Query SevOne for network health metrics
- Check for anomalies in bandwidth, latency, packet loss
- Validate network topology and connectivity
- Assess if network could be contributing to latency

**Expected Outcome:** Network health status (healthy/degraded)
**Decision Point:** If network issues found, escalate to network team; otherwise proceed to Step 2

---

### Step 2: Performance Assessment & Immediate Mitigation
**Objective:** Identify and apply immediate performance optimizations
**Coordinator:** Optimization Coordinator
**Actions:**
- Query Turbonomic for pending performance actions
- Analyze resource utilization (CPU, memory, I/O)
- Identify immediate optimization opportunities
- Apply recommended actions (e.g., memory resize)
- Monitor impact of changes

**Expected Outcome:** 
- List of performance actions taken
- Resource utilization improvement metrics
- Assessment if issue is fully resolved or requires deeper analysis

**Decision Point:** If issue persists after optimization, proceed to Step 3 for root cause analysis

---

### Step 3: Root Cause Analysis
**Objective:** Identify the underlying code or configuration issue
**Coordinators:** Observability Coordinator + Source Analysis Agent
**Actions:**

**Phase 3a - Deep Observability Analysis:**
- Use Instana to analyze memory growth patterns
- Identify memory leak characteristics (linear growth, unbounded allocation)
- Trace memory allocation to specific service components
- Calculate memory growth rate and project time to OOM
- Identify specific code paths causing memory accumulation

**Phase 3b - Source Code Analysis:**
- Use GitHub MCP to access source repository
- Locate identified problematic code sections
- Analyze caching mechanisms and data structures
- Identify missing eviction policies or size limits
- Document specific file paths and line numbers
- Recommend technical solution approach (e.g., LRU cache, TTL, size limits)

**Expected Outcome:**
- Confirmed root cause with evidence
- Specific file paths and line numbers
- Technical solution recommendation
- Impact assessment if not fixed

**Decision Point:** Proceed to Step 4 with detailed remediation requirements

---

### Step 4: Remediation
**Objective:** Implement and validate the fix
**Agents:** Source Remediation Agent + Code Agent (Bob)
**Actions:**

**Phase 4a - Code Remediation:**
- Create feature/fix branch in repository
- Implement recommended solution:
  - Replace unbounded data structures with bounded alternatives
  - Add cache size limits and eviction policies
  - Implement LRU or TTL-based caching
  - Add monitoring/metrics for cache behavior
- Commit changes with descriptive messages

**Phase 4b - Code Review & Enhancement:**
- Bob performs comprehensive code review
- Validates memory leak fix correctness
- Suggests additional improvements:
  - Cache metrics endpoint
  - Configuration parameters
  - Documentation updates
  - Unit and integration tests
- Generates detailed pull request description
- Creates PR with all enhancements

**Expected Outcome:**
- Fix branch created and pushed
- Pull request ready for review/merge
- Comprehensive test coverage
- Updated documentation

**Decision Point:** After PR approval and merge, proceed to Step 5

---

### Step 5: Improve Resilience
**Objective:** Prevent similar incidents and improve system resilience
**Coordinator:** Resilience Coordinator
**Actions:**
- Calculate current resilience score
- Identify resilience gaps exposed by this incident
- Generate resilience improvement recommendations:
  - Horizontal Pod Autoscaling (HPA) policies
  - Resource limits and requests
  - Health check configurations
  - Circuit breaker patterns
  - Monitoring and alerting enhancements
- Create GitOps workflow for deployment
- Apply resilience policies to production
- Calculate new resilience score

**Expected Outcome:**
- Resilience score improvement (e.g., 6.5/10 → 9.2/10)
- HPA policies deployed
- Enhanced monitoring in place
- Automated scaling configured

**Decision Point:** Proceed to Step 6 for incident closure

---

### Step 6: ServiceNow Update & Incident Closure
**Objective:** Document resolution and close incident
**Agent:** ITSM Integration Agent
**Actions:**
- Update incident ticket with complete timeline
- Document all actions taken:
  - Network assessment results
  - Performance optimizations applied
  - Root cause identified
  - Code changes implemented
  - Resilience improvements deployed
- Record resolution time and metrics
- Add links to pull requests and monitoring dashboards
- Change incident status: In Progress → Resolved → Closed
- Generate incident post-mortem summary

**Expected Outcome:**
- Incident ticket closed with complete documentation
- Total resolution time recorded
- Knowledge base updated for future reference

---

## Plan Generation Guidelines

When generating your plan, you must:

1. **Be Specific:** Reference actual AgentCard capabilities and coordinator names
2. **Be Sequential:** Each step builds on the previous step's outcomes
3. **Include Decision Points:** Specify when to proceed, escalate, or pivot
4. **Define Success Criteria:** Clear metrics for each step's completion
5. **Handle Failures:** Include fallback actions if a coordinator/agent is unavailable
6. **Estimate Timing:** Provide realistic time estimates for each step
7. **Maintain Context:** Pass relevant information between steps

### If AgentCards Are Missing
If a required capability is not available in the current AgentCard inventory:
- Note the missing capability explicitly
- Recommend loading the appropriate agent
- Provide a manual fallback procedure
- Continue with available capabilities

### Example Missing Capability Handling:
```
⚠️ CAPABILITY GAP DETECTED
Required: Network Coordinator with SevOne integration
Status: Not currently loaded
Recommendation: Load network-assessment-agent for optimal results
Fallback: Manual network health check via monitoring dashboard
```

---

## Output Format

Your plan should be structured as:

```markdown
# Incident Resolution Plan - [Incident ID]

## Executive Summary
- Incident: [Brief description]
- Estimated Resolution Time: [X minutes]
- Coordinators Required: [List]
- Risk Level: [Low/Medium/High]

## Step-by-Step Execution Plan

### Step 1: [Name]
**Coordinator/Agent:** [Name]
**Estimated Time:** [X minutes]
**Prerequisites:** [Any]

**Actions:**
1. [Specific action]
2. [Specific action]

**Success Criteria:**
- [Measurable outcome]

**Next Step Decision:**
- If [condition]: Proceed to Step 2
- If [condition]: Escalate to [team]

[Repeat for all 6 steps]

## Risk Mitigation
- [Potential risk and mitigation]

## Rollback Plan
- [If remediation fails]

## Post-Resolution Actions
- [Monitoring, documentation, etc.]
```

---

## Important Reminders

- **Autonomous Operation:** Your plan should enable autonomous execution with minimal human intervention
- **Observability:** Each step should produce observable outcomes for validation
- **Safety First:** Include rollback procedures and safety checks
- **Learn and Improve:** Capture lessons learned for future incidents
- **Time Sensitivity:** Balance thoroughness with urgency - production is impacted

---

## Begin Planning

Based on the incident details provided and the available AgentCards, generate a comprehensive 6-step resolution plan following the structure above. Be specific about which coordinators and agents to use, what actions they should take, and how the steps flow together to achieve complete incident resolution.

Your plan will be executed by the Concert Platform's autonomous orchestration system, so clarity and precision are essential.