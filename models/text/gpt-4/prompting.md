# GPT-4 Prompting Best Practices

## Overview
GPT-4 responds best to clear, structured prompts with explicit instructions and context.

## Prompt Structure

### Basic Structure
```
[System Message/Role Definition]
[Context/Background Information]
[Specific Task/Question]
[Output Format Requirements]
[Constraints/Guidelines]
```

### Effective Patterns

#### 1. Role-Based Prompting
```
You are an expert [role] with deep knowledge in [domain].
Your task is to [specific action].
```

#### 2. Step-by-Step Instructions
```
Please follow these steps:
1. First, analyze...
2. Then, identify...
3. Finally, provide...
```

#### 3. Few-Shot Examples
```
Here are examples of the desired output:
Example 1: [input] -> [output]
Example 2: [input] -> [output]

Now process: [actual input]
```

## Key Tips

1. **Be Specific**: Vague instructions lead to inconsistent results
2. **Use Delimiters**: Separate sections with clear markers (###, ---, etc.)
3. **Specify Output Format**: JSON, markdown, bullet points, etc.
4. **Include Constraints**: Word limits, tone, style requirements
5. **Iterative Refinement**: Start simple, add complexity as needed

## Advanced Techniques

### Chain-of-Thought (CoT)
```
Let's approach this step-by-step:
1. First, let me understand...
2. Now I'll analyze...
3. Based on this analysis...
```

### Self-Consistency
Ask the model to verify its own output:
```
Please double-check your response for accuracy and completeness.
```

### Temperature Control Context
- Lower temperature (0.0-0.3): Factual, consistent responses
- Medium temperature (0.4-0.7): Balanced creativity
- Higher temperature (0.8-1.0): Creative, varied outputs