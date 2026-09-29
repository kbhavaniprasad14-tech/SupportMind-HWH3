# Hindsight architecture

SupportMind uses Hindsight as the durable customer-memory layer. PostgreSQL stores operational data such as users, tickets, messages, and service metadata, while Hindsight stores the support memory that should persist across sessions and tickets.

## What Hindsight does
Hindsight is responsible for memory that helps the AI understand a customer's known environment, historical incidents, successful fixes, failed steps, and preferences. This memory is not decorative; it directly informs the next support response.

## Why it is necessary
The product's central premise is that a support agent should not force the customer to repeat prior troubleshooting. Hindsight gives the system a mechanism to recall relevant facts from earlier issues and apply them to the current request.

## Customer isolation
Each customer is mapped to a separate bank such as `customer:rahul-001`. The recall path always scopes queries to the current customer, so customer A cannot see customer B memory.

## Retain
Retain is used when the agent learns durable facts such as environment details, failed attempts, or successful resolutions.

## Recall
Recall is used before generating the response. The system builds a contextual query based on the current customer and ticket issue and retrieves the relevant memories from the customer-specific bank.

## Reflection
Reflection synthesizes multiple historical memories into a higher-level summary, allowing the agent to move beyond single facts and reason about the broader customer support history.

## Memory effects on the LLM
Retrieved memories are added to the agent context before a model call. The prompt instructs the agent to prefer current details, avoid repeating failed steps, and rely on previously successful solutions when they still apply.

## Memory evolution
Each new interaction can add new facts and update the durable account memory. Over time the AI becomes more specific and more useful to the customer.

## Failure handling
If Hindsight is unavailable, the system fails safely and continues with current ticket context. The app logs the failure and continues without crashing.
