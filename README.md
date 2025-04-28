# best_practice_database
Companion sample code for this article:
https://medium.com/@andrea.mariotti/best-practice-how-to-give-ai-agents-database-access-for-production-deployments-1c0f42766509

Summary:
Mariotti highlights the inherent risks of granting AI agents direct SQL access to databases, particularly when sensitive data is involved. He underscores that large language models (LLMs) are probabilistic systems prone to errors, including hallucinations—instances where the model generates incorrect or misleading information. In high-stakes applications like healthcare, these errors can lead to significant compliance and security issues.

To mitigate these risks, the article advocates for a design pattern where user role validation is enforced outside the LLM. By wrapping database access in a secure tool that checks user permissions before executing queries, developers can ensure that only authorized users can access sensitive data, regardless of the LLM’s output.

